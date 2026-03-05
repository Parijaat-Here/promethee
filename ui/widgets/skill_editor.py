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
skill_editor.py — Éditeur de skills (guides de bonnes pratiques LLM)

Sur le même modèle que ProfileEditorDialog / ProfileManagerDialog de
profile_selector.py, ce module fournit :

  - SkillEditorDialog   : dialogue de création/édition d'un skill
                          (nom, slug, description, tags, contenu Markdown)
  - SkillManagerDialog  : dialogue de gestion de la bibliothèque de skills
                          (liste, nouveau, éditer, supprimer, aperçu)

Les skills sont des fichiers Markdown stockés dans ~/.promethee/skills/.
Voir core/skill_manager.py pour la logique de persistance.
"""

import re

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QMessageBox, QGroupBox, QWidget,
    QListWidget, QListWidgetItem, QSplitter, QSizePolicy,
)

from .styles import ThemeManager


# ── Helpers de style ─────────────────────────────────────────────────────────

def _input_style() -> str:
    return (
        f"background-color: {ThemeManager.inline('input_bg')};"
        f"color: {ThemeManager.inline('input_color')};"
        f"border: 1px solid {ThemeManager.inline('input_border')};"
        f"border-radius: 6px;"
        f"padding: 6px 10px;"
        f"font-size: 13px;"
    )


def _group_style() -> str:
    return f"""
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
    """


def _list_style() -> str:
    return f"""
        QListWidget {{
            background-color: {ThemeManager.inline('input_bg')};
            color: {ThemeManager.inline('input_color')};
            border: 1px solid {ThemeManager.inline('input_border')};
            border-radius: 6px;
            padding: 4px;
            outline: none;
        }}
        QListWidget::item {{
            padding: 8px 10px;
            border-radius: 4px;
        }}
        QListWidget::item:hover {{
            background-color: {ThemeManager.inline('attachment_btn_hover_bg')};
        }}
        QListWidget::item:selected {{
            background-color: {ThemeManager.inline('attachment_btn_color')};
            color: white;
        }}
    """


def _hint_style() -> str:
    return (
        f"color: {ThemeManager.inline('tools_panel_info')};"
        f"font-size: 10px; font-weight: 400;"
    )


# ── SkillEditorDialog ─────────────────────────────────────────────────────────

class SkillEditorDialog(QDialog):
    """
    Dialogue de création ou d'édition d'un skill.

    Champs exposés :
      - Nom affiché (name)        : texte libre, ex. "Conventions de nommage"
      - Slug (identifiant fichier): lettres/chiffres/tirets/underscores
      - Description courte        : une ligne, résumée dans les listes
      - Tags                      : mots-clés séparés par des virgules
      - Version                   : ex. "1.0"
      - Contenu Markdown          : corps du skill avec frontmatter généré auto
    """

    def __init__(
        self,
        slug: str = None,
        content: str = None,
        parent=None,
    ):
        super().__init__(parent)
        self._slug    = slug
        self._is_new  = slug is None

        self.setWindowTitle("Nouveau skill" if self._is_new else f"Éditer : {slug}")
        self.setModal(True)
        self.setMinimumSize(700, 680)

        self._setup_ui(content or "")

    # ── Construction de l'interface ───────────────────────────────────

    def _setup_ui(self, raw_content: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        # ── Métadonnées ───────────────────────────────────────────────
        meta_group = QGroupBox("📋 Métadonnées du skill")
        meta_group.setStyleSheet(_group_style())
        meta_inner = QVBoxLayout(meta_group)
        meta_inner.setSpacing(8)
        meta_inner.setContentsMargins(10, 14, 10, 10)

        # Ligne 1 : Nom + Slug
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        col_name = QVBoxLayout()
        col_name.addWidget(QLabel("Nom affiché :"))
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Ex : Conventions de nommage")
        self._name_input.setStyleSheet(_input_style())
        # Générer le slug à la volée depuis le nom (mode création seulement)
        if self._is_new:
            self._name_input.textChanged.connect(self._auto_slug)
        col_name.addWidget(self._name_input)
        row1.addLayout(col_name, stretch=3)

        col_slug = QVBoxLayout()
        lbl_slug = QLabel("Slug (nom de fichier) :")
        col_slug.addWidget(lbl_slug)
        self._slug_input = QLineEdit()
        self._slug_input.setPlaceholderText("conventions_nommage")
        self._slug_input.setStyleSheet(_input_style())
        if not self._is_new:
            # Pas de renommage de fichier : slug verrouillé
            self._slug_input.setText(self._slug)
            self._slug_input.setEnabled(False)
            self._slug_input.setToolTip(
                "Le slug ne peut pas être modifié après la création.\n"
                "Supprimez et recréez le skill pour changer son identifiant."
            )
        col_slug.addWidget(self._slug_input)
        row1.addLayout(col_slug, stretch=2)

        meta_inner.addLayout(row1)

        # Ligne 2 : Description
        meta_inner.addWidget(QLabel("Description courte :"))
        self._desc_input = QLineEdit()
        self._desc_input.setPlaceholderText(
            "Résumé en une ligne affiché dans la liste des skills"
        )
        self._desc_input.setStyleSheet(_input_style())
        meta_inner.addWidget(self._desc_input)

        # Ligne 3 : Tags + Version
        row3 = QHBoxLayout()
        row3.setSpacing(12)

        col_tags = QVBoxLayout()
        col_tags.addWidget(QLabel("Tags (séparés par des virgules) :"))
        self._tags_input = QLineEdit()
        self._tags_input.setPlaceholderText("nommage, fichiers, organisation")
        self._tags_input.setStyleSheet(_input_style())
        col_tags.addWidget(self._tags_input)
        row3.addLayout(col_tags, stretch=4)

        col_ver = QVBoxLayout()
        col_ver.addWidget(QLabel("Version :"))
        self._version_input = QLineEdit()
        self._version_input.setPlaceholderText("1.0")
        self._version_input.setMaximumWidth(80)
        self._version_input.setStyleSheet(_input_style())
        col_ver.addWidget(self._version_input)
        row3.addLayout(col_ver, stretch=1)

        meta_inner.addLayout(row3)
        layout.addWidget(meta_group)

        # ── Pré-remplissage depuis le contenu existant ─────────────────
        if raw_content:
            self._parse_existing_content(raw_content)

        # ── Contenu Markdown ──────────────────────────────────────────
        content_lbl = QLabel("Contenu Markdown :")
        layout.addWidget(content_lbl)

        hint_lbl = QLabel(
            "Rédigez ici les instructions, conventions ou guides à suivre. "
            "Le frontmatter YAML sera généré automatiquement à la sauvegarde."
        )
        hint_lbl.setStyleSheet(_hint_style())
        hint_lbl.setWordWrap(True)
        layout.addWidget(hint_lbl)

        self._content_input = QTextEdit()
        self._content_input.setPlaceholderText(
            "# Titre du skill\n\n"
            "## Section 1\n\n"
            "Décrivez vos conventions ici…\n\n"
            "## Section 2\n\n"
            "- Règle A\n"
            "- Règle B\n"
        )
        self._content_input.setStyleSheet(
            f"QTextEdit {{"
            f"  background-color: {ThemeManager.inline('input_bg')};"
            f"  color: {ThemeManager.inline('input_color')};"
            f"  border: 1px solid {ThemeManager.inline('input_border')};"
            f"  border-radius: 6px;"
            f"  padding: 8px;"
            f"  font-size: 12px;"
            f"  font-family: 'Courier New', monospace;"
            f"}}"
        )
        # Insérer le corps sans frontmatter si contenu existant
        body = self._extract_body(raw_content) if raw_content else ""
        self._content_input.setPlainText(body)
        layout.addWidget(self._content_input, stretch=1)

        # ── Boutons ───────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Créer" if self._is_new else "Sauvegarder")
        save_btn.setObjectName("send_btn")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    # ── Parsing du contenu existant ───────────────────────────────────

    def _parse_existing_content(self, raw: str) -> None:
        """Pré-remplit les champs de métadonnées depuis un frontmatter existant."""
        import yaml as _yaml
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.DOTALL)
        if not fm_match:
            return
        try:
            fm = _yaml.safe_load(fm_match.group(1)) or {}
        except Exception:
            return

        self._name_input.setText(str(fm.get("name", "")))
        self._desc_input.setText(str(fm.get("description", "")))
        tags = fm.get("tags", [])
        if isinstance(tags, list):
            self._tags_input.setText(", ".join(str(t) for t in tags))
        self._version_input.setText(str(fm.get("version", "1.0")))

    @staticmethod
    def _extract_body(raw: str) -> str:
        """Retourne le corps d'un skill sans son frontmatter YAML."""
        match = re.match(r"^---\s*\n.*?\n---\s*\n", raw, re.DOTALL)
        return raw[match.end():].lstrip("\n") if match else raw

    # ── Auto-génération du slug ───────────────────────────────────────

    def _auto_slug(self, name: str) -> None:
        """Génère un slug depuis le nom saisi (mode création uniquement)."""
        import unicodedata
        # Normalisation Unicode → ASCII
        nfkd = unicodedata.normalize("NFKD", name)
        ascii_name = nfkd.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_name).strip("_").lower()
        self._slug_input.setText(slug)

    # ── Construction du contenu final ────────────────────────────────

    def _build_full_content(self) -> str:
        """Assemble frontmatter YAML + corps Markdown."""
        name    = self._name_input.text().strip()
        desc    = self._desc_input.text().strip()
        tags_raw = self._tags_input.text().strip()
        version = self._version_input.text().strip() or "1.0"
        body    = self._content_input.toPlainText()

        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        lines = ["---"]
        if name:
            lines.append(f"name: {name}")
        if desc:
            lines.append(f"description: {desc}")
        if tags:
            lines.append(f"tags: [{', '.join(tags)}]")
        lines.append(f"version: {version}")
        lines.append("---")
        lines.append("")
        lines.append(body)
        return "\n".join(lines)

    # ── Sauvegarde ────────────────────────────────────────────────────

    def _save(self) -> None:
        slug    = self._slug_input.text().strip()
        name    = self._name_input.text().strip()
        content = self._content_input.toPlainText().strip()

        # Validations
        if not slug:
            QMessageBox.warning(self, "Champ requis", "Le slug est requis.")
            return
        if not re.match(r"^[a-zA-Z0-9_\-]+$", slug):
            QMessageBox.warning(
                self,
                "Slug invalide",
                "Le slug ne peut contenir que des lettres, chiffres, tirets "
                "et underscores.\nExemple : conventions_nommage",
            )
            return
        if not name:
            QMessageBox.warning(self, "Champ requis", "Le nom affiché est requis.")
            return
        if not content:
            QMessageBox.warning(
                self, "Contenu vide",
                "Le contenu du skill est vide. Ajoutez au moins une ligne."
            )
            return

        self._result_slug    = slug
        self._result_content = self._build_full_content()
        self.accept()

    # ── Résultat ──────────────────────────────────────────────────────

    def get_result(self) -> tuple[str, str]:
        """Retourne (slug, full_content) après acceptation du dialogue."""
        return self._result_slug, self._result_content


# ── SkillManagerDialog ────────────────────────────────────────────────────────

class SkillManagerDialog(QDialog):
    """
    Dialogue de gestion de la bibliothèque de skills.

    Affiche la liste des skills disponibles avec un aperçu inline,
    et permet de créer, éditer ou supprimer des skills.

    Signal
    ------
    skills_changed : émis après toute modification (création, édition,
                     suppression) pour permettre aux composants amont
                     de rafraîchir leurs listes.
    """

    skills_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestion des skills")
        self.setModal(True)
        self.setMinimumSize(760, 520)

        from core.skill_manager import get_skill_manager
        self._sm = get_skill_manager()

        self._setup_ui()

    # ── Construction de l'interface ───────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        # Titre
        title = QLabel("📚 Gestion des skills")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Les skills sont des guides Markdown stockés dans "
            f"<code>~/.promethee/skills/</code>. "
            "Le LLM peut les consulter à la demande ou ils peuvent être "
            "épinglés dans un profil pour être injectés automatiquement."
        )
        subtitle.setStyleSheet(_hint_style())
        subtitle.setWordWrap(True)
        subtitle.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(subtitle)

        # ── Splitter liste / aperçu ───────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        # Panneau gauche : liste des skills
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(6)

        self._skill_list = QListWidget()
        self._skill_list.setStyleSheet(_list_style())
        self._skill_list.currentItemChanged.connect(self._on_selection_changed)
        self._skill_list.itemDoubleClicked.connect(self._edit_skill)
        left_layout.addWidget(self._skill_list)

        splitter.addWidget(left)

        # Panneau droit : aperçu du contenu
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(4)

        preview_lbl = QLabel("Aperçu :")
        preview_lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
        right_layout.addWidget(preview_lbl)

        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setStyleSheet(
            f"QTextEdit {{"
            f"  background-color: {ThemeManager.inline('input_bg')};"
            f"  color: {ThemeManager.inline('input_color')};"
            f"  border: 1px solid {ThemeManager.inline('input_border')};"
            f"  border-radius: 6px;"
            f"  padding: 8px;"
            f"  font-size: 11px;"
            f"  font-family: 'Courier New', monospace;"
            f"}}"
        )
        self._preview.setPlaceholderText("Sélectionnez un skill pour prévisualiser son contenu…")
        right_layout.addWidget(self._preview, stretch=1)

        splitter.addWidget(right)
        splitter.setSizes([280, 420])
        layout.addWidget(splitter, stretch=1)

        # ── Barre de boutons ──────────────────────────────────────────
        btn_layout = QHBoxLayout()

        new_btn = QPushButton("➕ Nouveau")
        new_btn.clicked.connect(self._new_skill)
        btn_layout.addWidget(new_btn)

        self._edit_btn = QPushButton("✏️ Éditer")
        self._edit_btn.clicked.connect(self._edit_skill)
        self._edit_btn.setEnabled(False)
        btn_layout.addWidget(self._edit_btn)

        self._delete_btn = QPushButton("🗑️ Supprimer")
        self._delete_btn.clicked.connect(self._delete_skill)
        self._delete_btn.setEnabled(False)
        btn_layout.addWidget(self._delete_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("send_btn")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # Peupler la liste
        self._refresh_list()

    # ── Gestion de la liste ───────────────────────────────────────────

    def _refresh_list(self, select_slug: str = None) -> None:
        """Relit le gestionnaire de skills et reconstruit la liste."""
        self._sm.refresh()
        self._skill_list.clear()
        self._preview.clear()

        skills = self._sm.list_skills()
        target_row = 0

        for i, sk in enumerate(skills):
            # Ligne : "Nom du skill  — description courte  [slug]"
            label = sk.name
            if sk.description:
                short = sk.description[:55] + ("…" if len(sk.description) > 55 else "")
                label += f"  —  {short}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, sk.slug)
            item.setToolTip(
                f"Slug : {sk.slug}\n"
                f"Version : {sk.version}\n"
                f"Taille : {sk.size:,} caractères\n"
                + (f"Tags : {', '.join(sk.tags)}" if sk.tags else "")
            )
            self._skill_list.addItem(item)
            if sk.slug == select_slug:
                target_row = i

        if skills:
            self._skill_list.setCurrentRow(target_row)

        # Boutons dépendent de la sélection
        has_items = bool(skills)
        self._edit_btn.setEnabled(has_items)
        self._delete_btn.setEnabled(has_items)

    def _on_selection_changed(
        self,
        current: QListWidgetItem,
        previous: QListWidgetItem,
    ) -> None:
        """Met à jour l'aperçu quand la sélection change."""
        if current is None:
            self._preview.clear()
            self._edit_btn.setEnabled(False)
            self._delete_btn.setEnabled(False)
            return

        slug = current.data(Qt.ItemDataRole.UserRole)
        try:
            content = self._sm.read_skill(slug)
            self._preview.setPlainText(content)
        except Exception as exc:
            self._preview.setPlainText(f"[Erreur de lecture : {exc}]")

        self._edit_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)

    # ── Actions CRUD ──────────────────────────────────────────────────

    def _new_skill(self) -> None:
        """Ouvre l'éditeur pour créer un nouveau skill."""
        dialog = SkillEditorDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        slug, content = dialog.get_result()

        # Vérifier les conflits de slug
        if self._sm.exists(slug):
            reply = QMessageBox.question(
                self,
                "Slug existant",
                f"Un skill avec le slug « {slug} » existe déjà.\n"
                "Voulez-vous remplacer son contenu ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            self._sm.save_skill(slug, content)
        except ValueError as exc:
            QMessageBox.critical(self, "Slug invalide", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Erreur de sauvegarde", str(exc))
            return

        self._refresh_list(select_slug=slug)
        self.skills_changed.emit()

    def _edit_skill(self, _item=None) -> None:
        """Ouvre l'éditeur pour modifier le skill sélectionné."""
        item = self._skill_list.currentItem()
        if item is None:
            return

        slug = item.data(Qt.ItemDataRole.UserRole)
        try:
            content = self._sm.read_skill(slug)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur de lecture", str(exc))
            return

        dialog = SkillEditorDialog(slug=slug, content=content, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        _, new_content = dialog.get_result()
        try:
            self._sm.save_skill(slug, new_content)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur de sauvegarde", str(exc))
            return

        self._refresh_list(select_slug=slug)
        self.skills_changed.emit()

    def _delete_skill(self) -> None:
        """Supprime le skill sélectionné après confirmation."""
        item = self._skill_list.currentItem()
        if item is None:
            return

        slug = item.data(Qt.ItemDataRole.UserRole)
        info = self._sm.get_info(slug)
        name = info.name if info else slug

        reply = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Supprimer le skill « {name} » ({slug}.md) ?\n\n"
            "Cette action est irréversible. Les profils qui l'épinglent "
            "devront être mis à jour.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self._sm.delete_skill(slug)
        except Exception as exc:
            QMessageBox.critical(self, "Erreur de suppression", str(exc))
            return

        self._refresh_list()
        self.skills_changed.emit()
