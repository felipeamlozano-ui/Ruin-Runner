//! Ruin Rust Core — Multi-Threaded High Performance Engine Extension
//! Built with PyO3, Rayon, and NumPy Zero-Copy Memory Views.
//! Offloads particle simulation, spatial hashing broadphase, and pathfinding
//! from Python to native Rayon CPU threads, bypassing the Python GIL.

use pyo3::prelude::*;
use numpy::{PyArray1, PyReadonlyArray1, PyReadwriteArray1};
use rayon::prelude::*;
use std::cmp::Ordering;
use std::collections::{BinaryHeap, HashMap};

/// Particle integration state updated in parallel with Rayon
#[pyfunction]
fn simulate_particles_rayon<'py>(
    py: Python<'py>,
    mut pos_x: PyReadwriteArray1<'py, f32>,
    mut pos_y: PyReadwriteArray1<'py, f32>,
    mut vel_x: PyReadwriteArray1<'py, f32>,
    mut vel_y: PyReadwriteArray1<'py, f32>,
    mut life: PyReadwriteArray1<'py, f32>,
    max_life: PyReadonlyArray1<'py, f32>,
    count: usize,
    dt: f32,
    gravity: f32,
    drag: f32,
    floor_y: f32,
    bounce: f32,
) -> PyResult<usize> {
    let px = pos_x.as_slice_mut()?;
    let py_slice = pos_y.as_slice_mut()?;
    let vx = vel_x.as_slice_mut()?;
    let vy = vel_y.as_slice_mut()?;
    let lf = life.as_slice_mut()?;
    let ml = max_life.as_slice()?;

    let n = count.min(px.len()).min(py_slice.len()).min(vx.len()).min(vy.len()).min(lf.len()).min(ml.len());

    // Release GIL for multi-threaded Rayon execution
    let alive_count = py.allow_threads(move || {
        // Zip slices into chunks and process with Rayon par_iter_mut
        let mut indices: Vec<usize> = (0..n).collect();
        let chunk_size = 256.max(n / (rayon::current_num_threads().max(1) * 4));

        indices.par_chunks_mut(chunk_size).for_each(|chunk| {
            for &idx in chunk.iter() {
                if lf[idx] <= 0.0 {
                    continue;
                }

                // Update Lifetime
                lf[idx] -= dt;
                if lf[idx] <= 0.0 {
                    lf[idx] = 0.0;
                    continue;
                }

                // Apply Drag & Gravity
                vx[idx] *= 1.0 - drag * dt;
                vy[idx] = (vy[idx] + gravity * dt) * (1.0 - drag * dt);

                // Integrate Kinematics
                px[idx] += vx[idx] * dt;
                py_slice[idx] += vy[idx] * dt;

                // Ground bounce / Floor collision
                if floor_y > 0.0 && py_slice[idx] >= floor_y {
                    py_slice[idx] = floor_y;
                    vy[idx] = -vy[idx] * bounce;
                    vx[idx] *= 0.85; // friction on ground contact
                }
            }
        });

        // Count remaining active particles
        lf[..n].iter().filter(|&&val| val > 0.0).count()
    });

    Ok(alive_count)
}

/// AABB Spatial Hashing for broadphase collision detection
#[pyfunction]
fn broadphase_spatial_hash<'py>(
    py: Python<'py>,
    rects_x: PyReadonlyArray1<'py, f32>,
    rects_y: PyReadonlyArray1<'py, f32>,
    rects_w: PyReadonlyArray1<'py, f32>,
    rects_h: PyReadonlyArray1<'py, f32>,
    cell_size: f32,
) -> PyResult<Vec<(usize, usize)>> {
    let rx = rects_x.as_slice()?;
    let ry = rects_y.as_slice()?;
    let rw = rects_w.as_slice()?;
    let rh = rects_h.as_slice()?;
    let count = rx.len().min(ry.len()).min(rw.len()).min(rh.len());

    let cs = if cell_size > 1.0 { cell_size } else { 64.0 };

    let pairs = py.allow_threads(move || {
        let mut grid: HashMap<(i32, i32), Vec<usize>> = HashMap::new();

        // 1. Insert AABBs into spatial grid
        for i in 0..count {
            let min_cx = (rx[i] / cs).floor() as i32;
            let max_cx = ((rx[i] + rw[i]) / cs).floor() as i32;
            let min_cy = (ry[i] / cs).floor() as i32;
            let max_cy = ((ry[i] + rh[i]) / cs).floor() as i32;

            for cx in min_cx..=max_cx {
                for cy in min_cy..=max_cy {
                    grid.entry((cx, cy)).or_default().push(i);
                }
            }
        }

        // 2. Query grid cells for overlapping candidates
        let mut candidate_pairs: Vec<(usize, usize)> = Vec::new();
        let mut seen: HashMap<(usize, usize), bool> = HashMap::new();

        for (_cell, items) in grid.iter() {
            if items.len() < 2 {
                continue;
            }
            for i in 0..items.len() {
                for j in (i + 1)..items.len() {
                    let a = items[i].min(items[j]);
                    let b = items[i].max(items[j]);
                    if a != b && !seen.contains_key(&(a, b)) {
                        seen.insert((a, b), true);
                        // Fast AABB intersection check
                        if rx[a] < rx[b] + rw[b]
                            && rx[a] + rw[a] > rx[b]
                            && ry[a] < ry[b] + rh[b]
                            && ry[a] + rh[a] > ry[b]
                        {
                            candidate_pairs.push((a, b));
                        }
                    }
                }
            }
        }

        candidate_pairs
    });

    Ok(pairs)
}

#[derive(Copy, Clone, Eq, PartialEq)]
struct State {
    cost: usize,
    position: (usize, usize),
}

impl Ord for State {
    fn cmp(&self, other: &Self) -> Ordering {
        other.cost.cmp(&self.cost)
    }
}

impl PartialOrd for State {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// A* Grid Pathfinding running in native code
#[pyfunction]
fn astar_pathfind<'py>(
    py: Python<'py>,
    grid: PyReadonlyArray1<'py, u8>,
    grid_w: usize,
    grid_h: usize,
    start_x: usize,
    start_y: usize,
    goal_x: usize,
    goal_y: usize,
) -> PyResult<Vec<(usize, usize)>> {
    let grid_slice = grid.as_slice()?;

    if start_x >= grid_w || start_y >= grid_h || goal_x >= grid_w || goal_y >= grid_h {
        return Ok(Vec::new());
    }

    let path = py.allow_threads(move || {
        let mut dist: Vec<usize> = vec![usize::MAX; grid_w * grid_h];
        let mut came_from: Vec<Option<(usize, usize)>> = vec![None; grid_w * grid_h];
        let mut heap = BinaryHeap::new();

        let start_idx = start_y * grid_w + start_x;
        dist[start_idx] = 0;
        heap.push(State {
            cost: 0,
            position: (start_x, start_y),
        });

        let neighbors: [(i32, i32); 4] = [(0, -1), (0, 1), (-1, 0), (1, 0)];

        while let Some(State { cost, position }) = heap.pop() {
            let (x, y) = position;

            if x == goal_x && y == goal_y {
                let mut curr = (x, y);
                let mut result = vec![curr];
                while let Some(prev) = came_from[curr.1 * grid_w + curr.0] {
                    result.push(prev);
                    curr = prev;
                }
                result.reverse();
                return result;
            }

            let idx = y * grid_w + x;
            if cost > dist[idx] {
                continue;
            }

            for &(dx, dy) in &neighbors {
                let nx = x as i32 + dx;
                let ny = y as i32 + dy;

                if nx >= 0 && nx < grid_w as i32 && ny >= 0 && ny < grid_h as i32 {
                    let unx = nx as usize;
                    let uny = ny as usize;
                    let n_idx = uny * grid_w + unx;

                    // 0 = walkable, 1 = solid/blocked
                    if grid_slice[n_idx] == 0 {
                        let next_cost = cost + 1;
                        if next_cost < dist[n_idx] {
                            dist[n_idx] = next_cost;
                            came_from[n_idx] = Some((x, y));
                            let h = (unx as i32 - goal_x as i32).abs() + (uny as i32 - goal_y as i32).abs();
                            heap.push(State {
                                cost: next_cost + h as usize,
                                position: (unx, uny),
                            });
                        }
                    }
                }
            }
        }

        Vec::new()
    });

    Ok(path)
}

/// PyO3 Module definition
#[pymodule]
fn ruin_rust_core(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(simulate_particles_rayon, m)?)?;
    m.add_function(wrap_pyfunction!(broadphase_spatial_hash, m)?)?;
    m.add_function(wrap_pyfunction!(astar_pathfind, m)?)?;
    Ok(())
}
