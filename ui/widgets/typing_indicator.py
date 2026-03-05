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
typing_indicator.py — Indicateur de frappe animé
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import QTimer, Qt
from .styles import ThemeManager


class TypingIndicator(QWidget):
    """Indicateur de frappe avec animation trois points."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 6, 0, 6)

        self._dots = QLabel()
        self._dots.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self._dots)
        layout.addStretch()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._step = 0
        self._animate()  # Afficher la première frame immédiatement
        self._timer.start(400)  # Animation toutes les 400ms

    def _animate(self):
        active   = ThemeManager.inline("dot_active")
        inactive = ThemeManager.inline("dot_inactive")

        # Utiliser des cercles au lieu d'emojis pour une meilleure compatibilité
        frames = [
            f'<span style="color:{active};font-size:20px;">●</span> <span style="color:{inactive};font-size:20px;">●</span> <span style="color:{inactive};font-size:20px;">●</span>',
            f'<span style="color:{inactive};font-size:20px;">●</span> <span style="color:{active};font-size:20px;">●</span> <span style="color:{inactive};font-size:20px;">●</span>',
            f'<span style="color:{inactive};font-size:20px;">●</span> <span style="color:{inactive};font-size:20px;">●</span> <span style="color:{active};font-size:20px;">●</span>',
        ]
        self._dots.setText(frames[self._step % 3])
        self._step += 1

    def stop(self):
        self._timer.stop()
