"""
Ruin Engine V3.0 — Industrial Telemetry Profiler & F3 Diagnostic Overlay.
Provides microsecond phase timers, frame pacing percentiles (P50, P95, P99, 1% / 0.1% lows),
draw calls, memory monitoring, and dynamic frame budget tracking.
"""

import time
import gc
import pygame
import numpy as np
from typing import Dict, Any, List, Optional
from engine.v3.core.jit_backend import get_jit_info
from engine.v3.core.surface_pool import SURFACE_POOL
from engine.v3.core.memory_manager import MEMORY_MANAGER

class PhaseTimer:
    """Context manager for zero-overhead phase timing."""
    __slots__ = ("profiler", "phase_name", "start_time")
    def __init__(self, profiler: "Profiler", phase_name: str):
        self.profiler = profiler
        self.phase_name = phase_name
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (time.perf_counter() - self.start_time) * 1000.0
        self.profiler.record_phase_time(self.phase_name, elapsed)

class Profiler:
    """
    Industrial-grade telemetry accumulator and real-time diagnostic profiler.
    Measures frame pacing, 1% / 0.1% lows, phase timings, draw calls, and resource budgets.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
            
        self.enabled: bool = False
        self.last_frame_time: float = time.perf_counter()
        self.frame_delta: float = 0.016
        self.frametimes: List[float] = [16.66] * 120
        self.fps: float = 60.0
        
        # Detailed phase timers (in ms)
        self.phase_times: Dict[str, float] = {
            "cpu_time": 0.0,
            "render_time": 0.0,
            "physics_time": 0.0,
            "ai_time": 0.0,
            "input_time": 0.0,
            "vfx_time": 0.0,
            "lighting_time": 0.0,
            "shadow_time": 0.0,
            "postfx_time": 0.0,
            "upscaling_time": 0.0,
            "present_time": 0.0,
            "gc_time": 0.0,
            "asset_streaming_time": 0.0,
        }
        
        # Real-time telemetry counters
        self.metrics: Dict[str, Any] = {
            "fps": 60.0,
            "frametime_ms": 16.66,
            "p50_ms": 16.66,
            "p95_ms": 16.66,
            "p99_ms": 16.66,
            "one_percent_low": 60.0,
            "point_one_percent_low": 58.0,
            "frametime_variance": 0.0,
            "draw_calls": 0,
            "surface_ops": 0,
            "blit_count": 0,
            "active_lights": 0,
            "lights_count": 0,
            "active_shadows": 0,
            "shadows": 0,
            "active_particles": 0,
            "particles": 0,
            "active_vfx": 0,
            "visible_entities": 0,
            "culled_entities": 0,
            "chunks_rendered": 0,
            "ray_count": 0,
            "cache_hits": 0,
            "cpu_percent": 0.0,
            "ram_mb": 0.0,
            "vram_mb": 0.0,
            "resolution": (1280, 720),
            "internal_resolution": (512, 384),
            "upscale_ratio": 1.0,
            "quality_tier": "Normal",
        }
        
        self.font_small = None
        self.font_bold = None
        self.frame_count = 0
        self._gc_count_prev = gc.get_count()
        self._initialized = True

    def toggle(self) -> bool:
        """Toggles the visibility of the F3 profiler overlay."""
        self.enabled = not self.enabled
        return self.enabled

    def time_phase(self, phase_name: str) -> PhaseTimer:
        """Context manager for measuring execution time of a specific engine subsystem."""
        return PhaseTimer(self, phase_name)

    def record_phase_time(self, phase: str, duration_ms: float) -> None:
        key = f"{phase}_time" if not phase.endswith("_time") else phase
        if key in self.phase_times:
            self.phase_times[key] += duration_ms
        else:
            self.phase_times[key] = duration_ms

    def record_draw_calls(self, count: int = 1) -> None:
        self.metrics["draw_calls"] += count
        self.metrics["blit_count"] += count

    def record_surface_ops(self, count: int = 1) -> None:
        self.metrics["surface_ops"] += count

    def record_particles(self, count: int) -> None:
        self.metrics["active_particles"] = count
        self.metrics["particles"] = count

    def record_vfx(self, count: int) -> None:
        self.metrics["active_vfx"] = count

    def record_entities(self, visible: int, culled: int = 0) -> None:
        self.metrics["visible_entities"] = visible
        self.metrics["culled_entities"] = culled

    def record_chunks(self, count: int) -> None:
        self.metrics["chunks_rendered"] = count

    def record_light(self, rays: int = 0) -> None:
        self.metrics["active_lights"] += 1
        self.metrics["lights_count"] = self.metrics.get("lights_count", 0) + 1
        self.metrics["ray_count"] += rays

    def record_shadow(self) -> None:
        self.metrics["active_shadows"] += 1
        self.metrics["shadows"] = self.metrics.get("shadows", 0) + 1

    def begin_frame(self) -> None:
        """Resets per-frame telemetry and computes frame pacing percentiles."""
        self.frame_count += 1
        now = time.perf_counter()
        dt = now - self.last_frame_time
        self.last_frame_time = now
        
        if dt > 0:
            self.frame_delta = dt
            cur_ms = dt * 1000.0
            self.frametimes.pop(0)
            self.frametimes.append(cur_ms)
            self.fps = 1.0 / dt
            self.metrics["fps"] = self.fps
            self.metrics["frametime_ms"] = cur_ms
            
            # Statistical frame pacing analysis (amortized every 30 frames to save CPU)
            if self.frame_count % 30 == 0:
                arr = np.array(self.frametimes, dtype=np.float32)
                p50 = float(np.percentile(arr, 50))
                p95 = float(np.percentile(arr, 95))
                p99 = float(np.percentile(arr, 99))
                p999 = float(np.percentile(arr, 99.9))
                variance = float(np.var(arr))
                
                self.metrics["p50_ms"] = p50
                self.metrics["p95_ms"] = p95
                self.metrics["p99_ms"] = p99
                self.metrics["one_percent_low"] = 1000.0 / max(0.1, p99)
                self.metrics["point_one_percent_low"] = 1000.0 / max(0.1, p999)
                self.metrics["frametime_variance"] = variance
            
        # Detect GC cycle activity
        gc_cur = gc.get_count()
        if gc_cur[0] < self._gc_count_prev[0]:
            self.record_phase_time("gc", 0.8)
        self._gc_count_prev = gc_cur

        # Reset per-frame counters
        self.metrics["draw_calls"] = 0
        self.metrics["surface_ops"] = 0
        self.metrics["blit_count"] = 0
        self.metrics["active_lights"] = 0
        self.metrics["lights_count"] = 0
        self.metrics["active_shadows"] = 0
        self.metrics["shadows"] = 0
        self.metrics["active_particles"] = 0
        self.metrics["particles"] = 0
        self.metrics["ray_count"] = 0
        self.metrics["chunks_rendered"] = 0
        
        # Reset phase timings
        for k in self.phase_times:
            self.phase_times[k] = 0.0

    def render_overlay(self, surface: pygame.Surface) -> None:
        """Renders comprehensive F3 diagnostic HUD."""
        if not self.enabled:
            return

        if self.font_small is None:
            pygame.font.init()
            self.font_small = pygame.font.SysFont("Consolas", 11, bold=False)
            self.font_bold = pygame.font.SysFont("Consolas", 12, bold=True)
            if not self.font_small:
                self.font_small = pygame.font.Font(None, 12)
                self.font_bold = pygame.font.Font(None, 14)

        jit_status = get_jit_info()["backend"]
        pool_stats = SURFACE_POOL.get_stats()
        mem_stats = MEMORY_MANAGER.get_memory_stats()
        self.metrics["ram_mb"] = mem_stats.get("ram_mb", 0.0)
        self.metrics["vram_mb"] = mem_stats.get("vram_mb", 0.0)

        overlay_w = 420
        overlay_h = 320
        x, y = 8, 8

        # Glassmorphic dark container
        bg_surf = pygame.Surface((overlay_w, overlay_h), pygame.SRCALPHA)
        bg_surf.fill((10, 14, 22, 225))
        pygame.draw.rect(bg_surf, (0, 230, 200, 200), (0, 0, overlay_w, overlay_h), width=1, border_radius=5)
        surface.blit(bg_surf, (x, y))

        # Header Title
        title_surf = self.font_bold.render("RUIN RUNNER — ADVANCED ENGINE V3.0 PROFILER", True, (0, 255, 210))
        surface.blit(title_surf, (x + 10, y + 8))

        # Main stats grid
        lines = [
            (f"FPS: {self.fps:5.1f} | Frame: {self.metrics['frametime_ms']:4.2f} ms | Var: {self.metrics['frametime_variance']:4.2f}", (255, 255, 255)),
            (f"1% Low: {self.metrics['one_percent_low']:4.1f} FPS | 0.1% Low: {self.metrics['point_one_percent_low']:4.1f} FPS", (255, 225, 110)),
            (f"P50: {self.metrics['p50_ms']:4.1f}ms | P95: {self.metrics['p95_ms']:4.1f}ms | P99: {self.metrics['p99_ms']:4.1f}ms", (200, 230, 255)),
            (f"Draw Calls: {self.metrics['draw_calls']:3d} | Blits: {self.metrics['blit_count']:3d} | Ops: {self.metrics['surface_ops']:3d}", (220, 220, 220)),
            (f"Entities: {self.metrics['visible_entities']:2d} vis / {self.metrics['culled_entities']:2d} culled | Chunks: {self.metrics['chunks_rendered']:2d}", (190, 255, 190)),
            (f"Particles: {self.metrics['active_particles']:4d} | VFX: {self.metrics['active_vfx']:2d} active", (255, 185, 80)),
            (f"Lights: {self.metrics['active_lights']:2d} | Shadows: {self.metrics['active_shadows']:2d} | Rays: {self.metrics['ray_count']:3d}", (130, 215, 255)),
            (f"RAM RSS: {self.metrics['ram_mb']:5.1f} MB | VRAM: {self.metrics['vram_mb']:4.1f} MB | Pool: {pool_stats['cache_hits']} hits", (255, 160, 225)),
            (f"Resolution: {self.metrics['resolution'][0]}x{self.metrics['resolution'][1]} (Internal: {self.metrics['internal_resolution'][0]}x{self.metrics['internal_resolution'][1]})", (180, 200, 240)),
            (f"Backend: {jit_status} | Quality: {self.metrics['quality_tier']}", (120, 255, 130)),
        ]

        text_y = y + 26
        for text, color in lines:
            rendered = self.font_small.render(text, True, color)
            surface.blit(rendered, (x + 10, text_y))
            text_y += 14

        # Subsystem Phase Timings Breakdown
        phases_title = self.font_bold.render("SUBSYSTEM TIMINGS (ms):", True, (255, 210, 140))
        surface.blit(phases_title, (x + 10, text_y + 2))
        text_y += 16

        p_lines = [
            f"Rndr: {self.phase_times['render_time']:3.1f}ms | Phys: {self.phase_times['physics_time']:3.1f}ms | AI: {self.phase_times['ai_time']:3.1f}ms | Inp: {self.phase_times['input_time']:3.1f}ms",
            f"Lgt: {self.phase_times['lighting_time']:3.1f}ms | Shdw: {self.phase_times['shadow_time']:3.1f}ms | VFX: {self.phase_times['vfx_time']:3.1f}ms | Post: {self.phase_times['postfx_time']:3.1f}ms",
            f"Upscale: {self.phase_times['upscaling_time']:3.1f}ms | Present: {self.phase_times['present_time']:3.1f}ms | GC: {self.phase_times['gc_time']:3.1f}ms"
        ]
        for pl in p_lines:
            rendered = self.font_small.render(pl, True, (230, 230, 210))
            surface.blit(rendered, (x + 10, text_y))
            text_y += 13

        # Frametime Sparkline Graph
        graph_x = x + 10
        graph_y = text_y + 4
        graph_w = overlay_w - 20
        graph_h = 42

        # Background frame for graph
        pygame.draw.rect(surface, (18, 24, 34), (graph_x, graph_y, graph_w, graph_h))
        pygame.draw.rect(surface, (60, 80, 110), (graph_x, graph_y, graph_w, graph_h), width=1)

        # Reference target line: 16.6ms (60 FPS) and 33.3ms (30 FPS)
        ref_60_y = graph_y + graph_h - int((16.66 / 40.0) * graph_h)
        ref_30_y = graph_y + graph_h - int((33.33 / 40.0) * graph_h)
        if graph_y <= ref_60_y <= graph_y + graph_h:
            pygame.draw.line(surface, (0, 255, 120), (graph_x, ref_60_y), (graph_x + graph_w, ref_60_y), 1)
        if graph_y <= ref_30_y <= graph_y + graph_h:
            pygame.draw.line(surface, (255, 80, 80), (graph_x, ref_30_y), (graph_x + graph_w, ref_30_y), 1)

        # Plot data points
        num_points = min(len(self.frametimes), graph_w)
        step_x = graph_w / float(num_points)
        pts = []
        for i in range(num_points):
            idx = len(self.frametimes) - num_points + i
            val = min(40.0, max(0.0, self.frametimes[idx]))
            px = graph_x + int(i * step_x)
            py = graph_y + graph_h - int((val / 40.0) * graph_h)
            pts.append((px, py))

        if len(pts) >= 2:
            pygame.draw.lines(surface, (0, 220, 255), False, pts, 1)

        # Graph label
        lbl_target = self.font_small.render("60 FPS Target (16.6ms)", True, (0, 255, 120))
        surface.blit(lbl_target, (graph_x + 4, ref_60_y - 11))

PROFILER = Profiler()
