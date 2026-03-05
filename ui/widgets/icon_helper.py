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
icon_helper.py — Icônes SVG vectorielles, compatibles toutes plateformes.

Remplace les emojis Unicode (qui s'affichent comme des blocs carrés sur Linux
sans police de symboles couleur) par des SVG dessinés avec les couleurs du thème.

Usage
-----
    from .icon_helper import icon_label, icon_pixmap

    lbl = icon_label("file")          # QLabel avec QPixmap SVG 20×20
    lbl = icon_label("file", size=16) # taille personnalisée
    px  = icon_pixmap("ocr", 24)      # QPixmap brut

Icônes disponibles
------------------
    file, image, url, link,
    pdf, ocr,
    preview_eye,
    close_x,
    settings_gear,
    cache_box,
    user_profile,
    agent_bot,
    rag_book,
    tools_wrench,
    arrow_left, arrow_right,
    new_plus,
    loading_spinner
"""

from __future__ import annotations
from PyQt6.QtGui import QPixmap, QColor, QPainter, QIcon
from PyQt6.QtCore import QByteArray, Qt, QSize
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QLabel


# ── Palette de couleurs ──────────────────────────────────────────────────────
# Ces couleurs sont volontairement indépendantes du ThemeManager pour que les
# icônes soient cohérentes dans les deux thèmes (fond transparent).

_CLR_ORANGE  = "#cc7c3a"
_CLR_BLUE    = "#6b9fd4"
_CLR_GREY    = "#888888"
_CLR_RED     = "#e07070"
_CLR_GREEN   = "#5a9a5a"
_CLR_WHITE   = "#e8e6e1"


# ── Bibliothèque SVG ─────────────────────────────────────────────────────────

_SVGS: dict[str, str] = {

    # ── Fichier / document ──────────────────────────────────────────────
    "file": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <path d="M4 2h8l4 4v12a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V3a1 1 0 0 1 0-1z"
        fill="none" stroke="{_CLR_BLUE}" stroke-width="1.4" stroke-linejoin="round"/>
  <path d="M12 2v4h4" fill="none" stroke="{_CLR_BLUE}" stroke-width="1.4"
        stroke-linejoin="round"/>
  <line x1="7" y1="9"  x2="13" y2="9"  stroke="{_CLR_GREY}" stroke-width="1.2"/>
  <line x1="7" y1="12" x2="13" y2="12" stroke="{_CLR_GREY}" stroke-width="1.2"/>
  <line x1="7" y1="15" x2="11" y2="15" stroke="{_CLR_GREY}" stroke-width="1.2"/>
</svg>""",

    # ── Image / photo ───────────────────────────────────────────────────
    "image": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="3" width="16" height="14" rx="2"
        fill="none" stroke="{_CLR_BLUE}" stroke-width="1.4"/>
  <circle cx="6.5" cy="7.5" r="1.5" fill="{_CLR_ORANGE}"/>
  <path d="M2 13l4-4 3 3 2.5-2.5L17 14" fill="none"
        stroke="{_CLR_GREEN}" stroke-width="1.3" stroke-linejoin="round"/>
</svg>""",

    # ── Lien / URL ──────────────────────────────────────────────────────
    "url": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <path d="M8 12a4 4 0 0 0 5.66 0l2-2a4 4 0 0 0-5.66-5.66L8.5 5.84"
        fill="none" stroke="{_CLR_ORANGE}" stroke-width="1.5" stroke-linecap="round"/>
  <path d="M12 8a4 4 0 0 0-5.66 0l-2 2a4 4 0 0 0 5.66 5.66l1.5-1.5"
        fill="none" stroke="{_CLR_ORANGE}" stroke-width="1.5" stroke-linecap="round"/>
</svg>""",

    # ── PDF ─────────────────────────────────────────────────────────────
    "pdf": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <path d="M4 2h8l4 4v12a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V3a1 1 0 0 1 0-1z"
        fill="none" stroke="{_CLR_RED}" stroke-width="1.4" stroke-linejoin="round"/>
  <path d="M12 2v4h4" fill="none" stroke="{_CLR_RED}" stroke-width="1.4"
        stroke-linejoin="round"/>
  <text x="5" y="15.5" font-size="5.5" font-family="sans-serif"
        font-weight="bold" fill="{_CLR_RED}">PDF</text>
</svg>""",

    # ── OCR / texte extrait ─────────────────────────────────────────────
    "ocr": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="3" width="16" height="14" rx="2"
        fill="none" stroke="{_CLR_GREY}" stroke-width="1.4"/>
  <line x1="5" y1="8"  x2="15" y2="8"  stroke="{_CLR_ORANGE}" stroke-width="1.4"/>
  <line x1="5" y1="11" x2="15" y2="11" stroke="{_CLR_ORANGE}" stroke-width="1.4"/>
  <line x1="5" y1="14" x2="11" y2="14" stroke="{_CLR_ORANGE}" stroke-width="1.4"/>
  <path d="M14 12l2 2-2 2" fill="none" stroke="{_CLR_BLUE}"
        stroke-width="1.3" stroke-linecap="round"/>
</svg>""",

    # ── Œil / prévisualiser ─────────────────────────────────────────────
    "preview_eye": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <path d="M1.5 10S5 3.5 10 3.5 18.5 10 18.5 10 15 16.5 10 16.5 1.5 10 1.5 10z"
        fill="none" stroke="{_CLR_BLUE}" stroke-width="1.4"/>
  <circle cx="10" cy="10" r="2.5" fill="{_CLR_ORANGE}"/>
</svg>""",

    # ── Croix / fermer ──────────────────────────────────────────────────
    "close_x": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <line x1="5" y1="5" x2="15" y2="15"
        stroke="{_CLR_GREY}" stroke-width="2" stroke-linecap="round"/>
  <line x1="15" y1="5" x2="5" y2="15"
        stroke="{_CLR_GREY}" stroke-width="2" stroke-linecap="round"/>
</svg>""",

    # ── Engrenage / paramètres ──────────────────────────────────────────
    "settings_gear": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <circle cx="10" cy="10" r="2.5"
          fill="none" stroke="{_CLR_ORANGE}" stroke-width="1.4"/>
  <path d="M10 2v2M10 16v2M2 10h2M16 10h2
           M4.22 4.22l1.41 1.41M14.37 14.37l1.41 1.41
           M4.22 15.78l1.41-1.41M14.37 5.63l1.41-1.41"
        stroke="{_CLR_ORANGE}" stroke-width="1.4" stroke-linecap="round"/>
</svg>""",

    # ── Boîte / cache ───────────────────────────────────────────────────
    "cache_box": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <rect x="3" y="8" width="14" height="9" rx="1.5"
        fill="none" stroke="{_CLR_BLUE}" stroke-width="1.4"/>
  <path d="M1.5 8h17M7 8V5.5a3 3 0 0 1 6 0V8"
        fill="none" stroke="{_CLR_BLUE}" stroke-width="1.4" stroke-linecap="round"/>
  <line x1="8" y1="12" x2="12" y2="12" stroke="{_CLR_ORANGE}" stroke-width="1.5"/>
</svg>""",

    # ── Profil utilisateur ──────────────────────────────────────────────
    "user_profile": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <circle cx="10" cy="7" r="3.5"
          fill="none" stroke="{_CLR_BLUE}" stroke-width="1.4"/>
  <path d="M3 17.5c0-3.59 3.13-6.5 7-6.5s7 2.91 7 6.5"
        fill="none" stroke="{_CLR_BLUE}" stroke-width="1.4" stroke-linecap="round"/>
</svg>""",

    # ── Robot / mode agent ──────────────────────────────────────────────
    "agent_bot": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <rect x="4" y="7" width="12" height="9" rx="2"
        fill="none" stroke="{_CLR_ORANGE}" stroke-width="1.4"/>
  <circle cx="7.5" cy="11" r="1.2" fill="{_CLR_ORANGE}"/>
  <circle cx="12.5" cy="11" r="1.2" fill="{_CLR_ORANGE}"/>
  <line x1="10" y1="2" x2="10" y2="7" stroke="{_CLR_GREY}" stroke-width="1.3"/>
  <circle cx="10" cy="2" r="1" fill="{_CLR_GREY}"/>
  <path d="M7 14h6" stroke="{_CLR_GREY}" stroke-width="1.2" stroke-linecap="round"/>
  <line x1="4" y1="10" x2="2" y2="10" stroke="{_CLR_GREY}" stroke-width="1.3"/>
  <line x1="16" y1="10" x2="18" y2="10" stroke="{_CLR_GREY}" stroke-width="1.3"/>
</svg>""",

    # ── Livre / RAG ─────────────────────────────────────────────────────
    "rag_book": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <path d="M3 4v13a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V4"
        fill="none" stroke="{_CLR_GREEN}" stroke-width="1.4"/>
  <path d="M3 4h14" stroke="{_CLR_GREEN}" stroke-width="1.4"/>
  <path d="M3 4c0-1 .9-2 2-2h10c1.1 0 2 1 2 2"
        fill="none" stroke="{_CLR_GREEN}" stroke-width="1.4"/>
  <line x1="7" y1="8"  x2="13" y2="8"  stroke="{_CLR_GREY}" stroke-width="1.2"/>
  <line x1="7" y1="11" x2="13" y2="11" stroke="{_CLR_GREY}" stroke-width="1.2"/>
  <line x1="7" y1="14" x2="10" y2="14" stroke="{_CLR_GREY}" stroke-width="1.2"/>
</svg>""",

    # ── Clé/outil ───────────────────────────────────────────────────────
    "tools_wrench": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <path d="M14.5 2a3.5 3.5 0 0 0-3.46 4.04L3.5 13.55A1.5 1.5 0 1 0 6.45 16.5l7.51-7.54A3.5 3.5 0 1 0 14.5 2z"
        fill="none" stroke="{_CLR_ORANGE}" stroke-width="1.4" stroke-linejoin="round"/>
  <circle cx="5" cy="15" r="1" fill="{_CLR_ORANGE}"/>
</svg>""",

    # ── Flèche gauche ───────────────────────────────────────────────────
    "arrow_left": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <path d="M13 4l-7 6 7 6" fill="none" stroke="{_CLR_ORANGE}"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    # ── Flèche droite ───────────────────────────────────────────────────
    "arrow_right": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <path d="M7 4l7 6-7 6" fill="none" stroke="{_CLR_ORANGE}"
        stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>""",

    # ── Plus / nouveau ──────────────────────────────────────────────────
    "new_plus": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <line x1="10" y1="3" x2="10" y2="17"
        stroke="{_CLR_ORANGE}" stroke-width="2" stroke-linecap="round"/>
  <line x1="3" y1="10" x2="17" y2="10"
        stroke="{_CLR_ORANGE}" stroke-width="2" stroke-linecap="round"/>
</svg>""",

    # ── Poubelle / supprimer ────────────────────────────────────────────
    "trash": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <path d="M5 7h10l-1 10H6L5 7z"
        fill="none" stroke="{_CLR_RED}" stroke-width="1.4" stroke-linejoin="round"/>
  <path d="M3 7h14M8 7V4h4v3"
        fill="none" stroke="{_CLR_RED}" stroke-width="1.4" stroke-linecap="round"/>
  <line x1="8.5" y1="10" x2="9" y2="14.5" stroke="{_CLR_RED}" stroke-width="1.2"/>
  <line x1="11.5" y1="10" x2="11" y2="14.5" stroke="{_CLR_RED}" stroke-width="1.2"/>
</svg>""",

    # ── Crayon / éditer ─────────────────────────────────────────────────
    "edit_pencil": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <path d="M14.5 2.5l3 3L6 17H3v-3L14.5 2.5z"
        fill="none" stroke="{_CLR_BLUE}" stroke-width="1.4"
        stroke-linejoin="round"/>
</svg>""",

    # ── Spinner / chargement ────────────────────────────────────────────
    "loading": f"""<svg viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
  <circle cx="10" cy="10" r="7"
          fill="none" stroke="{_CLR_GREY}" stroke-width="2"
          stroke-dasharray="22 22" stroke-linecap="round"/>
  <circle cx="10" cy="10" r="7"
          fill="none" stroke="{_CLR_ORANGE}" stroke-width="2"
          stroke-dasharray="11 33" stroke-linecap="round"/>
</svg>""",
}


# ── API publique ─────────────────────────────────────────────────────────────

def icon_pixmap(name: str, size: int = 20) -> QPixmap:
    """
    Retourne un QPixmap SVG de `size`×`size` pixels pour l'icône `name`.
    Si l'icône est inconnue, retourne un pixmap vide.
    """
    svg_src = _SVGS.get(name)
    if svg_src is None:
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        return px

    renderer = QSvgRenderer(QByteArray(svg_src.encode()))
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    return px


def icon_label(name: str, size: int = 20, tooltip: str = "") -> QLabel:
    """
    Retourne un QLabel avec le QPixmap SVG prêt à insérer dans un layout.
    """
    lbl = QLabel()
    lbl.setPixmap(icon_pixmap(name, size))
    lbl.setFixedSize(size, size)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet("background: transparent; border: none;")
    if tooltip:
        lbl.setToolTip(tooltip)
    return lbl


def icon_for_button(name: str, size: int = 16) -> QIcon:
    """Retourne un QIcon SVG utilisable dans QPushButton.setIcon()."""
    return QIcon(icon_pixmap(name, size))


def icon_for_file(path: str, size: int = 20) -> QLabel:
    """
    Choisit automatiquement l'icône selon l'extension du fichier.
    Retourne un QLabel prêt à l'emploi.
    """
    suffix = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    mapping = {
        "pdf":  "pdf",
        "png": "image", "jpg": "image", "jpeg": "image",
        "gif":  "image", "bmp": "image", "webp": "image",
        "docx": "file",  "xlsx": "file", "pptx": "file",
        "txt":  "file",  "md":   "file", "py":   "file",
        "js":   "file",  "json": "file", "csv":  "file",
        "html": "file",  "xml":  "file", "yaml": "file",
    }
    icon_name = mapping.get(suffix, "file")
    return icon_label(icon_name, size)
