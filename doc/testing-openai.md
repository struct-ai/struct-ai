# Tester l’API OpenAI avec une clé réelle

Ce guide décrit comment appeler **`OpenAIMentorAdapter`** contre l’API OpenAI (appels réseau, facturation possible). Les tests unitaires (`pytest`) **mockent** le client OpenAI : ils ne consomment pas de quota et n’exigent pas de clé.

---

## Prérequis

- Projet installé en éditable : `pip install -e .` (voir le README).
- Une [clé API OpenAI](https://platform.openai.com/api-keys) avec accès au modèle utilisé par l’adaptateur (**`gpt-4o`**, défini dans `openai_mentor_adapter.py`).
- Variable d’environnement **`OPENAI_API_KEY`** disponible dans le processus Python qui exécute le code.

---

## Fournir la clé (aucun chargement automatique de fichier)

Le package **ne charge pas** de fichier `.env` ou `.env.local` tout seul : seules les variables déjà présentes dans l’environnement du processus sont lues (`os.environ`).

**Option A — exporter dans le terminal (recommandé pour un essai rapide)**

```bash
export OPENAI_API_KEY='sk-...'
```

**Option B — fichier local (ex. `.env.local`)**

Créez un fichier à la racine du dépôt (une ligne par variable, sans guillemets sauf si la valeur en contient) :

```bash
OPENAI_API_KEY=sk-...
```

Puis chargez-le dans **la même session** avant de lancer Python :

```bash
set -a && source .env.local && set +a   # bash / zsh
```

> Le fichier `.env.local` est listé dans `.gitignore` : ne commitez jamais de secrets.

**Option C — secret GitHub Actions**

Pour un workflow futur : définir un secret du dépôt `OPENAI_API_KEY` et l’injecter dans `env:` du job. Même nom de variable que localement.

---

## Appel manuel (REPL ou script ponctuel)

Depuis la racine du dépôt, avec `PYTHONPATH` pointant vers `src` (comme `pytest`), ou après `pip install -e .` :

```bash
cd /chemin/vers/struct-ai
source .venv/bin/activate
export OPENAI_API_KEY='sk-...'   # ou source .env.local comme ci-dessus

python -c "
from struct_ai.adapters.ai.openai_mentor_adapter import OpenAIMentorAdapter
from struct_ai.core.entities.rule_type import RuleType

mentor = OpenAIMentorAdapter()
snippet = '''
from struct_ai.adapters.parsers import python_ast_adapter
'''
suggestion = mentor.suggest(snippet, RuleType.LAYER_VIOLATION)
print(suggestion.model_dump_json(indent=2))
"
```

Vous pouvez aussi passer la clé explicitement (utile pour des tests isolés) :

```python
mentor = OpenAIMentorAdapter(api_key="sk-...")
```

**Erreurs fréquentes**

- `EnvironmentError: OPENAI_API_KEY is not set` → la variable n’est pas visible dans ce shell / ce processus.
- Erreurs HTTP OpenAI (quota, modèle indisponible, clé invalide) → message renvoyé par le SDK ; vérifier le compte et les limites sur le dashboard OpenAI.

---

## Tests automatisés vs appel réel

| Mode | Commande | Clé requise ? |
|------|-----------|----------------|
| Suite unitaire | `pytest` | Non (mocks) |
| Appel réel | REPL / script comme ci-dessus | Oui |

Pour valider uniquement la logique sans réseau, gardez `pytest`.

---

## Coûts et bonnes pratiques

- Chaque exécution appelle l’API Chat Completions (JSON mode) avec le modèle configuré dans le code.
- Limitez les essais en boucle ; préférez des snippets courts.
- Ne partagez pas la clé (logs, captures d’écran, issues publiques).

---

## Entrypoints, résultats d’analyse et « UI »

Aujourd’hui le dépôt ne contient **pas encore** de couche `entrypoints/` (CLI, GitHub Action). Le domaine expose déjà des types stables, par exemple **`AnalysisResult`** (`file_path`, `line_number`, `rule_violation`, `mentor_feedback`), qui agrègent une violation et la **`Suggestion`** du mentor.

Quand vous brancherez le flux complet (analyse → `AnalysisResult`), la **présentation** dépendra du canal — ce sont des « UI » différentes au sens large :

| Canal | Rôle typique |
|--------|----------------|
| **CLI** | Affichage formaté sur la sortie standard (texte, JSON), codes de sortie. |
| **GitHub Action** | Commentaire de PR, résumé du job en Markdown, annotations sur les fichiers : c’est l’interface utilisateur *dans GitHub*. |
| **Application web** (si vous en ajoutez une) | Pages ou API qui consomment les mêmes entités ; ce serait un autre point d’entrée ou un service séparé, pas obligatoirement dans ce dépôt. |

En Clean Architecture, les **entrypoints** orchestrent les cas d’usage et **adaptent** le domaine au monde extérieur : ils ne doivent pas contenir la règle métier, mais c’est bien là qu’on formate un `AnalysisResult` pour un humain (Markdown, HTML, JSON API, etc.). Tant que cette couche n’est pas implémentée, un test réel se fait comme dans la section « Appel manuel », en appelant directement l’adaptateur (ou un futur use case) depuis Python.
