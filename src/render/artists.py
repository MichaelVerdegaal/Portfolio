"""Matplotlib collection subclasses for 3D nodes, edges and labels."""

import numpy as np
import numpy.typing as npt
from matplotlib.collections import PathCollection
from matplotlib.colors import to_rgba
from matplotlib.path import Path
from mpl_toolkits.mplot3d.art3d import Line3DCollection

from src.config import (
    COLOR_INK,
    LABEL_ALPHA_FAR,
    LABEL_ALPHA_NEAR,
    LABEL_FADE_GAMMA,
)


class TextPathCollection3D(PathCollection):
    def __init__(
        self,
        paths: list[Path],
        positions: npt.NDArray[np.float64],
        *,
        color: str = COLOR_INK,
        alpha_range: tuple[float, float] = (LABEL_ALPHA_FAR, LABEL_ALPHA_NEAR),
        gamma: float = LABEL_FADE_GAMMA,
        **kwargs: object,
    ) -> None:
        """Initialise the collection with per-label paths and 3D anchors.

        Args:
            paths: One glyph path per label, in node order.
            positions: (N, 3) array of anchor points in data coordinates.
            color: Base colour for the glyph fill and stroke.
            alpha_range: (far, near) alpha applied across the depth range.
            gamma: Exponent on the depth curve. Above 1 fades the far labels
                sooner than a linear ramp would.
            **kwargs: Styling forwarded to PathCollection.
        """
        super().__init__(paths, offsets=np.zeros((len(paths), 2)), **kwargs)
        self._positions3d: npt.NDArray[np.float64] = positions
        self._base_rgba: npt.NDArray[np.float64] = np.array(to_rgba(color))
        self._alpha_range: tuple[float, float] = alpha_range
        self._gamma: float = gamma
        self._alpha_scale: npt.NDArray[np.float64] = np.ones(len(paths))

    def _depth_rgba(self, depth: npt.NDArray[np.float64]) -> npt.NDArray[np.float64]:
        """Map projected depth to per-label RGBA.

        Args:
            depth: (N,) projected depths, larger values further from the camera.

        Returns:
            (N, 4) RGBA array in label order.
        """
        span = float(depth.max() - depth.min())
        far_alpha, near_alpha = self._alpha_range
        t = np.zeros_like(depth) if span < 1e-12 else (depth - depth.min()) / span
        rgba = np.tile(self._base_rgba, (len(depth), 1))
        rgba[:, 3] = (
            far_alpha + (near_alpha - far_alpha) * (1.0 - t) ** self._gamma
        ) * self._alpha_scale
        return rgba

    def set_alpha_scale(self, scale: npt.NDArray[np.float64]) -> None:
        """Set a per-label alpha multiplier.

        Args:
            scale: (N,) array of multipliers in [0, 1].
        """
        self._alpha_scale = scale

    def set_positions(self, positions: npt.NDArray[np.float64]) -> None:
        """Replace the 3D anchor points.

        Args:
            positions: (N, 3) array of anchor points in data coordinates.
        """
        self._positions3d = positions

    def do_3d_projection(self) -> float:
        homogeneous = np.column_stack(
            [self._positions3d, np.ones(len(self._positions3d))]
        )
        projected = homogeneous @ self.axes.M.T
        projected = projected[:, :3] / projected[:, 3, None]
        self.set_offsets(projected[:, :2])

        if not projected.size:
            return float("nan")

        depth = projected[:, 2]
        rgba = self._depth_rgba(depth)
        self.set_facecolor(rgba)
        self.set_edgecolor(rgba)
        return float(depth.min())


class EdgeCollection3D(Line3DCollection):
    """Line3DCollection whose per-edge alpha falls off with length and depth.

    Depth is only known once the axes projection matrix is applied, so the
    colours are rebuilt inside do_3d_projection rather than at construction.
    """

    def __init__(
        self,
        segments: npt.NDArray[np.float64],
        *,
        color: str,
        base_alpha: float,
        length_falloff: float,
        depth_range: tuple[float, float],
        gamma: float,
        **kwargs: object,
    ) -> None:
        """Initialise the collection with segments and falloff parameters.

        Args:
            segments: (E, 2, 3) array of edge endpoints in data coordinates.
            color: Base colour for every edge.
            base_alpha: Alpha applied before the length and depth weights.
            length_falloff: Fraction of alpha removed from the longest edge.
            depth_range: (far, near) depth weights.
            gamma: Exponent on the depth curve.
            **kwargs: Styling forwarded to Line3DCollection.
        """
        super().__init__(segments, **kwargs)
        self._base_rgb: npt.NDArray[np.float64] = np.array(to_rgba(color))[:3]
        self._base_alpha: float = base_alpha
        self._length_falloff: float = length_falloff
        self._depth_range: tuple[float, float] = depth_range
        self._gamma: float = gamma
        self._alpha_scale: npt.NDArray[np.float64] = np.ones(len(segments))
        self._midpoints: npt.NDArray[np.float64]
        self._length_weights: npt.NDArray[np.float64]
        self.set_geometry(segments)

    def set_geometry(self, segments: npt.NDArray[np.float64]) -> None:
        """Recompute midpoints and length weights from new segments.

        Args:
            segments: (E, 2, 3) array of edge endpoints in data coordinates.
        """
        self._midpoints = segments.mean(axis=1)
        lengths = np.linalg.norm(segments[:, 1] - segments[:, 0], axis=1)
        span = float(lengths.max() - lengths.min())
        if span < 1e-12:
            self._length_weights = np.ones(len(lengths))
            return
        normalized = (lengths - lengths.min()) / span
        self._length_weights = 1.0 - self._length_falloff * normalized

    def set_alpha_scale(self, scale: npt.NDArray[np.float64]) -> None:
        """Set a per-edge alpha multiplier.

        Args:
            scale: (E,) array of multipliers in [0, 1].
        """
        self._alpha_scale = scale

    def do_3d_projection(self) -> float:
        minz = super().do_3d_projection()

        homogeneous = np.column_stack([self._midpoints, np.ones(len(self._midpoints))])
        projected = homogeneous @ self.axes.M.T
        depth = projected[:, 2] / projected[:, 3]

        span = float(depth.max() - depth.min())
        t = np.zeros_like(depth) if span < 1e-12 else (depth - depth.min()) / span
        far_alpha, near_alpha = self._depth_range
        depth_weight = far_alpha + (near_alpha - far_alpha) * (1.0 - t) ** self._gamma

        rgba = np.tile(np.append(self._base_rgb, 1.0), (len(depth), 1))
        rgba[:, 3] = (
            self._base_alpha * self._length_weights * depth_weight * self._alpha_scale
        )
        self.set_color(rgba)
        return minz
