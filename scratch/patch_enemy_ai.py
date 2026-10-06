with open("src/entities/enemy.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add NeuralTacticalAI import
if "from engine.v3.ai.neural_ai import NeuralTacticalAI" not in content:
    content = content.replace(
        "from engine.animation import AnimationManager, load_animation_folder",
        "from engine.animation import AnimationManager, load_animation_folder\nfrom engine.v3.ai.neural_ai import NeuralTacticalAI"
    )

# 2. Update Enemy base class
old_enemy_init = '''        self.anim_manager = AnimationManager()
        self.state = "IDLE"
        self.slow_timer = 0.0
        self.slow_factor = 1.0
        self.burn_timer = 0.0
        self.burn_dps = 3.0
        self.burn_tick = 0.0'''

new_enemy_init = '''        self.anim_manager = AnimationManager()
        self.state = "IDLE"
        self.slow_timer = 0.0
        self.slow_factor = 1.0
        self.burn_timer = 0.0
        self.burn_dps = 3.0
        self.burn_tick = 0.0
        self.is_guarding = False
        self.guard_timer = 0.0
        self.is_dodging = False
        self.dodge_timer = 0.0
        self._guard_sparks: list[_Particle] = []'''

content = content.replace(old_enemy_init, new_enemy_init)

old_take_damage = '''    def take_damage(self, amount: int):
        if self.is_dead:
            return
        
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.die()
        else:
            self.change_state("HURT")'''

new_take_damage = '''    def take_damage(self, amount: int, hit_direction: int = 0):
        if self.is_dead:
            return
            
        if self.is_dodging:
            return # Dodged evasively!
            
        if self.is_guarding:
            is_frontal = (hit_direction == 0) or (hit_direction > 0 and not self.facing_right) or (hit_direction < 0 and self.facing_right)
            if is_frontal:
                amount = max(1, int(amount * 0.25)) # Guard absorbs 75%
                sx = self.rect.right if self.facing_right else self.rect.left
                sy = self.rect.centery
                for _ in range(6):
                    self._guard_sparks.append(_Particle(sx, sy, random.uniform(-50, 50), random.uniform(-80, 10), 0.22, (255, 215, 80), radius=2.5, gravity=180))
            else:
                self.is_guarding = False # Flanked!
        
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.die()
        else:
            self.change_state("HURT")'''

content = content.replace(old_take_damage, new_take_damage)

# Update _apply_physics in Enemy
old_apply_phys = '''        if self.slow_timer > 0:
            self.slow_timer -= dt
            effective_dt = dt * self.slow_factor
        else:
            effective_dt = dt'''

new_apply_phys = '''        if self.slow_timer > 0:
            self.slow_timer -= dt
            effective_dt = dt * self.slow_factor
        else:
            effective_dt = dt
            
        if self.dodge_timer > 0:
            self.dodge_timer -= effective_dt
            if self.dodge_timer <= 0:
                self.is_dodging = False
        if self.guard_timer > 0:
            self.guard_timer -= effective_dt
            if self.guard_timer <= 0:
                self.is_guarding = False
        self._guard_sparks = [p for p in self._guard_sparks if p.update(effective_dt)]'''

content = content.replace(old_apply_phys, new_apply_phys)

# Update Enemy.draw to render guard shield
old_enemy_draw = '''        else:
            surface.blit(img, (draw_x, draw_y))'''

new_enemy_draw = '''        else:
            surface.blit(img, (draw_x, draw_y))
            
        # Draw Guard Shield if active
        if self.is_guarding and not self.is_dead:
            bx = (self.rect.right - camera_offset.x + 2) if self.facing_right else (self.rect.left - camera_offset.x - 10)
            by = self.rect.centery - camera_offset.y - 16
            bs = pygame.Surface((8, 32), pygame.SRCALPHA)
            pygame.draw.rect(bs, (240, 230, 200, 220), (0, 0, 8, 32), border_radius=3)
            pygame.draw.rect(bs, (255, 215, 80), (0, 0, 8, 32), 1, border_radius=3)
            surface.blit(bs, (bx, by))
            
        for spk in self._guard_sparks:
            spk.draw(surface, camera_offset.x, camera_offset.y)'''

content = content.replace(old_enemy_draw, new_enemy_draw, 1)

# 3. Update Skeleton with Neural AI
old_skel_init = '''        self.attack_range = 65.0'''
new_skel_init = '''        self.attack_range = 65.0
        self.neural_ai = NeuralTacticalAI(entity_type="enemy", difficulty_scale=0.85)
        self.neural_eval_timer = random.uniform(0.0, 0.25)
        self.dodge_cooldown = 0.0'''

content = content.replace(old_skel_init, new_skel_init)

old_skel_update_chase = '''            elif self.state == "CHASE":
                if not player_in_range or player.invulnerable:
                    self.change_state("IDLE")
                elif abs_dist <= self.attack_range:
                    self.facing_right = dist_to_player > 0
                    self.change_state("ATTACK")
                else:
                    self.facing_right = dist_to_player > 0
                    self.velocity.x = self.chase_speed if self.facing_right else -self.chase_speed'''

new_skel_update_chase = '''            elif self.state == "CHASE":
                if self.dodge_cooldown > 0:
                    self.dodge_cooldown -= dt
                    
                # Neural Tactical Evaluation
                self.neural_eval_timer -= dt
                if self.neural_eval_timer <= 0:
                    self.neural_eval_timer = 0.25
                    proj_data = [{"pos": (p.rect.centerx, p.rect.centery), "vx": getattr(p, "velocity", pygame.math.Vector2(0,0)).x} for p in getattr(player, "projectiles", [])]
                    features = self.neural_ai.build_feature_vector(
                        self_pos=(self.rect.centerx, self.rect.bottom),
                        target_pos=(player.rect.centerx, player.rect.bottom),
                        target_vel=(player.velocity.x, player.velocity.y),
                        target_is_attacking=getattr(player, "is_attacking", False),
                        target_is_casting=getattr(player, "is_casting_aoe", False),
                        target_is_dashing=getattr(player, "is_dashing", False),
                        incoming_projectiles=proj_data,
                        self_cooldown=self.dodge_cooldown
                    )
                    act_name, _, _ = self.neural_ai.decide_action(features, temperature=0.6)
                    if act_name == "DODGE" and not self.is_dodging and self.dodge_cooldown <= 0:
                        self.is_dodging = True
                        self.dodge_timer = 0.26
                        self.dodge_cooldown = 2.0
                        dodge_dir = -1 if self.facing_right else 1
                        self.velocity.x = dodge_dir * 220.0
                        self.velocity.y = -90.0
                    elif act_name == "GUARD" and not self.is_guarding and not self.is_dodging:
                        self.is_guarding = True
                        self.guard_timer = 0.60
                        self.velocity.x = 0
                    elif act_name == "JUMP" and self.on_ground:
                        self.velocity.y = -350.0
                        self.on_ground = False

                if not player_in_range or player.invulnerable:
                    self.change_state("IDLE")
                elif abs_dist <= self.attack_range:
                    self.facing_right = dist_to_player > 0
                    self.change_state("ATTACK")
                else:
                    self.facing_right = dist_to_player > 0
                    if not self.is_guarding and not self.is_dodging:
                        self.velocity.x = self.chase_speed if self.facing_right else -self.chase_speed'''

content = content.replace(old_skel_update_chase, new_skel_update_chase)

# 4. Update WildBoar with jumping leap
old_boar_update = '''            elif self.state == "CHARGE":
                if not player_in_range:
                    self.change_state("IDLE")
                else:
                    self.patrol_dir = 1 if dist_to_player > 0 else -1
                    self.facing_right = self.patrol_dir > 0
                    self.velocity.x = self.charge_speed * self.patrol_dir'''

new_boar_update = '''            elif self.state == "CHARGE":
                if not player_in_range:
                    self.change_state("IDLE")
                else:
                    self.patrol_dir = 1 if dist_to_player > 0 else -1
                    self.facing_right = self.patrol_dir > 0
                    self.velocity.x = self.charge_speed * self.patrol_dir
                    # Charging leap over player slashes / traps
                    if self.on_ground and abs_dist < 140 and random.random() < 0.25:
                        self.velocity.y = -290.0
                        self.on_ground = False'''

content = content.replace(old_boar_update, new_boar_update)

with open("src/entities/enemy.py", "w", encoding="utf-8") as f:
    f.write(content)
print("src/entities/enemy.py patched with smart neural AI, jumping, dodging, and guarding!")
