"""Tests for the GitHub Action entrypoint."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from struct_ai.core.entities.analysis_result import AnalysisResult
from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.entities.suggestion import Suggestion
from struct_ai.core.exceptions.exceptions import AIMentorResponseError, InvalidCodeError
from struct_ai.entrypoints.github_action import main as github_action_module

_SUGGESTION = Suggestion(
    concept_name="Layer Isolation",
    educational_explanation="Domain code must never import from the adapters layer.",
    code_before="from struct_ai.adapters.parsers import python_ast_adapter",
    code_after="from struct_ai.core.interfaces.outputs.code_parser_port import CodeParserPort",
    documentation_links=["https://example.com/clean-arch"],
)

_ANALYSIS_RESULT = AnalysisResult(
    file_path="src/core/domain.py",
    line_number=5,
    rule_violation=RuleType.LAYER_VIOLATION,
    mentor_feedback=_SUGGESTION,
)

_BASE_ENV = {
    "GITHUB_TOKEN": "gh-test-token",
    "GITHUB_REPOSITORY": "owner/repo",
    "PR_NUMBER": "42",
    "STRUCT_IA_FAIL_ON_VIOLATION": "true",
}


# ---------------------------------------------------------------------------
# _get_changed_python_files
# ---------------------------------------------------------------------------


def describe_get_changed_python_files() -> None:
    def it_returns_python_files_from_git_diff(tmp_path: Path) -> None:
        py_file = tmp_path / "module.py"
        py_file.write_text("x = 1\n", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.stdout = "module.py\n"

        with patch("subprocess.run", return_value=mock_result):
            files = github_action_module._get_changed_python_files(tmp_path)

        assert files == [py_file]

    def it_ignores_non_python_files(tmp_path: Path) -> None:
        (tmp_path / "module.py").write_text("x = 1\n", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.stdout = "module.py\nREADME.md\nconfig.yaml\n"

        with patch("subprocess.run", return_value=mock_result):
            files = github_action_module._get_changed_python_files(tmp_path)

        assert all(f.suffix == ".py" for f in files)
        assert len(files) == 1

    def it_falls_back_to_rglob_when_git_diff_fails(tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("", encoding="utf-8")
        (tmp_path / "b.py").write_text("", encoding="utf-8")

        with patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            files = github_action_module._get_changed_python_files(tmp_path)

        assert len(files) == 2
        assert all(f.suffix == ".py" for f in files)

    def it_returns_empty_list_when_no_python_files_changed(tmp_path: Path) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "README.md\n"

        with patch("subprocess.run", return_value=mock_result):
            files = github_action_module._get_changed_python_files(tmp_path)

        assert files == []


# ---------------------------------------------------------------------------
# _build_pr_comment
# ---------------------------------------------------------------------------


def describe_build_pr_comment() -> None:
    def it_contains_success_message_when_no_violations(tmp_path: Path) -> None:
        comment = github_action_module._build_pr_comment([], [tmp_path / "a.py"])
        assert "Aucune violation" in comment
        assert "✅" in comment

    def it_contains_violation_count_when_violations_found(tmp_path: Path) -> None:
        py_file = tmp_path / "core/domain.py"
        comment = github_action_module._build_pr_comment([_ANALYSIS_RESULT], [py_file])
        assert "1 violation(s)" in comment
        assert "❌" in comment

    def it_contains_file_path_and_line_number(tmp_path: Path) -> None:
        py_file = tmp_path / "core/domain.py"
        comment = github_action_module._build_pr_comment([_ANALYSIS_RESULT], [py_file])
        assert "src/core/domain.py" in comment
        assert "ligne 5" in comment

    def it_contains_concept_name(tmp_path: Path) -> None:
        py_file = tmp_path / "core/domain.py"
        comment = github_action_module._build_pr_comment([_ANALYSIS_RESULT], [py_file])
        assert _SUGGESTION.concept_name in comment

    def it_contains_documentation_links_when_present(tmp_path: Path) -> None:
        py_file = tmp_path / "core/domain.py"
        comment = github_action_module._build_pr_comment([_ANALYSIS_RESULT], [py_file])
        assert "https://example.com/clean-arch" in comment

    def it_contains_html_marker(tmp_path: Path) -> None:
        comment = github_action_module._build_pr_comment([], [])
        assert github_action_module._COMMENT_HEADER in comment


def describe_build_no_files_comment() -> None:
    def it_contains_no_files_message() -> None:
        comment = github_action_module._build_no_files_comment()
        assert "Aucun fichier Python" in comment
        assert github_action_module._COMMENT_HEADER in comment


# ---------------------------------------------------------------------------
# _emit_annotations
# ---------------------------------------------------------------------------


def describe_emit_annotations() -> None:
    def it_prints_github_error_annotation(capsys: pytest.CaptureFixture[str]) -> None:
        github_action_module._emit_annotations([_ANALYSIS_RESULT])
        captured = capsys.readouterr()
        assert "::error file=" in captured.out
        assert "src/core/domain.py" in captured.out
        assert "line=5" in captured.out

    def it_prints_nothing_when_no_results(capsys: pytest.CaptureFixture[str]) -> None:
        github_action_module._emit_annotations([])
        captured = capsys.readouterr()
        assert captured.out == ""


# ---------------------------------------------------------------------------
# _post_pr_comment
# ---------------------------------------------------------------------------


def describe_post_pr_comment() -> None:
    def it_skips_posting_when_token_is_missing() -> None:
        with patch("requests.post") as mock_post:
            github_action_module._post_pr_comment(
                token="",
                repository="owner/repo",
                pr_number="42",
                body="hello",
            )
        mock_post.assert_not_called()

    def it_skips_posting_when_repository_is_missing() -> None:
        with patch("requests.post") as mock_post:
            github_action_module._post_pr_comment(
                token="gh-token",
                repository="",
                pr_number="42",
                body="hello",
            )
        mock_post.assert_not_called()

    def it_skips_posting_when_pr_number_is_missing() -> None:
        with patch("requests.post") as mock_post:
            github_action_module._post_pr_comment(
                token="gh-token",
                repository="owner/repo",
                pr_number="",
                body="hello",
            )
        mock_post.assert_not_called()

    def it_posts_comment_to_correct_github_url() -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None

        with patch("requests.post", return_value=mock_response) as mock_post:
            github_action_module._post_pr_comment(
                token="gh-token",
                repository="owner/repo",
                pr_number="42",
                body="hello",
            )

        mock_post.assert_called_once()
        called_url = mock_post.call_args[0][0]
        assert "owner/repo" in called_url
        assert "42" in called_url
        assert called_url.startswith("https://api.github.com")

    def it_uses_bearer_authorization_header() -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None

        with patch("requests.post", return_value=mock_response) as mock_post:
            github_action_module._post_pr_comment(
                token="my-secret-token",
                repository="owner/repo",
                pr_number="1",
                body="hello",
            )

        headers = mock_post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer my-secret-token"


# ---------------------------------------------------------------------------
# _run_analysis
# ---------------------------------------------------------------------------


def describe_run_analysis() -> None:
    def it_returns_empty_list_when_no_violations(tmp_path: Path) -> None:
        py_file = tmp_path / "clean.py"
        py_file.write_text("x = 1\n", encoding="utf-8")

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = ()

        results = github_action_module._run_analysis(mock_use_case, [py_file], tmp_path)
        assert results == []

    def it_collects_violations_from_multiple_files(tmp_path: Path) -> None:
        file_a = tmp_path / "a.py"
        file_b = tmp_path / "b.py"
        file_a.write_text("x = 1\n", encoding="utf-8")
        file_b.write_text("y = 2\n", encoding="utf-8")

        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = [(_ANALYSIS_RESULT,), (_ANALYSIS_RESULT,)]

        results = github_action_module._run_analysis(
            mock_use_case, [file_a, file_b], tmp_path
        )
        assert len(results) == 2

    def it_skips_file_on_invalid_code_error(tmp_path: Path) -> None:
        file_a = tmp_path / "bad.py"
        file_b = tmp_path / "good.py"
        file_a.write_text("???", encoding="utf-8")
        file_b.write_text("x = 1\n", encoding="utf-8")

        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = [InvalidCodeError("syntax error"), ()]

        results = github_action_module._run_analysis(
            mock_use_case, [file_a, file_b], tmp_path
        )
        assert results == []
        assert mock_use_case.execute.call_count == 2

    def it_skips_file_on_ai_mentor_response_error(tmp_path: Path) -> None:
        py_file = tmp_path / "problematic.py"
        py_file.write_text("x = 1\n", encoding="utf-8")

        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = [
            AIMentorResponseError("bad JSON", raw_response="{}")
        ]

        results = github_action_module._run_analysis(mock_use_case, [py_file], tmp_path)
        assert results == []


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------


def describe_main() -> None:
    def it_exits_0_when_no_python_files_changed(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        for key, value in _BASE_ENV.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))

        mock_result = MagicMock()
        mock_result.stdout = "README.md\n"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch(
                "requests.post", return_value=MagicMock(raise_for_status=MagicMock())
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            github_action_module.main()

        assert exc_info.value.code == 0

    def it_exits_0_when_no_violations_found(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        for key, value in _BASE_ENV.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setenv("STRUCT_IA_FAIL_ON_VIOLATION", "true")
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))

        py_file = tmp_path / "clean.py"
        py_file.write_text("x = 1\n", encoding="utf-8")

        mock_git_result = MagicMock()
        mock_git_result.stdout = "clean.py\n"

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = ()

        with (
            patch("subprocess.run", return_value=mock_git_result),
            patch(
                "struct_ai.entrypoints.github_action.main._build_use_case",
                return_value=mock_use_case,
            ),
            patch(
                "requests.post", return_value=MagicMock(raise_for_status=MagicMock())
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            github_action_module.main()

        assert exc_info.value.code == 0

    def it_exits_1_when_violations_found_and_fail_on_violation_is_true(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        for key, value in _BASE_ENV.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setenv("STRUCT_IA_FAIL_ON_VIOLATION", "true")
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))

        py_file = tmp_path / "violating.py"
        py_file.write_text("from adapters import foo\n", encoding="utf-8")

        mock_git_result = MagicMock()
        mock_git_result.stdout = "violating.py\n"

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = (_ANALYSIS_RESULT,)

        with (
            patch("subprocess.run", return_value=mock_git_result),
            patch(
                "struct_ai.entrypoints.github_action.main._build_use_case",
                return_value=mock_use_case,
            ),
            patch(
                "requests.post", return_value=MagicMock(raise_for_status=MagicMock())
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            github_action_module.main()

        assert exc_info.value.code == 1

    def it_exits_0_when_violations_found_but_fail_on_violation_is_false(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        for key, value in _BASE_ENV.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setenv("STRUCT_IA_FAIL_ON_VIOLATION", "false")
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))

        py_file = tmp_path / "violating.py"
        py_file.write_text("from adapters import foo\n", encoding="utf-8")

        mock_git_result = MagicMock()
        mock_git_result.stdout = "violating.py\n"

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = (_ANALYSIS_RESULT,)

        with (
            patch("subprocess.run", return_value=mock_git_result),
            patch(
                "struct_ai.entrypoints.github_action.main._build_use_case",
                return_value=mock_use_case,
            ),
            patch(
                "requests.post", return_value=MagicMock(raise_for_status=MagicMock())
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            github_action_module.main()

        assert exc_info.value.code == 0

    def it_exits_1_when_provider_not_configured(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        for key, value in _BASE_ENV.items():
            monkeypatch.setenv(key, value)
        monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
        for env_var in (
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GOOGLE_API_KEY",
            "MISTRAL_API_KEY",
            "OLLAMA_BASE_URL",
        ):
            monkeypatch.delenv(env_var, raising=False)

        py_file = tmp_path / "module.py"
        py_file.write_text("x = 1\n", encoding="utf-8")

        mock_git_result = MagicMock()
        mock_git_result.stdout = "module.py\n"

        with (
            patch("subprocess.run", return_value=mock_git_result),
            pytest.raises(SystemExit) as exc_info,
        ):
            github_action_module.main()

        assert exc_info.value.code == 1
