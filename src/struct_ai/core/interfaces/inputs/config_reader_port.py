"""Abstract port for reading local struct-ia configuration."""

from abc import ABC, abstractmethod
from pathlib import Path

from struct_ai.core.entities.config import StructIaConfig


class ConfigReaderPort(ABC):
    """Read and validate the .struct-ia.yaml file at a given project root."""

    @abstractmethod
    def read(self, project_root: Path) -> StructIaConfig:
        """Load and validate the configuration file.

        Args:
            project_root: Root directory of the project being analyzed.

        Returns:
            Validated StructIaConfig.

        Raises:
            ConfigNotFoundError: When .struct-ia.yaml does not exist.
            InvalidConfigError: When the file is malformed or fails validation.
        """
