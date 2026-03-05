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
Core module - Logique métier indépendante de l'UI
"""
from .config import Config
from .database import HistoryDB
from .rag_engine import (
    ensure_collection,
    ingest_text,
    ingest_file,
    search,
    build_rag_context,
    is_available,
)
from .tools_engine import (
    get_tool_schemas,
    call_tool,
    list_tools,
    list_families,
    enable_family,
    disable_family,
    is_family_disabled,
)

__all__ = [
    "Config",
    "HistoryDB",
    "ensure_collection",
    "ingest_text",
    "ingest_file",
    "search",
    "build_rag_context",
    "is_available",
    "get_tool_schemas",
    "call_tool",
    "list_tools",
    "list_families",
    "enable_family",
    "disable_family",
    "is_family_disabled",
]
