from pydantic import BaseModel, Field
from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.entities.suggestion import Suggestion


class AnalysisResult(BaseModel):
    """
    Define the result of the analysis of a file.
    """

    file_path: str = Field(..., description="The path of the file that was analyzed.")
    line_number: int = Field(
        ..., description="The line number of the code that was violated."
    )
    rule_violation: RuleType = Field(..., description="The rule that was violated.")
    mentor_feedback: Suggestion = Field(..., description="The feedback of the mentor.")

    model_config = {"frozen": True}
