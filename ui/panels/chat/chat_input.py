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
chat_input.py — Widget d'entrée de texte avec support drag & drop et historique
"""
from PyQt6.QtWidgets import QTextEdit, QCompleter
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel
from PyQt6.QtGui import QKeyEvent, QTextCursor


class KeyCatchTextEdit(QTextEdit):
    """
    TextEdit qui capture Enter pour envoyer et supporte le drag & drop.
    
    Fonctionnalités :
    - Entrée : envoyer le message
    - Shift+Entrée : nouvelle ligne
    - Flèche Haut/Bas : naviguer dans l'historique des prompts
    - Tab : autocomplétion des prompts précédents
    - Drag & drop de fichiers
    
    Signals
    -------
    send_requested : émis quand l'utilisateur appuie sur Entrée (sans Shift)
    files_dropped : émis avec une liste de chemins de fichiers lors d'un drop
    """
    
    send_requested = pyqtSignal()
    files_dropped = pyqtSignal(list)  # Liste de chemins de fichiers

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        
        # Historique des prompts
        self._history = []  # Liste des prompts envoyés
        self._history_index = -1  # Position actuelle dans l'historique (-1 = pas de navigation)
        self._current_text = ""  # Texte en cours de saisie avant navigation
        self._max_history = 100  # Nombre max d'entrées dans l'historique
        
        # Autocomplétion
        self._completer = None
        self._setup_completer()

    def _setup_completer(self):
        """Configure l'autocomplétion."""
        self._completer = QCompleter(self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        # Modèle vide au départ
        self._completer_model = QStringListModel([], self)
        self._completer.setModel(self._completer_model)
        
        # Connecter l'activation de la complétion
        self._completer.activated.connect(self._insert_completion)

    def _insert_completion(self, completion: str):
        """Insère la complétion sélectionnée."""
        self.setPlainText(completion)
        # Placer le curseur à la fin
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

    def _update_completer_model(self):
        """Met à jour le modèle de l'autocomplétion avec l'historique."""
        if self._completer_model:
            # Inverser pour avoir les plus récents en premier
            self._completer_model.setStringList(list(reversed(self._history)))

    def add_to_history(self, text: str):
        """
        Ajoute un prompt à l'historique.
        
        Parameters
        ----------
        text : str
            Le texte du prompt à ajouter
        """
        text = text.strip()
        if not text:
            return
        
        # Éviter les doublons consécutifs
        if self._history and self._history[-1] == text:
            return
        
        # Ajouter à l'historique
        self._history.append(text)
        
        # Limiter la taille de l'historique
        if len(self._history) > self._max_history:
            self._history.pop(0)
        
        # Réinitialiser la navigation
        self._history_index = -1
        self._current_text = ""
        
        # Mettre à jour l'autocomplétion
        self._update_completer_model()

    def _navigate_history(self, direction: int):
        """
        Navigate dans l'historique.
        
        Parameters
        ----------
        direction : int
            -1 pour remonter (flèche haut), +1 pour descendre (flèche bas)
        """
        if not self._history:
            return
        
        # Si on commence la navigation, sauvegarder le texte actuel
        if self._history_index == -1:
            self._current_text = self.toPlainText()
        
        # Calculer le nouvel index
        new_index = self._history_index + direction
        
        # Limiter aux bornes
        if new_index < -1:
            new_index = -1
        elif new_index >= len(self._history):
            new_index = len(self._history) - 1
        
        self._history_index = new_index
        
        # Afficher le texte correspondant
        if self._history_index == -1:
            # Revenir au texte en cours de saisie
            self.setPlainText(self._current_text)
        else:
            # Afficher l'entrée de l'historique
            self.setPlainText(self._history[self._history_index])
        
        # Placer le curseur à la fin
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)

    def _show_completions(self):
        """Affiche les suggestions d'autocomplétion."""
        if not self._history:
            return
        
        current_text = self.toPlainText().strip()
        
        if not current_text:
            # Pas de texte : montrer tout l'historique
            self._completer.setCompletionPrefix("")
        else:
            # Filtrer par le début du texte
            self._completer.setCompletionPrefix(current_text)
        
        # Afficher le popup si on a des suggestions
        if self._completer.completionCount() > 0:
            rect = self.cursorRect()
            rect.setWidth(self._completer.popup().sizeHintForColumn(0)
                         + self._completer.popup().verticalScrollBar().sizeHint().width())
            self._completer.complete(rect)

    def keyPressEvent(self, event: QKeyEvent):
        """Capture les touches spéciales."""
        # Si le popup d'autocomplétion est visible, le laisser gérer certaines touches
        if self._completer and self._completer.popup().isVisible():
            if event.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return, 
                              Qt.Key.Key_Escape, Qt.Key.Key_Tab):
                event.ignore()
                return
        
        # Entrée : envoyer le message
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) \
                and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.send_requested.emit()
            return
        
        # Flèche Haut : remonter dans l'historique
        elif event.key() == Qt.Key.Key_Up and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            # Seulement si le curseur est sur la première ligne
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
            if cursor.atStart() or self.toPlainText().count('\n') == 0:
                self._navigate_history(-1)
                return
        
        # Flèche Bas : descendre dans l'historique
        elif event.key() == Qt.Key.Key_Down and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            # Seulement si le curseur est sur la dernière ligne
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            if cursor.atEnd() or self.toPlainText().count('\n') == 0:
                self._navigate_history(+1)
                return
        
        # Tab : autocomplétion
        elif event.key() == Qt.Key.Key_Tab:
            self._show_completions()
            return
        
        # Toute autre touche : réinitialiser la navigation dans l'historique
        elif event.key() not in (Qt.Key.Key_Shift, Qt.Key.Key_Control, 
                                 Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            self._history_index = -1
        
        # Traitement par défaut
        super().keyPressEvent(event)

    def clear(self):
        """Efface le texte et réinitialise la navigation."""
        super().clear()
        self._history_index = -1
        self._current_text = ""

    # ── Drag & Drop (inchangé) ───────────────────────────────────────────

    def dragEnterEvent(self, event):
        """Accepte les fichiers glissés."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Permet le mouvement pendant le drag."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Traite les fichiers déposés."""
        if event.mimeData().hasUrls():
            file_paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    file_paths.append(url.toLocalFile())

            if file_paths:
                self.files_dropped.emit(file_paths)
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
