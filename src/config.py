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

# --- Render geometry ------------------------------------------------------------------
# FIGSIZE * DPI is the raw frame size piped to ffmpeg (3840x2160). Points are
# converted to pixels via DPI/72, so DPI must stay at 2x the effective output
# scale for the downsample to act as supersampling rather than shrinking.
FIGSIZE: tuple[float, float] = (19.2, 10.8)
DPI: int = 200
TARGET_WIDTH: int = 1920
TARGET_HEIGHT: int = 1080

# --- Video ----------------------------------------------------------------------------
FPS: int = 30
ORBIT_SECONDS: int = 20
LOOP_FRAMES: int = FPS * ORBIT_SECONDS
DEG_PER_FRAME: float = 360 / LOOP_FRAMES
CRF: int = 18
PRESET: str = "slow"
VIDEO_FILTERS: str = f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:flags=lanczos"

# --- Interactive preview (main.py) ----------------------------------------------------
PREVIEW_FPS: int = 60
PREVIEW_SECONDS: int = 10

# --- Intro clip -----------------------------------------------------------------------
# Off for now. The convergence animation moves to a dedicated project page later.
RENDER_INTRO: bool = False
INTRO_FRAMES: int = FPS * 20
