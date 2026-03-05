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
file_processor.py — Worker pour traiter les fichiers en arrière-plan
"""
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal, Qt


class FileProcessingWorker(QThread):
    """
    Worker qui traite un fichier (PDF, Office, image OCR) dans un thread
    séparé pour ne pas bloquer l'interface.

    Signaux
    -------
    progress(label, current, total)   – avancement textuel + chiffré
    finished(attachment_type, data)   – résultat prêt à passer à l'AttachmentBar
    error(message)                    – en cas d'échec
    """

    progress = pyqtSignal(str, int, int)  # (label, done, total)
    finished = pyqtSignal(str, dict)  # (att_type, data)
    error = pyqtSignal(str)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self._path = path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    # ── point d'entrée ────────────────────────────────────────────────

    def run(self):
        p = Path(self._path)
        suffix = p.suffix.lower()

        try:
            if suffix in ('.txt', '.md', '.py', '.js', '.json', '.xml',
                          '.yaml', '.csv', '.html', '.css'):
                self._process_text(p)
            elif suffix in ('.docx', '.xlsx', '.pptx'):
                self._process_office(p, suffix)
            elif suffix == '.pdf':
                self._process_pdf(p)
            elif suffix in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'):
                self._process_image(p)
            else:
                self.finished.emit("file", {
                    "name": p.name,
                    "path": str(p),
                    "content": f"[Fichier binaire : {suffix}]",
                    "size": p.stat().st_size,
                })
        except Exception as e:
            self.error.emit(str(e))

    # ── fichiers texte ────────────────────────────────────────────────

    def _process_text(self, p: Path):
        self.progress.emit(f"Lecture de {p.name}…", 0, 1)
        content = p.read_text(encoding='utf-8', errors='replace')
        if len(content) > 100_000:
            content = content[:100_000] + "\n\n... [tronqué]"
        self.finished.emit("file", {
            "name": p.name,
            "path": str(p),
            "content": content,
            "size": p.stat().st_size,
        })

    # ── fichiers Office ───────────────────────────────────────────────

    def _process_office(self, p: Path, suffix: str):
        from ui.widgets.office_extractor import (
            extract_from_docx, extract_from_xlsx, extract_from_pptx,
            extract_office_metadata
        )
        type_map = {'.docx': ('Word', extract_from_docx),
                    '.xlsx': ('Excel', extract_from_xlsx),
                    '.pptx': ('PowerPoint', extract_from_pptx)}
        file_type, extractor = type_map[suffix]

        self.progress.emit(f"Extraction {file_type} : {p.name}…", 0, 2)
        if self._cancelled:
            return
        content, err = extractor(str(p))
        if err:
            self.error.emit(err)
            return

        self.progress.emit("Métadonnées…", 1, 2)
        if self._cancelled:
            return
        try:
            metadata = extract_office_metadata(str(p))
        except Exception:
            metadata = {}

        self.finished.emit("file", {
            "name": p.name,
            "path": str(p),
            "content": content,
            "size": p.stat().st_size,
            "office_type": file_type,
            "metadata": metadata,
        })

    # ── PDF ──────────────────────────────────────────────────────────

    def _process_pdf(self, p: Path):
        from ui.widgets.ocr_engine import (
            is_available as ocr_available,
            extract_text_from_pdf,
            detect_pdf_type,
        )
        try:
            import fitz
        except ImportError:
            self.error.emit("PyMuPDF non installé (pip install pymupdf)")
            return

        doc = fitz.open(str(p))
        n_pages = len(doc)

        # Détection du type
        self.progress.emit(f"Analyse de {p.name}…", 0, n_pages + 2)
        if self._cancelled:
            doc.close()
            return

        pdf_type = detect_pdf_type(str(p)) if ocr_available() else "unknown"

        content = ""
        ocr_used = False

        if pdf_type in ("scanned", "mixed") and ocr_available():
            # OCR page par page avec progression
            max_pages = 10
            pages = min(n_pages, max_pages)
            all_text = []

            try:
                import pytesseract
                from PIL import Image
                import io

                for i in range(pages):
                    if self._cancelled:
                        doc.close()
                        return
                    self.progress.emit(
                        f"OCR page {i+1}/{pages} de {p.name}…",
                        i + 1, pages + 2
                    )
                    page = doc[i]
                    text = page.get_text().strip()
                    if len(text) < 50:
                        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
                        img = Image.open(io.BytesIO(pix.tobytes("png")))
                        text = pytesseract.image_to_string(img, lang="fra+eng",
                                                           config="--oem 3 --psm 3").strip()
                    if text:
                        all_text.append(f"--- Page {i+1} ---\n{text}\n")

                content = f"[OCR utilisé sur {pages} page(s)]\n\n" + "\n".join(all_text)
                ocr_used = True

            except Exception as e:
                # Fallback extraction normale
                content = "\n".join(page.get_text() for page in doc)
        else:
            for i, page in enumerate(doc):
                if self._cancelled:
                    doc.close()
                    return
                self.progress.emit(
                    f"Lecture page {i+1}/{n_pages}…", i + 1, n_pages + 2
                )
                content += page.get_text()

        if len(content) > 100_000:
            content = content[:100_000] + "\n\n... [tronqué]"

        # Thumbnail de la première page
        self.progress.emit("Génération de l'aperçu…", n_pages + 1, n_pages + 2)
        preview_b64 = None
        try:
            from PyQt6.QtGui import QImage
            from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(150/72, 150/72))
            qimg = QImage()
            qimg.loadFromData(pix.tobytes("png"))
            if qimg.width() > 200 or qimg.height() > 200:
                qimg = qimg.scaled(200, 200,
                                   Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            buf = QBuffer()
            buf.open(QIODevice.OpenModeFlag.WriteOnly)
            qimg.save(buf, "PNG")
            preview_b64 = buf.data().toBase64().data().decode()
        except Exception:
            pass

        doc.close()

        self.finished.emit("file", {
            "name": p.name,
            "path": str(p),
            "content": content,
            "size": p.stat().st_size,
            "preview": preview_b64,
            "pages": n_pages,
            "pdf_type": pdf_type,
            "ocr_used": ocr_used,
        })

    # ── image (OCR optionnel) ─────────────────────────────────────────

    def _process_image(self, p: Path):
        from ui.widgets.ocr_engine import (
            is_available as ocr_available,
            extract_text_from_image,
        )
        from PyQt6.QtGui import QImage
        from PyQt6.QtCore import QBuffer, QIODevice

        self.progress.emit(f"Chargement de {p.name}…", 0, 3)
        if self._cancelled:
            return

        image = QImage(str(p))
        if image.isNull():
            self.error.emit(f"Impossible de charger l'image : {p.name}")
            return

        max_size = 1024
        if image.width() > max_size or image.height() > max_size:
            image = image.scaled(max_size, max_size,
                                 Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)

        from PyQt6.QtCore import QByteArray
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buf, "PNG")
        img_b64 = buf.data().toBase64().data().decode()

        ocr_text = None
        if ocr_available():
            self.progress.emit(f"OCR sur {p.name}…", 1, 3)
            if not self._cancelled:
                text, _ = extract_text_from_image(str(p))
                ocr_text = text

        self.finished.emit("image", {
            "name": p.name,
            "path": str(p),
            "base64": img_b64,
            "size": p.stat().st_size,
            "mime_type": "image/png",
            "width": image.width(),
            "height": image.height(),
            "ocr_text": ocr_text,
            "has_ocr": ocr_text is not None,
        })
