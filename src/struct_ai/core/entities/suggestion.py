from pydantic import BaseModel, Field
from typing import List


class Suggestion(BaseModel):
    """
    Define the feedback pedagogical and refactoring.
    object immutable and frozen.
    """

    concept_name: str = Field(
        ..., description="The name of the concept that is violated. (Ex: STR)"
    )
    educational_explanation: str = Field(
        ...,
        description="The why of the concept that is violated. (Ex: Single Responsibility Principle)",
    )
    code_before: str = Field(
        ...,
        description="The code before the refactoring. (Ex: The code that is violating the concept.)",
    )
    code_after: str = Field(
        ...,
        description="The code after the refactoring. (Ex: The code that is refactored to fix the concept violation.)",
    )
    documentation_links: List[str] = Field(default_factory=list)

    model_config = {"frozen": True}
