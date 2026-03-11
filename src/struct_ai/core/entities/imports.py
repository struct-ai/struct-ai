from typing import List

from pydantic import BaseModel, Field


class ImportDependency(BaseModel):
    """
    Define the dependency of a import.
    """

    module_name: str = Field(
        ..., description="The name of the module that is imported."
    )
    line_number: int = Field(..., description="The line number of the import.")
    names: List[str] = Field(..., description="The names of the imported objects.")
