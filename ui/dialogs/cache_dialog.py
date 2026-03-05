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
cache_dialog.py — Dialogue de gestion du cache d'URLs
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QFormLayout, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.widgets.styles import ThemeManager
from ui.widgets.url_cache import get_url_cache


class CacheDialog(QDialog):
    """Dialogue pour voir et gérer le cache d'URLs."""
    
    cache_cleared = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestion du cache d'URLs")
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setMinimumHeight(300)
        self._setup_ui()
        self._update_stats()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(16)
        
        # Titre
        title = QLabel("📦 Cache d'URLs")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #e8e6e1;")
        layout.addWidget(title)
        
        # Statistiques
        stats_group = QGroupBox("Statistiques")
        stats_group.setStyleSheet(f"""
            QGroupBox {{
                color: {ThemeManager.inline('attachment_name_color')};
                border: 1px solid {ThemeManager.inline('attachment_item_border')};
                border-radius: 8px;
                margin-top: 8px;
                padding: 12px;
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
        """)
        
        stats_layout = QFormLayout(stats_group)
        stats_layout.setSpacing(10)
        
        # Nombre d'entrées
        self._entries_label = QLabel("0")
        self._entries_label.setStyleSheet(
            f"color: {ThemeManager.inline('attachment_name_color')}; font-weight: normal;"
        )
        stats_layout.addRow("Nombre d'URLs :", self._entries_label)
        
        # Taille totale
        self._size_label = QLabel("0 MB")
        self._size_label.setStyleSheet(
            f"color: {ThemeManager.inline('attachment_name_color')}; font-weight: normal;"
        )
        stats_layout.addRow("Taille totale :", self._size_label)
        
        # Barre de progression visuelle
        self._size_bar = QProgressBar()
        self._size_bar.setMaximum(100)  # 100 MB max pour l'affichage
        self._size_bar.setTextVisible(False)
        self._size_bar.setFixedHeight(8)
        self._size_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {ThemeManager.inline('attachment_item_border')};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {ThemeManager.inline('attachment_btn_color')};
                border-radius: 4px;
            }}
        """)
        stats_layout.addRow("Utilisation :", self._size_bar)
        
        # TTL
        cache = get_url_cache()
        ttl_hours = cache.ttl.total_seconds() / 3600
        ttl_label = QLabel(f"{ttl_hours:.0f} heures")
        ttl_label.setStyleSheet(
            f"color: {ThemeManager.inline('attachment_size_color')}; font-weight: normal;"
        )
        stats_layout.addRow("Durée de vie :", ttl_label)
        
        layout.addWidget(stats_group)
        
        # Actions
        actions_group = QGroupBox("Actions")
        actions_group.setStyleSheet(f"""
            QGroupBox {{
                color: {ThemeManager.inline('attachment_name_color')};
                border: 1px solid {ThemeManager.inline('attachment_item_border')};
                border-radius: 8px;
                margin-top: 8px;
                padding: 12px;
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
        """)
        
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(8)
        
        # Bouton nettoyer les expirés
        clean_btn = QPushButton("🧹 Nettoyer les entrées expirées")
        clean_btn.setFixedHeight(36)
        clean_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ThemeManager.inline('attachment_btn_bg')};
                border: 1px solid {ThemeManager.inline('attachment_btn_border')};
                border-radius: 8px;
                color: {ThemeManager.inline('attachment_name_color')};
                font-size: 13px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {ThemeManager.inline('attachment_btn_hover_bg')};
            }}
        """)
        clean_btn.clicked.connect(self._clean_expired)
        actions_layout.addWidget(clean_btn)
        
        # Bouton vider complètement
        self._clear_btn = QPushButton("🗑️ Vider complètement le cache")
        self._clear_btn.setFixedHeight(36)
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ThemeManager.inline('attachment_remove_hover_bg')};
                border: 1px solid {ThemeManager.inline('attachment_item_border')};
                border-radius: 8px;
                color: {ThemeManager.inline('attachment_remove_hover_color')};
                font-size: 13px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #4a2828;
            }}
        """)
        self._clear_btn.clicked.connect(self._clear_cache)
        actions_layout.addWidget(self._clear_btn)
        
        layout.addWidget(actions_group)
        
        layout.addStretch()
        
        # Boutons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self._update_stats)
        btn_row.addWidget(refresh_btn)
        
        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("send_btn")
        close_btn.setFixedHeight(36)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        
        layout.addLayout(btn_row)
    
    def _update_stats(self):
        """Met à jour les statistiques affichées."""
        cache = get_url_cache()
        
        # Nombre d'entrées
        count = cache.size()
        self._entries_label.setText(str(count))
        
        # Taille totale
        size_bytes = cache.total_size_bytes()
        size_mb = size_bytes / 1024 / 1024
        
        if size_mb < 1:
            size_kb = size_bytes / 1024
            self._size_label.setText(f"{size_kb:.1f} KB")
        else:
            self._size_label.setText(f"{size_mb:.1f} MB")
        
        # Barre de progression (max 100 MB pour l'affichage)
        progress = min(int(size_mb), 100)
        self._size_bar.setValue(progress)
        
        # Désactiver le bouton vider si vide
        self._clear_btn.setEnabled(count > 0)
    
    def _clean_expired(self):
        """Nettoie les entrées expirées."""
        cache = get_url_cache()
        count = cache.clear_expired()
        
        if count > 0:
            QMessageBox.information(
                self,
                "Nettoyage terminé",
                f"{count} entrée(s) expirée(s) supprimée(s)."
            )
        else:
            QMessageBox.information(
                self,
                "Nettoyage terminé",
                "Aucune entrée expirée trouvée."
            )
        
        self._update_stats()
    
    def _clear_cache(self):
        """Vide complètement le cache."""
        reply = QMessageBox.question(
            self,
            "Confirmation",
            "Êtes-vous sûr de vouloir vider complètement le cache ?\n\n"
            "Toutes les URLs devront être re-téléchargées.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            cache = get_url_cache()
            cache.clear()
            self._update_stats()
            self.cache_cleared.emit()
            
            QMessageBox.information(
                self,
                "Cache vidé",
                "Le cache a été complètement vidé."
            )
