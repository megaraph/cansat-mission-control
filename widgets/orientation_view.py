# ─────────────────────────────────────────────
#  CanSat Ground Station  |  widgets/orientation_view.py
#  3D orientation visualiser using PyOpenGL.
#  Renders a CanSat-shaped cuboid that rotates
#  according to the Madgwick quaternion output.
# ─────────────────────────────────────────────

import math
import numpy as np

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QSurfaceFormat

try:
    from OpenGL.GL import (
        glEnable,
        glDisable,
        glClearColor,
        glClear,
        glViewport,
        glMatrixMode,
        glLoadIdentity,
        glMultMatrixf,
        glBegin,
        glEnd,
        glVertex3f,
        glColor3f,
        glColor4f,
        glLineWidth,
        glBlendFunc,
        glDepthFunc,
        GL_COLOR_BUFFER_BIT,
        GL_DEPTH_BUFFER_BIT,
        GL_DEPTH_TEST,
        GL_BLEND,
        GL_LINES,
        GL_QUADS,
        GL_PROJECTION,
        GL_MODELVIEW,
        GL_SRC_ALPHA,
        GL_ONE_MINUS_SRC_ALPHA,
        GL_LEQUAL,
    )
    from OpenGL.GLU import gluPerspective

    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False

import config


def _quat_to_matrix(qw, qx, qy, qz):
    """Convert quaternion to 4x4 column-major rotation matrix (OpenGL format)."""
    m = np.zeros(16, dtype=np.float32)
    m[0] = 1 - 2 * (qy * qy + qz * qz)
    m[1] = 2 * (qx * qy + qz * qw)
    m[2] = 2 * (qx * qz - qy * qw)
    m[4] = 2 * (qx * qy - qz * qw)
    m[5] = 1 - 2 * (qx * qx + qz * qz)
    m[6] = 2 * (qy * qz + qx * qw)
    m[8] = 2 * (qx * qz + qy * qw)
    m[9] = 2 * (qy * qz - qx * qw)
    m[10] = 1 - 2 * (qx * qx + qy * qy)
    m[15] = 1.0
    return m


# ── Fallback when OpenGL not available ───────────────────────────────────────
class _FallbackWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        lbl = QLabel("3D view\nunavailable\n(install PyOpenGL)")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {config.COLOR_TEXT_DIM}; font-size: 11px;")
        layout.addWidget(lbl)


# ── OpenGL widget ─────────────────────────────────────────────────────────────
class _GL3DWidget(QOpenGLWidget):

    # CanSat body proportions (cylindrical can → tall narrow box)
    W, H, D = 0.4, 1.0, 0.4

    # Face definitions (vertex indices, normal-based color factor)
    FACES = [
        # (v0,v1,v2,v3, r, g, b)  — each face slightly different shade
        (0, 1, 2, 3, 0.05, 0.40, 0.28),  # front   (darkest)
        (4, 5, 6, 7, 0.04, 0.35, 0.24),  # back
        (0, 1, 5, 4, 0.06, 0.50, 0.35),  # bottom
        (3, 2, 6, 7, 0.08, 0.60, 0.42),  # top     (brightest — emerald)
        (0, 3, 7, 4, 0.05, 0.45, 0.30),  # left
        (1, 2, 6, 5, 0.05, 0.45, 0.30),  # right
    ]

    # Edge pairs for wireframe overlay
    EDGES = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),  # bottom face
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),  # top face
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),  # verticals
    ]

    def __init__(self, parent=None):
        fmt = QSurfaceFormat()
        fmt.setSamples(4)
        QSurfaceFormat.setDefaultFormat(fmt)
        super().__init__(parent)
        self._qw = 1.0
        self._qx = self._qy = self._qz = 0.0
        self.setMinimumHeight(200)

    def set_quaternion(self, qw, qx, qy, qz):
        self._qw = qw
        self._qx = qx
        self._qy = qy
        self._qz = qz
        self.update()

    def _vertices(self):
        w, h, d = self.W / 2, self.H / 2, self.D / 2
        return [
            (-w, -h, -d),
            (w, -h, -d),
            (w, -h, d),
            (-w, -h, d),  # 0-3 bottom
            (-w, h, -d),
            (w, h, -d),
            (w, h, d),
            (-w, h, d),  # 4-7 top
        ]

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthFunc(GL_LEQUAL)
        # Very dark background matching dashboard
        glClearColor(0.039, 0.039, 0.059, 1.0)

    def resizeGL(self, w, h):
        if h == 0:
            h = 1
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, w / h, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Camera: slightly above and in front
        from OpenGL.GL import glTranslatef, glRotatef

        glTranslatef(0.0, 0.0, -2.8)
        glRotatef(-20, 1, 0, 0)  # tilt camera down slightly

        # Apply quaternion rotation
        mat = _quat_to_matrix(self._qw, self._qx, self._qy, self._qz)
        glMultMatrixf(mat)

        verts = self._vertices()

        # ── Draw filled faces ─────────────────────────────────────────────────
        glBegin(GL_QUADS)
        for v0, v1, v2, v3, r, g, b in self.FACES:
            glColor3f(r, g, b)
            for vi in (v0, v1, v2, v3):
                glVertex3f(*verts[vi])
        glEnd()

        # ── Draw wireframe edges (emerald green, thin) ────────────────────────
        glLineWidth(1.2)
        glBegin(GL_LINES)
        glColor3f(0.063, 0.725, 0.506)  # #10B981 emerald
        for i, j in self.EDGES:
            glVertex3f(*verts[i])
            glVertex3f(*verts[j])
        glEnd()

        # ── Draw axes indicator (small, at origin) ────────────────────────────
        glLineWidth(1.5)
        glBegin(GL_LINES)
        size = 0.55
        glColor3f(0.9, 0.2, 0.2)
        glVertex3f(0, 0, 0)
        glVertex3f(size, 0, 0)  # X red
        glColor3f(0.2, 0.8, 0.2)
        glVertex3f(0, 0, 0)
        glVertex3f(0, size, 0)  # Y green
        glColor3f(0.2, 0.4, 0.9)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, size)  # Z blue
        glEnd()


# ── Public widget (container + GL + quaternion labels) ───────────────────────
class OrientationView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Header
        header = QLabel("ORIENTATION")
        header.setObjectName("section_header")
        layout.addWidget(header)

        # 3D widget or fallback
        if OPENGL_AVAILABLE:
            self._gl = _GL3DWidget()
            layout.addWidget(self._gl)
        else:
            self._gl = None
            layout.addWidget(_FallbackWidget())

        # Quaternion readout
        self._q_label = QLabel("q: [1.000  0.000  0.000  0.000]")
        font = QFont("JetBrains Mono, Courier New, monospace")
        font.setPixelSize(10)
        self._q_label.setFont(font)
        self._q_label.setStyleSheet(f"color: {config.COLOR_TEXT_DIM};")
        self._q_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._q_label)

        self.setStyleSheet(
            f"""
            OrientationView {{
                background-color: {config.COLOR_BG_WIDGET};
                border: 1px solid {config.COLOR_GRID};
                border-radius: 4px;
            }}
        """
        )

    def update_orientation(self, qw, qx, qy, qz):
        if self._gl:
            self._gl.set_quaternion(qw, qx, qy, qz)
        self._q_label.setText(f"q  {qw:+.3f}  {qx:+.3f}  {qy:+.3f}  {qz:+.3f}")
