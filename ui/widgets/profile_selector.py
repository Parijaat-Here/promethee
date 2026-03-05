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
profile_selector.py — Widget de sélection de profil système
"""
from PyQt6.QtWidgets import QComboBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QLineEdit, QMessageBox, QCheckBox, QGroupBox, QScrollArea, QWidget, QButtonGroup
from PyQt6.QtCore import pyqtSignal, Qt
from .styles import ThemeManager


class ProfileSelector(QComboBox):
    """ComboBox pour sélectionner un profil système."""

    profile_changed = pyqtSignal(str, str)  # (profile_name, system_prompt)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(28)
        self.setMinimumWidth(180)
        self._apply_style()

        # Connexion
        self.currentTextChanged.connect(self._on_selection_changed)

    def showPopup(self):
        """Override pour afficher le popup."""
        super().showPopup()

    def paintEvent(self, event):
        """Override pour ajouter une flèche visuelle."""
        super().paintEvent(event)
        from PyQt6.QtGui import QPainter, QColor
        from PyQt6.QtCore import QRect, Qt

        painter = QPainter(self)
        painter.setPen(QColor(ThemeManager.inline('logo_color')))

        # Dessiner une flèche à droite
        rect = self.rect()
        arrow_x = rect.width() - 20
        arrow_y = rect.height() // 2

        # Dessiner "▼"
        painter.setFont(self.font())
        painter.drawText(arrow_x, arrow_y + 5, "▼")
        painter.end()

    def _apply_style(self):
        """Applique le style du ComboBox."""
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {ThemeManager.inline('topbar_bg')};
                color: {ThemeManager.inline('logo_color')};
                border: 1px solid {ThemeManager.inline('topbar_border')};
                border-radius: 6px;
                padding: 4px 8px;
                padding-right: 28px;
                font-size: 12px;
            }}
            QComboBox:hover {{
                border-color: {ThemeManager.inline('attachment_btn_color')};
            }}
            QComboBox QAbstractItemView {{
                background-color: {ThemeManager.inline('menu_bg')};
                color: {ThemeManager.inline('menu_item_color')};
                border: 1px solid {ThemeManager.inline('menu_border')};
                selection-background-color: {ThemeManager.inline('menu_item_selected_bg')};
                selection-color: {ThemeManager.inline('menu_item_selected_color')};
                padding: 4px;
            }}
        """)

    def load_profiles(self, profile_names: list, current: str = None):
        """Charge la liste des profils."""
        self.blockSignals(True)
        self.clear()
        self.addItems(profile_names)

        if current and current in profile_names:
            self.setCurrentText(current)
        elif profile_names:
            self.setCurrentIndex(0)

        self.blockSignals(False)

    def _on_selection_changed(self, profile_name: str):
        """Appelé quand la sélection change."""
        # Le signal sera connecté au chat_panel pour récupérer le prompt
        from .profile_manager import get_profile_manager
        manager = get_profile_manager()
        prompt = manager.get_prompt(profile_name)
        self.profile_changed.emit(profile_name, prompt)

    def refresh_theme(self):
        """Rafraîchit le thème."""
        self._apply_style()
        self._apply_style()


class ProfileEditorDialog(QDialog):
    """Dialogue pour créer/éditer un profil."""

    def __init__(self, profile_name: str = None, prompt: str = None,
                 tool_families: dict = None, pinned_skills: list = None, parent=None):
        super().__init__(parent)
        self.profile_name = profile_name
        self.is_new = profile_name is None
        self._tool_families  = tool_families  or {'enabled': [], 'disabled': []}
        self._pinned_skills  = list(pinned_skills or [])

        self.setWindowTitle("Nouveau profil" if self.is_new else f"Éditer : {profile_name}")
        self.setModal(True)
        self.setMinimumSize(700, 820)

        self._setup_ui(prompt or "")

    def _setup_ui(self, initial_prompt: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        # Nom du profil
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nom du profil :"))

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex: Assistant juridique")
        if self.profile_name:
            self.name_input.setText(self.profile_name)
            self.name_input.setEnabled(False)  # Pas de renommage
        self.name_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {ThemeManager.inline('input_bg')};
                color: {ThemeManager.inline('input_color')};
                border: 1px solid {ThemeManager.inline('input_border')};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
            }}
        """)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Prompt système
        layout.addWidget(QLabel("Prompt système :"))

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(
            "Définissez le rôle, les règles et le comportement de l'assistant...\n\n"
            "Exemple:\n"
            "Rôle : Tu es un expert en...\n\n"
            "Règles :\n"
            "- Règle 1\n"
            "- Règle 2"
        )
        self.prompt_input.setPlainText(initial_prompt)
        self.prompt_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {ThemeManager.inline('input_bg')};
                color: {ThemeManager.inline('input_color')};
                border: 1px solid {ThemeManager.inline('input_border')};
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
                font-family: 'Courier New', monospace;
            }}
        """)
        layout.addWidget(self.prompt_input, stretch=4)

        # ── Familles d'outils ──────────────────────────────────────────
        group_box = QGroupBox("🛠️ Outils activés par ce profil")
        group_box.setStyleSheet(f"""
            QGroupBox {{
                color: {ThemeManager.inline('tools_card_name')};
                border: 1px solid {ThemeManager.inline('tools_card_border')};
                border-radius: 6px;
                margin-top: 8px;
                font-size: 12px;
                font-weight: 600;
                padding-top: 4px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }}
        """)
        group_inner = QVBoxLayout(group_box)
        group_inner.setSpacing(4)
        group_inner.setContentsMargins(10, 12, 10, 8)

        hint = QLabel("Coché = forcé actif  ·  Décoché = forcé inactif  ·  Indéterminé = laissé à l'utilisateur")
        hint.setStyleSheet(f"color: {ThemeManager.inline('tools_panel_info')}; font-size: 10px; font-weight: 400;")
        hint.setWordWrap(True)
        group_inner.addWidget(hint)

        # Récupérer les familles disponibles
        try:
            from core import tools_engine as _te
            families = _te.list_families()
        except Exception:
            families = []

        self._family_checkboxes: dict[str, QCheckBox] = {}
        enabled_set  = set(self._tool_families.get('enabled',  []))
        disabled_set = set(self._tool_families.get('disabled', []))

        families_widget = QWidget()
        from PyQt6.QtWidgets import QGridLayout
        families_layout = QGridLayout(families_widget)
        families_layout.setSpacing(3)
        families_layout.setContentsMargins(0, 4, 0, 0)
        families_layout.setColumnStretch(0, 1)
        families_layout.setColumnStretch(1, 1)

        for i, fam in enumerate(families):
            key   = fam['family']
            label = fam['label']
            icon  = fam['icon']

            cb = QCheckBox(f"{icon}  {label}")
            cb.setTristate(True)
            cb.setStyleSheet(f"color: {ThemeManager.inline('tools_card_name')}; font-size: 12px;")

            if key in enabled_set:
                cb.setCheckState(Qt.CheckState.Checked)
            elif key in disabled_set:
                cb.setCheckState(Qt.CheckState.Unchecked)
            else:
                cb.setCheckState(Qt.CheckState.PartiallyChecked)

            self._family_checkboxes[key] = cb
            families_layout.addWidget(cb, i // 2, i % 2)

        if not families:
            families_layout.addWidget(QLabel("(Aucune famille d'outil disponible)"), 0, 0, 1, 2)

        group_inner.addWidget(families_widget)
        layout.addWidget(group_box)

        # ── Skills épinglés ────────────────────────────────────────────
        skills_group = QGroupBox("📚 Skills épinglés dans ce profil")
        skills_group.setStyleSheet(f"""
            QGroupBox {{
                color: {ThemeManager.inline('tools_card_name')};
                border: 1px solid {ThemeManager.inline('tools_card_border')};
                border-radius: 6px;
                margin-top: 8px;
                font-size: 12px;
                font-weight: 600;
                padding-top: 4px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }}
        """)
        skills_inner = QVBoxLayout(skills_group)
        skills_inner.setSpacing(4)
        skills_inner.setContentsMargins(10, 12, 10, 8)

        skills_hint = QLabel(
            "Coché = injecté automatiquement dans le prompt système à chaque session.\n"
            "Les skills non épinglés restent accessibles via l'outil skill_read."
        )
        skills_hint.setStyleSheet(
            f"color: {ThemeManager.inline('tools_panel_info')}; font-size: 10px; font-weight: 400;"
        )
        skills_hint.setWordWrap(True)
        skills_inner.addWidget(skills_hint)

        try:
            from core.skill_manager import get_skill_manager
            available_skills = get_skill_manager().list_skills()
        except Exception:
            available_skills = []

        self._skill_checkboxes: dict[str, QCheckBox] = {}
        pinned_set = set(self._pinned_skills)

        skills_widget = QWidget()
        skills_layout = QVBoxLayout(skills_widget)
        skills_layout.setSpacing(3)
        skills_layout.setContentsMargins(0, 4, 0, 0)

        if available_skills:
            for sk in available_skills:
                label = f"{sk.name}"
                if sk.description:
                    label += f"  —  {sk.description[:60]}{'…' if len(sk.description) > 60 else ''}"
                cb = QCheckBox(label)
                cb.setChecked(sk.slug in pinned_set)
                cb.setStyleSheet(
                    f"color: {ThemeManager.inline('tools_card_name')}; font-size: 11px;"
                )
                cb.setToolTip(f"Slug : {sk.slug}  ·  Taille : {sk.size:,} chars")
                self._skill_checkboxes[sk.slug] = cb
                skills_layout.addWidget(cb)
        else:
            no_skills_lbl = QLabel(
                "Aucun skill disponible. "
                "Créez des fichiers .md dans ~/.promethee/skills/"
            )
            no_skills_lbl.setStyleSheet(
                f"color: {ThemeManager.inline('tools_panel_info')}; font-size: 11px;"
            )
            no_skills_lbl.setWordWrap(True)
            skills_layout.addWidget(no_skills_lbl)

        skills_inner.addWidget(skills_widget)
        layout.addWidget(skills_group)

        # Boutons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Créer" if self.is_new else "Sauvegarder")
        save_btn.setObjectName("send_btn")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _save(self):
        """Sauvegarde le profil."""
        name = self.name_input.text().strip()
        prompt = self.prompt_input.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "Erreur", "Le nom du profil est requis.")
            return

        if name == "Aucun rôle" and self.is_new:
            QMessageBox.warning(self, "Erreur", "Ce nom est réservé.")
            return

        self.profile_name = name
        self.result_prompt = prompt

        # Récupérer l'état des familles d'outils
        self.result_tool_families = {'enabled': [], 'disabled': []}
        for key, cb in self._family_checkboxes.items():
            state = cb.checkState()
            if state == Qt.CheckState.Checked:
                self.result_tool_families['enabled'].append(key)
            elif state == Qt.CheckState.Unchecked:
                self.result_tool_families['disabled'].append(key)
            # PartiallyChecked = indéterminé, pas de contrainte

        # Récupérer les skills épinglés
        self.result_pinned_skills = [
            slug for slug, cb in self._skill_checkboxes.items()
            if cb.isChecked()
        ]

        self.accept()

    def get_result(self):
        """Retourne le profil créé/édité : (name, prompt, tool_families, pinned_skills)."""
        return (
            self.profile_name,
            self.result_prompt,
            self.result_tool_families,
            getattr(self, "result_pinned_skills", []),
        )


class ProfileManagerDialog(QDialog):
    """Dialogue pour gérer tous les profils."""

    profiles_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestion des profils")
        self.setModal(True)
        self.setMinimumSize(500, 400)

        from .profile_manager import get_profile_manager
        self.manager = get_profile_manager()

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)

        # Titre
        title = QLabel("👤 Gestion des profils")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(title)

        # Liste des profils
        from PyQt6.QtWidgets import QListWidget
        self.profile_list = QListWidget()
        self.profile_list.addItems(self.manager.get_profile_names())
        self.profile_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {ThemeManager.inline('input_bg')};
                color: {ThemeManager.inline('input_color')};
                border: 1px solid {ThemeManager.inline('input_border')};
                border-radius: 6px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 4px;
            }}
            QListWidget::item:hover {{
                background-color: {ThemeManager.inline('attachment_btn_hover_bg')};
            }}
            QListWidget::item:selected {{
                background-color: {ThemeManager.inline('attachment_btn_color')};
                color: white;
            }}
        """)
        layout.addWidget(self.profile_list)

        # Boutons d'action
        btn_layout = QHBoxLayout()

        new_btn = QPushButton("➕ Nouveau")
        new_btn.clicked.connect(self._new_profile)
        btn_layout.addWidget(new_btn)

        edit_btn = QPushButton("✏️ Éditer")
        edit_btn.clicked.connect(self._edit_profile)
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton("🗑️ Supprimer")
        delete_btn.clicked.connect(self._delete_profile)
        btn_layout.addWidget(delete_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("send_btn")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _new_profile(self):
        """Créer un nouveau profil."""
        dialog = ProfileEditorDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, prompt, tool_families, pinned_skills = dialog.get_result()
            self.manager.add_profile(name, prompt)
            self.manager.set_tool_families(
                name,
                tool_families.get('enabled', []),
                tool_families.get('disabled', []),
            )
            self.manager.set_pinned_skills(name, pinned_skills)
            self.profile_list.addItem(name)
            self.profiles_changed.emit()

    def _edit_profile(self):
        """Éditer le profil sélectionné."""
        current_item = self.profile_list.currentItem()
        if not current_item:
            return

        name          = current_item.text()
        prompt        = self.manager.get_prompt(name)
        tool_families = self.manager.get_tool_families(name)
        pinned_skills = self.manager.get_pinned_skills(name)

        dialog = ProfileEditorDialog(
            name, prompt,
            tool_families=tool_families,
            pinned_skills=pinned_skills,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            _, new_prompt, new_tool_families, new_pinned = dialog.get_result()
            self.manager.update_profile(name, new_prompt)
            self.manager.set_tool_families(
                name,
                new_tool_families.get('enabled', []),
                new_tool_families.get('disabled', []),
            )
            self.manager.set_pinned_skills(name, new_pinned)
            self.profiles_changed.emit()

    def _delete_profile(self):
        """Supprimer le profil sélectionné."""
        current_item = self.profile_list.currentItem()
        if not current_item:
            return

        name = current_item.text()

        if name == "Aucun rôle":
            QMessageBox.warning(self, "Erreur", "Impossible de supprimer ce profil.")
            return

        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Supprimer le profil '{name}' ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.manager.remove_profile(name)
            self.profile_list.takeItem(self.profile_list.row(current_item))
            self.profiles_changed.emit()
