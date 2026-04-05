"""GitHub Action entrypoint for struct-ia.

Analyses only the Python files changed in the current Pull Request.
Expected to run inside a GitHub Actions workflow with the following
environment variables:

  GITHUB_TOKEN        – automatically injected by GitHub Actions
  GITHUB_REPOSITORY   – "owner/repo", e.g. "struct-ai/struct-ai"
  PR_NUMBER           – pull-request number (set from github.event.number)
  GITHUB_WORKSPACE    – absolute path to the checked-out repository root
  STRUCT_IA_FAIL_ON_VIOLATION – set to "false" to disable CI failure on
                                violations (default: "true")

Provider resolution follows the same order as the CLI:
  .struct-ia.yaml 'provider' key > env-var auto-detection
  (OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, MISTRAL_API_KEY, OLLAMA_BASE_URL)
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence

import requests
from loguru import logger

from struct_ai.adapters.ai.mentor_adapter_factory import build_mentor_adapter
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

_GITHUB_API_BASE = "https://api.github.com"

# Marker embedded in every comment so we can identify ours without updating.
# Each run posts a fresh comment (history is preserved intentionally).
_COMMENT_HEADER = "<!-- struct-ia-pr-analysis -->"


def main() -> None:
    """Entry point: analyse PR-changed files and report results."""
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    github_token = os.environ.get("GITHUB_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    pr_number_raw = os.environ.get("PR_NUMBER", "")
    fail_on_violation = (
        os.environ.get("STRUCT_IA_FAIL_ON_VIOLATION", "true").lower() != "false"
    )

    changed_python_files = _get_changed_python_files(workspace)

    if not changed_python_files:
        message = (
            "struct-ia: aucun fichier .py modifié dans cette PR — rien à analyser."
        )
        logger.info(message)
        print(message)
        _post_pr_comment(
            token=github_token,
            repository=repository,
            pr_number=pr_number_raw,
            body=_build_no_files_comment(),
        )
        sys.exit(0)

    config = _load_config(workspace)

    try:
        use_case = _build_use_case(config)
    except (EnvironmentError, ImportError) as error:
        logger.error("Provider configuration error: {error}", error=error)
        print(f"::error::struct-ia — erreur de configuration du provider: {error}")
        sys.exit(1)

    all_results = _run_analysis(use_case, changed_python_files, workspace)

    _emit_annotations(all_results)

    comment_body = _build_pr_comment(all_results, changed_python_files)
    _post_pr_comment(
        token=github_token,
        repository=repository,
        pr_number=pr_number_raw,
        body=comment_body,
    )

    violations_count = len(all_results)
    if violations_count > 0 and fail_on_violation:
        logger.error(
            "{count} violation(s) détectée(s) — CI en échec.", count=violations_count
        )
        sys.exit(1)

    sys.exit(0)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _get_changed_python_files(workspace: Path) -> list[Path]:
    """Return the list of .py files changed in the PR via git diff.

    Compares HEAD against the remote base branch (origin/main by default).
    Falls back to listing all .py files if the diff command fails
    (e.g. in local testing outside a real PR context).
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACM", "origin/main...HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=workspace,
        )
        raw_paths = [
            line.strip() for line in result.stdout.splitlines() if line.strip()
        ]
        python_files = [
            workspace / path
            for path in raw_paths
            if path.endswith(".py") and (workspace / path).is_file()
        ]
        logger.info(
            "{count} fichier(s) .py modifié(s) détecté(s).", count=len(python_files)
        )
        return python_files
    except subprocess.CalledProcessError as error:
        logger.warning(
            "git diff a échoué — fallback sur tous les .py. Erreur: {error}",
            error=error,
        )
        return sorted(workspace.rglob("*.py"))


# ---------------------------------------------------------------------------
# Config & use-case wiring
# ---------------------------------------------------------------------------


def _load_config(project_root: Path) -> StructIaConfig:
    """Load .struct-ia.yaml from project root, fall back to DEFAULT_CONFIG."""
    reader = YamlConfigReader()
    try:
        config = reader.read(project_root)
        logger.info(
            "Configuration chargée depuis {path}", path=project_root / ".struct-ia.yaml"
        )
        return config
    except InvalidConfigError as error:
        logger.error(
            "Fichier de configuration invalide : {detail}", detail=error.detail
        )
        print(f"::error::struct-ia — .struct-ia.yaml invalide: {error.detail}")
        sys.exit(1)
    except Exception:
        logger.warning(
            "Aucun .struct-ia.yaml trouvé dans {root} — règles par défaut utilisées.",
            root=project_root,
        )
        return DEFAULT_CONFIG


def _build_use_case(config: StructIaConfig) -> ReviewCodeUseCase:
    """Wire concrete adapters into ReviewCodeUseCase."""
    source_reader = PathlibSourceFileReader()
    parser = PythonAstAdapter()
    ai_mentor = build_mentor_adapter(config.provider)
    return ReviewCodeUseCase(source_reader, parser, ai_mentor, config)


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def _run_analysis(
    use_case: ReviewCodeUseCase,
    python_files: Sequence[Path],
    base_directory: Path,
) -> list[AnalysisResult]:
    """Run the use case on every file and collect all AnalysisResult objects."""
    all_results: list[AnalysisResult] = []

    for file_path in python_files:
        relative_path = file_path.relative_to(base_directory)
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
                "Erreur inattendue pour {path} : {error}", path=file_path, error=error
            )
            continue

        if results:
            all_results.extend(results)
            logger.info(
                "{path} — {count} violation(s).", path=relative_path, count=len(results)
            )
        else:
            logger.info("{path} — aucune violation.", path=relative_path)

    return all_results


# ---------------------------------------------------------------------------
# GitHub Actions annotations
# ---------------------------------------------------------------------------


def _emit_annotations(results: list[AnalysisResult]) -> None:
    """Print GitHub Actions ::error annotations for each violation.

    These appear as inline annotations in the PR 'Files changed' tab.
    """
    for result in results:
        safe_message = result.mentor_feedback.concept_name.replace("\n", " ").replace(
            "%", "%25"
        )
        print(
            f"::error file={result.file_path},line={result.line_number}"
            f",title=Clean Architecture violation::{safe_message} [{result.rule_violation.value}]"
        )


# ---------------------------------------------------------------------------
# PR comment formatting & posting
# ---------------------------------------------------------------------------


def _build_no_files_comment() -> str:
    return (
        f"{_COMMENT_HEADER}\n"
        "## struct-ia — Analyse architecturale\n\n"
        "> ℹ️ Aucun fichier Python modifié dans cette PR. Rien à analyser."
    )


def _build_pr_comment(
    results: list[AnalysisResult], analyzed_files: Sequence[Path]
) -> str:
    """Build a Markdown summary comment for the PR."""
    file_count = len(analyzed_files)
    violation_count = len(results)

    lines: list[str] = [_COMMENT_HEADER, "## struct-ia — Analyse architecturale\n"]

    if violation_count == 0:
        lines.append(
            f"✅ **Aucune violation détectée** sur {file_count} fichier(s) analysé(s)."
        )
        return "\n".join(lines)

    lines.append(
        f"❌ **{violation_count} violation(s) détectée(s)** sur {file_count} fichier(s) analysé(s).\n"
    )

    for result in results:
        suggestion = result.mentor_feedback
        lines.append(f"---\n### `{result.file_path}` — ligne {result.line_number}")
        lines.append(f"**Règle violée :** `{result.rule_violation.value}`")
        lines.append(f"**Concept :** {suggestion.concept_name}\n")
        lines.append(f"> {suggestion.educational_explanation}\n")
        lines.append("<details><summary>Voir l'exemple de refactoring</summary>\n")
        lines.append(f"**Avant :**\n```python\n{suggestion.code_before}\n```\n")
        lines.append(f"**Après :**\n```python\n{suggestion.code_after}\n```")
        if suggestion.documentation_links:
            links_md = "\n".join(f"- {link}" for link in suggestion.documentation_links)
            lines.append(f"\n**Ressources :**\n{links_md}")
        lines.append("</details>\n")

    return "\n".join(lines)


def _post_pr_comment(token: str, repository: str, pr_number: str, body: str) -> None:
    """Post a comment on the PR via the GitHub REST API.

    Logs a warning and continues without raising when the token or PR number
    is absent (e.g. during local testing).
    """
    if not token or not repository or not pr_number:
        logger.warning(
            "GITHUB_TOKEN, GITHUB_REPOSITORY ou PR_NUMBER manquant — "
            "le commentaire de PR ne sera pas publié."
        )
        return

    url = f"{_GITHUB_API_BASE}/repos/{repository}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        response = requests.post(url, json={"body": body}, headers=headers, timeout=15)
        response.raise_for_status()
        logger.info("Commentaire publié sur la PR #{pr_number}.", pr_number=pr_number)
    except requests.RequestException as error:
        logger.error(
            "Échec de la publication du commentaire GitHub : {error}", error=error
        )


if __name__ == "__main__":
    main()
