"""
Ruin Engine V3.0 — Decoupled ECS Logic Systems.
Implements data-driven systems for Physics, Animation, AI, Combat, and Projectiles.
Includes a non-intrusive Bridge Adapter for backward compatibility with classic Entity classes.
"""

import math
from typing import TYPE_CHECKING
from engine.v3.ecs.components import (
    TransformComponent, PhysicsComponent, AnimationComponent,
    HealthComponent, ManaComponent, StaminaComponent,
    HitboxComponent, HurtboxComponent, ColliderComponent,
    ProjectileComponent, EnemyAIComponent, ParticleEmitterComponent,
    LightSourceComponent
)

if TYPE_CHECKING:
    from engine.v3.ecs.world import ECSWorld

class PhysicsSystem:
    """Updates motion vectors, applies acceleration, friction and gravity."""
    def update(self, world: 'ECSWorld', dt: float) -> None:
        for entity_id, transform, physics in world.query(TransformComponent, PhysicsComponent):
            # Apply acceleration and gravity
            physics.vx += physics.ax * dt
            if not physics.on_ground:
                physics.vy += physics.gravity * dt
            else:
                physics.vy += physics.ay * dt
                physics.vx *= (physics.friction ** (dt * 60.0))

            # Integrate position
            transform.x += physics.vx * dt
            transform.y += physics.vy * dt


class AnimationSystem:
    """Ticks frame timers and advances frame indices."""
    def update(self, world: 'ECSWorld', dt: float) -> None:
        for entity_id, anim in world.query(AnimationComponent):
            if anim.finished:
                continue
            anim.frame_time += dt
            if anim.frame_time >= anim.frame_duration:
                anim.frame_time -= anim.frame_duration
                anim.frame_index += 1


class ProjectileSystem:
    """Moves projectiles along direction vectors and culls expired projectiles."""
    def update(self, world: 'ECSWorld', dt: float) -> None:
        to_destroy = []
        for entity_id, transform, proj in world.query(TransformComponent, ProjectileComponent):
            step = proj.speed * dt
            transform.x += proj.direction_x * step
            transform.y += proj.direction_y * step
            proj.traveled += step
            proj.lifetime -= dt

            if proj.lifetime <= 0 or proj.traveled >= proj.max_range:
                to_destroy.append(entity_id)

        for eid in to_destroy:
            world.destroy_entity(eid)


class CombatHitboxSystem:
    """Evaluates collisions between active hitboxes and susceptible hurtboxes."""
    def update(self, world: 'ECSWorld', dt: float) -> None:
        # Collect active hitboxes
        hitboxes = []
        for eid, trans, hit in world.query(TransformComponent, HitboxComponent):
            if hit.active:
                rect = (trans.x + hit.offset_x, trans.y + hit.offset_y, hit.width, hit.height)
                hitboxes.append((eid, rect, hit))

        if not hitboxes:
            return

        # Query hurtboxes
        for hurt_eid, trans, hurt, health in world.query(TransformComponent, HurtboxComponent, HealthComponent):
            if hurt.is_invulnerable or health.invulnerable_timer > 0:
                health.invulnerable_timer = max(0.0, health.invulnerable_timer - dt)
                continue

            hurt_rect = (trans.x + hurt.offset_x, trans.y + hurt.offset_y, hurt.width, hurt.height)

            for hit_eid, hit_rect, hit in hitboxes:
                if hit_eid == hurt_eid:
                    continue  # Cannot hit oneself
                # AABB collision check
                if (hit_rect[0] < hurt_rect[0] + hurt_rect[2] and
                    hit_rect[0] + hit_rect[2] > hurt_rect[0] and
                    hit_rect[1] < hurt_rect[1] + hurt_rect[3] and
                    hit_rect[1] + hit_rect[3] > hurt_rect[1]):
                    # Deal damage
                    health.current_hp = max(0.0, health.current_hp - hit.damage)
                    health.invulnerable_timer = 0.25  # brief mercy invulnerability


class EnemyAISystem:
    """Drives patrol and target pursuit state transitions."""
    def update(self, world: 'ECSWorld', dt: float) -> None:
        for eid, trans, ai, phys in world.query(TransformComponent, EnemyAIComponent, PhysicsComponent):
            ai.current_cooldown = max(0.0, ai.current_cooldown - dt)

            if ai.state == "patrol":
                dist = trans.x - ai.patrol_origin_x
                if dist > ai.patrol_distance:
                    phys.vx = -60.0
                elif dist < -ai.patrol_distance:
                    phys.vx = 60.0
                elif abs(phys.vx) < 5.0:
                    phys.vx = 60.0


class ClassicEntityBridge:
    """
    Adapter that allows existing object-oriented entities (Player, Skeleton, Boss)
    to interface with ECS queries effortlessly without modifying their internal code.
    """
    @staticmethod
    def sync_to_ecs(entity: any, world: 'ECSWorld', entity_id: int) -> None:
        """Copies entity attributes into the ECS component database."""
        trans = world.get_component(entity_id, TransformComponent)
        if trans and hasattr(entity, "rect"):
            trans.x = entity.rect.x
            trans.y = entity.rect.y

        health = world.get_component(entity_id, HealthComponent)
        if health and hasattr(entity, "hp"):
            health.current_hp = float(entity.hp)

    @staticmethod
    def sync_from_ecs(entity: any, world: 'ECSWorld', entity_id: int) -> None:
        """Applies ECS updates back to the classic entity."""
        trans = world.get_component(entity_id, TransformComponent)
        if trans and hasattr(entity, "rect"):
            entity.rect.x = int(trans.x)
            entity.rect.y = int(trans.y)
