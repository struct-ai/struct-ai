"""ReviewCodeUseCase: orchestrates the full analysis pipeline.

Wires together SourceFileReaderPort, CodeParserPort, find_first_layer_violation,
and AIMentorPort into a single execute() call. No infrastructure dependency is
imported here: all I/O concerns are delegated to the injected ports.
"""

from typing import Tuple

from struct_ai.core.entities.analysis_result import AnalysisResult
from struct_ai.core.entities.config import DEFAULT_CONFIG, StructIaConfig
from struct_ai.core.interfaces.ai_mentor_port import AIMentorPort
from struct_ai.core.interfaces.inputs.source_file_reader_port import (
    SourceFileReaderPort,
)
from struct_ai.core.interfaces.outputs.code_parser_port import CodeParserPort
from struct_ai.core.use_cases.layer_evaluator import find_first_layer_violation

# Number of source lines provided as context around the violating import line.
_SNIPPET_CONTEXT_LINES = 3


class ReviewCodeUseCase:
    """Central use case that drives the end-to-end Clean Architecture analysis
    for a single Python source file.

    Dependencies are injected at construction time so the class is fully
    testable without hitting the filesystem or the OpenAI API.
    """

    def __init__(
        self,
        source_reader: SourceFileReaderPort,
        parser: CodeParserPort,
        ai_mentor: AIMentorPort,
        config: StructIaConfig = DEFAULT_CONFIG,
    ) -> None:
        self._source_reader = source_reader
        self._parser = parser
        self._ai_mentor = ai_mentor
        self._config = config

    def execute(self, file_path: str) -> Tuple[AnalysisResult, ...]:
        """Run the full analysis pipeline on one Python source file.

        Steps:
          1. Read source code via SourceFileReaderPort.
          2. Parse imports via CodeParserPort.
          3. Evaluate layer rules against the injected config (pure, no I/O).
          4. If a violation is found, call AIMentorPort for a pedagogical suggestion.
          5. Return an immutable tuple of AnalysisResult (empty when no violation).

        Raises:
            FileNotFoundError: When file_path does not exist on disk.
            InvalidCodeError:  When the parser rejects the source (propagated as-is).
            AIMentorResponseError: When the AI response is malformed (propagated as-is).
        """
        source_code = self._source_reader.read_text(file_path)
        imports = self._parser.parse_code(source_code)

        violation = find_first_layer_violation(file_path, imports, self._config)
        if violation is None:
            return ()

        rule_type, offending_import = violation
        code_snippet = self._extract_snippet(source_code, offending_import.line_number)
        suggestion = self._ai_mentor.suggest(code_snippet, rule_type)

        result = AnalysisResult(
            file_path=file_path,
            line_number=offending_import.line_number,
            rule_violation=rule_type,
            mentor_feedback=suggestion,
        )
        return (result,)

    @staticmethod
    def _extract_snippet(source_code: str, line_number: int) -> str:
        """Extract a small window of source lines centred on line_number (1-indexed).

        Provides context for the AI mentor without sending the entire file.
        """
        lines = source_code.splitlines()
        start = max(0, line_number - 1 - _SNIPPET_CONTEXT_LINES)
        end = min(len(lines), line_number + _SNIPPET_CONTEXT_LINES)
        return "\n".join(lines[start:end])
