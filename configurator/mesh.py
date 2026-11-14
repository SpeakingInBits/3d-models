"""Reading STL meshes and drawing them on the CPU.

Both run with numpy alone, so the app's 3D view works on computers without OpenGL, such as virtual
machines and remote desktops, where VTK crashes.
"""

from dataclasses import dataclass

import numpy as np

MODEL_COLOUR = np.array((236, 228, 214))
BACKGROUND = (185, 185, 189)
EDGE_SHADE = 0.45       # how dark the outlines are, as a share of the surface colour
CREASE_COS = 0.8        # faces meeting at more than about 37 degrees get a line between them
LIGHT = np.array((-0.35, 0.45, 0.82))   # towards the light, from the camera's point of view


def read_stl(path):
    """The corners of each triangle in a binary STL, as an array of shape (triangles, 3, 3)."""
    record = [("normal", "<f4", 3), ("corners", "<f4", (3, 3)), ("attribute", "<u2")]
    return np.fromfile(path, dtype=record, offset=84)["corners"].astype(float)


def split_long_triangles(triangles):
    """Split long triangles into four, for renderers that draw each in order of its average depth."""
    limit = np.ptp(triangles.reshape(-1, 3), axis=0).max() / 20
    for _ in range(4):
        edges = np.linalg.norm(triangles - np.roll(triangles, 1, axis=1), axis=2).max(axis=1)
        long = edges > limit
        a, b, c = (triangles[long, i] for i in range(3))
        ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
        pieces = [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]
        triangles = np.concatenate([triangles[~long]] + [np.stack(p, axis=1) for p in pieces])
    return triangles


class Mesh:
    """A part's triangles, centred on its bounding box, with their normals worked out once."""

    def __init__(self, triangles):
        corners = triangles.reshape(-1, 3)
        low, high = corners.min(axis=0), corners.max(axis=0)
        self.size = high - low
        self.triangles = triangles - (low + high) / 2
        normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
        lengths = np.linalg.norm(normals, axis=1, keepdims=True)
        self.normals = normals / np.where(lengths == 0, 1, lengths)
        self.radius = np.linalg.norm(self.size) / 2 or 1.0


@dataclass
class Camera:
    """Looks at the middle of the part from any direction, without perspective.

    yaw turns the part about its Z axis, and pitch tilts the view from straight down (0) through
    level (-90) to straight up (-180). pan is in millimetres across the screen, and zoom 1 fits
    the whole part in the view.
    """
    yaw: float = -32.0
    pitch: float = -65.0
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0

    def rotation(self):
        """The matrix from the part's axes to the screen's: x right, y up, z towards the viewer."""
        yaw, pitch = np.radians(self.yaw), np.radians(self.pitch)
        cy, sy, cp, sp = np.cos(yaw), np.sin(yaw), np.cos(pitch), np.sin(pitch)
        spin = np.array(((cy, -sy, 0), (sy, cy, 0), (0, 0, 1)))
        tilt = np.array(((1, 0, 0), (0, cp, -sp), (0, sp, cp)))
        return tilt @ spin

    def pixels_per_mm(self, mesh, width, height):
        return 0.92 * min(width, height) / (2 * mesh.radius) * self.zoom


def render(mesh, camera, width, height):
    """Draw the mesh with a depth buffer. Returns an RGB array of shape (height, width, 3).

    Each triangle is filled a row at a time, so the work follows the pixels it covers rather than
    its size, and thin triangles cost no more than they show.
    """
    rotation = camera.rotation()
    normals = mesh.normals @ rotation.T
    facing = normals[:, 2] > 0
    normals = normals[facing]
    corners = mesh.triangles[facing] @ rotation.T
    scale = camera.pixels_per_mm(mesh, width, height)
    x = (corners[..., 0] + camera.pan_x) * scale + width / 2
    y = height / 2 - (corners[..., 1] + camera.pan_y) * scale
    z = corners[..., 2]

    # each triangle's depth as a plane over the screen: z = a x + b y + c
    ux, uy, uz = (x[:, 1] - x[:, 0], y[:, 1] - y[:, 0], z[:, 1] - z[:, 0])
    vx, vy, vz = (x[:, 2] - x[:, 0], y[:, 2] - y[:, 0], z[:, 2] - z[:, 0])
    det = ux * vy - uy * vx
    flat = np.abs(det) < 1e-9          # edge-on to the screen
    det = np.where(flat, 1, det)
    a = (uz * vy - uy * vz) / det
    b = (ux * vz - uz * vx) / det
    c = z[:, 0] - a * x[:, 0] - b * y[:, 0]

    # the rows of pixel centres each triangle crosses
    first_row = np.maximum(np.ceil(y.min(axis=1) - 0.5), 0).astype(np.int64)
    last_row = np.minimum(np.floor(y.max(axis=1) - 0.5), height - 1).astype(np.int64)
    rows = np.where(flat, 0, last_row - first_row + 1).clip(0)
    tri = np.repeat(np.arange(len(x)), rows)
    row = first_row[tri] + ramp(rows)

    # where each row enters and leaves its triangle
    centre_y = row + 0.5
    left = np.full(len(tri), np.inf)
    right = np.full(len(tri), -np.inf)
    for i, j in ((0, 1), (1, 2), (2, 0)):
        y0, y1, x0, x1 = y[tri, i], y[tri, j], x[tri, i], x[tri, j]
        crosses = (np.minimum(y0, y1) <= centre_y) & (centre_y <= np.maximum(y0, y1)) & (y0 != y1)
        at = x0 + (centre_y - y0) * (x1 - x0) / np.where(y0 == y1, 1, y1 - y0)
        left = np.where(crosses, np.minimum(left, at), left)
        right = np.where(crosses, np.maximum(right, at), right)
    first_col = np.maximum(np.ceil(left - 0.5), 0)
    last_col = np.minimum(np.floor(right - 0.5), width - 1)
    found = np.isfinite(first_col) & np.isfinite(last_col)
    cols = np.where(found, last_col - first_col + 1, 0).clip(0).astype(np.int64)
    first_col = np.where(cols > 0, first_col, 0).astype(np.int64)

    # every pixel of every row, and the nearest triangle at each one
    pixel_tri = np.repeat(tri, cols)
    pixel_row = np.repeat(row, cols)
    pixel_col = np.repeat(first_col, cols) + ramp(cols)
    pixel = pixel_row * width + pixel_col
    depth = a[pixel_tri] * (pixel_col + 0.5) + b[pixel_tri] * (pixel_row + 0.5) + c[pixel_tri]
    nearest = np.full(width * height, -np.inf)
    np.maximum.at(nearest, pixel, depth)
    shown = depth >= nearest[pixel]
    owner = np.full(width * height, -1)
    owner[pixel[shown]] = pixel_tri[shown]

    light = LIGHT / np.linalg.norm(LIGHT)
    brightness = 0.32 + 0.68 * np.clip(normals @ light, 0, 1)
    colours = (brightness[:, None] * MODEL_COLOUR).astype(np.uint8)
    image = np.empty((width * height, 3), np.uint8)
    image[:] = BACKGROUND
    covered = owner >= 0
    image[covered] = colours[owner[covered]]

    image = image.reshape(height, width, 3)
    depth = np.where(covered, nearest, 0).reshape(height, width)
    edges = outlines(owner.reshape(height, width), depth, normals, scale)
    image[edges] = (image[edges] * EDGE_SHADE).astype(np.uint8)
    return image


def ramp(counts):
    """0, 1, ... counts[i] - 1 for each i, one after another."""
    total = counts.sum()
    starts = np.repeat(np.cumsum(counts) - counts, counts)
    return np.arange(total) - starts


def outlines(owner, depth, normals, scale):
    """Pixels on the part's silhouette, at steps in depth and where faces meet at an angle.

    Only the nearer pixel of each pair is marked, so the lines are one pixel wide and on top.
    """
    step = max(1.0, 4 / scale)          # depth change, in mm, that counts as a step
    surface = owner >= 0
    pixel_normals = np.where(surface[..., None], normals[np.maximum(owner, 0)], 0)
    edges = np.zeros(owner.shape, bool)
    for axis in (0, 1):
        here = [slice(None)] * 2
        there = [slice(None)] * 2
        here[axis], there[axis] = slice(None, -1), slice(1, None)
        here, there = tuple(here), tuple(there)
        on_a, on_b = surface[here], surface[there]
        dz = depth[here] - depth[there]
        bend = (pixel_normals[here] * pixel_normals[there]).sum(axis=-1) < CREASE_COS
        jump = np.abs(np.where(on_a & on_b, dz, 0)) > step
        line = (on_a != on_b) | (on_a & on_b & (jump | bend))
        a_nearer = np.where(on_a & on_b, dz >= 0, on_a)
        edges[here] |= line & a_nearer
        edges[there] |= line & ~a_nearer
    return edges
