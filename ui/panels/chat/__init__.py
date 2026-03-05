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
chat — Module de gestion du panneau de chat
"""
from .chat_panel import ChatPanel
from .file_processor import FileProcessingWorker
from .message_builder import MessageBuilder
from .streaming_handler import StreamingHandler
from .chat_input import KeyCatchTextEdit
from .attachment_handler import AttachmentHandler, URLFetcher

__all__ = [
    'ChatPanel',
    'FileProcessingWorker',
    'MessageBuilder',
    'StreamingHandler',
    'KeyCatchTextEdit',
    'AttachmentHandler',
    'URLFetcher',
]
