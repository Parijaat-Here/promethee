---
name: Guide export Excel
description: Création de classeurs Excel avec export_xlsx_json — graphiques, feuilles multiples, mise en forme, bonnes pratiques
tags: [excel, xlsx, graphiques, export, données, tableaux]
version: 2.0
---

# Guide — Création de classeurs Excel avec export_xlsx_json

---

## 1. Structure générale

```json
{
  "sheets": [
    {
      "name": "Nom de la feuille",
      "headers": ["Col A", "Col B", "Col C"],
      "rows": [
        ["valeur1", 100, 0.42],
        ["valeur2", 200, 0.58]
      ],
      "charts": [ ... ]
    }
  ]
}
```

**Règles fondamentales :**
- Toujours fournir `headers` et `rows` même si vides (`[]`).
- Les types sont respectés : nombres sans guillemets, textes avec.
- Un seul appel `export_xlsx_json` suffit pour un classeur complet avec plusieurs feuilles et graphiques.

---

## 2. Types de graphiques disponibles

| Type           | Description                        | Cas d'usage typique                        |
|----------------|------------------------------------|--------------------------------------------|
| `bar`          | Barres verticales groupées         | Comparaison entre catégories               |
| `bar_stacked`  | Barres verticales empilées         | Composition d'un total                     |
| `bar_percent`  | Barres empilées 100 %              | Répartition en proportions                 |
| `bar_h`        | Barres horizontales groupées       | Libellés de catégories longs               |
| `line`         | Courbes                            | Évolution temporelle, tendances            |
| `line_smooth`  | Courbes lissées (spline)           | Tendances sans à-coups visuels             |
| `area`         | Aires                              | Volumes cumulés dans le temps              |
| `area_stacked` | Aires empilées                     | Parts cumulées d'un ensemble               |
| `pie`          | Camembert                          | Parts d'un tout (max 6 catégories)         |
| `doughnut`     | Anneau                             | Idem camembert, style plus moderne         |
| `scatter`      | Nuage de points                    | Corrélation entre deux variables           |
| `bubble`       | Bulles                             | Trois variables : x, y, taille             |
| `radar`        | Radar / toile d'araignée           | Profils multi-critères (ex : compétences)  |

---

## 3. Référence complète des paramètres graphique

```json
{
  "type": "bar",
  "title": "Titre affiché au-dessus du graphique",
  "data_sheet": "NomFeuille",
  "categories_col": 1,
  "series": [
    {
      "title": "Légende de la série",
      "col": 2,
      "color": "2255A4"
    }
  ],
  "data_rows": [2, 13],
  "anchor": "E2",
  "width_cm": 15,
  "height_cm": 10,
  "style": 10,
  "show_legend": true,
  "show_data_labels": false
}
```

**Notes sur les paramètres :**
- `categories_col` et `col` : numérotation **1-based** (A=1, B=2, C=3…)
- `data_rows` : exclut la ligne d'en-tête. `[2, 13]` = lignes 2 à 13. Si omis : toutes les lignes.
- `anchor` : cellule coin supérieur gauche du graphique. Si omis : positionné automatiquement.
- `color` : hexadécimal **sans le #** (optionnel).
- `style` : 1 à 48. Recommandés : `10` (sobre), `26` (coloré), `34` (sombre), `42` (pastel).
- `data_sheet` : feuille source si différente de la feuille courante.

---

## 4. Choix du type de graphique

- **Évolution dans le temps** → `line` ou `line_smooth`
- **Comparer des catégories** → `bar` (verticales) ou `bar_h` (si libellés longs)
- **Montrer une composition** → `bar_stacked` ou `pie` (si ≤ 6 catégories)
- **Comparer des proportions** → `bar_percent`
- **Deux variables quantitatives** → `scatter`
- **Profil ou score multi-axes** → `radar`

---

## 5. Positionnement des graphiques

Placer à droite des données pour ne pas les masquer :
- Données en colonnes A–C → ancrer en `E2` ou `F2`
- Plusieurs graphiques sur la même feuille → espacer verticalement : `E2`, `E18`, `E34` (hauteur 12 cm ≈ 16 lignes)

---

## 6. Cas particuliers

### Camembert (`pie` / `doughnut`)
- Maximum **6 catégories** pour la lisibilité.
- **Une seule série** uniquement.
- Activer `show_data_labels: true` pour afficher les pourcentages.

```json
{
  "type": "pie",
  "title": "Répartition du budget",
  "categories_col": 1,
  "series": [{"title": "Budget", "col": 2}],
  "show_legend": true,
  "show_data_labels": true,
  "style": 26
}
```

### Nuage de points (`scatter`)
`categories_col` = axe X (valeurs numériques), `col` dans la série = axe Y.

```json
{
  "type": "scatter",
  "title": "Corrélation prix / quantité",
  "categories_col": 2,
  "series": [{"title": "Quantité vendue", "col": 3}],
  "show_legend": false
}
```

### Feuille tableau de bord (graphiques sans données brutes)
Créer une feuille dédiée avec `headers: []` et `rows: []`, dont les graphiques pointent vers la feuille de données via `data_sheet` :

```json
{
  "sheets": [
    {
      "name": "Données",
      "headers": ["Mois", "CA", "Charges"],
      "rows": [["Jan", 12000, 9000], ["Fév", 15000, 10000]]
    },
    {
      "name": "Tableau de bord",
      "headers": [],
      "rows": [],
      "charts": [
        {
          "type": "line",
          "title": "Évolution CA et Charges",
          "data_sheet": "Données",
          "categories_col": 1,
          "series": [
            {"title": "CA",      "col": 2, "color": "2255A4"},
            {"title": "Charges", "col": 3, "color": "A42222"}
          ],
          "anchor": "B2",
          "width_cm": 20,
          "height_cm": 14
        }
      ]
    }
  ]
}
```

---

## 7. Erreurs fréquentes à éviter

| Erreur | Correction |
|--------|------------|
| Nombres entre guillemets `"100"` | Supprimer les guillemets : `100` |
| `categories_col` qui pointe vers une colonne de valeurs | Vérifier que c'est bien la colonne des libellés |
| `data_rows` qui inclut la ligne d'en-tête | Commencer à `2`, pas à `1` |
| Graphique hors de la zone visible | Augmenter la valeur de ligne dans `anchor` |
| Pie avec plus de 6 catégories | Regrouper les petites catégories en "Autres" |
| Feuille `data_sheet` inexistante | Vérifier l'orthographe exacte du nom de feuille |

---

## 8. Exemple complet : rapport mensuel avec 3 graphiques

```json
{
  "sheets": [
    {
      "name": "Données",
      "headers": ["Mois", "CA (€)", "Charges (€)", "Résultat (€)", "Part marché (%)"],
      "rows": [
        ["Janvier",  42000, 31000, 11000, 18.2],
        ["Février",  38000, 29000,  9000, 17.8],
        ["Mars",     51000, 35000, 16000, 19.1],
        ["Avril",    47000, 33000, 14000, 18.9],
        ["Mai",      55000, 37000, 18000, 20.3],
        ["Juin",     61000, 40000, 21000, 21.1]
      ],
      "charts": [
        {
          "type": "bar",
          "title": "CA et Charges mensuels",
          "categories_col": 1,
          "series": [
            {"title": "CA (€)",      "col": 2, "color": "2255A4"},
            {"title": "Charges (€)", "col": 3, "color": "C0504D"}
          ],
          "anchor": "G2",
          "width_cm": 18,
          "height_cm": 11,
          "style": 10
        },
        {
          "type": "line_smooth",
          "title": "Résultat net mensuel",
          "categories_col": 1,
          "series": [{"title": "Résultat (€)", "col": 4, "color": "4DAF4A"}],
          "anchor": "G20",
          "width_cm": 18,
          "height_cm": 11,
          "show_data_labels": true,
          "style": 10
        },
        {
          "type": "bar_percent",
          "title": "Répartition CA / Charges",
          "categories_col": 1,
          "series": [
            {"title": "CA (€)",      "col": 2, "color": "2255A4"},
            {"title": "Charges (€)", "col": 3, "color": "C0504D"}
          ],
          "anchor": "P2",
          "width_cm": 14,
          "height_cm": 11
        }
      ]
    }
  ]
}
```
