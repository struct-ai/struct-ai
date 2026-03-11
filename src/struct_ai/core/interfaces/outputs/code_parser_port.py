from abc import ABC, abstractmethod
from typing import List

from struct_ai.core.entities.imports import ImportDependency


class CodeParserPort(ABC):
    """
    Define the port for the code parser.
    """

    @abstractmethod
    def parse_code(self, code: str) -> List[ImportDependency]:
        """
        Parse the code and return the imports.
        Raises InvalidCodeError if the code is invalid.
        """
        raise NotImplementedError("Subclasses must implement this method.")
