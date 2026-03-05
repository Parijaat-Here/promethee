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
tools/modele_tools.py — [Courte description de la famille d'outils]
====================================================================

Outils exposés (N) :
  - mon_outil_simple    : [ce qu'il fait en une ligne]
  - mon_outil_avance    : [ce qu'il fait en une ligne]

Ce module s'enregistre automatiquement dans tools_engine au premier import.

Usage :
    import tools.modele_tools   # suffit à enregistrer les outils

Prérequis (si besoin) :
    pip install ma-dependance-externe
"""

# ── Imports standard ──────────────────────────────────────────────────────────
# Ajoutez ici vos imports Python stdlib
from typing import Optional

# ── Imports tiers (optionnels) ────────────────────────────────────────────────
# Protégez toujours les imports tiers avec try/except pour que le module
# reste importable même si la dépendance est absente.
try:
    # import ma_lib
    _HAS_MA_LIB = True
except ImportError:
    _HAS_MA_LIB = False

# ── Imports Prométhée ─────────────────────────────────────────────────────────
from core.tools_engine import tool, set_current_family, report_progress, _TOOL_ICONS

# Décommentez si votre outil a besoin de variables de configuration (.env) :
# from core.config import Config


# ══════════════════════════════════════════════════════════════════════════════
#  1. DÉCLARATION DE LA FAMILLE
#     À faire UNE seule fois, AVANT tous les @tool du fichier.
#     family  : identifiant unique snake_case, correspond au nom du fichier
#     label   : nom lisible affiché dans l'interface (onglet Outils)
#     icon    : emoji affiché dans l'interface
# ══════════════════════════════════════════════════════════════════════════════

set_current_family("modele_tools", "Ma Famille d'Outils", "🔧")


# ── Icônes UI (une par outil) ─────────────────────────────────────────────────
# Associe un emoji à chaque nom d'outil pour l'affichage dans l'interface.
_TOOL_ICONS.update({
    "mon_outil_simple":  "⚙️",
    "mon_outil_avance":  "🚀",
})


# ══════════════════════════════════════════════════════════════════════════════
#  2. OUTIL SIMPLE — paramètre requis + paramètre optionnel
# ══════════════════════════════════════════════════════════════════════════════

@tool(
    name="mon_outil_simple",
    description=(
        # La description EST le prompt envoyé au LLM : soyez précis et concret.
        # Indiquez CE QUE fait l'outil, QUAND l'utiliser, et le FORMAT de retour.
        "Décrivez ici ce que fait l'outil, dans quel contexte l'utiliser, "
        "et ce que retourne le résultat. Exemple : 'Retourne la liste des "
        "fichiers d'un répertoire au format JSON.'"
    ),
    parameters={
        "type": "object",
        "properties": {
            # Paramètre requis
            "mon_parametre": {
                "type": "string",           # string | number | integer | boolean | array | object
                "description": "Description claire et exemples concrets. Ex: chemin absolu vers le fichier, ex: '/home/user/doc.txt'.",
            },
            # Paramètre optionnel (absent de "required")
            "option": {
                "type": "string",
                "description": "Paramètre optionnel. Si absent, comportement par défaut.",
            },
        },
        "required": ["mon_parametre"],      # listez uniquement les paramètres obligatoires
    },
)
def mon_outil_simple(mon_parametre: str, option: Optional[str] = None) -> str:
    """
    Implémentation de mon_outil_simple.

    Règles de retour :
    - Retournez toujours une str (le moteur convertit dict/list en JSON automatiquement,
      mais une str explicite est plus claire pour le LLM).
    - En cas d'erreur, retournez un message d'erreur lisible — ne levez pas d'exception
      (call_tool() les capture, mais le message sera moins informatif).
    - Préfixez les erreurs par "Erreur : " pour que le LLM les distingue des succès.
    """
    # ── Validation des entrées ────────────────────────────────────────────────
    if not mon_parametre.strip():
        return "Erreur : mon_parametre ne peut pas être vide."

    # ── Logique métier ────────────────────────────────────────────────────────
    resultat = f"Traitement de '{mon_parametre}'"
    if option:
        resultat += f" avec l'option '{option}'"

    return resultat


# ══════════════════════════════════════════════════════════════════════════════
#  3. OUTIL AVANCÉ — progression, dépendance externe, configuration .env
# ══════════════════════════════════════════════════════════════════════════════

@tool(
    name="mon_outil_avance",
    description=(
        "Outil plus complexe illustrant : vérification de dépendance, "
        "lecture de la configuration .env, et signalement de la progression "
        "dans l'interface (barre de statut)."
    ),
    parameters={
        "type": "object",
        "properties": {
            "entree": {
                "type": "string",
                "description": "Valeur d'entrée à traiter.",
            },
            "nombre_etapes": {
                "type": "integer",
                "description": "Nombre d'étapes de traitement (1–10). Défaut : 3.",
            },
        },
        "required": ["entree"],
    },
)
def mon_outil_avance(entree: str, nombre_etapes: int = 3) -> str:
    # ── Vérification de la dépendance optionnelle ─────────────────────────────
    if not _HAS_MA_LIB:
        return (
            "Erreur : la dépendance 'ma-dependance-externe' est absente. "
            "Installez-la avec : pip install ma-dependance-externe"
        )

    # ── Lecture d'une variable de configuration ───────────────────────────────
    # Décommentez si vous avez activé l'import Config plus haut :
    # api_key = Config.MON_API_KEY
    # if not api_key:
    #     return "Erreur : MON_API_KEY absent du fichier .env."

    # ── Signalement de la progression (visible dans la barre de statut UI) ────
    nombre_etapes = max(1, min(nombre_etapes, 10))  # borne 1–10

    for i in range(1, nombre_etapes + 1):
        report_progress(f"⚙️ Étape {i}/{nombre_etapes} en cours…")
        # ... votre logique ici ...

    return f"Traitement de '{entree}' terminé en {nombre_etapes} étape(s)."


# ══════════════════════════════════════════════════════════════════════════════
#  4. AIDE-MÉMOIRE — types de paramètres JSON Schema
# ══════════════════════════════════════════════════════════════════════════════
#
#  "type": "string"   → str Python
#  "type": "number"   → float Python
#  "type": "integer"  → int Python
#  "type": "boolean"  → bool Python
#
#  Tableau de strings :
#    "type": "array",
#    "items": {"type": "string"}
#
#  Énumération (valeurs imposées) :
#    "type": "string",
#    "enum": ["valeur_a", "valeur_b", "valeur_c"]
#
#  Objet structuré :
#    "type": "object",
#    "properties": {
#        "cle": {"type": "string", "description": "..."}
#    }
#
# ══════════════════════════════════════════════════════════════════════════════
