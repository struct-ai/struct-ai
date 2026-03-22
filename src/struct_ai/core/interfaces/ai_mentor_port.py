"""
Abstract port for the AI mentor.
Any LLM-backed adapter must implement this interface.
"""

from abc import ABC, abstractmethod

from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.entities.suggestion import Suggestion


class AIMentorPort(ABC):
    @abstractmethod
    def suggest(self, code_snippet: str, violated_rule: RuleType) -> Suggestion:
        """
        Generate a Socratic, pedagogical refactoring suggestion for the given
        code snippet that violates the specified Clean Architecture rule.

        Args:
            code_snippet: The raw source code that triggered the violation.
            violated_rule: The rule that was broken (e.g. LAYER_VIOLATION).

        Returns:
            A frozen Suggestion entity with explanation and refactored code.

        Raises:
            AIMentorResponseError: When the LLM response cannot be mapped to
                a valid Suggestion (missing fields, wrong types, etc.).
        """
        raise NotImplementedError
