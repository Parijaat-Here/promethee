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
latex_renderer.py — Détection et rendu LaTeX via KaTeX (assets locaux)
=======================================================================

Rôle
----
Ce module est l'unique point de vérité pour tout ce qui touche au LaTeX
dans l'application. Il s'interface avec message_widget.py via deux
fonctions publiques :

    katex_html_tags()   → balises <link>/<script> à injecter dans le <head>
    protect_latex(text) → préserve les blocs LaTeX avant le passage Markdown
    restore_latex(html) → réinjecte les blocs après le rendu Markdown

Pourquoi protect/restore ?
--------------------------
Le parser Markdown transforme les underscores, les backslashes et les
accolades présents dans les formules LaTeX en balises HTML ou en entités,
ce qui brise systématiquement le rendu KaTeX.
La stratégie est la suivante :
  1. protect_latex() extrait chaque bloc LaTeX, le stocke dans un cache
     et le remplace par un placeholder neutre <!-- LATEX_n -->.
  2. Le Markdown est rendu normalement (il ne voit que du texte neutre).
  3. restore_latex() remplace chaque placeholder par la balise KaTeX
     correspondante (<span class="math-inline"> ou <div class="math-display">).
  4. KaTeX (auto-render désactivé, appel explicite) interprète ces balises.

Délimiteurs reconnus
--------------------
  Display (bloc centré)
    $$  ...  $$
    \\[  ...  \\]

  Inline (dans le texte)
    $  ...  $   — avec heuristique anti-faux-positifs (voir _is_math_dollar)
    \\(  ...  \\)

Heuristique anti-faux-positifs pour $...$
------------------------------------------
Un dollar simple est ignoré quand il ressemble à un montant ou à un symbole
monétaire, c'est-à-dire quand :
  • il est immédiatement suivi d'un chiffre (ex : $42, $1 200)
  • il est précédé d'un chiffre ou d'une lettre collée (ex : USD$)
  • le contenu entre les deux $ contient un espace en début ou en fin
    (heuristique forte : les formules LaTeX ne commencent/finissent pas
    par un espace, contrairement aux phrases de langage naturel)
  • le contenu est vide

Dépendances
-----------
- Aucune dépendance Python externe (stdlib uniquement).
- Les fichiers KaTeX doivent être présents dans assets/katex/ :
    katex.min.js, katex.min.css
  Le fichier auto-render.min.js N'est PAS utilisé (rendu explicite).
"""

import re
from pathlib import Path

# ── Chemins assets ────────────────────────────────────────────────────────────

_ASSETS_DIR = Path(__file__).parent.parent.parent / "assets" / "katex"
_KATEX_AVAILABLE = (
    (_ASSETS_DIR / "katex.min.js").exists()
    and (_ASSETS_DIR / "katex.min.css").exists()
)

# ── Cache des placeholders (par appel à protect_latex) ───────────────────────
# Chaque appel à protect_latex() reçoit son propre dict isolé afin d'éviter
# toute collision entre messages rendus en parallèle.

_PLACEHOLDER_PREFIX = "LATEX"
_PLACEHOLDER_RE = re.compile(r"<!--\s*LATEX_(\d+)\s*-->")


# ══════════════════════════════════════════════════════════════════════════════
#  API publique
# ══════════════════════════════════════════════════════════════════════════════

def is_available() -> bool:
    """Retourne True si les assets KaTeX locaux sont présents."""
    return _KATEX_AVAILABLE


def katex_html_tags() -> str:
    """
    Retourne les balises <link> et <script> KaTeX à injecter dans le <head>.

    Utilise les assets locaux (pas de CDN, pas de réseau).
    Le script de rendu appelle renderMathInElement() en mode explicite
    (ciblé sur les classes .math-inline et .math-display) plutôt que
    d'utiliser auto-render, ce qui évite les interférences avec le texte.

    Retourne une chaîne vide si KaTeX n'est pas disponible.
    """
    if not _KATEX_AVAILABLE:
        return "<!-- KaTeX non disponible : assets/katex/ introuvable -->"

    base = _ASSETS_DIR.as_uri()
    return f"""\
<link rel="stylesheet" href="{base}/katex.min.css">
<script defer src="{base}/katex.min.js" onload="
(function() {{
    // Rendu explicite sur les éléments .math-inline et .math-display.
    // On n'utilise PAS auto-render pour éviter tout scan du DOM entier
    // qui pourrait interpréter des dollars dans du texte ordinaire.
    function renderAll() {{
        document.querySelectorAll('.math-display').forEach(function(el) {{
            var src = el.getAttribute('data-latex');
            el.innerHTML = '';
            try {{
                katex.render(src, el, {{
                    displayMode: true,
                    throwOnError: false,
                    strict: 'ignore'
                }});
            }} catch(e) {{
                el.textContent = src;
            }}
        }});
        document.querySelectorAll('.math-inline').forEach(function(el) {{
            var src = el.getAttribute('data-latex');
            el.innerHTML = '';
            try {{
                katex.render(src, el, {{
                    displayMode: false,
                    throwOnError: false,
                    strict: 'ignore'
                }});
            }} catch(e) {{
                el.textContent = src;
            }}
        }});
    }}
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', renderAll);
    }} else {{
        renderAll();
    }}
}})();
"></script>"""


def katex_css_extras() -> str:
    """
    CSS complémentaire pour les blocs LaTeX (mise en page, overflow).
    À injecter dans le <style> du document HTML.
    """
    return """\
/* ── LaTeX / KaTeX ───────────────────────────────────────────── */
.math-display {
    display: block;
    overflow-x: auto;
    overflow-y: hidden;
    margin: 12px 0;
    padding: 4px 0;
    text-align: center;
    max-width: 100%;
}
.math-inline {
    display: inline;
}
/* Fallback quand KaTeX n'est pas chargé : affichage monospace */
.math-display:not(.katex-rendered),
.math-inline:not(.katex-rendered) {
    font-family: "JetBrains Mono", "Fira Code", monospace;
    font-size: 0.95em;
    background: rgba(128,128,128,0.08);
    border-radius: 3px;
    padding: 1px 4px;
}
"""


def protect_latex(text: str) -> tuple[str, dict[int, tuple[str, bool]]]:
    """
    Extrait les blocs LaTeX du texte et les remplace par des placeholders.

    Doit être appelé AVANT le rendu Markdown.

    Parameters
    ----------
    text : str
        Texte brut (Markdown + LaTeX mélangés).

    Returns
    -------
    protected_text : str
        Texte avec les blocs LaTeX remplacés par <!-- LATEX_n -->.
    cache : dict[int, tuple[str, bool]]
        Dictionnaire {index: (source_latex, is_display)}.
        - source_latex : contenu LaTeX brut (sans délimiteurs)
        - is_display   : True pour $$, \\[…\\] ; False pour $, \\(…\\)
    """
    cache: dict[int, tuple[str, bool]] = {}
    counter = [0]  # liste pour mutation dans closure

    def store(latex_src: str, display: bool) -> str:
        idx = counter[0]
        cache[idx] = (latex_src, display)
        counter[0] += 1
        return f"<!-- {_PLACEHOLDER_PREFIX}_{idx} -->"

    # Ordre d'application : du plus spécifique au moins spécifique.
    # 1. Blocs display $$ ... $$ (multiligne autorisé)
    text = re.sub(
        r'\$\$(.*?)\$\$',
        lambda m: store(m.group(1).strip(), True),
        text,
        flags=re.DOTALL,
    )

    # 2. Blocs display \[ ... \]
    text = re.sub(
        r'\\\[(.*?)\\\]',
        lambda m: store(m.group(1).strip(), True),
        text,
        flags=re.DOTALL,
    )

    # 3. Inline \( ... \)
    text = re.sub(
        r'\\\((.*?)\\\)',
        lambda m: store(m.group(1).strip(), False),
        text,
        flags=re.DOTALL,
    )

    # 4. Inline $ ... $ — avec heuristique anti-faux-positifs
    text = _replace_inline_dollars(text, store)

    return text, cache


def restore_latex(html: str, cache: dict[int, tuple[str, bool]]) -> str:
    """
    Réinjecte les blocs LaTeX dans le HTML rendu.

    Doit être appelé APRÈS le rendu Markdown.

    Les blocs sont réinjectés sous la forme :
        <div  class="math-display" data-latex="...">...</div>
        <span class="math-inline"  data-latex="...">...</span>

    Les balises produites sont volontairement vides (pas de contenu texte) :
    KaTeX remplace l'intégralité du innerHTML, et un contenu préexistant
    pourrait déclencher des warnings sur des caractères Unicode non reconnus.

    Parameters
    ----------
    html : str
        HTML issu du rendu Markdown (contient des placeholders).
    cache : dict[int, tuple[str, bool]]
        Cache retourné par protect_latex().

    Returns
    -------
    str
        HTML avec les placeholders remplacés par des balises LaTeX.
    """
    if not cache:
        return html

    def replace_placeholder(m: re.Match) -> str:
        idx = int(m.group(1))
        if idx not in cache:
            return m.group(0)  # placeholder inconnu → laisser tel quel
        latex_src, is_display = cache[idx]
        escaped = _escape_for_attr(latex_src)
        if is_display:
            return f'<div class="math-display" data-latex="{escaped}"></div>'
        else:
            return f'<span class="math-inline" data-latex="{escaped}"></span>'

    # Les placeholders peuvent avoir été partiellement altérés par le parser
    # Markdown (ex: <!-- --> transformé). On cherche les deux formes.
    html = _PLACEHOLDER_RE.sub(replace_placeholder, html)
    return html


# ══════════════════════════════════════════════════════════════════════════════
#  Fonctions internes
# ══════════════════════════════════════════════════════════════════════════════

def _replace_inline_dollars(
    text: str,
    store_fn,
) -> str:
    """
    Remplace les blocs $ ... $ inline en appliquant l'heuristique
    anti-faux-positifs.

    L'heuristique rejette un dollar quand :
      - il est immédiatement suivi d'un chiffre (montant monétaire)
      - le contenu entre dollars est vide
      - le contenu commence ou finit par un espace (langage naturel)
      - le contenu contient un saut de ligne (trop long pour de l'inline)

    On traite le texte caractère par caractère pour gérer correctement
    les dollars échappés (\\$) et les imbrications.
    """
    result = []
    i = 0
    n = len(text)

    while i < n:
        # Dollar échappé → on le passe tel quel
        if text[i] == '\\' and i + 1 < n and text[i + 1] == '$':
            result.append('\\$')
            i += 2
            continue

        if text[i] != '$':
            result.append(text[i])
            i += 1
            continue

        # On est sur un $. Chercher le $ fermant.
        j = i + 1
        while j < n:
            if text[j] == '\\' and j + 1 < n and text[j + 1] == '$':
                j += 2  # dollar échappé à l'intérieur
                continue
            if text[j] == '$':
                break
            j += 1

        if j >= n:
            # Pas de $ fermant → dollar littéral
            result.append(text[i])
            i += 1
            continue

        content = text[i + 1:j]

        # ── Heuristique anti-faux-positifs ────────────────────────────
        if _is_likely_not_math(text, i, content):
            result.append(text[i])
            i += 1
            continue

        # C'est du LaTeX inline valide
        result.append(store_fn(content.strip(), False))
        i = j + 1

    return ''.join(result)


def _is_likely_not_math(text: str, pos: int, content: str) -> bool:
    """
    Retourne True si le $ à la position pos est probablement monétaire
    ou non-mathématique.
    """
    # Contenu vide
    if not content.strip():
        return True

    # Contenu multiligne → pas de l'inline
    if '\n' in content:
        return True

    # Contenu qui commence ou finit par un espace
    if content != content.strip():
        return True

    # $ suivi directement d'un chiffre : $42, $1,200
    if pos + 1 < len(text) and text[pos + 1].isdigit():
        return True

    # Précédé d'un chiffre ou d'une lettre collée : 100$, USD$
    if pos > 0 and (text[pos - 1].isalnum()):
        return True

    # Contenu trop long (>200 chars) pour de l'inline réaliste
    if len(content) > 200:
        return True

    return False


def _escape_for_attr(s: str) -> str:
    """Échappe une chaîne pour l'utiliser dans un attribut HTML double-quote."""
    return (
        s.replace('&', '&amp;')
         .replace('"', '&quot;')
         .replace('<', '&lt;')
         .replace('>', '&gt;')
    )
