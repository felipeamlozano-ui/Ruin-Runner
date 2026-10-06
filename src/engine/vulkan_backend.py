"""Low-Level Vulkan Hardware-Accelerated Render Engine.

Utilizes wgpu-native / Vulkan API to offload fullscreen scaling, letterboxing,
post-processing shaders, and presentation directly to the GPU hardware
(AMD Radeon Graphics / Dedicated GPUs), completely eliminating CPU fill-rate bottlenecks.
"""

import sys
from typing import Optional, Tuple
import pygame

try:
    import wgpu
    _WGPU_AVAILABLE = True
except ImportError:
    _WGPU_AVAILABLE = False


_VULKAN_WGSL_SHADER = """
struct Uniforms {
    viewport: vec4<f32>,  // x: offset_x, y: offset_y, z: width, w: height (normalized 0..1 in NDC)
    params: vec4<f32>,    // x: scanlines (0/1), y: vignette (0/1), z: time, w: reserved
    shockwave: vec4<f32>, // x: center_u, y: center_v, z: radius, w: intensity
};

@group(0) @binding(0) var u_sampler: sampler;
@group(0) @binding(1) var u_texture: texture_2d<f32>;
@group(0) @binding(2) var<uniform> u_data: Uniforms;

struct VertexOutput {
    @builtin(position) pos: vec4<f32>,
    @location(0) uv: vec2<f32>,
};

@vertex
fn vs_main(@builtin(vertex_index) in_vertex_index: u32) -> VertexOutput {
    var quad_pos = array<vec2<f32>, 4>(
        vec2<f32>(-1.0, -1.0),
        vec2<f32>( 1.0, -1.0),
        vec2<f32>(-1.0,  1.0),
        vec2<f32>( 1.0,  1.0)
    );
    var quad_uv = array<vec2<f32>, 4>(
        vec2<f32>(0.0, 1.0),
        vec2<f32>(1.0, 1.0),
        vec2<f32>(0.0, 0.0),
        vec2<f32>(1.0, 0.0)
    );

    var raw_p = quad_pos[in_vertex_index];
    var screen_p = vec2<f32>(
        raw_p.x * u_data.viewport.z + u_data.viewport.x,
        raw_p.y * u_data.viewport.w + u_data.viewport.y
    );

    var out: VertexOutput;
    out.pos = vec4<f32>(screen_p, 0.0, 1.0);
    out.uv = quad_uv[in_vertex_index];
    return out;
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
    var uv = in.uv;

    // Shockwave UV Refraction Distortion
    if (u_data.shockwave.w > 0.0005) {
        var diff = uv - u_data.shockwave.xy;
        var dist = length(diff);
        var sw_r = u_data.shockwave.z;
        var width = 0.07;
        if (dist > sw_r - width && dist < sw_r + width) {
            var diff_norm = (dist - sw_r) / width;
            var falloff = 1.0 - abs(diff_norm);
            var offset = normalize(diff) * sin(diff_norm * 3.14159265) * u_data.shockwave.w * falloff;
            uv = clamp(uv + offset, vec2<f32>(0.0, 0.0), vec2<f32>(1.0, 1.0));
        }
    }

    var col = textureSample(u_texture, u_sampler, uv);

    // Soft Filmic Tonemapping (Reinhard-Jodie style shoulder) to avoid blown-out highlights
    var hdr = col.rgb;
    var luma = dot(hdr, vec3<f32>(0.2126, 0.7152, 0.0722));
    var tc = hdr / (vec3<f32>(1.0, 1.0, 1.0) + hdr);
    col = vec4<f32>(mix(hdr, tc, smoothstep(0.75, 1.0, luma) * 0.35), col.a);

    // Optional hardware scanline effect
    if (u_data.params.x > 0.5) {
        var scan = sin(in.pos.y * 3.14159265) * 0.06;
        col = vec4<f32>(col.rgb * (1.0 - scan), col.a);
    }

    // Optional subtle vignette
    if (u_data.params.y > 0.5) {
        var d = distance(uv, vec2<f32>(0.5, 0.5));
        var vig = smoothstep(0.85, 0.35, d);
        col = vec4<f32>(col.rgb * vig, col.a);
    }

    return col;
}
"""


class VulkanRenderBackend:
    """Hardware accelerated Vulkan render pipeline using wgpu-native."""

    def __init__(self):
        self.available = False
        self.device = None
        self.adapter = None
        self.ctx = None
        self.pipeline = None
        self.sampler = None
        self.tex = None
        self.tex_size = (0, 0)
        self.bind_group = None
        self.uniform_buffer = None
        self.win_size = (0, 0)
        self.adapter_name = "Unavailable"
        self._init_error = None

    def initialize(self, window_size: Tuple[int, int]) -> bool:
        """Initializes the Vulkan device, swapchain and pipelines."""
        if not _WGPU_AVAILABLE:
            self._init_error = "wgpu module is not installed"
            return False

        try:
            wm_info = pygame.display.get_wm_info()
            hwnd = wm_info.get("window")
            if not hwnd:
                self._init_error = "Could not retrieve Win32 HWND from pygame display"
                return False

            self.win_size = window_size
            self.ctx = wgpu.gpu.get_canvas_context({"window": hwnd})
            self.ctx.set_physical_size(window_size[0], window_size[1])

            # Prioritize Vulkan adapter (AMD Radeon / Dedicated GPU)
            adapters = wgpu.gpu.enumerate_adapters_sync()
            vulkan_adapters = [a for a in adapters if "vulkan" in a.summary.lower()]
            if vulkan_adapters:
                self.adapter = vulkan_adapters[0]
            elif adapters:
                self.adapter = adapters[0]
            else:
                self.adapter = wgpu.gpu.request_adapter_sync()

            self.adapter_name = self.adapter.summary
            self.device = self.adapter.request_device_sync()

            # Configure Swapchain Surface
            fmt = self.ctx.get_preferred_format(self.adapter)
            self.ctx.configure(device=self.device, format=fmt)

            # Build WGSL Shader & Render Pipeline
            shader = self.device.create_shader_module(code=_VULKAN_WGSL_SHADER)
            self.sampler = self.device.create_sampler(
                mag_filter="linear",
                min_filter="linear",
                address_mode_u="clamp-to-edge",
                address_mode_v="clamp-to-edge"
            )

            # Uniform buffer for viewport, postfx params and shockwaves (48 bytes = 3x vec4<f32>)
            self.uniform_buffer = self.device.create_buffer(
                size=48,
                usage=wgpu.BufferUsage.UNIFORM | wgpu.BufferUsage.COPY_DST
            )

            self.pipeline = self.device.create_render_pipeline(
                layout="auto",
                vertex={"module": shader, "entry_point": "vs_main"},
                fragment={
                    "module": shader,
                    "entry_point": "fs_main",
                    "targets": [{"format": fmt}]
                },
                primitive={"topology": "triangle-strip"}
            )

            self.available = True
            print(f"[Vulkan Engine] Active Backend: {self.adapter_name}")
            return True

        except Exception as ex:
            self._init_error = str(ex)
            self.available = False
            print(f"[Vulkan Engine] Fallback to Software CPU (Reason: {ex})")
            return False

    def resize(self, new_width: int, new_height: int):
        """Notifies the Vulkan context of window size updates."""
        if not self.available or self.ctx is None:
            return
        if (new_width, new_height) != self.win_size and new_width > 0 and new_height > 0:
            self.win_size = (new_width, new_height)
            try:
                self.ctx.set_physical_size(new_width, new_height)
            except Exception:
                pass

    def trigger_shockwave(
        self,
        center_norm_x: float = 0.5,
        center_norm_y: float = 0.5,
        max_radius: float = 0.45,
        duration: float = 0.40,
        intensity: float = 0.035
    ):
        """Triggers a GPU-accelerated refraction shockwave ring."""
        import time
        self.shockwave_event = {
            "center": (center_norm_x, center_norm_y),
            "start_time": time.time(),
            "duration": duration,
            "max_radius": max_radius,
            "intensity": intensity
        }

    def _ensure_texture(self, width: int, height: int):
        """Ensures the source texture matches the game surface dimensions."""
        if self.tex is not None and self.tex_size == (width, height):
            return

        self.tex = self.device.create_texture(
            size=(width, height, 1),
            usage=wgpu.TextureUsage.TEXTURE_BINDING | wgpu.TextureUsage.COPY_DST,
            format=wgpu.TextureFormat.bgra8unorm
        )
        self.tex_size = (width, height)

        # Update Bind Group with new texture view
        self.bind_group = self.device.create_bind_group(
            layout=self.pipeline.get_bind_group_layout(0),
            entries=[
                {"binding": 0, "resource": self.sampler},
                {"binding": 1, "resource": self.tex.create_view()},
                {"binding": 2, "resource": {"buffer": self.uniform_buffer, "offset": 0, "size": 48}}
            ]
        )

    def render_frame(
        self,
        surface: pygame.Surface,
        target_box: Tuple[int, int, int, int],
        scanlines: bool = False,
        vignette: bool = False,
        time_sec: float = 0.0
    ) -> bool:
        """Transfers the frame to Vulkan texture via zero-copy buffer and renders via GPU hardware."""
        if not self.available or self.device is None:
            return False

        try:
            gw, gh = surface.get_size()
            self._ensure_texture(gw, gh)

            # High-performance zero-copy memoryview from pygame surface (0 CPU allocation!)
            raw_data = surface.get_buffer()
            try:
                self.device.queue.write_texture(
                    {"texture": self.tex},
                    raw_data,
                    {"bytes_per_row": gw * 4, "rows_per_image": gh},
                    (gw, gh, 1)
                )
            finally:
                raw_data.release()

            # Calculate normalized viewport parameters in NDC (-1..1 range)
            target_x, target_y, target_w, target_h = target_box
            sw, sh = self.win_size
            if sw <= 0 or sh <= 0:
                sw, sh = target_w, target_h

            scale_x = target_w / sw
            scale_y = target_h / sh
            offset_x = (2.0 * target_x + target_w - sw) / sw
            offset_y = (sh - 2.0 * target_y - target_h) / sh

            # Shockwave animation progression
            import time
            sw_data = (0.5, 0.5, 0.0, 0.0)
            if getattr(self, "shockwave_event", None):
                ev = self.shockwave_event
                elapsed = time.time() - ev["start_time"]
                progress = elapsed / ev["duration"]
                if progress >= 1.0:
                    self.shockwave_event = None
                else:
                    cx, cy = ev["center"]
                    radius = ev["max_radius"] * progress
                    intens = ev["intensity"] * (1.0 - progress)
                    sw_data = (cx, cy, radius, intens)

            # Pack uniforms (12 x float32 = 48 bytes)
            import struct
            uniform_bytes = struct.pack(
                "12f",
                offset_x, offset_y, scale_x, scale_y,
                1.0 if scanlines else 0.0,
                1.0 if vignette else 0.0,
                float(time_sec),
                0.0,
                sw_data[0], sw_data[1], sw_data[2], sw_data[3]
            )
            self.device.queue.write_buffer(self.uniform_buffer, 0, uniform_bytes)


            # Acquire current swapchain target
            current_tex = self.ctx.get_current_texture()
            encoder = self.device.create_command_encoder()

            # Begin Render Pass: Clear to dark letterbox color (10, 10, 15)
            render_pass = encoder.begin_render_pass(
                color_attachments=[{
                    "view": current_tex.create_view(),
                    "resolve_target": None,
                    "clear_value": (10 / 255.0, 10 / 255.0, 15 / 255.0, 1.0),
                    "load_op": "clear",
                    "store_op": "store"
                }]
            )
            render_pass.set_pipeline(self.pipeline)
            render_pass.set_bind_group(0, self.bind_group)
            render_pass.draw(4, 1, 0, 0)
            render_pass.end()

            self.device.queue.submit([encoder.finish()])
            self.ctx.present()
            return True

        except Exception as ex:
            # On swapchain resize / minimize or error, allow seamless CPU fallback
            return False


def is_vulkan_available() -> bool:
    """Returns True if Vulkan/wgpu is available on this system."""
    if not _WGPU_AVAILABLE:
        return False
    try:
        adapters = wgpu.gpu.enumerate_adapters_sync()
        return any("vulkan" in a.summary.lower() for a in adapters) or len(adapters) > 0
    except Exception:
        return False

