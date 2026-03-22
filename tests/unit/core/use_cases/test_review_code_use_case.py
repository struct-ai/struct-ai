"""
Unit tests for ReviewCodeUseCase.

All I/O is eliminated: SourceFileReaderPort, CodeParserPort, and AIMentorPort
are replaced by MagicMock instances. No real file reads and no network calls.
"""

from unittest.mock import MagicMock

import pytest

from struct_ai.core.entities.analysis_result import AnalysisResult
from struct_ai.core.entities.imports import ImportDependency
from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.entities.suggestion import Suggestion
from struct_ai.core.exceptions.exceptions import AIMentorResponseError, InvalidCodeError
from struct_ai.core.use_cases.review_code_use_case import ReviewCodeUseCase

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

_FILE_PATH = "struct_ai/core/entities/foo.py"
_SOURCE_CODE = (
    "import os\nfrom struct_ai.adapters.parsers import python_ast_adapter\nx = 1\n"
)

_VIOLATING_IMPORT = ImportDependency(
    module_name="struct_ai.adapters.parsers.python_ast_adapter",
    line_number=2,
    names=["python_ast_adapter"],
)

_CLEAN_IMPORT = ImportDependency(
    module_name="os",
    line_number=1,
    names=["os"],
)

_SUGGESTION = Suggestion(
    concept_name="Layer Isolation",
    educational_explanation="Domain must not depend on Infrastructure.",
    code_before="from struct_ai.adapters.parsers import python_ast_adapter",
    code_after="from struct_ai.core.interfaces.outputs.code_parser_port import CodeParserPort",
    documentation_links=[],
)


def _make_use_case(
    parser_imports: list[ImportDependency] | None = None,
    suggestion: Suggestion | None = None,
) -> tuple[ReviewCodeUseCase, MagicMock, MagicMock, MagicMock]:
    """
    Build a ReviewCodeUseCase with mocked source reader, parser, and AI mentor.
    Returns (use_case, mock_source_reader, mock_parser, mock_ai_mentor).
    """
    mock_source_reader = MagicMock()
    mock_source_reader.read_text.return_value = _SOURCE_CODE

    mock_parser = MagicMock()
    mock_parser.parse_code.return_value = parser_imports or []

    mock_ai_mentor = MagicMock()
    if suggestion is not None:
        mock_ai_mentor.suggest.return_value = suggestion

    return (
        ReviewCodeUseCase(mock_source_reader, mock_parser, mock_ai_mentor),
        mock_source_reader,
        mock_parser,
        mock_ai_mentor,
    )


# ---------------------------------------------------------------------------
# Scenario 1: valid file, no violation → empty tuple
# ---------------------------------------------------------------------------


def test_execute_returns_empty_tuple_when_no_violation() -> None:
    """No layer violation → execute() returns ()."""
    use_case, _, mock_parser, mock_ai_mentor = _make_use_case(
        parser_imports=[_CLEAN_IMPORT]
    )

    result = use_case.execute(_FILE_PATH)

    assert result == ()
    mock_ai_mentor.suggest.assert_not_called()
    mock_parser.parse_code.assert_called_once()


# ---------------------------------------------------------------------------
# Scenario 2: valid file, violation detected → AI called → AnalysisResult
# ---------------------------------------------------------------------------


def test_execute_returns_analysis_result_when_violation_detected() -> None:
    """Layer violation → AI is called → a single AnalysisResult is returned."""
    use_case, _, _, _ = _make_use_case(
        parser_imports=[_VIOLATING_IMPORT],
        suggestion=_SUGGESTION,
    )

    result = use_case.execute(_FILE_PATH)

    assert len(result) == 1
    analysis = result[0]
    assert isinstance(analysis, AnalysisResult)
    assert analysis.file_path == _FILE_PATH
    assert analysis.line_number == _VIOLATING_IMPORT.line_number
    assert analysis.rule_violation == RuleType.LAYER_VIOLATION
    assert analysis.mentor_feedback == _SUGGESTION


# ---------------------------------------------------------------------------
# Scenario 3: result is an immutable tuple
# ---------------------------------------------------------------------------


def test_execute_result_is_immutable_tuple() -> None:
    """Return value must be a tuple (frozen / immutable by construction)."""
    use_case, _, _, _ = _make_use_case(parser_imports=[_CLEAN_IMPORT])

    result = use_case.execute(_FILE_PATH)

    assert isinstance(result, tuple)


# ---------------------------------------------------------------------------
# Scenario 4: file not found → FileNotFoundError propagated
# ---------------------------------------------------------------------------


def test_execute_raises_file_not_found_when_path_missing() -> None:
    """FileNotFoundError from SourceFileReaderPort is not swallowed."""
    use_case, mock_source_reader, _, _ = _make_use_case()
    mock_source_reader.read_text.side_effect = FileNotFoundError("no such file")

    with pytest.raises(FileNotFoundError):
        use_case.execute(_FILE_PATH)


# ---------------------------------------------------------------------------
# Scenario 5: parser raises InvalidCodeError → propagated
# ---------------------------------------------------------------------------


def test_execute_propagates_invalid_code_error() -> None:
    """InvalidCodeError from the parser is not swallowed."""
    use_case, _, mock_parser, _ = _make_use_case()
    mock_parser.parse_code.side_effect = InvalidCodeError("syntax error")

    with pytest.raises(InvalidCodeError):
        use_case.execute(_FILE_PATH)


# ---------------------------------------------------------------------------
# Scenario 6: AI raises AIMentorResponseError → propagated
# ---------------------------------------------------------------------------


def test_execute_propagates_ai_mentor_response_error() -> None:
    """AIMentorResponseError from the AI mentor is not swallowed."""
    use_case, _, _, mock_ai_mentor = _make_use_case(
        parser_imports=[_VIOLATING_IMPORT]
    )
    mock_ai_mentor.suggest.side_effect = AIMentorResponseError(
        "bad response", raw_response="{}"
    )

    with pytest.raises(AIMentorResponseError):
        use_case.execute(_FILE_PATH)


# ---------------------------------------------------------------------------
# Scenario 7: parser is called with the correct source code
# ---------------------------------------------------------------------------


def test_execute_calls_parser_with_correct_source_code() -> None:
    """The parser must receive the exact source code from SourceFileReaderPort."""
    use_case, _, mock_parser, _ = _make_use_case(parser_imports=[_CLEAN_IMPORT])

    use_case.execute(_FILE_PATH)

    mock_parser.parse_code.assert_called_once_with(_SOURCE_CODE)


# ---------------------------------------------------------------------------
# Scenario 8 (bonus): AI is NOT called when there is no violation
# ---------------------------------------------------------------------------


def test_execute_does_not_call_ai_when_no_violation() -> None:
    """AI mentor must never be invoked when no rule is violated."""
    use_case, _, _, mock_ai_mentor = _make_use_case(parser_imports=[_CLEAN_IMPORT])

    use_case.execute(_FILE_PATH)

    mock_ai_mentor.suggest.assert_not_called()


# ---------------------------------------------------------------------------
# Scenario 9: source reader receives the requested path
# ---------------------------------------------------------------------------


def test_execute_calls_source_reader_with_file_path() -> None:
    """SourceFileReaderPort.read_text must be invoked with execute()'s path."""
    use_case, mock_source_reader, _, _ = _make_use_case(parser_imports=[_CLEAN_IMPORT])

    use_case.execute(_FILE_PATH)

    mock_source_reader.read_text.assert_called_once_with(_FILE_PATH)
