struct-ia/
├── .github/                      # CI/CD (GitHub Actions)
│   └── workflows/
│       └── main.yml              # Build, Test, Lint, Deploy (futur action)
├── build/                        # Outils de build (Docker, CI)
├── docs/                         # Documentation (MkDocs ou Sphinx)
├── scripts/                      # Scripts utilitaires (setup, dev, seed data)
├── src/                          # Le code source
│   └── struct_ia/                # Le package Python principal
│       ├── core/                 # LE DOMAINE (Immuable, pas de dépendances infra)
│       │   ├── entities/         # DTOs (Pydantic Models) - (Violation, MentorshipSuggestion)
│       │   ├── exceptions/       # Exceptions spécifiques au domaine
│       │   ├── interfaces/       # Ports d'entrée/sortie (Abstract Base Classes)
│       │   │   ├── inputs/       # Use Cases Interfaces
│       │   │   └── outputs/      # Repositories / AI adapters Interfaces
│       │   │       └── code_parser_port.py  # parse_code(code) -> List[ImportDependency]
│       │   └── use_cases/        # Logique métier pure (Analyzer, FeedbackGenerator)
│       │
│       ├── adapters/             # L'INFRASTRUCTURE (Implémentations des interfaces core)
│       │   ├── ai/               # Implémentations IA (OpenAI, HuggingFace, Ollama)
│       │   ├── parsers/          # Analyse de code (AST, Tree-Sitter, Regex)
│       │   │   └── python_ast_adapter.py  # Extrait les imports Python via ast (stdlib)
│       │   ├── repository/       # Stockage de données (Fichiers, DB, Cache)
│       │   └── vcs/              # Intégration VCS (GitLab, GitHub API)
│       │
│       ├── entrypoints/          # LES INTERFACES (Comment le monde extérieur interagit)
│       │   ├── cli/              # L'interface en ligne de commande (Typer, Click)
│       │   ├── dashboard/        # Future interface Web (FastAPI/Flask) (Optionnel v2)
│       │   └── github_action/    # Code spécifique à l'action GitHub
│       │
│       ├── shared/               # Code utilitaire partagé (Configuration, Loggers)
│       │   ├── config/           # Configuration management (Pydantic Settings)
│       │   └── logging/          # Structured Logging (Loguru)
│       │
│       └── __init__.py           # Point d'entrée du package
│
├── tests/                        # Tests (Pytest)
│   ├── conftest.py               # Fixtures partagées
│   ├── unit/                     # Tests du cœur (Core Use Cases, Entities)
│   ├── integration/              # Tests des adaptateurs (AI, Parsers)
│   └── end_to_end/               # Tests CLI ou Action complets
│
├── .gitignore                    # Fichiers à ignorer par git
├── .pylintrc                     # Configuration Linter (L'ironie...)
├── LICENSE                       # Licence Open Source (ex: Apache 2.0 ou MIT)
├── README.md                     # Documentation principale
├── Makefile                      # Raccourcis pour les commandes (install, test, run)
├── pyproject.toml                # Configuration du projet (Poetry, Pytest, Black, etc.)
└── poetry.lock                   # Verrouillage des dépendances

---

## Code parser (analyse des imports)

- **Port** : `CodeParserPort` (`core/interfaces/outputs/code_parser_port.py`) — méthode `parse_code(code: str) -> List[ImportDependency]`. Le domaine ne dépend que de ce port.
- **Adapter** : `PythonAstAdapter` (`adapters/parsers/python_ast_adapter.py`) — implémentation qui utilise le module standard `ast` pour parcourir l’AST Python et extraire les `import` / `from ... import ...`.
- **Comportement** : Code vide ou uniquement des espaces → lève `InvalidCodeError`. Syntaxe Python invalide → lève `InvalidCodeError` ; l’exception expose un attribut `log` avec `message` et `lines` pour le diagnostic.
- **Dépendances** : uniquement la bibliothèque standard (`ast`), pas de dépendance externe pour le parsing.