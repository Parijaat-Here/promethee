# ============================================================================
# Prométhée — Assistant IA desktop
# ============================================================================
# Auteur  : Pierre COUGET
# Licence : GNU Affero General Public License v3.0 (AGPL-3.0)
#           https://www.gnu.org/licenses/agpl-3.0.html
# Année   : 2026
# ----------------------------------------------------------------------------
# Ce fichier fait partie du projet Prométhée.
# Vous pouvez le redistribuer et/ou le modifier selon les termes de la
# licence AGPL-3.0 publiée par la Free Software Foundation.
# ============================================================================

"""
theme_switch.py — Widget toggle sombre/clair animé

Extrait de main_window.py pour une meilleure organisation du code.
"""
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPointF, QRectF, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QPen

from .styles import ThemeManager


class ThemeSwitch(QWidget):
    """
    Switch sombre/clair animé.
    - Côté gauche  : soleil (thème clair)
    - Côté droit   : lune   (thème sombre)
    - Le thumb glisse avec une animation fluide.
    Émet toggled(is_dark: bool) à chaque bascule.
    """
    toggled = pyqtSignal(bool)

    # Géométrie du track
    _W   = 72   # largeur totale
    _H   = 32   # hauteur totale
    _R   = 13   # rayon du thumb
    _PAD = 3    # marge interne

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self._W + 4, self._H + 4)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Basculer thème clair / sombre  (Ctrl+Shift+T)")

        self._pos: float = 1.0 if ThemeManager.is_dark() else 0.0

        self._anim = QPropertyAnimation(self, b"animPos", self)
        self._anim.setDuration(260)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    # ── Propriété animable (pyqtProperty obligatoire pour QPropertyAnimation) ──

    def _get_pos(self) -> float:
        return self._pos

    def _set_pos(self, v: float):
        self._pos = v
        self.update()

    animPos = pyqtProperty(float, _get_pos, _set_pos)

    # ── API publique ──────────────────────────────────────────────────

    def sync(self):
        """Synchronise l'animation après un toggle externe (menu)."""
        target = 1.0 if ThemeManager.is_dark() else 0.0
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(target)
        self._anim.start()

    # ── Événements ────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            ThemeManager.toggle()
            self.sync()
            self.toggled.emit(ThemeManager.is_dark())

    # ── Rendu ─────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        ox, oy = 2, 2          # offset pour ne pas clipper l'ombre du thumb
        w, h   = self._W, self._H

        # ── Track ────────────────────────────────────────────────────
        # Couleur du fond interpolée entre clair et sombre selon la position
        def lerp_color(c1: QColor, c2: QColor, t: float) -> QColor:
            return QColor(
                int(c1.red()   + (c2.red()   - c1.red())   * t),
                int(c1.green() + (c2.green() - c1.green()) * t),
                int(c1.blue()  + (c2.blue()  - c1.blue())  * t),
            )

        track_light = QColor("#e2dfd8")   # fond clair
        track_dark  = QColor("#26262a")   # fond sombre
        track_col   = lerp_color(track_light, track_dark, self._pos)
        border_col  = lerp_color(QColor("#c4c0b8"), QColor("#48484e"), self._pos)

        p.setPen(QPen(border_col, 1.0))
        p.setBrush(track_col)
        p.drawRoundedRect(ox, oy, w, h, h / 2, h / 2)

        # ── Icône soleil (gauche) ─────────────────────────────────────
        sun_cx = ox + h / 2
        sun_cy = oy + h / 2
        sun_alpha = int((1.0 - self._pos) * 255)
        self._draw_sun(p, sun_cx, sun_cy, alpha=sun_alpha)

        # ── Icône lune (droite) ───────────────────────────────────────
        moon_cx = ox + w - h / 2
        moon_cy = oy + h / 2
        moon_alpha = int(self._pos * 255)
        self._draw_moon(p, moon_cx, moon_cy, alpha=moon_alpha)

        # ── Thumb ─────────────────────────────────────────────────────
        travel = w - 2 * self._PAD - 2 * self._R
        cx = ox + self._PAD + self._R + self._pos * travel
        cy = oy + h / 2

        # Ombre portée
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 35))
        p.drawEllipse(QRectF(cx - self._R + 1, cy - self._R + 2,
                             self._R * 2, self._R * 2))

        # Corps du thumb
        thumb_col = lerp_color(QColor("#ffffff"), QColor("#e8e5df"), self._pos)
        p.setBrush(thumb_col)
        p.setPen(QPen(QColor(0, 0, 0, 25), 1.0))
        p.drawEllipse(QRectF(cx - self._R, cy - self._R,
                             self._R * 2, self._R * 2))

        # Icône dans le thumb : soleil si pos<0.5, lune si pos≥0.5
        if self._pos < 0.5:
            icon_alpha = int((0.5 - self._pos) * 2 * 220)
            self._draw_sun(p, cx, cy, r=5.5, alpha=icon_alpha, color=QColor(220, 140, 30))
        else:
            icon_alpha = int((self._pos - 0.5) * 2 * 220)
            self._draw_moon(p, cx, cy, r=5.0, alpha=icon_alpha, color=QColor(100, 120, 200))

        p.end()

    # ── Helpers de dessin ─────────────────────────────────────────────

    def _draw_sun(self, p: QPainter, cx: float, cy: float,
                  r: float = 4.5, alpha: int = 255,
                  color: QColor = None):
        """Soleil : disque central + 8 rayons."""
        if alpha <= 0:
            return
        col = color or QColor(255, 195, 50)
        col = QColor(col.red(), col.green(), col.blue(), alpha)

        p.save()
        p.translate(cx, cy)

        # Disque
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawEllipse(QRectF(-r, -r, r * 2, r * 2))

        # Rayons
        pen = QPen(col, 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        ray_inner = r + 1.5
        ray_outer = r + 3.5
        for i in range(8):
            angle = math.radians(i * 45)
            x1 = math.cos(angle) * ray_inner
            y1 = math.sin(angle) * ray_inner
            x2 = math.cos(angle) * ray_outer
            y2 = math.sin(angle) * ray_outer
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        p.restore()

    def _draw_moon(self, p: QPainter, cx: float, cy: float,
                   r: float = 5.5, alpha: int = 255,
                   color: QColor = None):
        """Lune : croissant dessiné par soustraction de deux disques."""
        if alpha <= 0:
            return
        col = color or QColor(180, 185, 230)
        col = QColor(col.red(), col.green(), col.blue(), alpha)

        p.save()
        p.translate(cx, cy)

        # Croissant via QPainterPath
        path = QPainterPath()
        # Grand disque (corps)
        path.addEllipse(QRectF(-r, -r, r * 2, r * 2))
        # Petit disque de soustraction (décalé vers le haut-droite)
        offset = r * 0.42
        cut_r  = r * 0.82
        cut = QPainterPath()
        cut.addEllipse(QRectF(offset - cut_r, -r * 0.55 - cut_r,
                              cut_r * 2, cut_r * 2))
        crescent = path.subtracted(cut)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawPath(crescent)

        p.restore()
