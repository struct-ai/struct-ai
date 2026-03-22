"""
ReviewCodeUseCase: orchestrates the full analysis pipeline.

Wires together CodeParserPort, evaluate_layer_rules, and AIMentorPort
into a single execute() call. No infrastructure dependency is imported here:
all I/O concerns are delegated to the injected ports.
"""

from struct_ai.core.interfaces.ai_mentor_port import AIMentorPort
from struct_ai.core.interfaces.outputs.code_parser_port import CodeParserPort


class ReviewCodeUseCase:
    """
    Central use case that drives the end-to-end Clean Architecture analysis
    for a single Python source file.

    Dependencies are injected at construction time so the class is fully
    testable without hitting the filesystem or the OpenAI API.
    """

    def __init__(self, parser: CodeParserPort, ai_mentor: AIMentorPort) -> None:
        self._parser = parser
        self._ai_mentor = ai_mentor
