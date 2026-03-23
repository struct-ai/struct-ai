"""CLI entrypoint for struct-ia.

Exposes the `analyze` command which recursively traverses a directory,
runs ReviewCodeUseCase on every .py file, and renders educational
feedback via Rich panels when a Clean Architecture violation is detected.

Usage:
    struct-ia analyze <path_to_directory>
"""

import os
from pathlib import Path
from typing import Tuple

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from struct_ai.adapters.ai.openai_mentor_adapter import OpenAIMentorAdapter
from struct_ai.adapters.config.yaml_config_reader import YamlConfigReader
from struct_ai.adapters.io.pathlib_source_file_reader import PathlibSourceFileReader
from struct_ai.adapters.parsers.python_ast_adapter import PythonAstAdapter
from struct_ai.core.entities.analysis_result import AnalysisResult
from struct_ai.core.entities.config import DEFAULT_CONFIG, StructIaConfig
from struct_ai.core.exceptions.exceptions import (
    AIMentorResponseError,
    InvalidCodeError,
    InvalidConfigError,
)
from struct_ai.core.use_cases.review_code_use_case import ReviewCodeUseCase

app = typer.Typer(
    name="struct-ia",
    help="Analyse les violations d'architecture Clean dans votre code Python.",
    no_args_is_help=True,
)

_console = Console()


@app.command()
def analyze(
    directory: Path = typer.Argument(
        ...,
        help="Chemin du répertoire à analyser récursivement.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        resolve_path=True,
    ),
) -> None:
    """Analyse récursivement tous les fichiers .py dans le répertoire cible.

    Détecte les violations d'architecture Clean et fournit des suggestions
    pédagogiques générées par l'IA pour chaque fichier concerné.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("Environment variable OPENAI_API_KEY is not set.")
        _console.print(
            "[bold red]Erreur :[/bold red] La variable d'environnement "
            "[bold]OPENAI_API_KEY[/bold] n'est pas définie.\n"
            "Définissez-la avec : [italic]export OPENAI_API_KEY=sk-...[/italic]"
        )
        raise typer.Exit(code=1)

    config = _load_config(directory)

    python_files = sorted(directory.rglob("*.py"))

    if not python_files:
        _console.print(
            f"[yellow]Aucun fichier .py trouvé dans[/yellow] [bold]{directory}[/bold]"
        )
        raise typer.Exit(code=0)

    _console.print(
        f"\n[bold cyan]struct-ia[/bold cyan] — Analyse de "
        f"[bold]{len(python_files)}[/bold] fichier(s) dans [bold]{directory}[/bold]\n"
    )

    use_case = _build_use_case(config)
    violations_found, analyzed_files = _run_analysis(
        use_case,
        python_files,
        directory,
    )
    _display_summary(len(python_files), analyzed_files, violations_found)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _load_config(project_root: Path) -> StructIaConfig:
    """Discover and load .struct-ia.yaml at the project root.

    Falls back to DEFAULT_CONFIG and logs a warning when the file is absent.
    Exits with code 1 and an explicit error log when the file is malformed.
    """
    reader = YamlConfigReader()
    try:
        config = reader.read(project_root)
        logger.info(
            "Configuration chargée depuis {path}",
            path=project_root / ".struct-ia.yaml",
        )
        return config
    except InvalidConfigError as error:
        logger.error(
            "Fichier de configuration invalide : {detail}", detail=error.detail
        )
        _console.print(
            "[bold red]Erreur :[/bold red] Le fichier .struct-ia.yaml est invalide.\n"
            f"{error.detail}"
        )
        raise typer.Exit(code=1) from error
    except Exception:  # ConfigNotFoundError and anything unexpected
        logger.warning(
            "Aucun fichier .struct-ia.yaml trouvé dans {root}. "
            "Les règles par défaut sont utilisées. "
            "Créez-en un en plaçant un .struct-ia.yaml à la racine du projet.",
            root=project_root,
        )
        return DEFAULT_CONFIG


def _build_use_case(config: StructIaConfig = DEFAULT_CONFIG) -> ReviewCodeUseCase:
    """Instantiate concrete adapters and wire them into ReviewCodeUseCase."""
    source_reader = PathlibSourceFileReader()
    parser = PythonAstAdapter()
    ai_mentor = OpenAIMentorAdapter()
    return ReviewCodeUseCase(source_reader, parser, ai_mentor, config)


def _run_analysis(
    use_case: ReviewCodeUseCase,
    python_files: list[Path],
    base_directory: Path,
) -> Tuple[int, int]:
    """Iterate over python_files, execute the use case, and render results.

    Returns a tuple: (violations_found, analyzed_files).

    analyzed_files counts the number of files where ``use_case.execute(...)``
    completed successfully (even if it returned zero violations).

    Skips files that raise InvalidCodeError or AIMentorResponseError,
    logging a warning or error respectively.
    """
    violations_found = 0
    analyzed_files = 0

    for file_path in python_files:
        relative_path = file_path.relative_to(base_directory)
        results: Tuple[AnalysisResult, ...]

        try:
            results = use_case.execute(str(file_path))
        except InvalidCodeError as error:
            logger.warning(
                "Fichier ignoré (code invalide) : {path} — {log}",
                path=file_path,
                log=error.log,
            )
            continue
        except AIMentorResponseError as error:
            logger.error(
                "Réponse IA malformée pour {path} : {error}",
                path=file_path,
                error=error,
            )
            continue
        except Exception as error:  # noqa: BLE001
            logger.error(
                "Erreur inattendue pour {path} : {error}",
                path=file_path,
                error=error,
            )
            continue

        analyzed_files += 1

        if not results:
            _console.print(f"  [green]✓[/green] {relative_path}")
            continue

        for result in results:
            violations_found += 1
            _display_violation(result, relative_path)

    return violations_found, analyzed_files


def _display_violation(result: AnalysisResult, relative_path: Path) -> None:
    """Render a single AnalysisResult as Rich panels in the terminal."""
    suggestion = result.mentor_feedback

    header = Text()
    header.append("  ✗ ", style="bold red")
    header.append(str(relative_path), style="bold white")
    header.append(f"  ligne {result.line_number}", style="dim")
    header.append(f"  [{result.rule_violation.value}]", style="bold yellow")
    _console.print(header)

    _console.print(
        Panel(
            suggestion.educational_explanation,
            title=f"[bold yellow]{suggestion.concept_name}[/bold yellow]",
            border_style="yellow",
            expand=False,
        )
    )
    _console.print(
        Panel(
            Syntax(
                suggestion.code_before,
                "python",
                theme="monokai",
                line_numbers=True,
            ),
            title="[red]Avant[/red]",
            border_style="red",
            expand=False,
        )
    )
    _console.print(
        Panel(
            Syntax(
                suggestion.code_after,
                "python",
                theme="monokai",
                line_numbers=True,
            ),
            title="[green]Après[/green]",
            border_style="green",
            expand=False,
        )
    )

    if suggestion.documentation_links:
        links = "\n".join(f"  • {link}" for link in suggestion.documentation_links)
        _console.print(f"[dim]Ressources :[/dim]\n{links}")

    _console.print()


def _display_summary(
    discovered_files: int, analyzed_files: int, violations_found: int
) -> None:
    """Print a final summary line and exit with code 1 when needed."""
    skipped_files = discovered_files - analyzed_files

    if analyzed_files == 0:
        _console.print(
            f"\n[bold red]✗ Aucun fichier analysé[/bold red] "
            f"({discovered_files} fichier(s) ignoré(s) à cause d'erreurs)"
        )
        raise typer.Exit(code=1)

    skipped_suffix = f" (et {skipped_files} ignoré(s))" if skipped_files > 0 else ""

    if violations_found == 0:
        _console.print(
            f"\n[bold green]✓ Aucune violation détectée[/bold green] "
            f"({analyzed_files} fichier(s) analysé(s)){skipped_suffix}"
        )
        return

    _console.print(
        f"\n[bold red]✗ {violations_found} violation(s) détectée(s)[/bold red] "
        f"sur {analyzed_files} fichier(s) analysé(s){skipped_suffix}"
    )
    raise typer.Exit(code=1)
