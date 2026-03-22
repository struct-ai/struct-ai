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

Install the package in editable mode with **runtime** dependencies:

```bash
pip install --upgrade pip
pip install -e .
```

For **development** (tests, formatting, type-checking), install the `dev` extra so that test dependencies (e.g. `pytest`, `loguru`) are available:

```bash
pip install -e ".[dev]"
```

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

### Testing OpenAI with a real API key

Unit tests mock OpenAI and do not need a key. To call the live API (manual checks, integration experiments), see **[doc/testing-openai.md](doc/testing-openai.md)** — environment variable `OPENAI_API_KEY`, shell loading of `.env.local`, and a minimal Python example.

---

## Project structure

- `src/struct_ai/core/`        — Domain (entities, interfaces, use cases)
- `src/struct_ai/adapters/`    — Infrastructure (parsers, AI, VCS)
- `src/struct_ai/entrypoints/` — CLI, future GitHub Action
- `src/struct_ai/shared/`      — Config, logging
- `tests/`                     — Unit, integration, and e2e tests

See `doc/intro.md` and `doc/structure.md` for product vision and detailed architecture.

---

## Code parser (import analysis)

The project provides a **code parser** that extracts import dependencies from Python source without executing code.

- **Interface** : `CodeParserPort` (`core/interfaces/outputs/code_parser_port.py`) — abstract method `parse_code(code: str) -> List[ImportDependency]`.
- **Implementation** : `PythonAstAdapter` (`adapters/parsers/python_ast_adapter.py`) — uses the standard library `ast` module to walk the AST and collect `import` / `from ... import ...` statements. Each result is an `ImportDependency` with `module_name`, `line_number`, and `names` (imported symbols).
- **Error handling** : Empty or whitespace-only code, or invalid Python syntax, raises `InvalidCodeError`. The exception has a `.log` property with `message` and `lines` for debugging.

**Example**

```python
from struct_ai.adapters.parsers.python_ast_adapter import PythonAstAdapter
from struct_ai.core.exceptions.exceptions import InvalidCodeError

adapter = PythonAstAdapter()
try:
    dependencies = adapter.parse_code("import os\nfrom sys import path\n")
    for dep in dependencies:
        print(dep.module_name, dep.line_number, dep.names)
except InvalidCodeError as e:
    print("Invalid code:", e.log)
```

---

## License

See the `LICENSE` file in the project root.
