# Struct-IA

**Automated architectural mentor** for Pull Requests: detects Clean Architecture violations, explains the rationale, and suggests refactorings (immutability, separation of concerns). Designed to teach Clean Architecture and SOLID principles through pedagogical feedback.

---

## Prerequisites

- **Python 3.12+**
- `pip`

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd struct-ai
```

### 2. Create and activate a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate     # Windows
```

### 3. Install dependencies

The project uses `pyproject.toml` for tooling (Black, isort, mypy). Runtime dependencies are not yet declared in a `[project]` section; install them manually:

```bash
pip install --upgrade pip
pip install pydantic loguru typer
pip install -e .   # installs the struct_ai package in editable mode (once [project] is added)
```

For **development tools** (tests, formatting, type-checking):

```bash
pip install pytest black isort mypy
```

*(Consider adding a `requirements.txt` or a `[project]` section in `pyproject.toml` with these dependencies for a one-command setup.)*

---

## Running the project

### Run tests

```bash
pytest
# or with verbose output
pytest -v
# or a specific directory
pytest tests/unit/
```

### Code quality

```bash
black src/ tests/          # formatting
isort src/ tests/          # import sorting
mypy src/                  # static type-checking (config in pyproject.toml)
```

### CLI (coming soon)

The command-line interface (Typer) will be documented here once the CLI entrypoint is implemented.

---

## Project structure

- `src/struct_ai/core/`        — Domain (entities, interfaces, use cases)
- `src/struct_ai/adapters/`    — Infrastructure (parsers, AI, VCS)
- `src/struct_ai/entrypoints/` — CLI, future GitHub Action
- `src/struct_ai/shared/`      — Config, logging
- `tests/`                     — Unit, integration, and e2e tests

See `doc/intro.md` and `doc/structure.md` for product vision and detailed architecture.

---

## License

See the `LICENSE` file in the project root.
