"""Interactive preview of the 3D graph animation."""

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

from src import config
from src.animation import spin_camera, tween_history
from src.graph import layout_function
from src.render.figure import maximize_window
from src.scene import build_scene, frame_updater

IS_3D = True
SAVE_ANIM = False
FULLSCREEN = False
INTERVAL_MS = 1000 // config.PREVIEW_FPS
FRAMES = config.PREVIEW_FPS * config.PREVIEW_SECONDS


def main() -> None:
    """Run the preview window with the layout convergence animation."""
    fig, ax, view = build_scene(is_3d=IS_3D)
    target = layout_function(view.graph, view.pos, is_3d=IS_3D)
    history = tween_history(view.pos.copy(), target, FRAMES)
    update = frame_updater(
        view,
        ax,
        pos_for=lambda frame: history[min(frame, len(history) - 1)],
        camera_for=spin_camera(FRAMES) if IS_3D else None,
    )

    # anim must stay referenced or it is garbage collected and nothing draws.
    anim = FuncAnimation(
        fig,
        func=update,
        interval=INTERVAL_MS,
        frames=FRAMES,
        repeat=False,
        blit=not IS_3D,  # Limited support for Axes3D blitting.
    )
    if SAVE_ANIM:
        anim.save("animation.mp4", writer="ffmpeg")
    if FULLSCREEN:
        maximize_window(fig)
    plt.show()


if __name__ == "__main__":
    main()
