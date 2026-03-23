"""
Unit tests for the CLI analyze command.

All infrastructure calls (filesystem I/O, AST parsing, OpenAI) are eliminated
via patch. The Typer CliRunner is used to invoke the command as a real user would.

Note: struct-ia is a single-command Typer app, so args are passed directly
without a subcommand prefix (e.g. [str(directory)], not ["analyze", str(directory)]).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import Result
from typer.testing import CliRunner

from struct_ai.core.entities.analysis_result import AnalysisResult
from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.entities.suggestion import Suggestion
from struct_ai.core.exceptions.exceptions import AIMentorResponseError, InvalidCodeError
from struct_ai.entrypoints.cli.main import app

_runner = CliRunner()

_SUGGESTION = Suggestion(
    concept_name="Layer Isolation",
    educational_explanation="Domain code must never import from the adapters layer.",
    code_before="from struct_ai.adapters.parsers import python_ast_adapter",
    code_after="from struct_ai.core.interfaces.outputs.code_parser_port import CodeParserPort",
    documentation_links=["https://example.com/clean-arch"],
)

_ANALYSIS_RESULT = AnalysisResult(
    file_path="some/path/foo.py",
    line_number=3,
    rule_violation=RuleType.LAYER_VIOLATION,
    mentor_feedback=_SUGGESTION,
)

_OPENAI_KEY = "OPENAI_API_KEY"
_TEST_API_KEY = "sk-test-key"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def directory_with_python_files(tmp_path: Path) -> Path:
    """Temporary directory containing two minimal .py stub files."""
    (tmp_path / "module_a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "module_b.py").write_text("y = 2\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def empty_directory(tmp_path: Path) -> Path:
    """Temporary directory with no .py files."""
    return tmp_path


# ---------------------------------------------------------------------------
# Helper: invoke analyze with a fully mocked use case
# ---------------------------------------------------------------------------


def _run_with_mock_use_case(
    directory: Path,
    side_effects: list[object],
) -> Result:
    """
    Invoke `analyze <directory>` with ReviewCodeUseCase fully mocked.

    side_effects: return values (or exceptions) for successive execute() calls,
                  one entry per .py file in directory (sorted order).
    Assumes OPENAI_API_KEY is already set in the environment by the calling test.
    """
    mock_use_case = MagicMock()
    mock_use_case.execute.side_effect = side_effects

    with patch(
        "struct_ai.entrypoints.cli.main._build_use_case", return_value=mock_use_case
    ):
        return _runner.invoke(app, [str(directory)], catch_exceptions=False)


# ---------------------------------------------------------------------------
# Scenario 1: OPENAI_API_KEY absent → exit code 1, explicit error message
# ---------------------------------------------------------------------------


def test_analyze_exits_when_api_key_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    empty_directory: Path,
) -> None:
    """CLI must print an error and exit with code 1 when OPENAI_API_KEY is absent."""
    monkeypatch.delenv(_OPENAI_KEY, raising=False)

    with patch("struct_ai.entrypoints.cli.main.logger.error") as mock_error:
        result = _runner.invoke(
            app,
            [str(empty_directory)],
            catch_exceptions=False,
        )

    assert result.exit_code == 1
    assert _OPENAI_KEY in result.output
    assert mock_error.called
    assert any(_OPENAI_KEY in str(call.args[0]) for call in mock_error.call_args_list)


# ---------------------------------------------------------------------------
# Scenario 2: no .py files → exit code 0, informational message
# ---------------------------------------------------------------------------


def test_analyze_exits_cleanly_when_no_python_files_found(
    monkeypatch: pytest.MonkeyPatch,
    empty_directory: Path,
) -> None:
    """An empty directory should produce an informational message and exit 0."""
    monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)

    result = _run_with_mock_use_case(empty_directory, side_effects=[])

    assert result.exit_code == 0
    assert "Aucun fichier .py" in result.output


# ---------------------------------------------------------------------------
# Scenario 3: files with no violations → exit code 0
# ---------------------------------------------------------------------------


def test_analyze_exits_cleanly_when_no_violations_detected(
    monkeypatch: pytest.MonkeyPatch,
    directory_with_python_files: Path,
) -> None:
    """All files clean → exit code 0 with a no-violations summary."""
    monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)

    # Two files, both clean
    result = _run_with_mock_use_case(directory_with_python_files, side_effects=[(), ()])

    assert result.exit_code == 0
    assert "Aucune violation" in result.output


# ---------------------------------------------------------------------------
# Scenario 4: violation detected → exit code 1, violation output present
# ---------------------------------------------------------------------------


def test_analyze_exits_with_error_when_violation_detected(
    monkeypatch: pytest.MonkeyPatch,
    directory_with_python_files: Path,
) -> None:
    """A violation in any file should produce feedback panels and exit code 1."""
    monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)

    # First file clean, second has a violation
    result = _run_with_mock_use_case(
        directory_with_python_files,
        side_effects=[(), (_ANALYSIS_RESULT,)],
    )

    assert result.exit_code == 1
    assert _SUGGESTION.concept_name in result.output
    assert "1 violation(s)" in result.output


# ---------------------------------------------------------------------------
# Scenario 5: InvalidCodeError → file skipped, analysis continues
# ---------------------------------------------------------------------------


def test_analyze_skips_file_on_invalid_code_error(
    monkeypatch: pytest.MonkeyPatch,
    directory_with_python_files: Path,
) -> None:
    """A file raising InvalidCodeError must be skipped; other files still processed."""
    monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)

    mock_use_case = MagicMock()
    mock_use_case.execute.side_effect = [
        InvalidCodeError("syntax error"),
        (),  # second file is clean
    ]

    with patch(
        "struct_ai.entrypoints.cli.main._build_use_case", return_value=mock_use_case
    ):
        result = _runner.invoke(
            app,
            [str(directory_with_python_files)],
            catch_exceptions=False,
        )

    assert mock_use_case.execute.call_count == 2
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Scenario 6: AIMentorResponseError → file skipped, analysis continues
# ---------------------------------------------------------------------------


def test_analyze_skips_file_on_ai_mentor_response_error(
    monkeypatch: pytest.MonkeyPatch,
    directory_with_python_files: Path,
) -> None:
    """A file raising AIMentorResponseError must be skipped gracefully."""
    monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)

    mock_use_case = MagicMock()
    mock_use_case.execute.side_effect = [
        AIMentorResponseError("bad JSON", raw_response="{}"),
        (),
    ]

    with patch(
        "struct_ai.entrypoints.cli.main._build_use_case", return_value=mock_use_case
    ):
        result = _runner.invoke(
            app,
            [str(directory_with_python_files)],
            catch_exceptions=False,
        )

    assert mock_use_case.execute.call_count == 2
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Scenario 7: violation count matches the number of AnalysisResult objects
# ---------------------------------------------------------------------------


def test_analyze_counts_violations_correctly(
    monkeypatch: pytest.MonkeyPatch,
    directory_with_python_files: Path,
) -> None:
    """The summary must report the exact number of violations returned by the use case."""
    monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)

    # Both files have one violation each → 2 total
    result = _run_with_mock_use_case(
        directory_with_python_files,
        side_effects=[(_ANALYSIS_RESULT,), (_ANALYSIS_RESULT,)],
    )

    assert result.exit_code == 1
    assert "2 violation(s)" in result.output


# ---------------------------------------------------------------------------
# Scenario 8: all files skipped due to errors → fail with no false confidence
# ---------------------------------------------------------------------------


def test_analyze_fails_when_all_files_are_skipped(
    monkeypatch: pytest.MonkeyPatch,
    directory_with_python_files: Path,
) -> None:
    """If every file is ignored due to errors, exit code must be 1."""
    monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)

    mock_use_case = MagicMock()
    mock_use_case.execute.side_effect = [
        InvalidCodeError("syntax error"),
        AIMentorResponseError("bad JSON", raw_response="{}"),
    ]

    with patch(
        "struct_ai.entrypoints.cli.main._build_use_case", return_value=mock_use_case
    ):
        result = _runner.invoke(
            app,
            [str(directory_with_python_files)],
            catch_exceptions=False,
        )

    assert mock_use_case.execute.call_count == 2
    assert result.exit_code == 1
    assert "Aucun fichier analysé" in result.output
    assert "Aucune violation détectée" not in result.output
