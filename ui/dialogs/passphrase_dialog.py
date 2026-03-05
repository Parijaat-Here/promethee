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
passphrase_dialog.py — Dialogue de saisie / création de passphrase de chiffrement

Deux modes
----------
  MODE_OPEN   : ouverture d'une base existante — demande la passphrase et la valide.
  MODE_CREATE : première utilisation — demande la passphrase + confirmation,
                affiche les exigences minimales et génère un avertissement de
                non-récupérabilité.

Intégration dans app.py
-----------------------
    from ui.dialogs.passphrase_dialog import PassphraseDialog
    dlg = PassphraseDialog(mode=PassphraseDialog.MODE_OPEN, parent=None)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        db.set_passphrase(dlg.passphrase())
    else:
        sys.exit(0)  # l'utilisateur a annulé → on ne peut pas ouvrir la base
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QSizePolicy,
)
from PyQt6.QtGui import QFont

from ui.widgets.styles import ThemeManager


class PassphraseDialog(QDialog):
    """
    Dialogue modal de saisie de passphrase.

    Attributs de classe
    -------------------
    MODE_OPEN   : str — ouverture d'une base existante
    MODE_CREATE : str — création d'une nouvelle base chiffrée
    """

    MODE_OPEN   = "open"
    MODE_CREATE = "create"

    def __init__(self, mode: str = MODE_OPEN, parent=None):
        super().__init__(parent)
        self._mode = mode
        self._passphrase_value = ""

        self.setWindowTitle("Prométhée — Base de données chiffrée")
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.CustomizeWindowHint
        )
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setStyleSheet(ThemeManager.dialog_style())

        self._setup_ui()

    # ── Construction ─────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)

        # ── Icône + titre ─────────────────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(12)
        icon_lbl = QLabel("🔒")
        icon_lbl.setStyleSheet("font-size: 28px;")
        icon_lbl.setFixedWidth(40)
        hdr.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        if self._mode == self.MODE_CREATE:
            title_text = "Créer une passphrase de chiffrement"
            sub_text   = "La base de données sera protégée par AES-256-GCM."
        else:
            title_text = "Base de données chiffrée"
            sub_text   = "Saisissez votre passphrase pour ouvrir l'historique."

        title = QLabel(title_text)
        title.setStyleSheet(
            f"color: {ThemeManager.inline('text_primary')}; "
            "font-size: 14px; font-weight: 700;"
        )
        title_col.addWidget(title)

        sub = QLabel(sub_text)
        sub.setStyleSheet(
            f"color: {ThemeManager.inline('text_secondary')}; font-size: 11px;"
        )
        sub.setWordWrap(True)
        title_col.addWidget(sub)

        hdr.addLayout(title_col, stretch=1)
        layout.addLayout(hdr)

        # ── Séparateur ────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {ThemeManager.inline('border')};")
        layout.addWidget(sep)

        # ── Champ passphrase ──────────────────────────────────────
        pp_label = QLabel("Passphrase :")
        pp_label.setStyleSheet(
            f"color: {ThemeManager.inline('text_secondary')}; font-size: 12px;"
        )
        layout.addWidget(pp_label)

        pp_row = QHBoxLayout()
        pp_row.setSpacing(6)
        self._pp_field = QLineEdit()
        self._pp_field.setObjectName("input_box")
        self._pp_field.setEchoMode(QLineEdit.EchoMode.Password)
        self._pp_field.setPlaceholderText("Entrez votre passphrase…")
        self._pp_field.setMinimumHeight(36)
        self._pp_field.textChanged.connect(self._on_text_changed)
        self._pp_field.returnPressed.connect(self._on_accept)
        pp_row.addWidget(self._pp_field)

        self._eye_btn = QPushButton("👁")
        self._eye_btn.setObjectName("tool_btn")
        self._eye_btn.setFixedSize(36, 36)
        self._eye_btn.setCheckable(True)
        self._eye_btn.setToolTip("Afficher / masquer")
        self._eye_btn.toggled.connect(self._toggle_echo)
        pp_row.addWidget(self._eye_btn)
        layout.addLayout(pp_row)

        # ── Confirmation (mode CREATE seulement) ──────────────────
        if self._mode == self.MODE_CREATE:
            confirm_label = QLabel("Confirmer la passphrase :")
            confirm_label.setStyleSheet(
                f"color: {ThemeManager.inline('text_secondary')}; font-size: 12px;"
            )
            layout.addWidget(confirm_label)

            confirm_row = QHBoxLayout()
            confirm_row.setSpacing(6)
            self._confirm_field = QLineEdit()
            self._confirm_field.setObjectName("input_box")
            self._confirm_field.setEchoMode(QLineEdit.EchoMode.Password)
            self._confirm_field.setPlaceholderText("Répétez la passphrase…")
            self._confirm_field.setMinimumHeight(36)
            self._confirm_field.textChanged.connect(self._on_text_changed)
            self._confirm_field.returnPressed.connect(self._on_accept)
            confirm_row.addWidget(self._confirm_field)

            eye_btn2 = QPushButton("👁")
            eye_btn2.setObjectName("tool_btn")
            eye_btn2.setFixedSize(36, 36)
            eye_btn2.setCheckable(True)
            eye_btn2.setToolTip("Afficher / masquer")
            eye_btn2.toggled.connect(
                lambda checked: self._confirm_field.setEchoMode(
                    QLineEdit.EchoMode.Normal if checked
                    else QLineEdit.EchoMode.Password
                )
            )
            confirm_row.addWidget(eye_btn2)
            layout.addLayout(confirm_row)

            # Indicateur de force
            self._strength_lbl = QLabel("")
            self._strength_lbl.setStyleSheet("font-size: 11px;")
            layout.addWidget(self._strength_lbl)
        else:
            self._confirm_field  = None
            self._strength_lbl   = None

        # ── Message d'erreur ──────────────────────────────────────
        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet(
            f"color: {ThemeManager.inline('stop_btn_color')}; font-size: 11px;"
        )
        self._error_lbl.setWordWrap(True)
        self._error_lbl.setVisible(False)
        layout.addWidget(self._error_lbl)

        # ── Avertissement (mode CREATE) ────────────────────────────
        if self._mode == self.MODE_CREATE:
            warn_box = QFrame()
            warn_box.setStyleSheet(
                f"QFrame {{ background: {ThemeManager.inline('elevated_bg')}; "
                f"border: 1px solid {ThemeManager.inline('eco_warn_color')}; "
                "border-radius: 6px; padding: 2px; }}"
            )
            warn_layout = QVBoxLayout(warn_box)
            warn_layout.setContentsMargins(10, 8, 10, 8)
            warn = QLabel(
                "⚠️  Cette passphrase est la seule clé d'accès à vos conversations.\n"
                "Il n'existe aucun mécanisme de récupération en cas d'oubli.\n"
                "Conservez-la dans un gestionnaire de mots de passe."
            )
            warn.setStyleSheet(
                f"color: {ThemeManager.inline('eco_warn_color')}; font-size: 11px;"
                "border: none; background: transparent;"
            )
            warn.setWordWrap(True)
            warn_layout.addWidget(warn)
            layout.addWidget(warn_box)

        # ── Boutons ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("tool_btn")
        cancel_btn.setMinimumWidth(90)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._ok_btn = QPushButton(
            "Créer" if self._mode == self.MODE_CREATE else "Ouvrir"
        )
        self._ok_btn.setObjectName("send_btn")
        self._ok_btn.setMinimumWidth(90)
        self._ok_btn.setEnabled(False)
        self._ok_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(self._ok_btn)

        layout.addLayout(btn_row)

        # Focus initial
        self._pp_field.setFocus()

    # ── Validation en temps réel ──────────────────────────────────────

    def _on_text_changed(self) -> None:
        pp = self._pp_field.text()
        self._error_lbl.setVisible(False)

        if self._mode == self.MODE_CREATE:
            strength, color = self._evaluate_strength(pp)
            if self._strength_lbl:
                self._strength_lbl.setText(f"Force : {strength}")
                self._strength_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
            confirm = self._confirm_field.text() if self._confirm_field else ""
            self._ok_btn.setEnabled(bool(pp) and pp == confirm and len(pp) >= 8)
        else:
            self._ok_btn.setEnabled(bool(pp))

    def _evaluate_strength(self, pp: str) -> tuple[str, str]:
        """Retourne (libellé de force, couleur) pour la passphrase donnée."""
        if len(pp) < 8:
            return "Trop courte (min. 8 caractères)", ThemeManager.inline("stop_btn_color")
        score = 0
        if len(pp) >= 12:   score += 1
        if len(pp) >= 20:   score += 1
        if any(c.isupper() for c in pp): score += 1
        if any(c.isdigit() for c in pp): score += 1
        if any(not c.isalnum() for c in pp): score += 1
        if score <= 1:
            return "Faible", ThemeManager.inline("stop_btn_color")
        if score <= 3:
            return "Correcte", ThemeManager.inline("eco_warn_color")
        return "Forte", ThemeManager.inline("eco_color")

    def _toggle_echo(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self._pp_field.setEchoMode(mode)

    # ── Acceptation ───────────────────────────────────────────────────

    def _on_accept(self) -> None:
        pp = self._pp_field.text()

        if self._mode == self.MODE_CREATE:
            confirm = self._confirm_field.text() if self._confirm_field else ""
            if pp != confirm:
                self._show_error("Les deux passphrases ne correspondent pas.")
                return
            if len(pp) < 8:
                self._show_error("La passphrase doit contenir au moins 8 caractères.")
                return

        if not pp:
            self._show_error("La passphrase ne peut pas être vide.")
            return

        self._passphrase_value = pp
        self.accept()

    def _show_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)
        self._error_lbl.setVisible(True)

    # ── API publique ──────────────────────────────────────────────────

    def passphrase(self) -> str:
        """Retourne la passphrase saisie. Vide si le dialogue a été annulé."""
        return self._passphrase_value

    def show_error(self, msg: str) -> None:
        """
        Affiche un message d'erreur dans le dialogue (ex. passphrase incorrecte).
        Appelé depuis app.py après tentative de set_passphrase() échouée.
        """
        self._show_error(msg)
        self._pp_field.clear()
        self._pp_field.setFocus()
        # Ré-activer pour permettre une nouvelle tentative
        self._ok_btn.setEnabled(False)
