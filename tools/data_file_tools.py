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
tools/data_file_tools.py — Outils CSV / Excel avancés
=======================================================

Outils exposés (10) :

  Lecture (2) :
    - df_read           : charge un CSV ou Excel en mémoire sous un nom de dataset
    - df_list           : liste les datasets chargés en session (noms, dimensions, colonnes)

  Exploration (3) :
    - df_head           : affiche les premières/dernières lignes d'un dataset
    - df_info           : statistiques descriptives et infos sur les colonnes
    - df_value_counts   : fréquence des valeurs d'une colonne

  Transformation (3) :
    - df_query          : filtre / sélectionne / trie avec une expression pandas
    - df_pivot          : tableau croisé dynamique (pivot table)
    - df_merge          : fusionne deux datasets (JOIN)

  Écriture (2) :
    - df_write          : exporte un dataset en CSV ou Excel
    - df_drop           : supprime un dataset de la mémoire session

Stratégie :
  - Les datasets sont nommés et conservés en session (dict global)
  - Tout passe par pandas ; les feuilles Excel multiples sont supportées
  - Les résultats volumineux sont tronqués avec indicateur
  - Les valeurs non JSON-sérialisables (NaT, NaN, Decimal…) sont normalisées

Prérequis :
    pip install pandas openpyxl
"""

import json
import math
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

import pandas as pd
import numpy as np

from core.tools_engine import tool, set_current_family, _TOOL_ICONS

set_current_family("data_file_tools", "Fichiers de données", "📊")

# ── Icônes ────────────────────────────────────────────────────────────────────
_TOOL_ICONS.update({
    "df_read":         "📂",
    "df_list":         "📋",
    "df_head":         "👁️",
    "df_info":         "📊",
    "df_value_counts": "🔢",
    "df_query":        "🔍",
    "df_pivot":        "🔄",
    "df_merge":        "🔗",
    "df_write":        "💾",
    "df_drop":         "🗑️",
})

# ── Registre de datasets (session) ────────────────────────────────────────────
# { nom: { "df": DataFrame, "source": str, "loaded_at": str } }
_DATASETS: dict[str, dict] = {}

_MAX_ROWS_DISPLAY = 100     # lignes max dans les retours JSON
_MAX_COLS_DISPLAY = 50      # colonnes max dans les retours JSON


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _safe(val: Any) -> Any:
    """Normalise les valeurs non JSON-sérialisables."""
    if val is None:
        return None
    if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
        return None
    if isinstance(val, (pd.Timestamp, datetime)):
        return val.isoformat()
    if isinstance(val, pd.NaT.__class__):
        return None
    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, np.floating):
        v = float(val)
        return None if math.isnan(v) or math.isinf(v) else v
    if isinstance(val, np.bool_):
        return bool(val)
    if isinstance(val, np.ndarray):
        return val.tolist()
    if isinstance(val, bytes):
        return f"<bytes {len(val)}>"
    return val


def _df_to_records(df: pd.DataFrame, max_rows: int = _MAX_ROWS_DISPLAY) -> tuple[list, bool]:
    """Convertit un DataFrame en liste de dicts JSON-safe. Retourne (records, tronqué)."""
    truncated = len(df) > max_rows
    subset = df.head(max_rows)
    records = []
    for row in subset.itertuples(index=False):
        records.append({
            col: _safe(val)
            for col, val in zip(subset.columns, row)
        })
    return records, truncated


def _get_df(nom: str) -> pd.DataFrame:
    """Retourne le DataFrame nommé ou lève une erreur explicite."""
    if nom not in _DATASETS:
        noms = list(_DATASETS.keys())
        hint = f" Datasets disponibles : {noms}." if noms else " Aucun dataset chargé."
        raise KeyError(
            f"Dataset '{nom}' introuvable.{hint} "
            "Utilisez df_read pour charger un fichier."
        )
    return _DATASETS[nom]["df"]


def _detect_encoding(path: Path) -> str:
    """Détecte l'encodage d'un fichier CSV (UTF-8 BOM, latin-1, etc.)."""
    try:
        with open(path, "rb") as f:
            raw = f.read(4096)
        if raw.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig"
        # Tentative UTF-8
        raw.decode("utf-8")
        return "utf-8"
    except Exception:
        return "latin-1"


def _infer_separator(path: Path, encoding: str) -> str:
    """Détecte le séparateur CSV (virgule, point-virgule, tabulation)."""
    try:
        with open(path, encoding=encoding, errors="replace") as f:
            first_line = f.readline()
        counts = {sep: first_line.count(sep) for sep in (",", ";", "\t", "|")}
        return max(counts, key=counts.get)
    except Exception:
        return ","


# ══════════════════════════════════════════════════════════════════════════════
# OUTILS
# ══════════════════════════════════════════════════════════════════════════════

@tool(
    name="df_read",
    description=(
        "Charge un fichier CSV ou Excel (.xlsx, .xls, .ods) en mémoire sous un nom court. "
        "Détecte automatiquement l'encodage et le séparateur des fichiers CSV. "
        "Pour les Excel multi-feuilles, utiliser le paramètre 'feuille'. "
        "Le dataset reste disponible pour toute la session sous le nom donné."
    ),
    parameters={
        "type": "object",
        "properties": {
            "chemin": {
                "type": "string",
                "description": "Chemin absolu ou relatif du fichier CSV ou Excel.",
            },
            "nom": {
                "type": "string",
                "description": (
                    "Nom court pour référencer ce dataset (ex: 'ventes', 'clients'). "
                    "Défaut : nom du fichier sans extension."
                ),
            },
            "feuille": {
                "type": "string",
                "description": "Nom ou index (0-basé) de la feuille Excel (défaut : première feuille).",
            },
            "separateur": {
                "type": "string",
                "description": "Séparateur CSV (défaut : détection automatique parmi , ; \\t |).",
            },
            "encodage": {
                "type": "string",
                "description": "Encodage du fichier CSV (défaut : détection automatique).",
            },
            "lignes_header": {
                "type": "integer",
                "description": "Numéro de la ligne d'en-têtes (0-basé, défaut: 0).",
            },
            "ignorer_lignes": {
                "type": "integer",
                "description": "Nombre de lignes à sauter en début de fichier (défaut: 0).",
            },
        },
        "required": ["chemin"],
    },
)
def df_read(
    chemin: str,
    nom: Optional[str] = None,
    feuille: Optional[str] = None,
    separateur: Optional[str] = None,
    encodage: Optional[str] = None,
    lignes_header: int = 0,
    ignorer_lignes: int = 0,
) -> dict:
    path = Path(chemin).expanduser()
    if not path.exists():
        return {"status": "error", "error": f"Fichier introuvable : {chemin}"}

    dataset_name = nom or path.stem
    ext = path.suffix.lower()

    try:
        t0 = time.perf_counter()

        if ext in (".xlsx", ".xls", ".ods", ".xlsm"):
            # ── Excel ──
            xl = pd.ExcelFile(path, engine="openpyxl" if ext != ".xls" else "xlrd")
            sheet_names = xl.sheet_names

            sheet = feuille
            if sheet is None:
                sheet = sheet_names[0]
            elif isinstance(sheet, str) and sheet.isdigit():
                sheet = sheet_names[int(sheet)]

            df = pd.read_excel(
                xl, sheet_name=sheet,
                header=lignes_header,
                skiprows=ignorer_lignes if ignorer_lignes > 0 else None,
            )
            source_info = f"{path.name} / feuille '{sheet}'"
            extra = {"feuilles_disponibles": sheet_names, "feuille_chargee": sheet}

        elif ext in (".csv", ".tsv", ".txt"):
            # ── CSV ──
            enc = encodage or _detect_encoding(path)
            sep = separateur or _infer_separator(path, enc)

            df = pd.read_csv(
                path,
                sep=sep,
                encoding=enc,
                header=lignes_header,
                skiprows=range(1, ignorer_lignes + 1) if ignorer_lignes > 0 else None,
                low_memory=False,
                na_values=["", "NA", "N/A", "NULL", "null", "None", "#N/A"],
            )
            source_info = path.name
            extra = {"separateur_detecte": sep, "encodage_detecte": enc}

        else:
            return {
                "status": "error",
                "error": f"Format non supporté : '{ext}'. Formats acceptés : .csv, .tsv, .xlsx, .xls, .ods",
            }

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

        # Nettoyer les noms de colonnes
        df.columns = [str(c).strip() for c in df.columns]

        # Stocker
        _DATASETS[dataset_name] = {
            "df":        df,
            "source":    source_info,
            "loaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Aperçu des types
        types = {col: str(dtype) for col, dtype in df.dtypes.items()}

        return {
            "status":       "success",
            "nom":          dataset_name,
            "source":       source_info,
            "nb_lignes":    len(df),
            "nb_colonnes":  len(df.columns),
            "colonnes":     list(df.columns),
            "types":        types,
            "duree_ms":     elapsed_ms,
            "message":      f"Dataset '{dataset_name}' chargé : {len(df)} lignes × {len(df.columns)} colonnes.",
            **extra,
        }

    except Exception as e:
        return {"status": "error", "error": f"Erreur lecture : {e}"}


@tool(
    name="df_list",
    description="Liste tous les datasets chargés en session avec leurs dimensions et source.",
    parameters={"type": "object", "properties": {}, "required": []},
)
def df_list() -> dict:
    if not _DATASETS:
        return {
            "status":   "success",
            "nombre":   0,
            "datasets": [],
            "message":  "Aucun dataset en mémoire. Utilisez df_read pour charger un fichier.",
        }
    datasets = []
    for nom, info in _DATASETS.items():
        df = info["df"]
        datasets.append({
            "nom":         nom,
            "source":      info["source"],
            "nb_lignes":   len(df),
            "nb_colonnes": len(df.columns),
            "colonnes":    list(df.columns),
            "charge_le":   info["loaded_at"],
        })
    return {"status": "success", "nombre": len(datasets), "datasets": datasets}


@tool(
    name="df_head",
    description=(
        "Affiche les premières ou dernières lignes d'un dataset. "
        "Utile pour vérifier rapidement le contenu après chargement."
    ),
    parameters={
        "type": "object",
        "properties": {
            "nom": {
                "type": "string",
                "description": "Nom du dataset.",
            },
            "n": {
                "type": "integer",
                "description": "Nombre de lignes à afficher (défaut: 10). Négatif = dernières lignes.",
            },
            "colonnes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Sous-ensemble de colonnes à afficher (défaut: toutes).",
            },
        },
        "required": ["nom"],
    },
)
def df_head(
    nom: str,
    n: int = 10,
    colonnes: Optional[list] = None,
) -> dict:
    try:
        df = _get_df(nom)
        n = max(-len(df), min(n, _MAX_ROWS_DISPLAY))

        if colonnes:
            manquantes = [c for c in colonnes if c not in df.columns]
            if manquantes:
                return {
                    "status": "error",
                    "error": f"Colonnes introuvables : {manquantes}. "
                             f"Colonnes disponibles : {list(df.columns)}",
                }
            subset = df[colonnes]
        else:
            subset = df

        view = subset.tail(abs(n)) if n < 0 else subset.head(n)
        records, _ = _df_to_records(view, max_rows=abs(n))

        return {
            "status":      "success",
            "nom":         nom,
            "nb_lignes":   len(df),
            "nb_colonnes": len(df.columns),
            "affichees":   len(records),
            "sens":        "fin" if n < 0 else "début",
            "lignes":      records,
        }

    except KeyError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": f"Erreur df_head : {e}"}


@tool(
    name="df_info",
    description=(
        "Retourne des statistiques descriptives complètes sur un dataset : "
        "types de colonnes, valeurs manquantes, min/max/moyenne/médiane/écart-type "
        "pour les colonnes numériques, valeurs uniques pour les colonnes texte. "
        "Idéal pour comprendre rapidement la structure et la qualité des données."
    ),
    parameters={
        "type": "object",
        "properties": {
            "nom": {
                "type": "string",
                "description": "Nom du dataset.",
            },
            "colonnes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Colonnes à analyser (défaut: toutes).",
            },
        },
        "required": ["nom"],
    },
)
def df_info(nom: str, colonnes: Optional[list] = None) -> dict:
    try:
        df = _get_df(nom)

        if colonnes:
            manquantes = [c for c in colonnes if c not in df.columns]
            if manquantes:
                return {"status": "error",
                        "error": f"Colonnes introuvables : {manquantes}"}
            df = df[colonnes]

        infos = []
        for col in df.columns:
            series = df[col]
            nb_null = int(series.isna().sum())
            nb_unique = int(series.nunique(dropna=True))
            col_info: dict = {
                "colonne":         col,
                "type":            str(series.dtype),
                "nb_valeurs":      len(series),
                "nb_manquants":    nb_null,
                "pct_manquants":   round(nb_null / len(series) * 100, 1) if len(series) else 0,
                "nb_uniques":      nb_unique,
            }

            if pd.api.types.is_numeric_dtype(series):
                desc = series.describe()
                col_info.update({
                    "min":    _safe(desc.get("min")),
                    "max":    _safe(desc.get("max")),
                    "moyenne":  _safe(desc.get("mean")),
                    "mediane":  _safe(series.median()),
                    "ecart_type": _safe(desc.get("std")),
                    "q25":    _safe(desc.get("25%")),
                    "q75":    _safe(desc.get("75%")),
                })
            elif pd.api.types.is_datetime64_any_dtype(series):
                col_info.update({
                    "min": _safe(series.min()),
                    "max": _safe(series.max()),
                })
            else:
                # Texte : top valeurs
                top = series.value_counts(dropna=True).head(5)
                col_info["top_valeurs"] = [
                    {"valeur": _safe(v), "occurrences": int(c)}
                    for v, c in top.items()
                ]

            infos.append(col_info)

        # Doublons
        nb_doublons = int(df.duplicated().sum())

        return {
            "status":       "success",
            "nom":          nom,
            "nb_lignes":    len(df),
            "nb_colonnes":  len(df.columns),
            "nb_doublons":  nb_doublons,
            "pct_doublons": round(nb_doublons / len(df) * 100, 1) if len(df) else 0,
            "colonnes":     infos,
        }

    except KeyError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": f"Erreur df_info : {e}"}


@tool(
    name="df_value_counts",
    description=(
        "Compte la fréquence de chaque valeur dans une colonne. "
        "Permet de détecter rapidement les valeurs dominantes, les anomalies "
        "ou la distribution d'une variable catégorielle."
    ),
    parameters={
        "type": "object",
        "properties": {
            "nom": {
                "type": "string",
                "description": "Nom du dataset.",
            },
            "colonne": {
                "type": "string",
                "description": "Colonne à analyser.",
            },
            "limite": {
                "type": "integer",
                "description": "Nombre max de valeurs à retourner (défaut: 20).",
            },
            "normaliser": {
                "type": "boolean",
                "description": "Si true, retourne les pourcentages plutôt que les comptages bruts.",
            },
            "inclure_nan": {
                "type": "boolean",
                "description": "Si true, inclut les valeurs manquantes dans le décompte (défaut: false).",
            },
        },
        "required": ["nom", "colonne"],
    },
)
def df_value_counts(
    nom: str,
    colonne: str,
    limite: int = 20,
    normaliser: bool = False,
    inclure_nan: bool = False,
) -> dict:
    try:
        df = _get_df(nom)
        if colonne not in df.columns:
            return {
                "status": "error",
                "error": f"Colonne '{colonne}' introuvable. "
                         f"Colonnes disponibles : {list(df.columns)}",
            }

        vc = df[colonne].value_counts(normalize=normaliser, dropna=not inclure_nan)
        total = len(df[colonne].dropna() if not inclure_nan else df[colonne])

        resultats = []
        for val, count in vc.head(limite).items():
            entry: dict = {"valeur": _safe(val)}
            if normaliser:
                entry["pourcentage"] = round(float(count) * 100, 2)
            else:
                entry["occurrences"] = int(count)
                entry["pourcentage"] = round(int(count) / total * 100, 2) if total else 0
            resultats.append(entry)

        return {
            "status":          "success",
            "nom":             nom,
            "colonne":         colonne,
            "nb_valeurs_total": total,
            "nb_valeurs_uniques": int(df[colonne].nunique(dropna=not inclure_nan)),
            "nb_manquants":    int(df[colonne].isna().sum()),
            "affichees":       len(resultats),
            "resultats":       resultats,
        }

    except KeyError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": f"Erreur df_value_counts : {e}"}


@tool(
    name="df_query",
    description=(
        "Filtre, sélectionne, trie et transforme un dataset avec une expression pandas. "
        "Peut créer un nouveau dataset ou retourner le résultat directement. "
        "Exemples d'expression : "
        "'age > 30 and ville == \"Paris\"' — "
        "'salaire.between(30000, 60000)' — "
        "'dept.str.contains(\"Tech\", case=False)'. "
        "Pour le tri, utiliser le paramètre 'trier_par'. "
        "Pour sélectionner des colonnes, utiliser 'colonnes'."
    ),
    parameters={
        "type": "object",
        "properties": {
            "nom": {
                "type": "string",
                "description": "Nom du dataset source.",
            },
            "filtre": {
                "type": "string",
                "description": "Expression de filtre pandas (ex: 'age > 30 and pays == \"FR\"').",
            },
            "colonnes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Colonnes à conserver dans le résultat (défaut: toutes).",
            },
            "trier_par": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Colonnes de tri (ex: ['date', 'montant']).",
            },
            "ordre_desc": {
                "type": "boolean",
                "description": "Si true, tri décroissant (défaut: false = croissant).",
            },
            "sauvegarder_sous": {
                "type": "string",
                "description": "Si fourni, sauvegarde le résultat comme nouveau dataset sous ce nom.",
            },
            "limite": {
                "type": "integer",
                "description": f"Nombre max de lignes retournées (défaut: {_MAX_ROWS_DISPLAY}).",
            },
        },
        "required": ["nom"],
    },
)
def df_query(
    nom: str,
    filtre: Optional[str] = None,
    colonnes: Optional[list] = None,
    trier_par: Optional[list] = None,
    ordre_desc: bool = False,
    sauvegarder_sous: Optional[str] = None,
    limite: int = _MAX_ROWS_DISPLAY,
) -> dict:
    limite = min(max(1, limite), _MAX_ROWS_DISPLAY)

    try:
        df = _get_df(nom).copy()

        # Filtre
        if filtre:
            try:
                df = df.query(filtre, engine="python")
            except Exception as e:
                return {
                    "status": "error",
                    "error":  f"Expression de filtre invalide : {e}. "
                              f"Vérifiez la syntaxe (guillemets doubles pour les chaînes).",
                }

        # Sélection de colonnes
        if colonnes:
            manquantes = [c for c in colonnes if c not in df.columns]
            if manquantes:
                return {"status": "error",
                        "error": f"Colonnes introuvables : {manquantes}"}
            df = df[colonnes]

        # Tri
        if trier_par:
            manquantes = [c for c in trier_par if c not in df.columns]
            if manquantes:
                return {"status": "error",
                        "error": f"Colonnes de tri introuvables : {manquantes}"}
            df = df.sort_values(trier_par, ascending=not ordre_desc)

        # Sauvegarder si demandé
        if sauvegarder_sous:
            _DATASETS[sauvegarder_sous] = {
                "df":        df.reset_index(drop=True),
                "source":    f"df_query({nom})",
                "loaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        records, truncated = _df_to_records(df, limite)

        return {
            "status":         "success",
            "nom_source":     nom,
            "filtre":         filtre,
            "nb_lignes":      len(df),
            "nb_colonnes":    len(df.columns),
            "tronque":        truncated,
            "sauvegarde_sous": sauvegarder_sous,
            "colonnes":       list(df.columns),
            "lignes":         records,
        }

    except KeyError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": f"Erreur df_query : {e}"}


@tool(
    name="df_pivot",
    description=(
        "Crée un tableau croisé dynamique (pivot table) à partir d'un dataset. "
        "Permet d'agréger des données par groupes (somme, moyenne, comptage, min, max…). "
        "Exemple : résumé des ventes par région et par produit."
    ),
    parameters={
        "type": "object",
        "properties": {
            "nom": {
                "type": "string",
                "description": "Nom du dataset source.",
            },
            "index": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Colonnes à utiliser comme index des lignes du pivot.",
            },
            "colonnes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Colonnes à déployer en en-têtes de colonnes (optionnel).",
            },
            "valeurs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Colonnes numériques à agréger.",
            },
            "agregation": {
                "type": "string",
                "description": "Fonction d'agrégation : 'sum', 'mean', 'count', 'min', 'max', 'median', 'std' (défaut: 'sum').",
            },
            "totaux": {
                "type": "boolean",
                "description": "Ajouter des totaux de lignes et colonnes (défaut: true).",
            },
            "sauvegarder_sous": {
                "type": "string",
                "description": "Si fourni, sauvegarde le pivot comme nouveau dataset.",
            },
        },
        "required": ["nom", "index"],
    },
)
def df_pivot(
    nom: str,
    index: list,
    colonnes: Optional[list] = None,
    valeurs: Optional[list] = None,
    agregation: str = "sum",
    totaux: bool = True,
    sauvegarder_sous: Optional[str] = None,
) -> dict:
    AGGS = {"sum", "mean", "count", "min", "max", "median", "std", "nunique"}
    if agregation not in AGGS:
        return {"status": "error",
                "error": f"Agrégation '{agregation}' non supportée. Valeurs : {sorted(AGGS)}"}

    try:
        df = _get_df(nom)

        # Vérifier les colonnes
        all_cols = index + (colonnes or []) + (valeurs or [])
        manquantes = [c for c in all_cols if c not in df.columns]
        if manquantes:
            return {"status": "error",
                    "error": f"Colonnes introuvables : {manquantes}"}

        pivot = pd.pivot_table(
            df,
            index=index,
            columns=colonnes if colonnes else None,
            values=valeurs if valeurs else None,
            aggfunc=agregation,
            margins=totaux,
            margins_name="Total",
        )

        # Aplatir les multi-index de colonnes
        if isinstance(pivot.columns, pd.MultiIndex):
            pivot.columns = [" / ".join(str(c) for c in col).strip()
                             for col in pivot.columns]

        pivot = pivot.reset_index()

        if sauvegarder_sous:
            _DATASETS[sauvegarder_sous] = {
                "df":        pivot,
                "source":    f"df_pivot({nom})",
                "loaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        records, truncated = _df_to_records(pivot)

        return {
            "status":          "success",
            "nom_source":      nom,
            "agregation":      agregation,
            "nb_lignes":       len(pivot),
            "nb_colonnes":     len(pivot.columns),
            "tronque":         truncated,
            "sauvegarde_sous": sauvegarder_sous,
            "colonnes":        list(pivot.columns),
            "lignes":          records,
        }

    except KeyError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": f"Erreur df_pivot : {e}"}


@tool(
    name="df_merge",
    description=(
        "Fusionne deux datasets (JOIN). "
        "Types de jointure : 'inner' (intersection), 'left', 'right', 'outer' (union). "
        "Equivalent SQL : SELECT * FROM gauche JOIN droite ON gauche.cle = droite.cle"
    ),
    parameters={
        "type": "object",
        "properties": {
            "gauche": {
                "type": "string",
                "description": "Nom du dataset gauche.",
            },
            "droite": {
                "type": "string",
                "description": "Nom du dataset droit.",
            },
            "sur": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Colonne(s) commune(s) pour la jointure (même nom dans les deux datasets).",
            },
            "sur_gauche": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Colonne(s) de jointure dans le dataset gauche (si noms différents).",
            },
            "sur_droite": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Colonne(s) de jointure dans le dataset droit (si noms différents).",
            },
            "type_jointure": {
                "type": "string",
                "description": "Type de jointure : 'inner' (défaut), 'left', 'right', 'outer'.",
            },
            "sauvegarder_sous": {
                "type": "string",
                "description": "Nom du dataset résultat (obligatoire pour conserver le résultat).",
            },
        },
        "required": ["gauche", "droite"],
    },
)
def df_merge(
    gauche: str,
    droite: str,
    sur: Optional[list] = None,
    sur_gauche: Optional[list] = None,
    sur_droite: Optional[list] = None,
    type_jointure: str = "inner",
    sauvegarder_sous: Optional[str] = None,
) -> dict:
    TYPES = {"inner", "left", "right", "outer"}
    if type_jointure not in TYPES:
        return {"status": "error",
                "error": f"Type de jointure invalide : '{type_jointure}'. Valeurs : {sorted(TYPES)}"}

    try:
        df_g = _get_df(gauche)
        df_d = _get_df(droite)

        merged = pd.merge(
            df_g, df_d,
            on=sur if sur else None,
            left_on=sur_gauche if sur_gauche else None,
            right_on=sur_droite if sur_droite else None,
            how=type_jointure,
            suffixes=("_g", "_d"),
        )

        if sauvegarder_sous:
            _DATASETS[sauvegarder_sous] = {
                "df":        merged,
                "source":    f"df_merge({gauche}, {droite})",
                "loaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        records, truncated = _df_to_records(merged)

        return {
            "status":          "success",
            "gauche":          gauche,
            "droite":          droite,
            "type_jointure":   type_jointure,
            "cle_jointure":    sur or {"gauche": sur_gauche, "droite": sur_droite},
            "nb_lignes":       len(merged),
            "nb_colonnes":     len(merged.columns),
            "tronque":         truncated,
            "sauvegarde_sous": sauvegarder_sous,
            "colonnes":        list(merged.columns),
            "lignes":          records,
        }

    except KeyError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": f"Erreur df_merge : {e}"}


@tool(
    name="df_write",
    description=(
        "Exporte un dataset en CSV ou Excel. "
        "Pour Excel, possibilité d'écrire plusieurs datasets dans des feuilles séparées. "
        "Le fichier est créé ou écrasé à l'emplacement indiqué."
    ),
    parameters={
        "type": "object",
        "properties": {
            "nom": {
                "type": "string",
                "description": "Nom du dataset à exporter.",
            },
            "destination": {
                "type": "string",
                "description": "Chemin du fichier de sortie (.csv, .xlsx). Défaut : ~/export_<nom>_<timestamp>.csv",
            },
            "format": {
                "type": "string",
                "description": "Format de sortie : 'csv' (défaut si .csv) ou 'excel' (défaut si .xlsx).",
            },
            "separateur": {
                "type": "string",
                "description": "Séparateur CSV (défaut: ',').",
            },
            "inclure_index": {
                "type": "boolean",
                "description": "Inclure l'index pandas dans l'export (défaut: false).",
            },
            "feuille": {
                "type": "string",
                "description": "Nom de la feuille Excel (défaut: nom du dataset).",
            },
            "datasets_supplementaires": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Autres datasets à inclure comme feuilles supplémentaires (Excel uniquement).",
            },
        },
        "required": ["nom"],
    },
)
def df_write(
    nom: str,
    destination: Optional[str] = None,
    format: Optional[str] = None,
    separateur: str = ",",
    inclure_index: bool = False,
    feuille: Optional[str] = None,
    datasets_supplementaires: Optional[list] = None,
) -> dict:
    try:
        df = _get_df(nom)

        # Déterminer le format et le chemin
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if destination:
            dest = Path(destination).expanduser()
            fmt = format or ("excel" if dest.suffix.lower() in (".xlsx", ".xls") else "csv")
        else:
            fmt = format or "csv"
            ext = ".xlsx" if fmt == "excel" else ".csv"
            dest = Path.home() / f"export_{nom}_{ts}{ext}"

        dest.parent.mkdir(parents=True, exist_ok=True)

        t0 = time.perf_counter()

        if fmt == "csv":
            df.to_csv(dest, sep=separateur, index=inclure_index, encoding="utf-8-sig")
            nb_lignes = len(df)

        elif fmt == "excel":
            sheet_name = feuille or nom[:31]  # Excel limite les noms à 31 chars
            with pd.ExcelWriter(dest, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=inclure_index)
                if datasets_supplementaires:
                    for ds_nom in datasets_supplementaires:
                        if ds_nom in _DATASETS:
                            ds_df = _DATASETS[ds_nom]["df"]
                            ds_df.to_excel(writer, sheet_name=ds_nom[:31], index=inclure_index)
            nb_lignes = len(df)

        else:
            return {"status": "error", "error": f"Format inconnu : '{fmt}'. Utilisez 'csv' ou 'excel'."}

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        taille = dest.stat().st_size
        taille_str = f"{taille / 1024:.1f} Ko" if taille < 1_048_576 else f"{taille / 1_048_576:.2f} Mo"

        return {
            "status":    "success",
            "nom":       nom,
            "fichier":   str(dest),
            "format":    fmt,
            "nb_lignes": nb_lignes,
            "taille":    taille_str,
            "duree_ms":  elapsed_ms,
            "message":   f"Dataset '{nom}' exporté dans {dest.name} ({taille_str}).",
        }

    except KeyError as e:
        return {"status": "error", "error": str(e)}
    except PermissionError:
        return {"status": "error", "error": f"Permission refusée pour écrire dans : {dest}"}
    except Exception as e:
        return {"status": "error", "error": f"Erreur df_write : {e}"}


@tool(
    name="df_drop",
    description=(
        "Supprime un ou plusieurs datasets de la mémoire session pour libérer des ressources. "
        "Les fichiers sources ne sont pas modifiés."
    ),
    parameters={
        "type": "object",
        "properties": {
            "noms": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Liste des noms de datasets à supprimer.",
            },
        },
        "required": ["noms"],
    },
)
def df_drop(noms: list) -> dict:
    supprimes = []
    introuvables = []
    for nom in noms:
        if nom in _DATASETS:
            del _DATASETS[nom]
            supprimes.append(nom)
        else:
            introuvables.append(nom)

    return {
        "status":       "success",
        "supprimes":    supprimes,
        "introuvables": introuvables,
        "restants":     list(_DATASETS.keys()),
        "message":      f"{len(supprimes)} dataset(s) supprimé(s) de la mémoire.",
    }
