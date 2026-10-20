# Graph Report - ruin_runner  (2026-10-05)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1926 nodes · 4035 edges · 127 communities (42 shown, 85 thin omitted)
- Extraction: 91% EXTRACTED · 9% INFERRED · 0% AMBIGUOUS · INFERRED: 361 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bc43a570`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Ultimate AoE VFX
- Neural AI Controller
- VFX Math Utilities
- Game Scene Management
- Engine Core Modules
- Configuration and Profiling
- Camera and Visuals
- Input Management System
- Procedural Particle VFX
- Native Raycasting Engine
- Arcane Visual Effects
- Animation State Manager
- Sprite Animation Handler
- Engine Performance Pipeline
- JIT Compilation Backend
- Phase Timing Utilities
- Settings Menu UI
- Enemy Combat Logic
- Benchmark Suite
- ECS Component Definitions
- Scene Lifecycle Manager
- ECS World System
- Player Character Controller
- Co-op Synergy System
- Enemy Combat Visuals
- Character Data Management
- Lighting and Shadows
- Tilemap Chunk Renderer
- Spatial Partitioning QuadTree
- Dynamic Impact Particles
- F3 Debug Profiler
- Combat Feedback Manager
- VFX Budget Manager
- Skeleton Enemy Logic
- UI Rendering Helpers
- Async Task Worker
- Procedural Physics Simulation
- Particle and Weather Engine
- SIMD Particle Integrator
- Sprite Sheet Assembly
- Character Sprite Generator
- Asset Resource Manager
- Screen Post-Processing
- Temporal Super Resolution
- Projectile Combat System
- Color Grading Engine
- Procedural Geometry Engine
- Main Game Loop
- Adaptive Quality Governor
- Elemental Particle Effects
- Sprite Atlas Pipeline
- Native C Bridge
- Tilemap Integration
- Character Portrait Utilities
- Dynamic Camera System
- Master Render Pipeline
- Ether Convergence Ultimate
- Inferno Ultimate VFX
- Menu UI Screens
- SDF Raymarching Engine
- ECS Physics System
- Normal Map Shading
- Static Radiance Cache
- Master Sprite Atlas
- Robust Sprite Processor
- Engine Diagnostics HUD
- AABB Collision Physics
- Memory and GC Manager
- Volumetric Lighting Engine
- Motion Trail Renderer
- Glacial Blizzard VFX
- Shadow Clone Ultimate
- Menu Navigation Base
- Game State Manager
- Tactical Synergy UI
- Projectile Trajectory Logic
- Destructible Prop Physics
- Dragon Fury Ultimate
- Shadow Polygon Projection
- HDR Bloom Engine
- FidelityFX Upscaling Kernels
- Temporal Accumulation Resolver
- Environmental Ember Particles
- Player HUD UI
- Pixel Art Generator
- Character Selection Tests
- Decoupled Event Bus
- Ambient Occlusion Baker
- FSR 2D Engine
- Cosmic Singularity VFX
- Valkyrie Judgment Ultimate
- Atmospheric Prop Animation
- Surface Memory Pool
- ECS Entity Adapter
- Dimensional Slash VFX
- Telluric Cataclysm Ultimate
- Checkpoint Save System
- .execute
- MarchingSquares
- SplineRenderer
- materials.py
- ShaiaDivineJudgementVFX
- CherryBlossomUltimate
- KaelenCelestialVolleyUltimate
- ShadowStormUltimate
- AmbientParticle
- LightSource
- AureliaDawnMiracleUltimate
- GlaciationUltimate
- SupernovaUltimate
- EnergyStreak
- HolyCrossParticle
- LeafWindParticle
- SmokeParticle
- StardustParticle
- WindCrescentParticle
- ShockwaveRingParticle
- build_native.sh
- test_clamp_color_safety

## God Nodes (most connected - your core abstractions)
1. `TestRuinEngineV3` - 65 edges
2. `Player` - 55 edges
3. `CharacterSelectScene` - 51 edges
4. `LevelScene` - 42 edges
5. `BossScene` - 40 edges
6. `SettingsMenuScene` - 39 edges
7. `SkeletonBoss` - 38 edges
8. `MainMenuScene` - 35 edges
9. `Projectile` - 34 edges
10. `AnimationManager` - 30 edges

## Surprising Connections (you probably didn't know these)
- `test_character_animations()` --uses--> `Player`  [INFERRED]
  scratch/test_character_select_and_coop.py → src/entities/player.py
- `main()` --uses--> `Game`  [INFERRED]
  main.py → src/engine/game.py
- `test_all_characters_and_skills()` --uses--> `UltimateAoE_VFX`  [INFERRED]
  scratch/test_skills_and_characters.py → src/entities/ultimate_aoe_vfx.py
- `test_polymorphic_subclass_dispatch()` --uses--> `UltimateAoE_VFX`  [INFERRED]
  tests/test_ultimate_aoe_vfx.py → src/entities/ultimate_aoe_vfx.py
- `test_coop_character_select()` --uses--> `CharacterSelectScene`  [INFERRED]
  scratch/test_character_select_and_coop.py → src/scenes/character_select_scene.py

## Import Cycles
- None detected.

## Communities (127 total, 85 thin omitted)

### Community 0 - "Ultimate AoE VFX"
Cohesion: 0.06
Nodes (3): UltimateAoE_VFX, CharacterSelectScene, test_full_vfx_simulation_and_render_all_heroes()

### Community 1 - "Neural AI Controller"
Cohesion: 0.05
Nodes (4): NeuralTacticalAI, _BossParticle, BossShockwave, SkeletonBoss

### Community 2 - "VFX Math Utilities"
Cohesion: 0.12
Nodes (11): clamp(), clamp_color(), ease_in_back(), ease_in_expo(), ease_in_out_quad(), ease_in_quad(), ease_out_back(), ease_out_elastic() (+3 more)

### Community 3 - "Game Scene Management"
Cohesion: 0.08
Nodes (10): Collectible, BossScene, WaterDroplet, LevelScene, LoadingScene, MainMenuScene, test_dev_mode_workflow(), test_game_full_loop() (+2 more)

### Community 6 - "Camera and Visuals"
Cohesion: 0.08
Nodes (3): CameraV3, clamp(), lerp()

### Community 7 - "Input Management System"
Cohesion: 0.08
Nodes (3): InputAction, InputManager, PlayerInput

### Community 8 - "Procedural Particle VFX"
Cohesion: 0.08
Nodes (9): AureliaSanctuaryAoE_VFX, BaseVFXParticle, BoranSeismicWaveAoE_VFX, ease_out_quad(), IgnisVolcanicEruptionVFX, KaelenArrowRainAoE_VFX, VolcanicCinder, VolcanicSmokePuff (+1 more)

### Community 9 - "Native Raycasting Engine"
Cohesion: 0.09
Nodes (10): ray_segment_intersect_jit(), has_native(), native_compute_soft_shadow_mask(), native_compute_visibility_rays(), native_integrate_particles(), native_neural_adapt(), native_neural_forward(), native_pixel_aa_sharp_bilinear() (+2 more)

### Community 10 - "Arcane Visual Effects"
Cohesion: 0.08
Nodes (6): AfterImage, draw_sacred_runic_circle(), ImpactSmoke, UltimateEnergyParticle, UltimateShockwaveRing, UltimateSlash

### Community 11 - "Animation State Manager"
Cohesion: 0.11
Nodes (5): AnimationManager, load_animation_folder(), load_spritesheet(), Portal, Prop

### Community 12 - "Sprite Animation Handler"
Cohesion: 0.10
Nodes (13): Animation, _get_fallback_anim(), get_fireball_anims(), get_high_dpi_palette(), get_purple_sphere_anims(), get_shuriken_anims(), get_sphere_projectile_anims(), get_vacuum_slash_anims() (+5 more)

### Community 14 - "JIT Compilation Backend"
Cohesion: 0.10
Nodes (12): is_jit_enabled(), jit_compile(), op_intersect(), op_smooth_union(), op_subtract(), op_union(), sdf_box(), sdf_capsule() (+4 more)

### Community 17 - "Enemy Combat Logic"
Cohesion: 0.13
Nodes (3): Enemy, _Particle, WildBoar

### Community 18 - "Benchmark Suite"
Cohesion: 0.12
Nodes (11): main(), run_scenario(), setup_boss_scene(), setup_level_scene(), setup_max_particles(), setup_max_vfx(), update_draw_boss(), update_draw_level() (+3 more)

### Community 19 - "ECS Component Definitions"
Cohesion: 0.11
Nodes (16): AnimationComponent, CameraTargetComponent, ColliderComponent, EnemyAIComponent, LightSourceComponent, LootDropComponent, ManaComponent, ParticleEmitterComponent (+8 more)

### Community 20 - "Scene Lifecycle Manager"
Cohesion: 0.08
Nodes (3): SceneManager, test_character_select_all_profiles(), TestFullGameDiagnostics

### Community 24 - "Enemy Combat Visuals"
Cohesion: 0.12
Nodes (3): MageSkeleton, SpikeTrap, run_tests()

### Community 25 - "Character Data Management"
Cohesion: 0.12
Nodes (5): test_all_characters_and_skills(), CharacterProfile, get_character_profile(), SkillData, test_player_integration_aoe_visuals()

### Community 29 - "Dynamic Impact Particles"
Cohesion: 0.12
Nodes (4): BloodDripParticle, EarthRubbleParticle, KiRingParticle, ShadowMistParticle

### Community 31 - "Combat Feedback Manager"
Cohesion: 0.11
Nodes (3): HitEffectsManager, Shockwave, Spark

### Community 32 - "VFX Budget Manager"
Cohesion: 0.17
Nodes (4): SkillVFXProfile, VFX_LOD, VFXBudgetManager, VFXPriority

### Community 36 - "Procedural Physics Simulation"
Cohesion: 0.12
Nodes (3): ProceduralLava, ProceduralWater, VerletRope

### Community 39 - "Sprite Sheet Assembly"
Cohesion: 0.33
Nodes (10): assemble_jump_frame(), assemble_single_character_frame(), build_perfect_archer(), build_perfect_aurelia(), build_perfect_boran(), build_perfect_zephyr(), clean_crop_transparency(), main() (+2 more)

### Community 40 - "Character Sprite Generator"
Cohesion: 0.33
Nodes (11): assemble_jump_frame(), assemble_pose_frame(), build_archer(), build_aurelia(), build_boran(), build_zephyr(), clean_crop_transparency(), main() (+3 more)

### Community 47 - "Main Game Loop"
Cohesion: 0.19
Nodes (3): run_smoke_test(), Game, Timer

### Community 50 - "Elemental Particle Effects"
Cohesion: 0.13
Nodes (4): BaseParticle, IceShardParticle, ImpactSparkStreak, RuneSparkParticle

### Community 51 - "Sprite Atlas Pipeline"
Cohesion: 0.14
Nodes (4): clean_extract_pose(), place_in_safe_cell(), place_jump_in_safe_cell(), extract_clean_sprite()

### Community 52 - "Native C Bridge"
Cohesion: 0.24
Nodes (9): c_compute_soft_shadow_mask(), c_compute_visibility_rays(), c_integrate_particles_soa(), c_neural_adapt(), c_neural_forward(), c_pixel_aa_sharp_bilinear(), c_rcas_sharpen_image(), c_tsr_reproject_and_validate() (+1 more)

### Community 54 - "Character Portrait Utilities"
Cohesion: 0.26
Nodes (7): build_all(), extract_rows_and_sprites(), fit_to_craftpix_frame(), flood_fill_transparency(), get_bounding_box(), make_portrait(), make_strip()

### Community 56 - "Master Render Pipeline"
Cohesion: 0.20
Nodes (4): MasterRenderPipeline, LightRayCaster, AntiAliasingEngine, run_benchmarks()

### Community 61 - "ECS Physics System"
Cohesion: 0.32
Nodes (8): HealthComponent, HitboxComponent, HurtboxComponent, PhysicsComponent, TransformComponent, CombatHitboxSystem, PhysicsSystem, TestRuinEngineV3

### Community 64 - "Master Sprite Atlas"
Cohesion: 0.27
Nodes (8): build_diagnostic_validation_image(), clean_extract_pose(), generate_all(), make_portrait(), make_strip(), place_dead_in_safe_cell(), place_in_safe_cell(), place_jump_in_safe_cell()

### Community 65 - "Robust Sprite Processor"
Cohesion: 0.33
Nodes (8): main(), make_breathing_idle(), process_character(), assemble_anchored_frame(), find_sprite_columns(), flood_fill_transparency(), make_portrait(), make_strip()

### Community 67 - "AABB Collision Physics"
Cohesion: 0.20
Nodes (3): AABB, resolve_collision_x(), resolve_collision_y()

### Community 71 - "Glacial Blizzard VFX"
Cohesion: 0.20
Nodes (3): AstraShardBlizzardVFX, DiamondDustParticle, ShardSpikeData

### Community 72 - "Shadow Clone Ultimate"
Cohesion: 0.18
Nodes (4): CloneDashVector, RyuuKiDomainVFX, ShinobiShadowDanceVFX, test_polymorphic_subclass_dispatch()

### Community 74 - "Game State Manager"
Cohesion: 0.33
Nodes (3): Direction, GameState, GameStateManager

### Community 76 - "Projectile Trajectory Logic"
Cohesion: 0.29
Nodes (3): LinearTrajectory, Trajectory, WaveTrajectory

### Community 86 - "Pixel Art Generator"
Cohesion: 0.36
Nodes (3): create_character_sprites(), _draw_humanoid(), _draw_portrait()

### Community 88 - "Character Selection Tests"
Cohesion: 0.36
Nodes (5): MockSceneManager, test_character_animations(), test_coop_character_select(), test_settings_menu_no_p2(), test_solo_character_select()

### Community 98 - "Telluric Cataclysm Ultimate"
Cohesion: 0.38
Nodes (3): BoranTelluricCataclysmUltimate, create_ultimate(), ease_out_back()

### Community 104 - "materials.py"
Cohesion: 0.53
Nodes (3): get_material(), Material2D, MaterialType

## Knowledge Gaps
- **10 isolated node(s):** `QualityProfile`, `CameraTargetComponent`, `LootDropComponent`, `ShadowCasterComponent`, `StateMachineComponent` (+5 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 802 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **85 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TestRuinEngineV3` connect `ECS Physics System` to `Engine Core Modules`, `Camera and Visuals`, `JIT Compilation Backend`, `ECS World System`, `Tilemap Chunk Renderer`, `Spatial Partitioning QuadTree`, `F3 Debug Profiler`, `Combat Feedback Manager`, `Procedural Physics Simulation`, `Particle and Weather Engine`, `Color Grading Engine`, `Adaptive Quality Governor`, `Surface Pool Management`, `Master Render Pipeline`, `SDF Raymarching Engine`, `Normal Map Shading`, `Engine Diagnostics HUD`, `Memory and GC Manager`, `Volumetric Lighting Engine`, `Motion Trail Renderer`, `Spline Ribbon Renderer`, `Shadow Polygon Projection`, `HDR Bloom Engine`, `Temporal Accumulation Resolver`, `Ambient Occlusion Baker`, `FSR 2D Engine`, `Surface Memory Pool`, `MarchingSquares`, `SplineRenderer`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Why does `CharacterSelectScene` connect `Ultimate AoE VFX` to `Game Scene Management`, `Configuration and Profiling`, `Projectile Combat System`, `Scene Lifecycle Manager`, `Player Character Controller`, `Character Selection Tests`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `Player` connect `Player Character Controller` to `Ultimate AoE VFX`, `Skeleton Enemy Logic`, `Game Scene Management`, `Configuration and Profiling`, `Arcane Visual Effects`, `Animation State Manager`, `Projectile Combat System`, `HDR Bloom Engine`, `Scene Lifecycle Manager`, `Player HUD UI`, `Dynamic Camera System`, `Co-op Synergy System`, `Character Selection Tests`, `Character Data Management`, `Menu UI Screens`, `Enemy Combat Visuals`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Are the 36 inferred relationships involving `TestRuinEngineV3` (e.g. with `CameraV3` and `AdaptiveQualityGovernor`) actually correct?**
  _`TestRuinEngineV3` has 36 INFERRED edges - model-reasoned connections that need verification._
- **Are the 23 inferred relationships involving `Player` (e.g. with `test_character_animations()` and `test_all_characters_and_skills()`) actually correct?**
  _`Player` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `CharacterSelectScene` (e.g. with `test_coop_character_select()` and `test_solo_character_select()`) actually correct?**
  _`CharacterSelectScene` has 15 INFERRED edges - model-reasoned connections that need verification._
- **What connects `QualityProfile`, `CameraTargetComponent`, `LootDropComponent` to the rest of the system?**
  _10 weakly-connected nodes found - possible documentation gaps or missing edges._