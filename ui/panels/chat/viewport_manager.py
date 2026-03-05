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
viewport_manager.py — Virtualisation des MessageWidget dans un QScrollArea
"""
from PyQt6.QtCore import QTimer


class ViewportManager:
    """
    Gère la virtualisation des MessageWidget dans un QScrollArea.

    Principe
    ────────
    Seuls les widgets dans la zone visible + un buffer vertical sont maintenus
    ATTACHÉS (renderer WebEngine actif). Les widgets hors de cette zone sont
    DÉTACHÉS (renderer suspendu via LifecycleState.Discarded).

    Avec une fenêtre de 800px, des messages de ~150px et un buffer de 1×
    la hauteur du viewport, environ 16 WebViews sont actifs simultanément
    quel que soit le nombre total de messages.

    Intégration
    ───────────
    ViewportManager s'abonne au signal valueChanged de la scrollbar verticale
    et planifie une passe de synchronisation via un QTimer debounce (200ms).
    Cela évite de déclencher des attach/detach à chaque pixel de scroll.

    La passe est également déclenchée manuellement après l'ajout d'un widget
    (add_widget) pour s'assurer que les nouveaux messages sont correctement
    attachés s'ils sont dans la zone visible.

    Parameters
    ----------
    scroll_area : QScrollArea
        La zone de scroll contenant les messages.
    msgs_layout : QVBoxLayout
        Le layout vertical dans lequel les MessageWidget sont insérés.
    buffer_factor : float
        Multiplicateur de la hauteur du viewport pour définir le buffer.
        1.0 = buffer de 1× la hauteur du viewport au-dessus et en-dessous.
        Défaut : 1.0 (bon compromis mémoire/fluidité).
    """

    def __init__(self, scroll_area, msgs_layout, buffer_factor: float = 1.0):
        self._scroll      = scroll_area
        self._layout      = msgs_layout
        self._buffer      = buffer_factor

        # Timer debounce : regroupe les événements scroll rapprochés
        self._sync_timer  = QTimer()
        self._sync_timer.setSingleShot(True)
        self._sync_timer.setInterval(200)  # ms
        self._sync_timer.timeout.connect(self._sync)

        # Abonnement au scroll
        self._scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)

    # ── API publique ──────────────────────────────────────────────────

    def add_widget(self, widget):
        """
        Notifie le manager qu'un nouveau widget vient d'être ajouté.

        Déclenche une passe de synchronisation immédiate (sans debounce)
        car le widget est probablement dans la zone visible — notamment
        lors du streaming où les messages arrivent en bas de la liste.

        Parameters
        ----------
        widget : QWidget
            Le widget nouvellement inséré dans le layout.
        """
        # Passe immédiate (pas de debounce) : le nouveau message est
        # très probablement dans la zone visible (bas de la liste).
        QTimer.singleShot(0, self._sync)

    def sync_now(self):
        """Force une passe de synchronisation immédiate (sans debounce)."""
        self._sync_timer.stop()
        self._sync()

    def cleanup(self):
        """Arrête le timer debounce et détache tous les widgets."""
        self._sync_timer.stop()
        self._scroll.verticalScrollBar().valueChanged.disconnect(self._on_scroll)
        # Réattacher tous les widgets avant destruction (évite les fuites)
        for w in self._iter_message_widgets():
            if not w.is_attached:
                w.attach()

    # ── Scroll handler ────────────────────────────────────────────────

    def _on_scroll(self, _value: int):
        """Réponse au scroll : démarre/redémarre le debounce timer."""
        self._sync_timer.start()   # restart si déjà actif

    # ── Passe de synchronisation ──────────────────────────────────────

    def _sync(self):
        """
        Parcourt tous les MessageWidget et ajuste leur état attaché/détaché.

        Calcul de la zone active
        ────────────────────────
        viewport_top    = position actuelle de la scrollbar
        viewport_bottom = viewport_top + hauteur visible
        buffer          = viewport_height × buffer_factor

        zone_active = [viewport_top - buffer, viewport_bottom + buffer]

        Un widget dont le rectangle intersecte zone_active est attaché ;
        les autres sont détachés.

        Note sur les coordonnées
        ─────────────────────────
        Les positions sont calculées relativement au widget conteneur
        (_msgs_container) via mapTo, ce qui est cohérent avec la valeur
        retournée par verticalScrollBar().value().
        """
        sb              = self._scroll.verticalScrollBar()
        viewport_top    = sb.value()
        viewport_height = self._scroll.viewport().height()
        viewport_bottom = viewport_top + viewport_height
        buffer          = int(viewport_height * self._buffer)

        zone_top    = viewport_top    - buffer
        zone_bottom = viewport_bottom + buffer

        container = self._scroll.widget()  # _msgs_container

        for w in self._iter_message_widgets():
            # Position du widget dans le repère du conteneur de scroll
            pos_in_container = w.mapTo(container, w.rect().topLeft())
            w_top    = pos_in_container.y()
            w_bottom = w_top + w.height()

            in_zone = w_bottom > zone_top and w_top < zone_bottom

            if in_zone and not w.is_attached:
                w.attach()
            elif not in_zone and w.is_attached:
                w.detach()

    # ── Itérateur interne ─────────────────────────────────────────────

    def _iter_message_widgets(self):
        """
        Itère sur les MessageWidget présents dans le layout.

        Yields
        ------
        MessageWidget
            Chaque widget de message trouvé dans le layout.
        """
        from ui.widgets.message_widget import MessageWidget
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            if item:
                w = item.widget()
                if isinstance(w, MessageWidget):
                    yield w
