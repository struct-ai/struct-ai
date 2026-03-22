"""
OpenAI-backed implementation of AIMentorPort.

Responsibilities:
- Inject the offending code snippet and violated rule into a structured prompt.
- Call the OpenAI Chat Completions API (JSON mode).
- Deserialize the raw JSON response into a frozen Suggestion entity.
- Raise AIMentorResponseError when the response is malformed or incomplete.
"""

import json
import os
from typing import Final

from openai import OpenAI
from pydantic import ValidationError

from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.entities.suggestion import Suggestion
from struct_ai.core.exceptions.exceptions import AIMentorResponseError
from struct_ai.core.interfaces.ai_mentor_port import AIMentorPort

# ---------------------------------------------------------------------------
# System prompt — forces the model into a strict architectural mentor persona.
# Immutability and separation of concerns are non-negotiable constraints.
# ---------------------------------------------------------------------------
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

_MODEL: Final[str] = "gpt-4o"
_TEMPERATURE: Final[float] = 0.2  # low temperature for deterministic, precise output


class OpenAIMentorAdapter(AIMentorPort):
    """
    Calls OpenAI's Chat Completions API in JSON mode to generate Socratic
    refactoring suggestions tied to a specific Clean Architecture violation.

    The API key is resolved via the OPENAI_API_KEY environment variable (DI
    through the environment — no hard-coded secrets).
    """

    def __init__(self, api_key: str | None = None) -> None:
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not resolved_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. "
                "Provide it as an environment variable or pass it explicitly."
            )
        self._client = OpenAI(api_key=resolved_key)

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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_user_message(self, code_snippet: str, violated_rule: RuleType) -> str:
        return (
            f"The following Python code violates the '{violated_rule.value}' rule:\n\n"
            f"```python\n{code_snippet}\n```\n\n"
            "Provide a structured refactoring suggestion in the JSON format described."
        )

    def _call_api(self, user_message: str) -> str:
        response = self._client.chat.completions.create(
            model=_MODEL,
            temperature=_TEMPERATURE,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            raise AIMentorResponseError(
                "OpenAI returned an empty response.",
                raw_response=None,
            )
        return content

    def _parse_response(self, raw_response: str) -> Suggestion:
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as error:
            raise AIMentorResponseError(
                f"OpenAI response is not valid JSON: {error}",
                raw_response=raw_response,
            ) from error

        try:
            return Suggestion(**payload)
        except (ValidationError, TypeError) as error:
            raise AIMentorResponseError(
                f"OpenAI response does not match the Suggestion schema: {error}",
                raw_response=raw_response,
            ) from error
