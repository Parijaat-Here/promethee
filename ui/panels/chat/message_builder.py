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
message_builder.py — Construction de messages avec attachements pour l'API
"""
from typing import List, Dict, Tuple, Any


class MessageBuilder:
    """Construit des messages formatés pour l'API avec support des attachements."""

    @staticmethod
    def build_display_text(text: str, attachments: List[Dict]) -> str:
        """
        Crée une version texte du message pour affichage/sauvegarde en DB.

        Parameters
        ----------
        text : str
            Texte brut du message
        attachments : List[Dict]
            Liste des attachements

        Returns
        -------
        str
            Texte enrichi avec résumé des attachements
        """
        display_text = text
        if attachments:
            att_summary = ", ".join([
                f"[F] {a['data']['name']}" if a['type'] == 'file'
                else f"[IMG] {a['data']['name']}" if a['type'] == 'image'
                else f"🔗 {a['data']['url'][:30]}..."
                for a in attachments
            ])
            display_text += f"\n\n_Attachements : {att_summary}_"
        return display_text

    @staticmethod
    def build_multipart_content(text: str, attachments: List[Dict]) -> List[Dict[str, Any]]:
        """
        Construit un message multi-part pour l'API avec texte et attachements.

        Parameters
        ----------
        text : str
            Texte du message
        attachments : List[Dict]
            Liste des attachements avec leur type et data

        Returns
        -------
        List[Dict]
            Liste de parts (text, image_url, etc.) pour l'API
        """
        content_parts = []

        # Ajouter le texte
        if text.strip():
            content_parts.append({"type": "text", "text": text})

        # Ajouter les attachements
        for att in attachments:
            if att["type"] == "image":
                MessageBuilder._add_image_part(content_parts, att)
            elif att["type"] == "file":
                MessageBuilder._add_file_part(content_parts, att)
            elif att["type"] == "url":
                MessageBuilder._add_url_part(content_parts, att)

        return content_parts

    @staticmethod
    def _add_image_part(content_parts: List[Dict], att: Dict):
        """Ajoute une image au format API vision."""
        # Image en base64 - format API vision
        content_parts.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{att['data']['mime_type']};base64,{att['data']['base64']}"
            }
        })

        # Ajouter le texte OCR si disponible
        if att['data'].get('has_ocr') and att['data'].get('ocr_text'):
            ocr_text = f"\n\n--- Texte extrait de l'image '{att['data']['name']}' (OCR) ---\n"
            ocr_text += att['data']['ocr_text']
            ocr_text += f"\n--- Fin du texte OCR ---\n"
            content_parts.append({"type": "text", "text": ocr_text})

    @staticmethod
    def _add_file_part(content_parts: List[Dict], att: Dict):
        """Ajoute un fichier texte ou référence un fichier binaire par son chemin."""
        data = att['data']
        name = data['name']
        file_content = data.get('content', '')
        file_path = data.get('path', '')

        # Fichier binaire (audio, vidéo, archive…) : pas de contenu textuel exploitable
        # On injecte uniquement le chemin absolu pour que l'agent puisse le passer aux outils
        if file_content.startswith('[Fichier binaire'):
            ref_text = (
                f"\n\n--- Fichier joint : '{name}' ---\n"
                f"Chemin absolu : {file_path}\n"
                f"Ce fichier est disponible localement. Utilise son chemin absolu "
                f"pour le traiter avec l'outil approprié.\n"
                f"--- Fin ---\n"
            )
            content_parts.append({"type": "text", "text": ref_text})
        else:
            file_text = f"\n\n--- Contenu du fichier '{name}' ---\n"
            file_text += file_content
            file_text += f"\n--- Fin du fichier '{name}' ---\n"
            content_parts.append({"type": "text", "text": file_text})

    @staticmethod
    def _add_url_part(content_parts: List[Dict], att: Dict):
        """Ajoute le contenu d'une URL."""
        if 'content' in att['data'] and att['data']['content']:
            url_text = f"\n\n--- Contenu de l'URL '{att['data']['url']}' ---\n"
            url_text += att['data']['content']
            url_text += f"\n--- Fin du contenu de l'URL ---\n"
            content_parts.append({"type": "text", "text": url_text})
        else:
            # Fallback si pas de contenu
            url_text = f"\n\nAnalyse cette URL : {att['data']['url']}\n"
            content_parts.append({"type": "text", "text": url_text})

    @staticmethod
    def has_images(attachments: List[Dict]) -> bool:
        """Vérifie si la liste contient des images."""
        return any(att["type"] == "image" for att in attachments)

    @staticmethod
    def apply_multipart_to_history(history: List[Dict], content_parts: List[Dict]):
        """
        Applique le contenu multi-part au dernier message utilisateur de l'historique.

        Parameters
        ----------
        history : List[Dict]
            Historique des messages
        content_parts : List[Dict]
            Parts multi-part à appliquer
        """
        if history and history[-1]["role"] == "user":
            history[-1]["content"] = content_parts
