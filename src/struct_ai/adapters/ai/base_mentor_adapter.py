"""
Shared base class for all AIMentorPort implementations.

Centralises:
- The system prompt (single source of truth)
- The suggest() template method  (build → call → parse)
- _build_user_message()
- _parse_response()

Each concrete adapter only needs to implement:
- __init__() — SDK/credential wiring
- _call_api()  — provider-specific HTTP call, returns the raw text response
- provider_name — short label used in error messages (e.g. "OpenAI", "Anthropic")
"""

import json
from abc import abstractmethod
from typing import Final

from pydantic import ValidationError

from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.entities.suggestion import Suggestion
from struct_ai.core.exceptions.exceptions import AIMentorResponseError
from struct_ai.core.interfaces.ai_mentor_port import AIMentorPort

SYSTEM_PROMPT: Final[str] = """
You are a strict but educational Clean Architecture mentor specialized in Python.
Your sole purpose is to review code that violates a specific architectural rule and
produce a structured, Socratic refactoring suggestion.

Rules you enforce:
- Immutability: domain entities must be frozen (use Pydantic frozen models or dataclasses(frozen=True)).
- Separation of concerns: each module has one responsibility; side effects belong in adapters.
- Layer isolation: domain code (core/) must never import from adapters/ or entrypoints/.
- Dependency Inversion: domain depends on abstractions (ports), never on concrete adapters.

Response format — you MUST reply with a valid JSON object and nothing else:
{
  "concept_name": "<name of the violated principle>",
  "educational_explanation": "<Socratic explanation of why this violates the rule and how to think about it>",
  "code_before": "<the original offending snippet, verbatim>",
  "code_after": "<refactored snippet that respects immutability and separation of concerns>",
  "documentation_links": ["<optional URL>"]
}

Constraints:
- The refactored code in code_after MUST respect immutability (no mutation of shared state).
- Do NOT include markdown fences, prose, or keys outside the JSON schema above.
- If you cannot suggest a safe refactoring, explain why in educational_explanation and
  leave code_after identical to code_before.
""".strip()


class BaseMentorAdapter(AIMentorPort):
    """
    Abstract base class that implements the suggest() template method and all
    provider-agnostic helpers. Concrete subclasses only override _call_api().
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider label used in error messages."""
        ...

    @abstractmethod
    def _call_api(self, user_message: str) -> str:
        """
        Call the provider API with the given user message and return the raw
        text content of the model response.

        Raises:
            AIMentorResponseError: when the provider returns an empty, missing,
                or non-text response.
        """
        ...

    def suggest(self, code_snippet: str, violated_rule: RuleType) -> Suggestion:
        """
        Template method: build message → call provider → parse response.

        Raises:
            AIMentorResponseError: propagated from _call_api or _parse_response.
        """
        user_message = _build_user_message(code_snippet, violated_rule)
        raw_response = self._call_api(user_message)
        return self._parse_response(raw_response)

    def _parse_response(self, raw_response: str) -> Suggestion:
        """Deserialise raw JSON text into a frozen Suggestion entity."""
        cleaned = _strip_markdown_fences(raw_response)

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as error:
            raise AIMentorResponseError(
                f"{self.provider_name} response is not valid JSON: {error}",
                raw_response=raw_response,
            ) from error

        try:
            return Suggestion(**payload)
        except (ValidationError, TypeError) as error:
            raise AIMentorResponseError(
                f"{self.provider_name} response does not match the Suggestion schema: {error}",
                raw_response=raw_response,
            ) from error


# ---------------------------------------------------------------------------
# Module-level pure helpers (no self needed — easier to unit test in isolation)
# ---------------------------------------------------------------------------


def _build_user_message(code_snippet: str, violated_rule: RuleType) -> str:
    return (
        f"The following Python code violates the '{violated_rule.value}' rule:\n\n"
        f"```python\n{code_snippet}\n```\n\n"
        "Provide a structured refactoring suggestion in the JSON format described."
    )


def _strip_markdown_fences(text: str) -> str:
    """Remove optional markdown code fences that some models wrap JSON in."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    return "\n".join(line for line in lines if not line.startswith("```")).strip()
