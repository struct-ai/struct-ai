"""
Mistral AI implementation of AIMentorPort.

Requires the optional `mistralai` package:
    pip install "struct-ai[mistral]"

The API key is resolved from the MISTRAL_API_KEY environment variable.
"""

import json
import os
from typing import Final

from pydantic import ValidationError

from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.entities.suggestion import Suggestion
from struct_ai.core.exceptions.exceptions import AIMentorResponseError
from struct_ai.core.interfaces.ai_mentor_port import AIMentorPort

_MODEL: Final[str] = "mistral-large-latest"

_SYSTEM_PROMPT: Final[str] = """
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


class MistralMentorAdapter(AIMentorPort):
    """
    Calls Mistral AI's chat API to generate Socratic refactoring suggestions.

    The API key is resolved via MISTRAL_API_KEY (DI through the environment).
    Requires the optional `mistralai` package.
    """

    def __init__(self, api_key: str | None = None) -> None:
        try:
            from mistralai import Mistral  # noqa: PLC0415
        except ImportError as error:
            raise ImportError(
                "The 'mistralai' package is required for MistralMentorAdapter. "
                "Install it with: pip install 'struct-ai[mistral]'"
            ) from error

        resolved_key = api_key or os.environ.get("MISTRAL_API_KEY")
        if not resolved_key:
            raise EnvironmentError(
                "MISTRAL_API_KEY is not set. "
                "Provide it as an environment variable or pass it explicitly."
            )
        self._client = Mistral(api_key=resolved_key)

    def suggest(self, code_snippet: str, violated_rule: RuleType) -> Suggestion:
        """
        Generate a pedagogical Suggestion for the given violation.

        Raises:
            AIMentorResponseError: when the model returns malformed JSON or a
                payload that does not match the Suggestion schema.
        """
        user_message = self._build_user_message(code_snippet, violated_rule)
        raw_response = self._call_api(user_message)
        return self._parse_response(raw_response)

    def _build_user_message(self, code_snippet: str, violated_rule: RuleType) -> str:
        return (
            f"The following Python code violates the '{violated_rule.value}' rule:\n\n"
            f"```python\n{code_snippet}\n```\n\n"
            "Provide a structured refactoring suggestion in the JSON format described."
        )

    def _call_api(self, user_message: str) -> str:
        response = self._client.chat.complete(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        choices = getattr(response, "choices", None)
        if not choices:
            raise AIMentorResponseError(
                "Mistral returned no completion choices.",
                raw_response=None,
            )
        message = getattr(choices[0], "message", None)
        if message is None:
            raise AIMentorResponseError(
                "Mistral completion has no message.",
                raw_response=None,
            )
        content = getattr(message, "content", None)
        if not content or not isinstance(content, str):
            raise AIMentorResponseError(
                "Mistral returned an empty or non-text response.",
                raw_response=None,
            )
        return content

    def _parse_response(self, raw_response: str) -> Suggestion:
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as error:
            raise AIMentorResponseError(
                f"Mistral response is not valid JSON: {error}",
                raw_response=raw_response,
            ) from error

        try:
            return Suggestion(**payload)
        except (ValidationError, TypeError) as error:
            raise AIMentorResponseError(
                f"Mistral response does not match the Suggestion schema: {error}",
                raw_response=raw_response,
            ) from error
