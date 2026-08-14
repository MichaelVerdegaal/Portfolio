"""Export the looping hero orbit and its poster frame for the portfolio site."""

import matplotlib.pyplot as plt

plt.switch_backend("Agg")

from src import config  # noqa: E402
from src.animation import (  # noqa: E402
    breath_field,
    drift_field,
    intro_camera,
    loop_camera,
    tween_history,
)
from src.export import check_ffmpeg, render_clip, save_poster  # noqa: E402
from src.graph import layout_function  # noqa: E402
from src.scene import build_scene, frame_updater  # noqa: E402


def main() -> None:
    """Render the hero loop and poster into the static directory."""
    check_ffmpeg()
    config.STATIC_DIR.mkdir(exist_ok=True)

    fig, ax, view = build_scene(figsize=config.FIGSIZE, dpi=config.DPI, is_3d=True)
    final_positions = layout_function(view.graph, view.pos, is_3d=True)
    drift = drift_field(view.graph.number_of_nodes())
    breath = breath_field(view.graph.number_of_nodes())

    if config.RENDER_INTRO:
        history = tween_history(view.pos.copy(), final_positions, config.INTRO_FRAMES)
        update = frame_updater(
            view,
            ax,
            pos_for=lambda frame: history[min(frame, len(history) - 1)],
            camera_for=intro_camera,
        )
        render_clip(
            fig, update, config.STATIC_DIR / "hero-intro.mp4", config.INTRO_FRAMES
        )

    update = frame_updater(
        view,
        ax,
        pos_for=lambda frame: final_positions + drift(frame),
        camera_for=loop_camera,
        alpha_for=breath,
    )
    render_clip(fig, update, config.STATIC_DIR / "hero-loop.mp4", config.LOOP_FRAMES)
    save_poster(fig, update, 0, config.STATIC_DIR / "hero-poster.webp")
    plt.close(fig)


if __name__ == "__main__":
    main()
