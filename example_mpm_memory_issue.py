"""Minimal implicit MPM setup to reproduce GPU memory growth/OOM."""

import math
import os
import sys
from pathlib import Path

import numpy as np
import psutil
import pynvml
import warp as wp

import newton
import newton.viewer
from newton.solvers import SolverImplicitMPM

# Tunable parameters for the repro
WORLD_SPACING = 4.0
NUM_WORLDS = 256
PARTICLES_PER_WORLD = 8000

NUM_STEPS = 10000
FPS = 30.0
SUBSTEPS = 1
DT = 1.0 / FPS / SUBSTEPS

VOXEL_SIZE = 0.15
TOLERANCE = 1.0e-7
MAX_ITERATIONS = 200
TRANSFER_SCHEME = "apic"
GRID_TYPE = "fixed"
PARTICLE_RADIUS = 0.025
PARTICLE_MASS = 1.0
PARTICLE_HEIGHT = 0.5

LOG_DIR = Path("mpm_memory_issue_output")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "memory_log.txt"

USE_VIEWER = "--viewer" in sys.argv
if USE_VIEWER:
    sys.argv.remove("--viewer")

def process_cpu_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / (1024.0**2)


def process_gpu_mb() -> float:
    total_bytes = 0
    pid = os.getpid()
    device_count = pynvml.nvmlDeviceGetCount()

    for idx in range(device_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(idx)
        procs = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
        for proc in procs:
            used = getattr(proc, "usedGpuMemory", None)
            if used and proc.pid == pid:
                total_bytes += used

    return total_bytes / (1024.0**2)


def world_positions(origin: np.ndarray, radius: float) -> list[np.ndarray]:
    if PARTICLES_PER_WORLD == 1:
        return [origin.copy()]
    spacing = max(radius * 4.0, 1e-3)
    per_axis = math.ceil(PARTICLES_PER_WORLD ** (1.0 / 3.0))
    positions: list[np.ndarray] = []
    for index in range(PARTICLES_PER_WORLD):
        ix = index % per_axis
        iy = (index // per_axis) % per_axis
        iz = index // (per_axis * per_axis)
        offset = np.array([ix, iy, iz], dtype=float) * spacing
        positions.append(origin + offset)
    return positions


def main():
    pynvml.nvmlInit()

    builder = newton.ModelBuilder()
    builder.add_ground_plane()

    for world_id in range(NUM_WORLDS):
        builder.current_world = world_id
        origin = np.array([WORLD_SPACING * world_id, 0.0, PARTICLE_HEIGHT], dtype=float)
        positions = world_positions(origin, PARTICLE_RADIUS)
        pos_vecs = [wp.vec3(float(p[0]), float(p[1]), float(p[2])) for p in positions]
        zero_vel = [wp.vec3(0.0, 0.0, 0.0) for _ in pos_vecs]
        masses = [PARTICLE_MASS] * len(pos_vecs)
        radii = [PARTICLE_RADIUS] * len(pos_vecs)
        builder.add_particles(pos_vecs, zero_vel, masses, radius=radii, flags=None)

    model = builder.finalize()
    model.set_gravity((0.0, 0.0, -1.0))
    model.particle_mu = 1.0
    model.particle_ke = 1.0e15

    mpm_options = SolverImplicitMPM.Options()
    mpm_options.voxel_size = VOXEL_SIZE
    mpm_options.tolerance = TOLERANCE
    mpm_options.max_iterations = MAX_ITERATIONS
    mpm_options.transfer_scheme = TRANSFER_SCHEME
    mpm_options.grid_type = GRID_TYPE

    if GRID_TYPE == "fixed":
        mpm_options.grid_padding = 10  # number of cells to add around the particles (account for particle motion)
        mpm_options.max_active_cell_count = 1 << 20  # max number of cells

    mpm_model = SolverImplicitMPM.Model(model, mpm_options)
    state_0 = model.state()
    state_1 = model.state()
    solver = SolverImplicitMPM(mpm_model, mpm_options)
    solver.enrich_state(state_0)
    solver.enrich_state(state_1)

    viewer = None
    if USE_VIEWER:
        try:
            viewer = newton.viewer.ViewerGL(headless=False)
            viewer.set_model(model)
            viewer.show_joints = False
            viewer.show_particles = True
            viewer.show_visual = False
        except Exception as exc:  # simple repro, so just print and continue headless
            print(f"Viewer initialization failed: {exc}")
            viewer = None

    with LOG_PATH.open("w", encoding="utf-8") as log_file:
        log_file.write("# step cpu_mb gpu_mb\n")
        cpu = process_cpu_mb()
        gpu = process_gpu_mb()
        log_file.write(f"0 {cpu:.2f} {gpu:.2f}\n")
        print(f"step {0:6d} cpu={cpu:9.2f} MiB gpu={gpu:9.2f} MiB")

        if viewer is not None:
            viewer.begin_frame(0.0)
            viewer.log_state(state_0)
            viewer.end_frame()

        def step_impl():
            for _ in range(SUBSTEPS):
                state_0.clear_forces()
                solver.step(state_0, state_0, None, None, DT)
                solver.project_outside(state_0, state_0, DT)

        with wp.ScopedCapture() as capture:
            step_impl()
        graph = capture.graph

        for step in range(1, NUM_STEPS + 1):
            wp.capture_launch(graph)

            cpu = process_cpu_mb()
            gpu = process_gpu_mb()
            log_file.write(f"{step} {cpu:.2f} {gpu:.2f}\n")
            if step % 100 == 0:
                print(f"step {step:6d} cpu={cpu:9.2f} MiB gpu={gpu:9.2f} MiB")
            log_file.flush()

            if viewer is not None:
                viewer.begin_frame(step * DT)
                viewer.log_state(state_0)
                viewer.end_frame()
                if not viewer.is_running():
                    break

    if viewer is not None:
        viewer.close()


if __name__ == "__main__":
    main()
