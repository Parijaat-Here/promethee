---
name: Guide création PowerPoint
description: Protocole de création de présentations PowerPoint — workflow, outils export_pptx_json et export_pptx_outline, gabarits de slides, erreurs fréquentes
tags: [powerpoint, présentation, export, pptx, slides]
version: 2.0
---

# Guide création PowerPoint

Protocole complet pour produire des présentations PowerPoint avec les outils d'export disponibles.

---

## 1. Choisir le bon outil

| Situation | Outil recommandé |
|---|---|
| Structure libre, rédigée au fil du contenu | `export_pptx_outline` |
| Structure précise, avec tableaux ou mise en forme avancée | `export_pptx_json` |
| Convertir un fichier existant (ODT, DOCX…) en PPTX | `export_libreoffice` |

**Règle : un seul appel suffit.** Ne pas fragmenter la création en plusieurs appels successifs. Construire l'outline ou le JSON complet, puis appeler l'outil une seule fois.

---

## 2. `export_pptx_outline` — création rapide par outline texte

### Syntaxe de l'outline

```
# Titre du slide       → crée un nouveau slide
Sous-titre ou phase    → texte de sous-titre (sans puce)
- Puce niveau 1        → point principal
  - Puce niveau 2      → sous-point (indentation 2 espaces)
> Note du présentateur → note (invisible en présentation)
```

### Exemple complet

```
# Bilan RH 2024
Direction des Ressources Humaines

# Effectifs au 31 décembre 2024
- 1 247 agents en poste (+3,2 % vs 2023)
- 89 recrutements réalisés
  - 42 titulaires (concours et mutation)
  - 47 contractuels
- 34 départs (retraite, mobilité, démission)
> Préciser que les chiffres incluent les agents en détachement entrant

# Absentéisme
- Taux annuel moyen : 5,8 % (vs 6,1 % en 2023)
- Principaux motifs :
  - Maladie ordinaire : 68 %
  - Longue maladie : 21 %
  - Accidents de service : 11 %

# Axes prioritaires 2025
Phase 1 — Recrutement
- Lancement de 3 concours internes
- Renforcement de la filière numérique

Phase 2 — Formation
- Déploiement du plan de formation obligatoire
- Partenariat avec l'INSP pour les cadres A+

# Conclusion
- Stabilisation des effectifs atteinte
- Cap mis sur la montée en compétences
> Ouvrir la discussion sur les arbitrages budgétaires T1 2025
```

### Appel à l'outil

```json
{
  "outline": "# Titre\n- Point 1\n- Point 2\n...",
  "title": "Nom de la présentation",
  "output_path": "~/Exports/Prométhée/bilan_rh_2024.pptx"
}
```

---

## 3. `export_pptx_json` — création structurée avec tableaux

### Format JSON de la structure

```json
{
  "title": "Titre de la présentation",
  "slides": [
    {
      "title": "Titre du slide",
      "subtitle": "Sous-titre optionnel",
      "content": "Texte libre"
    },
    {
      "title": "Slide avec puces",
      "bullets": [
        "Point principal 1",
        "Point principal 2",
        "Point principal 3"
      ]
    },
    {
      "title": "Slide avec tableau",
      "table": {
        "headers": ["Colonne A", "Colonne B", "Colonne C"],
        "rows": [
          ["Valeur 1", "Valeur 2", "Valeur 3"],
          ["Valeur 4", "Valeur 5", "Valeur 6"]
        ]
      }
    }
  ]
}
```

---

## 4. Règles de conception des slides

### Concision (règle absolue)
- **Maximum 5 puces par slide**
- **Maximum 10 mots par puce**
- Une idée = un slide
- Pas de phrases complètes → des fragments nominaux

```
❌ « Il convient de noter que les effectifs ont augmenté de manière significative »
✅ « Effectifs : +3,2 % en un an »
```

### Hiérarchie logique
```
Slide 1 : Contexte / Problématique
Slides 2-N : Développement (1 thème par slide)
Dernier slide : Conclusion + actions / questions
```

### Pas de slide de titre générique
Commencer directement par le premier slide de contenu. Le titre de la présentation est défini dans les métadonnées, pas dans un slide dédié.

---

## 5. Types de slides selon le contenu

| Contenu | Format |
|---|---|
| Chiffres clés | 3-4 grands chiffres centrés, 1 ligne de contexte chacun |
| Comparaison | Tableau 2-3 colonnes |
| Processus séquentiel | Puces avec sous-niveau Phase 1 / Phase 2… |
| Décision / recommandation | Puce unique en gras + 3 arguments max |
| Citation / verbatim | Texte en italique, source en sous-titre |

---

## 6. Erreurs fréquentes à éviter

| Erreur | Correction |
|---|---|
| Phrases longues dans les puces | Reformuler en fragment nominal (≤ 10 mots) |
| Plus de 5 puces par slide | Diviser en 2 slides ou regrouper par thème |
| Slide de titre vide en premier | Commencer directement par le premier slide de contenu |
| Plusieurs appels pour une même présentation | Construire l'outline/JSON complet, un seul appel |
| `\n` manquants dans l'outline (appel JSON) | Utiliser `\n` pour séparer les lignes dans la chaîne |
| Tableau avec colonnes inégales | Vérifier que chaque ligne de `rows` a le même nombre de cellules que `headers` |

---

## 7. Workflow recommandé

```
1. Clarifier avec l'utilisateur : sujet, audience, durée, nombre de slides
2. Rédiger l'outline Markdown complet
3. Si tableaux nécessaires → convertir en JSON
4. Appeler export_pptx_outline ou export_pptx_json (un seul appel)
5. Indiquer le chemin exact du fichier généré à l'utilisateur
```

### Estimation durée → slides
- Présentation courte (5-10 min) : 5-8 slides
- Présentation standard (15-20 min) : 10-15 slides
- Présentation longue (30-45 min) : 20-30 slides

---

## 8. Chemin de sortie par défaut

Si `output_path` n'est pas précisé, le fichier est créé dans :
```
~/Exports/Prométhée/[nom_auto_généré].pptx
```

Toujours indiquer le chemin exact à l'utilisateur en fin de génération.
