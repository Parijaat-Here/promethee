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
attachment_handler.py — Gestionnaire des attachements (fichiers, images, URLs)
"""
from pathlib import Path
from datetime import datetime
from typing import Callable
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QProgressDialog

from ui.widgets.attachment_widget import AttachmentBar, LoadingItem
from ui.widgets.url_cache import get_url_cache
from ui.widgets.ocr_engine import is_available as ocr_available
from ui.widgets.office_extractor import is_available as office_available
from ui.widgets.url_extractor import (
    is_available as url_extractor_available,
    extract_article_content,
    get_content_summary
)


class URLFetcher(QThread):
    """Worker pour récupérer le contenu d'une URL."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        """Récupère le contenu de l'URL."""
        if not url_extractor_available():
            self.error.emit("Module d'extraction d'URL non disponible")
            return

        if self._cancelled:
            return

        self.progress.emit(f"Connexion à {self.url[:50]}…")

        try:
            # Extraire le contenu
            content, error = extract_article_content(self.url)
            if error:
                self.error.emit(error)
                return

            if self._cancelled:
                return

            # Obtenir un résumé/titre
            summary = get_content_summary(content)

            self.finished.emit({
                "url": self.url,
                "name": summary.get("title", self.url[:50]),
                "content": content,
                "size": len(content)
            })

        except Exception as e:
            self.error.emit(str(e))


class AttachmentHandler:
    """
    Gère l'ajout et le traitement des attachements.

    Parameters
    ----------
    attachment_bar : AttachmentBar
        Barre d'attachements de l'UI
    status_callback : Callable
        Callback pour afficher un message de statut
    parent : QWidget
        Widget parent
    """

    def __init__(self, attachment_bar: AttachmentBar, status_callback: Callable, parent=None):
        self.attachment_bar = attachment_bar
        self.status_callback = status_callback
        self.parent = parent
        self._file_workers = []
        self._url_fetchers = {}

    # ── Fichiers & Images ─────────────────────────────────────────────────

    def handle_file(self, path: str):
        """Traite un fichier attaché (tout type hors image directe)."""
        self._validate_and_start(path, is_image=False)

    def handle_image(self, path: str):
        """Traite une image attachée."""
        self._validate_and_start(path, is_image=True)

    def _validate_and_start(self, path: str, is_image: bool):
        """
        Vérifie l'existence du fichier et les dépendances requises,
        puis lance le worker de traitement.

        Parameters
        ----------
        path : str
            Chemin du fichier à traiter.
        is_image : bool
            True pour une image (ignore les vérifications Office/PDF).
        """
        p = Path(path)
        kind = "Image" if is_image else "Fichier"
        if not p.exists():
            self.status_callback(f"{kind} introuvable : {path}")
            return

        if not is_image:
            suffix = p.suffix.lower()
            if suffix in ('.docx', '.xlsx', '.pptx'):
                if not office_available():
                    self.status_callback(
                        "[!] Librairies Office non installées "
                        "(pip install python-docx openpyxl python-pptx)"
                    )
                    return
            if suffix == '.pdf':
                try:
                    import fitz  # noqa: F401
                except ImportError:
                    self.status_callback("PyMuPDF non installé (pip install pymupdf)")
                    return

        self._start_file_worker(path)

    def _start_file_worker(self, path: str):
        """Lance le worker de traitement de fichier avec indicateur de progression."""
        from ui.panels.chat.file_processor import FileProcessingWorker

        p = Path(path)
        suffix = p.suffix.lower()

        # Fichiers texte simples : pas besoin de dialog
        fast_suffixes = {'.txt', '.md', '.py', '.js', '.json', '.xml',
                         '.yaml', '.csv', '.html', '.css'}
        heavy = suffix not in fast_suffixes

        # Créer et lancer le worker
        worker = FileProcessingWorker(path, parent=self.parent)

        # Progress dialog pour les traitements lourds
        progress_dlg = None
        if heavy:
            progress_dlg = QProgressDialog(
                f"Traitement de {p.name}…", "Annuler", 0, 0, self.parent
            )
            progress_dlg.setWindowTitle("Chargement du fichier")
            progress_dlg.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dlg.setMinimumDuration(400)
            progress_dlg.setAutoClose(True)
            progress_dlg.setAutoReset(False)
            progress_dlg.setMinimumWidth(360)
            progress_dlg.canceled.connect(worker.cancel)

            def _on_progress(label: str, done: int, total: int):
                if progress_dlg.wasCanceled():
                    return
                progress_dlg.setLabelText(label)
                if total > 0:
                    progress_dlg.setMaximum(total)
                    progress_dlg.setValue(done)
                else:
                    progress_dlg.setMaximum(0)

            worker.progress.connect(_on_progress)

        def _on_done(att_type: str, data: dict):
            if progress_dlg:
                progress_dlg.close()
            self.attachment_bar.add_attachment(att_type, data)
            self.status_callback(self._format_status_message(att_type, data))

        def _on_error(msg: str):
            if progress_dlg:
                progress_dlg.close()
            self.status_callback(f"[!] {msg}")

        worker.finished.connect(_on_done)
        worker.error.connect(_on_error)

        # Garder une référence
        self._file_workers.append(worker)
        worker.finished.connect(lambda *_: self._cleanup_worker(worker))
        worker.error.connect(lambda *_: self._cleanup_worker(worker))
        worker.start()

        if not heavy:
            self.status_callback(f"Lecture de {p.name}…")

    def _cleanup_worker(self, worker):
        """Nettoie un worker terminé."""
        if worker in self._file_workers:
            self._file_workers.remove(worker)

    def _format_status_message(self, att_type: str, data: dict) -> str:
        """Formate un message de statut enrichi."""
        name = data.get("name", "")

        if att_type == "image":
            msg = f"Image attachée : {name}"
            if data.get("has_ocr"):
                word_count = len((data.get('ocr_text') or '').split())
                msg += f" (OCR : {word_count} mots)"
            return msg

        if data.get("office_type"):
            msg = f"{data['office_type']} attaché : {name}"
            m = data.get("metadata", {})
            if m.get("paragraphs"):
                msg += f" ({m['paragraphs']} paragraphes)"
            elif m.get("sheets"):
                msg += f" ({m['sheets']} feuilles)"
            elif m.get("slides"):
                msg += f" ({m['slides']} slides)"
            return msg

        if data.get("pages"):
            msg = f"PDF attaché : {name} ({data['pages']} pages"
            if data.get("ocr_used"):
                msg += ", OCR"
            elif data.get("pdf_type") == "text":
                msg += ", texte natif"
            msg += ")"
            return msg

        return f"Fichier attaché : {name}"

    # ── URLs ──────────────────────────────────────────────────────────────

    def handle_url(self, url: str):
        """
        Traite une URL attachée.

        Parameters
        ----------
        url : str
            URL à récupérer
        """
        # Vérifier le cache
        cache = get_url_cache()
        cached = cache.get(url)

        if cached:
            self.attachment_bar.add_attachment("url", {
                "url": cached["url"],
                "name": cached["title"],
                "content": cached["content"],
                "size": cached["size"]
            })
            cache_age = (datetime.now() - cached["cached_at"]).total_seconds() / 60
            self.status_callback(f"[ok] URL chargée depuis le cache ({cache_age:.0f}min)")
            return

        # Créer l'indicateur de chargement
        loading_item = LoadingItem(url)
        loading_item.cancel_requested.connect(lambda: self._cancel_url_fetch(url, loading_item))

        # Ajouter à la barre via l'API publique
        self.attachment_bar.add_loading_item(loading_item)

        # Fetcher dans un thread
        fetcher = URLFetcher(url)
        self._url_fetchers[url] = (fetcher, loading_item)

        def _on_finished(data: dict):
            self._remove_loading_item(url, loading_item)
            self.attachment_bar.add_attachment("url", data)
            # Mettre en cache
            cache.set(data["url"], data["name"], data["content"])
            self.status_callback(f"[ok] URL chargée : {data['name']}")

        def _on_error(msg: str):
            self._remove_loading_item(url, loading_item)
            self.status_callback(f"[!] Erreur URL : {msg}")

        fetcher.finished.connect(_on_finished)
        fetcher.error.connect(_on_error)
        fetcher.start()

        self.status_callback(f"Chargement de l'URL : {url[:50]}…")

    def _cancel_url_fetch(self, url: str, loading_item):
        """Annule la récupération d'une URL."""
        if url in self._url_fetchers:
            fetcher, _ = self._url_fetchers[url]
            fetcher.cancel()
            fetcher.wait(1000)
        self._remove_loading_item(url, loading_item)
        self.status_callback("Chargement annulé")

    def _remove_loading_item(self, url: str, loading_item):
        """Retire l'indicateur de chargement."""
        self.attachment_bar.remove_loading_item(loading_item)
        if url in self._url_fetchers:
            del self._url_fetchers[url]

    # ── Drag & Drop ───────────────────────────────────────────────────────

    def handle_files_dropped(self, file_paths: list):
        """
        Traite des fichiers glissés-déposés.

        Parameters
        ----------
        file_paths : list
            Liste de chemins de fichiers
        """
        for path in file_paths:
            p = Path(path)

            # Déterminer le type
            if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'):
                self.handle_image(path)
            else:
                self.handle_file(path)

    # ── Nettoyage ─────────────────────────────────────────────────────────

    def cleanup(self):
        """Nettoie tous les workers en cours."""
        for worker in self._file_workers:
            worker.cancel()
            worker.wait(1000)
        self._file_workers.clear()

        for fetcher, _ in self._url_fetchers.values():
            fetcher.cancel()
            fetcher.wait(1000)
        self._url_fetchers.clear()
