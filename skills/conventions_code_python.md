---
name: Conventions de code Python
description: Standards de qualité pour la production de code Python — style, structure, sécurité, outils disponibles
tags: [python, code, conventions, qualité, ruff, mypy]
version: 2.0
---

# Conventions de code Python

Standards à appliquer systématiquement lors de la production de code Python dans ce projet.

---

## 1. Style et formatage

- **Longueur de ligne** : 100 caractères maximum (configuré dans `pyproject.toml`).
- **Indentation** : 4 espaces, jamais de tabulation.
- **Imports** : groupés dans l'ordre stdlib → third-party → local, séparés par une ligne vide (isort).
- **Nommage** :
  - Variables et fonctions : `snake_case`
  - Classes : `PascalCase`
  - Constantes module-level : `UPPER_SNAKE_CASE`
  - Paramètres privés : préfixe `_`

```python
# ✅ Correct
MAX_RETRIES = 3

def fetch_document(url: str, timeout: int = 30) -> str:
    ...

class DocumentParser:
    def __init__(self, encoding: str = "utf-8") -> None:
        self._encoding = encoding
```

---

## 2. Typage statique

Toutes les fonctions publiques doivent avoir des annotations de types complètes.
Mypy est configuré avec `warn_return_any = true`.

```python
# ✅ Correct
def parse_date(value: str) -> datetime | None:
    ...

# ❌ À éviter
def parse_date(value):
    ...
```

Pour les types complexes, utiliser les imports de `typing` ou les syntaxes Python 3.10+ :

```python
from typing import Optional   # < 3.10
result: str | None            # >= 3.10 (préféré)

from typing import Callable
callback: Callable[[str, int], bool]
```

---

## 3. Gestion des erreurs

- Capturer les exceptions **spécifiques**, jamais `Exception` seule sauf au point d'entrée.
- Toujours loguer l'exception originale avec `logging.exception` ou en passant `exc_info=True`.
- Retourner `None` ou une valeur sentinelle plutôt que de laisser se propager une exception dans les modules utilitaires.

```python
import logging
_log = logging.getLogger(__name__)

# ✅ Correct
try:
    result = api_call()
except httpx.TimeoutException as exc:
    _log.warning("Timeout lors de l'appel API : %s", exc)
    return None
except httpx.HTTPStatusError as exc:
    _log.error("Erreur HTTP %d : %s", exc.response.status_code, exc)
    raise
```

---

## 4. Docstrings

Format NumPy pour les fonctions publiques complexes, une ligne pour les fonctions simples.

```python
def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Calcule la similarité cosinus entre deux vecteurs.

    Parameters
    ----------
    vec_a : list[float]
        Premier vecteur (doit être normalisé).
    vec_b : list[float]
        Second vecteur (même dimension que vec_a).

    Returns
    -------
    float
        Score entre -1.0 (opposés) et 1.0 (identiques).

    Raises
    ------
    ValueError
        Si les vecteurs n'ont pas la même dimension.
    """
```

---

## 5. Outils d'exécution disponibles

Il n'existe qu'**un seul outil d'exécution Python** : `python_exec`.

### `python_exec` — outil unique pour tout le code Python

S'exécute dans un virtualenv dédié (`~/.promethee_python_env/`).
**L'état est PERSISTANT entre les appels** : les variables, imports et fonctions définis
dans un appel sont immédiatement disponibles dans les suivants, sans les redéfinir.

**Règles d'usage :**
- **Un seul appel par tâche logique.** Ne pas fragmenter le code en plusieurs petits appels successifs.
- **Tout le code d'une tâche va dans un seul appel.** Imports, traitement, affichage : tout ensemble.
- **Plusieurs appels sont justifiés uniquement quand les étapes sont logiquement indépendantes** :
  - `python_install` puis `python_exec` (installer avant d'utiliser)
  - Charger des données, puis dans un second appel les analyser de façon interactive
  - Corriger une erreur retournée par l'appel précédent

```python
# ✅ Un seul appel — tout en une fois
import pandas as pd
from pathlib import Path

df = pd.read_csv(Path.home() / "data.csv")
print(df.describe())
print(df.isnull().sum())
```

```python
# ❌ À éviter — fragmentation inutile
# Appel 1 : import pandas as pd
# Appel 2 : df = pd.read_csv(...)
# Appel 3 : print(df.describe())
```

Paramètres utiles :
- `timeout` : augmenter pour les traitements longs (défaut 30 s)
- `reset_state` : `True` pour repartir d'un environnement propre

### `python_install` — installation de packages

À appeler **avant** `python_exec` si un package est manquant.
Un seul appel suffit par package ; il reste installé pour toute la session.

```python
# Via l'outil python_install :
package = "httpx"   # installe dans le venv dédié
```

### `python_run_script` — exécuter un fichier .py existant

Utile pour les scripts déjà écrits sur le disque.
N'utilise pas l'état persistant de session.

---

## 6. Patterns à privilégier

### Context managers pour les ressources
```python
with open(path, encoding="utf-8") as f:
    content = f.read()
```

### Pathlib plutôt qu'os.path
```python
from pathlib import Path

output = Path.home() / "exports" / "rapport.docx"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(content, encoding="utf-8")
```

### Dataclasses pour les structures de données
```python
from dataclasses import dataclass, field

@dataclass
class DocumentInfo:
    title: str
    path: Path
    tags: list[str] = field(default_factory=list)
    size: int = 0
```

---

## 7. Sécurité

- Ne jamais interpoler des données utilisateur dans des requêtes SQL → utiliser les paramètres (`?` ou `%s`).
- Ne jamais utiliser `eval()` ou `exec()` sur des données externes.
- Pas de secrets (clés API, mots de passe) dans le code source → passer par `Config` (`.env`).
- Valider les chemins de fichiers fournis par l'utilisateur avant toute écriture.

```python
# ✅ SQL paramétré
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# ❌ Injection possible
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

---

## 8. Checklist avant livraison

- [ ] Annotations de types complètes sur les fonctions publiques
- [ ] Aucune exception capturée silencieusement (bare `except` ou `pass` seul)
- [ ] Pas de `print()` de debug oublié → utiliser `logging`
- [ ] Chemins avec `pathlib.Path`, pas de `os.path.join`
- [ ] Pas de secret en clair dans le code
- [ ] Docstring sur les fonctions non triviales
