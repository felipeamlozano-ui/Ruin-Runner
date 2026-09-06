import pygame
import math
import random
import os

class _VFXParticle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "gravity", "shape")
    def __init__(self, x, y, vx, vy, life, color, size=3.0, gravity=0.0, shape="circle"):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity
        self.shape = shape
        
    def update(self, dt: float) -> bool:
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

class BaseUltimate:
    """Base class for character-specific Triple-AAA Ultimate visual effects."""
    def __init__(self):
        self.active = False
        self.timer = 0.0
        self.duration = 1.6
        self.cx = 0.0
        self.cy = 0.0
        self.facing_right = True
        self.damage_applied = False
        self.particles: list[_VFXParticle] = []
        
    def trigger(self, cx: float, cy: float, facing_right: bool):
        self.active = True
        self.timer = 0.0
        self.cx = cx
        self.cy = cy
        self.facing_right = facing_right
        self.damage_applied = False
        self.particles.clear()
        
    def update(self, dt: float, player, enemies=None, camera=None):
        if not self.active:
            return
            
        self.timer += dt
        
        # Keep player invulnerable and stationary during casting
        player.invulnerable = True
        player.invulnerability_timer = max(player.invulnerability_timer, 0.2)
        player.velocity.x = 0
        
        # Update particles
        self.particles = [p for p in self.particles if p.update(dt)]
        
        # Apply damage at climax (~0.75s)
        if not self.damage_applied and self.timer >= 0.75:
            self.damage_applied = True
            if camera:
                camera.shake(14.0, 0.6)
            if enemies:
                self._deal_damage(enemies, player)
                
        if self.timer >= self.duration:
            self.active = False
            player.is_casting_ultimate = False
            
    def _deal_damage(self, enemies, player):
        # Fetch ultimate damage from character profile (defaults to 180+)
        ult_damage = 180
        if hasattr(player, "profile") and hasattr(player.profile, "skills") and "r" in player.profile.skills:
            ult_damage = max(180, int(player.profile.skills["r"].damage))
            
        for e in enemies:
            if not getattr(e, "is_dead", False):
                dist = math.hypot(e.rect.centerx - self.cx, e.rect.centery - self.cy)
                # Full arena reach so the cinematic Ultimate strikes every enemy and boss
                if dist <= 1500.0:
                    e.take_damage(ult_damage)
                    if hasattr(e, "apply_slow"):
                        e.apply_slow(3.0, 0.15)
                    # Knockback on non-boss minions
                    dx = 1 if e.rect.centerx >= self.cx else -1
                    if hasattr(e, "velocity") and not getattr(e, "is_dead", False):
                        is_boss = (getattr(e, "max_health", 0) > 100)
                        if not is_boss:
                            e.velocity.x = dx * 320
                            e.velocity.y = -220
                        
    def draw_world(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        pass
        
    def draw_screen(self, surface: pygame.Surface):
        pass


# ─────────────────────────────────────────────────────────────────────────────
# 1. SHAIA: CORTE CELESTIAL DA VALQUÍRIA
# ─────────────────────────────────────────────────────────────────────────────
class ValkyrieUltimate(BaseUltimate):
    """Divine judgment: golden rays, sacred mandala, and a colossal holy blade falling from heaven."""
    def __init__(self):
        super().__init__()
        self.feathers: list[dict] = []
        self.swords: list[dict] = []
        self.shockwaves: list[dict] = []
        
    def trigger(self, cx: float, cy: float, facing_right: bool):
        super().trigger(cx, cy, facing_right)
        self.feathers = [
            {
                "x": cx + random.uniform(-140, 140),
                "y": cy - random.uniform(120, 260),
                "vx": random.uniform(-25, 25),
                "vy": random.uniform(40, 90),
                "angle": random.uniform(0, 360),
                "rot_speed": random.uniform(-90, 90),
                "size": random.uniform(8, 14),
                "alpha": 255
            } for _ in range(24)
        ]
        self.swords = []
        self.shockwaves = []
        
    def update(self, dt: float, player, enemies=None, camera=None):
        super().update(dt, player, enemies, camera)
        if not self.active:
            return
            
        # Update feathers
        for f in self.feathers:
            f["x"] += f["vx"] * dt
            f["y"] += f["vy"] * dt
            f["angle"] += f["rot_speed"] * dt
            f["alpha"] = max(0, int(255 * (1.0 - self.timer / self.duration)))
            
        # Spawn descending giant sword at 0.35s
        if 0.35 <= self.timer <= 0.75 and not self.swords:
            self.swords.append({
                "y": self.cy - 350,
                "target_y": self.cy - 20,
                "speed": 850.0
            })
            
        for sw in self.swords:
            if sw["y"] < sw["target_y"]:
                sw["y"] += sw["speed"] * dt
                if sw["y"] >= sw["target_y"]:
                    sw["y"] = sw["target_y"]
                    # Sword hits ground: spawn golden shockwaves & burst
                    self.shockwaves.append({"r": 10.0, "max_r": 280.0, "speed": 550.0, "color": (255, 235, 120)})
                    self.shockwaves.append({"r": 5.0, "max_r": 210.0, "speed": 400.0, "color": (255, 255, 255)})
                    for _ in range(35):
                        ang = random.uniform(0, math.pi * 2)
                        spd = random.uniform(120, 340)
                        self.particles.append(_VFXParticle(
                            self.cx, self.cy,
                            math.cos(ang) * spd, math.sin(ang) * spd - 60,
                            random.uniform(0.5, 1.0), (255, 230, 90),
                            random.uniform(2, 5), gravity=200
                        ))
                        
        for sh in self.shockwaves:
            sh["r"] += sh["speed"] * dt
            
    def draw_world(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active:
            return
            
        px = int(self.cx - camera_offset.x)
        py = int(self.cy - camera_offset.y)
        
        # 1. Sacred Ground Mandala
        if self.timer < 1.4:
            mandala_alpha = int(220 * min(1.0, self.timer / 0.3) * max(0.0, 1.0 - (self.timer - 0.9) / 0.5 if self.timer > 0.9 else 1.0))
            if mandala_alpha > 0:
                m_surf = pygame.Surface((260, 70), pygame.SRCALPHA)
                rot = self.timer * 45.0
                pygame.draw.ellipse(m_surf, (255, 215, 70, mandala_alpha), (10, 10, 240, 50), 3)
                pygame.draw.ellipse(m_surf, (255, 255, 220, mandala_alpha), (30, 18, 200, 34), 2)
                for i in range(8):
                    ang = math.radians(i * 45 + rot)
                    rx = int(130 + 105 * math.cos(ang))
                    ry = int(35 + 20 * math.sin(ang))
                    pygame.draw.circle(m_surf, (255, 240, 150, mandala_alpha), (rx, ry), 4)
                surface.blit(m_surf, (px - 130, py - 35), special_flags=pygame.BLEND_RGBA_ADD)
                
        # 2. Divine Pillar of Sunlight
        if 0.2 <= self.timer <= 1.2:
            beam_alpha = int(140 * math.sin(min(1.0, (self.timer - 0.2) / 0.6) * math.pi))
            if beam_alpha > 0:
                beam_surf = pygame.Surface((120, 420), pygame.SRCALPHA)
                pygame.draw.polygon(beam_surf, (255, 240, 160, beam_alpha), [(35, 0), (85, 0), (120, 420), (0, 420)])
                pygame.draw.polygon(beam_surf, (255, 255, 255, beam_alpha // 2), [(50, 0), (70, 0), (80, 420), (40, 420)])
                surface.blit(beam_surf, (px - 60, py - 390), special_flags=pygame.BLEND_RGBA_ADD)
                
        # 3. Descending Colossal Greatsword
        for sw in self.swords:
            sy = int(sw["y"] - camera_offset.y)
            sword_surf = pygame.Surface((44, 200), pygame.SRCALPHA)
            pygame.draw.polygon(sword_surf, (255, 220, 80, 230), [(22, 195), (6, 40), (38, 40)])
            pygame.draw.polygon(sword_surf, (255, 255, 255, 255), [(22, 190), (14, 45), (30, 45)])
            pygame.draw.rect(sword_surf, (255, 190, 40), (2, 36, 40, 8), border_radius=3)
            pygame.draw.rect(sword_surf, (140, 100, 30), (19, 8, 6, 28))
            pygame.draw.circle(sword_surf, (255, 220, 90), (22, 6), 5)
            surface.blit(sword_surf, (px - 22, sy - 100), special_flags=pygame.BLEND_RGBA_ADD)
            
        # 4. Shockwaves
        for sh in self.shockwaves:
            prog = sh["r"] / sh["max_r"]
            if prog < 1.0:
                alpha = int(230 * (1.0 - prog))
                r = int(sh["r"])
                sh_surf = pygame.Surface((r * 2 + 10, r + 10), pygame.SRCALPHA)
                pygame.draw.ellipse(sh_surf, (*sh["color"], alpha), (5, 5, r * 2, r), max(2, int(6 * (1.0 - prog))))
                surface.blit(sh_surf, (px - r - 5, py - r // 2 - 5), special_flags=pygame.BLEND_RGBA_ADD)
                
        # 5. Feathers
        for f in self.feathers:
            if f["alpha"] > 0:
                fx = int(f["x"] - camera_offset.x)
                fy = int(f["y"] - camera_offset.y)
                fs = pygame.Surface((int(f["size"] * 2), int(f["size"] * 2)), pygame.SRCALPHA)
                pygame.draw.ellipse(fs, (255, 240, 180, f["alpha"]), (0, 0, int(f["size"] * 2), int(f["size"])))
                surface.blit(fs, (fx, fy), special_flags=pygame.BLEND_RGBA_ADD)
                
        # 6. Particles
        for p in self.particles:
            alpha = int(255 * (p.life / p.max_life))
            ps = pygame.Surface((int(p.size * 2), int(p.size * 2)), pygame.SRCALPHA)
            pygame.draw.circle(ps, (*p.color, alpha), (int(p.size), int(p.size)), int(p.size))
            surface.blit(ps, (int(p.x - camera_offset.x - p.size), int(p.y - camera_offset.y - p.size)), special_flags=pygame.BLEND_RGBA_ADD)


# ─────────────────────────────────────────────────────────────────────────────
# 2. LUNARIA: SUPERNOVA ARCANA
# ─────────────────────────────────────────────────────────────────────────────
class SupernovaUltimate(BaseUltimate):
    """Cosmic void singularity imploding and detonating into a massive spiral galaxy blastwave."""
    def __init__(self):
        super().__init__()
        self.imploding_stars: list[dict] = []
        self.rings: list[dict] = []
        
    def trigger(self, cx: float, cy: float, facing_right: bool):
        super().trigger(cx, cy, facing_right)
        self.imploding_stars = [
            {
                "r": random.uniform(180, 360),
                "angle": random.uniform(0, math.pi * 2),
                "speed": random.uniform(280, 520),
                "color": random.choice([(140, 200, 255), (230, 140, 255), (255, 255, 255), (100, 240, 255)]),
                "size": random.uniform(4.5, 9.0)
            } for _ in range(80)
        ]
        self.rings = []
        
    def update(self, dt: float, player, enemies=None, camera=None):
        super().update(dt, player, enemies, camera)
        if not self.active:
            return
            
        # Implosion phase (0.0s - 0.65s)
        if self.timer < 0.65:
            for s in self.imploding_stars:
                s["r"] = max(0.0, s["r"] - s["speed"] * dt)
                s["angle"] += 3.8 * dt
                
        # Detonation phase at 0.65s
        if 0.65 <= self.timer < 0.70 and not self.rings:
            self.rings.append({"r": 10.0, "max_r": 650.0, "speed": 850.0, "color": (120, 220, 255)})
            self.rings.append({"r": 5.0, "max_r": 540.0, "speed": 720.0, "color": (230, 110, 255)})
            self.rings.append({"r": 0.0, "max_r": 440.0, "speed": 580.0, "color": (255, 255, 255)})
            for _ in range(120):
                ang = random.uniform(0, math.pi * 2)
                spd = random.uniform(200, 680)
                self.particles.append(_VFXParticle(
                    self.cx, self.cy - 40,
                    math.cos(ang) * spd, math.sin(ang) * spd,
                    random.uniform(0.7, 1.4),
                    random.choice([(100, 220, 255), (240, 120, 255), (255, 255, 255), (160, 240, 255)]),
                    random.uniform(6.0, 14.0)
                ))
                
        for r in self.rings:
            r["r"] += r["speed"] * dt
            
    def draw_world(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active:
            return
            
        px = int(self.cx - camera_offset.x)
        py = int(self.cy - 40 - camera_offset.y)
        
        # 1. Singularity Core (Implosion)
        if self.timer < 0.70:
            core_r = max(8, int(60 * (1.0 - self.timer / 0.65)))
            core_surf = pygame.Surface((core_r * 4 + 20, core_r * 4 + 20), pygame.SRCALPHA)
            cc = core_r * 2 + 10
            # Concentric cosmic singularity rings
            pygame.draw.circle(core_surf, (255, 255, 255, 255), (cc, cc), int(core_r * 0.45))
            pygame.draw.circle(core_surf, (140, 90, 255, 230), (cc, cc), core_r, 5)
            pygame.draw.circle(core_surf, (80, 220, 255, 230), (cc, cc), core_r + 8, 4)
            pygame.draw.circle(core_surf, (220, 120, 255, 170), (cc, cc), core_r + 16, 2)
            surface.blit(core_surf, (px - cc, py - cc), special_flags=pygame.BLEND_RGBA_ADD)
            
            # Swirling stars
            for s in self.imploding_stars:
                if s["r"] > 2:
                    sx = int(px + s["r"] * math.cos(s["angle"]))
                    sy = int(py + (s["r"] * 0.6) * math.sin(s["angle"]))
                    sz = int(s["size"])
                    star_s = pygame.Surface((sz * 2 + 6, sz * 2 + 6), pygame.SRCALPHA)
                    sc = sz + 3
                    pygame.draw.circle(star_s, (*s["color"], 230), (sc, sc), sz)
                    pygame.draw.circle(star_s, (255, 255, 255, 255), (sc, sc), max(1, sz // 2))
                    surface.blit(star_s, (sx - sc, sy - sc), special_flags=pygame.BLEND_RGBA_ADD)
                    
        # 2. Supernova Explosion Blast (Detonation)
        if self.timer >= 0.65:
            gal_rot = (self.timer - 0.65) * 6.0
            gal_alpha = int(255 * max(0.0, 1.0 - (self.timer - 0.65) / 0.75))
            if gal_alpha > 0:
                g_surf = pygame.Surface((640, 640), pygame.SRCALPHA)
                gc = 320
                for arm in range(4):
                    arm_ang = gal_rot + arm * (math.pi / 2)
                    pts = []
                    for step in range(24):
                        rad = step * 14
                        ang = arm_ang + step * 0.22
                        pts.append((int(gc + rad * math.cos(ang)), int(gc + rad * math.sin(ang))))
                    if len(pts) > 1:
                        pygame.draw.lines(g_surf, (180, 130, 255, gal_alpha), False, pts, 8)
                        pygame.draw.lines(g_surf, (90, 240, 255, gal_alpha // 2), False, pts, 16)
                        pygame.draw.lines(g_surf, (255, 255, 255, gal_alpha), False, pts, 3)
                surface.blit(g_surf, (px - gc, py - gc), special_flags=pygame.BLEND_RGBA_ADD)
                
            for r in self.rings:
                prog = r["r"] / r["max_r"]
                if prog < 1.0:
                    alpha = int(240 * (1.0 - prog))
                    rad = int(r["r"])
                    rs = pygame.Surface((rad * 2 + 16, rad * 2 + 16), pygame.SRCALPHA)
                    rc = rad + 8
                    pygame.draw.circle(rs, (*r["color"], alpha), (rc, rc), rad, max(3, int(12 * (1.0 - prog))))
                    pygame.draw.circle(rs, (255, 255, 255, alpha), (rc, rc), max(1, rad - 4), 2)
                    surface.blit(rs, (px - rc, py - rc), special_flags=pygame.BLEND_RGBA_ADD)
                    
        # 3. Particles
        for p in self.particles:
            alpha = int(255 * (p.life / p.max_life))
            ps = pygame.Surface((int(p.size * 2 + 6), int(p.size * 2 + 6)), pygame.SRCALPHA)
            pc = int(p.size + 3)
            pygame.draw.circle(ps, (*p.color, alpha), (pc, pc), int(p.size))
            pygame.draw.circle(ps, (255, 255, 255, alpha), (pc, pc), max(1, int(p.size * 0.45)))
            surface.blit(ps, (int(p.x - camera_offset.x - pc), int(p.y - camera_offset.y - pc)), special_flags=pygame.BLEND_RGBA_ADD)


# ─────────────────────────────────────────────────────────────────────────────
# 3. IGNIS: INFERNO DEVASTADOR
# ─────────────────────────────────────────────────────────────────────────────
class InfernoUltimate(BaseUltimate):
    """Volcanic cataclysm: fiery ground fissures, 3 colossal roaring flame pillars, and raining meteors."""
    def __init__(self):
        super().__init__()
        self.pillars: list[dict] = []
        self.meteors: list[dict] = []
        self.shockwaves: list[dict] = []
        
    def trigger(self, cx: float, cy: float, facing_right: bool):
        super().trigger(cx, cy, facing_right)
        self.pillars = [
            {"x": cx - 140, "delay": 0.22, "active": False, "timer": 0.0, "w": 130},
            {"x": cx + 140, "delay": 0.36, "active": False, "timer": 0.0, "w": 130},
            {"x": cx,       "delay": 0.52, "active": False, "timer": 0.0, "w": 190}
        ]
        self.meteors = [
            {"x": cx - 180, "y": cy - 420, "tx": cx - 90, "ty": cy, "spd": 720, "delay": 0.60, "hit": False},
            {"x": cx + 180, "y": cy - 420, "tx": cx + 90, "ty": cy, "spd": 720, "delay": 0.72, "hit": False},
            {"x": cx,       "y": cy - 460, "tx": cx,      "ty": cy, "spd": 800, "delay": 0.84, "hit": False}
        ]
        self.shockwaves = []
        
    def update(self, dt: float, player, enemies=None, camera=None):
        super().update(dt, player, enemies, camera)
        if not self.active:
            return
            
        for pil in self.pillars:
            if self.timer >= pil["delay"]:
                pil["active"] = True
                pil["timer"] += dt
                for _ in range(3):
                    self.particles.append(_VFXParticle(
                        pil["x"] + random.uniform(-pil["w"] // 2, pil["w"] // 2),
                        self.cy - random.uniform(10, 260),
                        random.uniform(-50, 50), random.uniform(-280, -130),
                        random.uniform(0.5, 0.9), (255, random.randint(70, 220), 20),
                        random.uniform(6, 13)
                    ))
                    
        for m in self.meteors:
            if self.timer >= m["delay"] and not m["hit"]:
                dx = m["tx"] - m["x"]
                dy = m["ty"] - m["y"]
                dist = math.hypot(dx, dy)
                if dist < 35:
                    m["hit"] = True
                    if camera:
                        camera.shake(10.0, 0.35)
                    self.shockwaves.append({"x": m["tx"], "r": 10.0, "max_r": 260.0, "speed": 620.0, "color": (255, 170, 30)})
                    for _ in range(60):
                        ang = random.uniform(0, math.pi * 2)
                        spd = random.uniform(150, 460)
                        self.particles.append(_VFXParticle(
                            m["tx"], m["ty"],
                            math.cos(ang) * spd, math.sin(ang) * spd - 60,
                            random.uniform(0.5, 1.0), (255, random.randint(60, 200), 15),
                            random.uniform(6, 12), gravity=160
                        ))
                else:
                    m["x"] += (dx / dist) * m["spd"] * dt
                    m["y"] += (dy / dist) * m["spd"] * dt

        for sh in self.shockwaves:
            sh["r"] += sh["speed"] * dt
                    
    def draw_world(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active:
            return
            
        px = int(self.cx - camera_offset.x)
        py = int(self.cy - camera_offset.y)
        
        # 1. Fiery Ground Fissures
        prog = self.timer / self.duration
        fiss_alpha = int(255 * (1.0 - prog))
        if fiss_alpha > 0:
            f_surf = pygame.Surface((640, 80), pygame.SRCALPHA)
            pts1 = [(20, 40), (100, 25), (190, 48), (280, 30), (370, 52), (460, 26), (540, 45), (620, 36)]
            pygame.draw.lines(f_surf, (255, 60, 10, fiss_alpha), False, pts1, 14)
            pygame.draw.lines(f_surf, (255, 170, 30, fiss_alpha), False, pts1, 8)
            pygame.draw.lines(f_surf, (255, 255, 160, fiss_alpha), False, pts1, 3)
            surface.blit(f_surf, (px - 320, py - 40), special_flags=pygame.BLEND_RGBA_ADD)
            
        # 2. Roaring Flame Pillars
        for pil in self.pillars:
            if pil["active"] and pil["timer"] < 0.95:
                pil_prog = pil["timer"] / 0.95
                pil_alpha = int(240 * math.sin(pil_prog * math.pi))
                pil_x = int(pil["x"] - camera_offset.x)
                w = pil["w"]
                p_surf = pygame.Surface((w + 60, 440), pygame.SRCALPHA)
                pw = w + 20
                pygame.draw.rect(p_surf, (255, 60, 10, pil_alpha), (20, 0, pw, 440), border_radius=18)
                pygame.draw.rect(p_surf, (255, 170, 30, pil_alpha), (20 + int(pw * 0.18), 0, int(pw * 0.64), 440), border_radius=14)
                pygame.draw.rect(p_surf, (255, 245, 100, pil_alpha), (20 + int(pw * 0.35), 0, int(pw * 0.30), 440), border_radius=10)
                pygame.draw.rect(p_surf, (255, 255, 255, pil_alpha), (20 + int(pw * 0.44), 0, int(pw * 0.12), 440), border_radius=6)
                surface.blit(p_surf, (pil_x - pw // 2 - 20, py - 440), special_flags=pygame.BLEND_RGBA_ADD)
                
        # 3. Ground shockwaves from meteors
        for sh in self.shockwaves:
            prog = sh["r"] / sh["max_r"]
            if prog < 1.0:
                alpha = int(240 * (1.0 - prog))
                r = int(sh["r"])
                sh_x = int(sh["x"] - camera_offset.x)
                sh_surf = pygame.Surface((r * 2 + 16, r + 16), pygame.SRCALPHA)
                pygame.draw.ellipse(sh_surf, (*sh["color"], alpha), (8, 8, r * 2, r), max(3, int(10 * (1.0 - prog))))
                pygame.draw.ellipse(sh_surf, (255, 255, 200, alpha), (8, 8, r * 2, r), max(1, int(4 * (1.0 - prog))))
                surface.blit(sh_surf, (sh_x - r - 8, py - r // 2 - 8), special_flags=pygame.BLEND_RGBA_ADD)

        # 4. Raining Meteors
        for m in self.meteors:
            if self.timer >= m["delay"] and not m["hit"]:
                mx = int(m["x"] - camera_offset.x)
                my = int(m["y"] - camera_offset.y)
                tail_end = (mx - int((m["tx"] - m["x"]) * 0.22), my - int((m["ty"] - m["y"]) * 0.22))
                pygame.draw.line(surface, (255, 70, 10), (mx, my), tail_end, 22)
                pygame.draw.line(surface, (255, 180, 30), (mx, my), tail_end, 12)
                pygame.draw.line(surface, (255, 255, 220), (mx, my), tail_end, 4)
                pygame.draw.circle(surface, (255, 255, 200), (mx, my), 24)
                pygame.draw.circle(surface, (255, 140, 20), (mx, my), 36, 6)
                
        # 5. Particles
        for p in self.particles:
            alpha = int(255 * (p.life / p.max_life))
            ps = pygame.Surface((int(p.size * 2 + 6), int(p.size * 2 + 6)), pygame.SRCALPHA)
            pc = int(p.size + 3)
            pygame.draw.circle(ps, (*p.color, alpha), (pc, pc), int(p.size))
            pygame.draw.circle(ps, (255, 255, 200, alpha), (pc, pc), max(1, int(p.size * 0.4)))
            surface.blit(ps, (int(p.x - camera_offset.x - pc), int(p.y - camera_offset.y - pc)), special_flags=pygame.BLEND_RGBA_ADD)


# ─────────────────────────────────────────────────────────────────────────────
# 4. ASTRA: GLACIAÇÃO ABSOLUTA
# ─────────────────────────────────────────────────────────────────────────────
class GlaciationUltimate(BaseUltimate):
    """Arctic absolute zero: aurora borealis, colossal jagged ice monoliths, and diamond blizzard shatter."""
    def __init__(self):
        super().__init__()
        self.monoliths: list[dict] = []
        self.shattered = False
        self.frost_rings: list[dict] = []
        
    def trigger(self, cx: float, cy: float, facing_right: bool):
        super().trigger(cx, cy, facing_right)
        self.shattered = False
        self.frost_rings = []
        self.monoliths = [
            {"x": cx - 170, "h": 220, "max_h": 220, "cur_h": 0, "w": 72},
            {"x": cx - 85,  "h": 290, "max_h": 290, "cur_h": 0, "w": 88},
            {"x": cx,       "h": 380, "max_h": 380, "cur_h": 0, "w": 115},
            {"x": cx + 85,  "h": 290, "max_h": 290, "cur_h": 0, "w": 88},
            {"x": cx + 170, "h": 220, "max_h": 220, "cur_h": 0, "w": 72}
        ]
        
    def update(self, dt: float, player, enemies=None, camera=None):
        super().update(dt, player, enemies, camera)
        if not self.active:
            return
            
        if 0.18 <= self.timer < 0.65:
            grow_speed = 750.0
            for m in self.monoliths:
                m["cur_h"] = min(m["max_h"], m["cur_h"] + grow_speed * dt)
                
        if self.timer >= 0.75 and not self.shattered:
            self.shattered = True
            if camera:
                camera.shake(14.0, 0.45)
            self.frost_rings.append({"r": 10.0, "max_r": 550.0, "speed": 750.0, "color": (140, 240, 255)})
            for m in self.monoliths:
                for _ in range(40):
                    ang = random.uniform(0, math.pi * 2)
                    spd = random.uniform(180, 520)
                    self.particles.append(_VFXParticle(
                        m["x"] + random.uniform(-m["w"] // 3, m["w"] // 3),
                        self.cy - m["cur_h"] * random.uniform(0.1, 0.95),
                        math.cos(ang) * spd, math.sin(ang) * spd,
                        random.uniform(0.6, 1.2),
                        random.choice([(200, 245, 255), (130, 220, 255), (255, 255, 255), (90, 190, 255)]),
                        random.uniform(7.0, 16.0), gravity=80, shape="shard"
                    ))

        for fr in self.frost_rings:
            fr["r"] += fr["speed"] * dt
                    
    def draw_world(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active:
            return
            
        px = int(self.cx - camera_offset.x)
        py = int(self.cy - camera_offset.y)
        
        # 1. Waving Celestial Aurora Borealis
        if self.timer < 1.4:
            aurora_alpha = int(220 * math.sin(min(1.0, self.timer / 0.6) * math.pi))
            if aurora_alpha > 0:
                a_surf = pygame.Surface((720, 180), pygame.SRCALPHA)
                pts1 = []
                pts2 = []
                for step in range(36):
                    ax = step * 20
                    ay1 = int(70 + 35 * math.sin(step * 0.25 + self.timer * 3.5))
                    ay2 = int(90 + 30 * math.cos(step * 0.22 + self.timer * 3.0))
                    pts1.append((ax, ay1))
                    pts2.append((ax, ay2))
                if len(pts1) > 1:
                    pygame.draw.lines(a_surf, (90, 240, 255, aurora_alpha), False, pts1, 28)
                    pygame.draw.lines(a_surf, (220, 120, 255, aurora_alpha // 2), False, pts2, 45)
                    pygame.draw.lines(a_surf, (255, 255, 255, aurora_alpha), False, pts1, 4)
                surface.blit(a_surf, (px - 360, py - 380), special_flags=pygame.BLEND_RGBA_ADD)
                
        # 2. Ice Monoliths
        if not self.shattered:
            for m in self.monoliths:
                if m["cur_h"] > 0:
                    mx = int(m["x"] - camera_offset.x)
                    h = int(m["cur_h"])
                    w = m["w"]
                    mono_surf = pygame.Surface((w + 30, h + 30), pygame.SRCALPHA)
                    poly = [(w // 2 + 15, 8), (w + 22, h + 22), (8, h + 22)]
                    pygame.draw.polygon(mono_surf, (140, 225, 255, 230), poly)
                    pygame.draw.polygon(mono_surf, (255, 255, 255, 255), [(w // 2 + 15, 12), (w // 2 + 20, h + 22), (w // 2 + 8, h + 22)])
                    pygame.draw.polygon(mono_surf, (70, 190, 255, 255), poly, 5)
                    pygame.draw.polygon(mono_surf, (255, 255, 255, 220), poly, 2)
                    surface.blit(mono_surf, (mx - w // 2 - 15, py - h - 15), special_flags=pygame.BLEND_RGBA_ADD)

        # 3. Ground frost blast ring
        for fr in self.frost_rings:
            prog = fr["r"] / fr["max_r"]
            if prog < 1.0:
                alpha = int(240 * (1.0 - prog))
                r = int(fr["r"])
                fr_surf = pygame.Surface((r * 2 + 20, r + 20), pygame.SRCALPHA)
                pygame.draw.ellipse(fr_surf, (*fr["color"], alpha), (10, 10, r * 2, r), max(3, int(12 * (1.0 - prog))))
                pygame.draw.ellipse(fr_surf, (255, 255, 255, alpha), (10, 10, r * 2, r), max(1, int(5 * (1.0 - prog))))
                surface.blit(fr_surf, (px - r - 10, py - r // 2 - 10), special_flags=pygame.BLEND_RGBA_ADD)
                    
        # 4. Particles
        for p in self.particles:
            alpha = int(255 * (p.life / p.max_life))
            ps = pygame.Surface((int(p.size * 2 + 8), int(p.size * 2 + 8)), pygame.SRCALPHA)
            s = int(p.size)
            sc = s + 4
            pygame.draw.polygon(ps, (*p.color, alpha), [(sc, sc - s), (sc + s, sc), (sc, sc + s), (sc - s, sc)])
            pygame.draw.polygon(ps, (255, 255, 255, alpha), [(sc, sc - s // 2), (sc + s // 2, sc), (sc, sc + s // 2), (sc - s // 2, sc)])
            surface.blit(ps, (int(p.x - camera_offset.x - sc), int(p.y - camera_offset.y - sc)), special_flags=pygame.BLEND_RGBA_ADD)


# ─────────────────────────────────────────────────────────────────────────────
# 5. HAYATE: TEMPESTADE DE SOMBRAS
# ─────────────────────────────────────────────────────────────────────────────
class ShadowStormUltimate(BaseUltimate):
    """Midnight shadow realm: 6 phantom ninja clones in zigzag flurry and electric violet execution slashes."""
    def __init__(self):
        super().__init__()
        self.clones: list[dict] = []
        self.slashes: list[dict] = []
        
    def trigger(self, cx: float, cy: float, facing_right: bool):
        super().trigger(cx, cy, facing_right)
        self.clones = [
            {"sx": cx - 180, "sy": cy - 100, "tx": cx + 180, "ty": cy - 20, "prog": 0.0, "spd": 3.8, "delay": 0.20},
            {"sx": cx + 180, "sy": cy - 140, "tx": cx - 180, "ty": cy - 40, "prog": 0.0, "spd": 4.2, "delay": 0.32},
            {"sx": cx - 120, "sy": cy + 20,  "tx": cx + 140, "ty": cy - 120, "prog": 0.0, "spd": 4.0, "delay": 0.44},
            {"sx": cx + 140, "sy": cy - 20,  "tx": cx - 140, "ty": cy - 100, "prog": 0.0, "spd": 4.5, "delay": 0.56},
            {"sx": cx,       "sy": cy - 200, "tx": cx,       "ty": cy,       "prog": 0.0, "spd": 5.0, "delay": 0.68},
            {"sx": cx - 160, "sy": cy - 80,  "tx": cx + 160, "ty": cy - 80,  "prog": 0.0, "spd": 4.8, "delay": 0.78}
        ]
        self.slashes = []
        
    def update(self, dt: float, player, enemies=None, camera=None):
        super().update(dt, player, enemies, camera)
        if not self.active:
            return
            
        for c in self.clones:
            if self.timer >= c["delay"]:
                old_prog = c["prog"]
                c["prog"] = min(1.0, c["prog"] + c["spd"] * dt)
                if old_prog < 1.0 and c["prog"] >= 1.0:
                    self.slashes.append({
                        "p1": (c["sx"], c["sy"]), "p2": (c["tx"], c["ty"]),
                        "life": 0.45, "max_life": 0.45, "color": (190, 80, 255)
                    })
                    if camera:
                        camera.shake(5.0, 0.15)
                        
        for sl in self.slashes:
            sl["life"] -= dt
        self.slashes = [s for s in self.slashes if s["life"] > 0]
        
    def draw_world(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active:
            return
            
        px = int(self.cx - camera_offset.x)
        py = int(self.cy - camera_offset.y)
        
        # 1. Midnight Vignette
        if self.timer < 1.3:
            vig_alpha = int(140 * math.sin(min(1.0, self.timer / 0.6) * math.pi))
            if vig_alpha > 0:
                vs = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                vs.fill((15, 5, 25, vig_alpha))
                surface.blit(vs, (0, 0))
                
        # 2. Shadow Phantom Clones
        for c in self.clones:
            if self.timer >= c["delay"] and c["prog"] < 1.0:
                cur_x = c["sx"] + (c["tx"] - c["sx"]) * c["prog"] - camera_offset.x
                cur_y = c["sy"] + (c["ty"] - c["sy"]) * c["prog"] - camera_offset.y
                cs = pygame.Surface((36, 48), pygame.SRCALPHA)
                cs.fill((180, 70, 255, 190))
                pygame.draw.line(cs, (255, 255, 255), (10, 14), (26, 14), 2)
                surface.blit(cs, (int(cur_x - 18), int(cur_y - 24)), special_flags=pygame.BLEND_RGBA_ADD)
                
        # 3. Electric Violet Slash Trails
        for sl in self.slashes:
            prog = sl["life"] / sl["max_life"]
            alpha = int(255 * prog)
            p1 = (int(sl["p1"][0] - camera_offset.x), int(sl["p1"][1] - camera_offset.y))
            p2 = (int(sl["p2"][0] - camera_offset.x), int(sl["p2"][1] - camera_offset.y))
            pygame.draw.line(surface, (*sl["color"], alpha), p1, p2, max(2, int(7 * prog)))
            pygame.draw.line(surface, (255, 255, 255, alpha), p1, p2, 2)


# ─────────────────────────────────────────────────────────────────────────────
# 6. KENSHIN: DANÇA DA CEREJEIRA
# ─────────────────────────────────────────────────────────────────────────────
class CherryBlossomUltimate(BaseUltimate):
    """Sumi-e duel aesthetic: screen turns monochrome, pink sakura petals swirl, dimensional katana cuts."""
    def __init__(self):
        super().__init__()
        self.petals: list[dict] = []
        self.slashes: list[dict] = []
        self.sheath_clicked = False
        
    def trigger(self, cx: float, cy: float, facing_right: bool):
        super().trigger(cx, cy, facing_right)
        self.sheath_clicked = False
        self.petals = [
            {
                "x": cx + random.uniform(-160, 160),
                "y": cy - random.uniform(20, 220),
                "vx": random.uniform(-40, -10),
                "vy": random.uniform(15, 45),
                "angle": random.uniform(0, 360),
                "rot_speed": random.uniform(-120, 120),
                "size": random.uniform(5, 10),
                "color": random.choice([(255, 185, 215), (255, 150, 190), (255, 215, 235)])
            } for _ in range(40)
        ]
        self.slashes = [
            {"p1": (cx - 140, cy - 80),  "p2": (cx + 140, cy - 20),  "color": (255, 40, 60),  "w": 4.5, "delay": 0.45},
            {"p1": (cx + 130, cy - 100), "p2": (cx - 130, cy - 10),  "color": (255, 255, 255), "w": 3.0, "delay": 0.50},
            {"p1": (cx - 100, cy - 130), "p2": (cx + 100, cy + 10),  "color": (255, 50, 80),  "w": 4.0, "delay": 0.55},
            {"p1": (cx + 90,  cy - 140), "p2": (cx - 90,  cy + 20),  "color": (255, 255, 255), "w": 3.0, "delay": 0.60},
            {"p1": (cx - 160, cy - 50),  "p2": (cx + 160, cy - 50),  "color": (255, 30, 50),  "w": 5.0, "delay": 0.65},
            {"p1": (cx,       cy - 170), "p2": (cx,       cy + 30),  "color": (255, 255, 255), "w": 4.0, "delay": 0.70}
        ]
        
    def update(self, dt: float, player, enemies=None, camera=None):
        super().update(dt, player, enemies, camera)
        if not self.active:
            return
            
        for p in self.petals:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["angle"] += p["rot_speed"] * dt
            
        if self.timer >= 0.75 and not self.sheath_clicked:
            self.sheath_clicked = True
            if camera:
                camera.shake(15.0, 0.5)
            for p in self.petals:
                ang = random.uniform(0, math.pi * 2)
                spd = random.uniform(180, 360)
                p["vx"] = math.cos(ang) * spd
                p["vy"] = math.sin(ang) * spd
                
    def draw_world(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active:
            return
            
        px = int(self.cx - camera_offset.x)
        py = int(self.cy - camera_offset.y)
        
        # 1. Sumi-e Monochrome Screen Tint
        if 0.1 <= self.timer < 0.75:
            ink_alpha = int(120 * min(1.0, (self.timer - 0.1) / 0.2))
            ink_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            ink_surf.fill((20, 20, 25, ink_alpha))
            surface.blit(ink_surf, (0, 0))
            
        # 2. Dimensional Slashes (Judgement Cut)
        for sl in self.slashes:
            if self.timer >= sl["delay"]:
                prog = min(1.0, (self.timer - sl["delay"]) / 0.4)
                if prog < 1.0:
                    alpha = int(255 * (1.0 - prog))
                    p1 = (int(sl["p1"][0] - camera_offset.x), int(sl["p1"][1] - camera_offset.y))
                    p2 = (int(sl["p2"][0] - camera_offset.x), int(sl["p2"][1] - camera_offset.y))
                    pygame.draw.line(surface, (*sl["color"], alpha), p1, p2, max(1, int(sl["w"] * (1.0 - prog))))
                    pygame.draw.circle(surface, (255, 255, 255, alpha), p1, 3)
                    pygame.draw.circle(surface, (255, 255, 255, alpha), p2, 3)
                    
        # 3. Swirling Sakura Petals
        for p in self.petals:
            ptx = int(p["x"] - camera_offset.x)
            pty = int(p["y"] - camera_offset.y)
            sz = int(p["size"])
            ps = pygame.Surface((sz * 2, sz), pygame.SRCALPHA)
            pygame.draw.ellipse(ps, p["color"], (0, 0, sz * 2, sz))
            rot_surf = pygame.transform.rotate(ps, p["angle"])
            surface.blit(rot_surf, (ptx, pty))


# ─────────────────────────────────────────────────────────────────────────────
# 7. RYUU: FÚRIA DO DRAGÃO
# ─────────────────────────────────────────────────────────────────────────────
class DragonFuryUltimate(BaseUltimate):
    """Surging golden Ki aura, soaring serpentine dragon spirit, and explosive Ki shockwave."""
    def __init__(self):
        super().__init__()
        self.dragon_height = 0.0
        self.ki_waves: list[dict] = []
        self.burst_done = False
        
    def trigger(self, cx: float, cy: float, facing_right: bool):
        super().trigger(cx, cy, facing_right)
        self.dragon_height = 0.0
        self.ki_waves = []
        self.burst_done = False
        
    def update(self, dt: float, player, enemies=None, camera=None):
        super().update(dt, player, enemies, camera)
        if not self.active:
            return
            
        if self.timer < 0.45:
            if random.random() < 0.45:
                self.ki_waves.append({"r": 10.0, "max_r": 440.0, "speed": 540.0})
                
        if self.timer >= 0.35:
            if not self.burst_done:
                self.burst_done = True
                for _ in range(70):
                    ang = random.uniform(0, math.pi * 2)
                    spd = random.uniform(180, 520)
                    self.particles.append(_VFXParticle(
                        self.cx, self.cy - 25,
                        math.cos(ang) * spd, math.sin(ang) * spd - 60,
                        random.uniform(0.6, 1.2), (255, 235, 80),
                        random.uniform(6.0, 14.0), gravity=120
                    ))
            self.dragon_height += 560.0 * dt
            for _ in range(8):
                ang = random.uniform(0, math.pi * 2)
                spd = random.uniform(100, 320)
                self.particles.append(_VFXParticle(
                    self.cx + random.uniform(-35, 35),
                    self.cy - self.dragon_height + random.uniform(-40, 40),
                    math.cos(ang) * spd, math.sin(ang) * spd - 80,
                    random.uniform(0.5, 0.9), random.choice([(255, 235, 70), (255, 180, 30), (255, 255, 210)]),
                    random.uniform(5.0, 12.0), gravity=80
                ))
                
        for kw in self.ki_waves:
            kw["r"] += kw["speed"] * dt
            
    def draw_world(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active:
            return
            
        px = int(self.cx - camera_offset.x)
        py = int(self.cy - camera_offset.y)
        
        # 1. Pulsing Golden Ki Aura on Ground
        for kw in self.ki_waves:
            prog = kw["r"] / kw["max_r"]
            if prog < 1.0:
                alpha = int(240 * (1.0 - prog))
                r = int(kw["r"])
                ks = pygame.Surface((r * 2 + 20, r + 20), pygame.SRCALPHA)
                pygame.draw.ellipse(ks, (255, 175, 30, alpha), (10, 10, r * 2, r), max(4, int(12 * (1.0 - prog))))
                pygame.draw.ellipse(ks, (255, 245, 100, alpha), (10, 10, r * 2, r), max(1, int(5 * (1.0 - prog))))
                surface.blit(ks, (px - r - 10, py - r // 2 - 10), special_flags=pygame.BLEND_RGBA_ADD)
                
        # 2. Soaring Serpentine Golden Ki Dragon
        if self.timer >= 0.35 and self.dragon_height < 520.0:
            dh = self.dragon_height
            head_y = py - int(dh)
            
            body_pts = []
            for seg in range(16):
                seg_y = head_y + seg * 26
                seg_x = px + int(45 * math.sin((seg * 0.45) + self.timer * 8.5))
                body_pts.append((seg_x, seg_y))
                
            if len(body_pts) > 1:
                pygame.draw.lines(surface, (255, 150, 10), False, body_pts, 50)
                pygame.draw.lines(surface, (255, 225, 40), False, body_pts, 28)
                pygame.draw.lines(surface, (255, 255, 220), False, body_pts, 10)
                
            head_surf = pygame.Surface((140, 140), pygame.SRCALPHA)
            hc = 70
            pygame.draw.polygon(head_surf, (255, 160, 20), [(hc, 10), (hc + 50, 80), (hc + 30, 120), (hc - 30, 120), (hc - 50, 80)])
            pygame.draw.polygon(head_surf, (255, 230, 60), [(hc, 25), (hc + 35, 78), (hc - 35, 78)])
            pygame.draw.polygon(head_surf, (255, 255, 255), [(hc, 35), (hc + 20, 72), (hc - 20, 72)])
            # Blazing white dragon eyes
            pygame.draw.circle(head_surf, (255, 255, 255), (hc - 18, 62), 7)
            pygame.draw.circle(head_surf, (255, 255, 255), (hc + 18, 62), 7)
            pygame.draw.circle(head_surf, (255, 210, 40), (hc - 18, 62), 11, 2)
            pygame.draw.circle(head_surf, (255, 210, 40), (hc + 18, 62), 11, 2)
            # Horns and whiskers
            pygame.draw.line(head_surf, (255, 240, 120), (hc - 28, 85), (hc - 55, 35), 4)
            pygame.draw.line(head_surf, (255, 240, 120), (hc + 28, 85), (hc + 55, 35), 4)
            surface.blit(head_surf, (px - hc, head_y - hc), special_flags=pygame.BLEND_RGBA_ADD)
            
        # 3. Particles
        for p in self.particles:
            alpha = int(255 * (p.life / p.max_life))
            ps = pygame.Surface((int(p.size * 2 + 6), int(p.size * 2 + 6)), pygame.SRCALPHA)
            pc = int(p.size + 3)
            pygame.draw.circle(ps, (*p.color, alpha), (pc, pc), int(p.size))
            pygame.draw.circle(ps, (255, 255, 255, alpha), (pc, pc), max(1, int(p.size * 0.45)))
            surface.blit(ps, (int(p.x - camera_offset.x - pc), int(p.y - camera_offset.y - pc)), special_flags=pygame.BLEND_RGBA_ADD)


# ─────────────────────────────────────────────────────────────────────────────
# Factory Function
# ─────────────────────────────────────────────────────────────────────────────
def create_ultimate(character_id: str) -> BaseUltimate:
    """Instantiates the dedicated Triple-AAA Ultimate visual controller for the given character."""
    cid = character_id.lower()
    if cid == "shaia":
        return ValkyrieUltimate()
    elif cid == "lunaria":
        return SupernovaUltimate()
    elif cid == "ignis":
        return InfernoUltimate()
    elif cid == "astra":
        return GlaciationUltimate()
    elif cid == "shinobi":
        return ShadowStormUltimate()
    elif cid == "samurai":
        return CherryBlossomUltimate()
    elif cid == "fighter":
        return DragonFuryUltimate()
    return ValkyrieUltimate()
