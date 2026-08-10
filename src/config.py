"""Central configuration for the portfolio graph visualiser.

This module imports nothing from the rest of the package, so it is safe to
import from anywhere without creating a cycle.
"""

from pathlib import Path

# --- Paths ----------------------------------------------------------------------------
SRC_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = SRC_DIR.parent
STATIC_DIR: Path = PROJECT_ROOT / "static"
GRAPH_YAML: Path = SRC_DIR / "graph.yaml"

# --- Colours --------------------------------------------------------------------------
COLOR_BG: str = "#101010"
COLOR_NODES: str = "#ff8f40"
COLOR_EDGES: str = "#bbb9b2"

# --- Scene bounds and layout ----------------------------------------------------------
AXIS_MIN: int = 0
AXIS_MAX: int = 100
SPAWN_MARGIN: int = 10
RNG_SEED: int = 3
LAYOUT_SEED: int = 3
LAYOUT_ITERATIONS: int = 100
LAYOUT_PADDING: int = 3  # Inset from the axis bounds for the converged layout.

# --- Camera ---------------------------------------------------------------------------
ELEV0: float = 30.0
AZIM0: float = 100.0
ZOOM: float = 1.4
FOCAL_LENGTH: float = 0.25

# --- Camera motion --------------------------------------------------------------------
# Every term is sin(2*pi * k * t + phase) with a whole-number k, so the loop closes
# in both position and velocity. Amplitudes are in degrees. Raising any of these
# blurs the labels; re-run the motion probe before you do.
AZIM_AMPLITUDE: float = 16.0  # Sweeps AZIM0 +/- this, one cycle per loop.
ELEV_AMPLITUDE: float = 7.0  # First harmonic.
ELEV_AMPLITUDE_3: float = 2.0  # Third harmonic, breaks the metronome feel.
ELEV_PHASE: float = 1.1  # Radians. Desynchronises elevation from azimuth.
ROLL_AMPLITUDE: float = 2.0  # Second harmonic. Small on purpose.
ROLL_PHASE: float = 0.6

# --- Render geometry ------------------------------------------------------------------
# FIGSIZE is the layout knob and DPI is the resolution knob. An element's size
# relative to the frame is size_pt / (72 * FIGSIZE[0]), so changing FIGSIZE
# rescales everything in the scene, while changing DPI only adds pixels.
# Raise DPI to sharpen. Do not touch FIGSIZE.
# 19.2 * 250 = 4800 and 10.8 * 250 = 2700, a 1.875x supersample of the target.
FIGSIZE: tuple[float, float] = (19.2, 10.8)
DPI: int = 250
TARGET_WIDTH: int = 2560
TARGET_HEIGHT: int = 1440
LABEL_FONT_SIZE: int = 10

# --- Video ----------------------------------------------------------------------------
FPS: int = 30
ORBIT_SECONDS: int = 30
LOOP_FRAMES: int = FPS * ORBIT_SECONDS
DEG_PER_FRAME: float = 360 / LOOP_FRAMES  # Intro clip only.
CRF: int = 20
PRESET: str = "slow"
VIDEO_FILTERS: str = f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:flags=lanczos"

# --- Interactive preview (main.py) ----------------------------------------------------
PREVIEW_FPS: int = 60
PREVIEW_SECONDS: int = 10

# --- Node drift -----------------------------------------------------------------------
# Per-node sinusoidal wander around the converged layout, in axis units (the
# scene spans AXIS_MIN..AXIS_MAX). Each node gets its own random phase per
# harmonic so they do not breathe in unison. Peak node speed is
# sum(A_k * k) * 2*pi / ORBIT_SECONDS units per second, which is far below the
# camera's contribution, so this is nearly free in the motion budget.
DRIFT_SEED: int = 7
DRIFT_HARMONICS: tuple[int, ...] = (1, 2)
DRIFT_AMPLITUDES: tuple[float, ...] = (1.5, 0.6)

# --- Intro clip -----------------------------------------------------------------------
# Off for now. The convergence animation moves to a dedicated project page later.
RENDER_INTRO: bool = False
INTRO_FRAMES: int = FPS * 20
