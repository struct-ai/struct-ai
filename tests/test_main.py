"""Tests for the CLI analyze command."""

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


def _make_directory_with_py_files(tmp_path: Path) -> Path:
    (tmp_path / "module_a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "module_b.py").write_text("y = 2\n", encoding="utf-8")
    return tmp_path


def _run_with_mock_use_case(directory: Path, side_effects: list[object]) -> Result:
    mock_use_case = MagicMock()
    mock_use_case.execute.side_effect = side_effects
    with patch(
        "struct_ai.entrypoints.cli.main._build_use_case", return_value=mock_use_case
    ):
        return _runner.invoke(app, [str(directory)], catch_exceptions=False)


def describe_analyze_command() -> None:
    def it_exits_with_code_1_when_no_provider_is_configured(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Provider resolution now lives in the factory, not the CLI guard.

        When no API key or provider is available the factory raises
        EnvironmentError which the CLI catches and turns into exit code 1.
        """
        monkeypatch.delenv(_OPENAI_KEY, raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        # Ensure at least one .py file exists so the CLI reaches _build_use_case.
        (tmp_path / "dummy.py").write_text("x = 1\n", encoding="utf-8")
        result = _runner.invoke(app, [str(tmp_path)], catch_exceptions=False)
        assert result.exit_code == 1

    def it_exits_cleanly_when_no_python_files_found(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)
        result = _run_with_mock_use_case(tmp_path, side_effects=[])
        assert result.exit_code == 0
        assert "Aucun fichier .py" in result.output

    def it_exits_cleanly_when_no_violations_detected(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)
        directory = _make_directory_with_py_files(tmp_path)
        result = _run_with_mock_use_case(directory, side_effects=[(), ()])
        assert result.exit_code == 0
        assert "Aucune violation" in result.output

    def it_exits_with_code_1_when_violation_is_detected(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)
        directory = _make_directory_with_py_files(tmp_path)
        result = _run_with_mock_use_case(
            directory, side_effects=[(), (_ANALYSIS_RESULT,)]
        )
        assert result.exit_code == 1
        assert _SUGGESTION.concept_name in result.output
        assert "1 violation(s)" in result.output

    def it_skips_file_on_invalid_code_error(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)
        directory = _make_directory_with_py_files(tmp_path)
        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = [InvalidCodeError("syntax error"), ()]
        with patch(
            "struct_ai.entrypoints.cli.main._build_use_case",
            return_value=mock_use_case,
        ):
            result = _runner.invoke(app, [str(directory)], catch_exceptions=False)
        assert mock_use_case.execute.call_count == 2
        assert result.exit_code == 0

    def it_skips_file_on_ai_mentor_response_error(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)
        directory = _make_directory_with_py_files(tmp_path)
        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = [
            AIMentorResponseError("bad JSON", raw_response="{}"),
            (),
        ]
        with patch(
            "struct_ai.entrypoints.cli.main._build_use_case",
            return_value=mock_use_case,
        ):
            result = _runner.invoke(app, [str(directory)], catch_exceptions=False)
        assert mock_use_case.execute.call_count == 2
        assert result.exit_code == 0

    def it_counts_violations_correctly(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)
        directory = _make_directory_with_py_files(tmp_path)
        result = _run_with_mock_use_case(
            directory, side_effects=[(_ANALYSIS_RESULT,), (_ANALYSIS_RESULT,)]
        )
        assert result.exit_code == 1
        assert "2 violation(s)" in result.output

    def it_fails_when_all_files_are_skipped(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)
        directory = _make_directory_with_py_files(tmp_path)
        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = [
            InvalidCodeError("syntax error"),
            AIMentorResponseError("bad JSON", raw_response="{}"),
        ]
        with patch(
            "struct_ai.entrypoints.cli.main._build_use_case",
            return_value=mock_use_case,
        ):
            result = _runner.invoke(app, [str(directory)], catch_exceptions=False)
        assert result.exit_code == 1
        assert "Aucun fichier analysé" in result.output

    def describe_config_loading() -> None:
        def it_exits_with_code_1_on_invalid_config_file(
            monkeypatch: pytest.MonkeyPatch, tmp_path: Path
        ) -> None:
            monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)
            (tmp_path / ".struct-ia.yaml").write_text(
                "project_package: [\ninvalid", encoding="utf-8"
            )
            result = _runner.invoke(app, [str(tmp_path)], catch_exceptions=False)
            assert result.exit_code == 1

        def it_falls_back_to_default_when_config_file_is_absent(
            monkeypatch: pytest.MonkeyPatch, tmp_path: Path
        ) -> None:
            monkeypatch.setenv(_OPENAI_KEY, _TEST_API_KEY)
            result = _run_with_mock_use_case(tmp_path, side_effects=[])
            assert result.exit_code == 0
