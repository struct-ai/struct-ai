"""Reads and validates a .struct-ia.yaml file at the root of the analyzed project."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from struct_ai.core.entities.config import StructIaConfig
from struct_ai.core.exceptions.exceptions import ConfigNotFoundError, InvalidConfigError
from struct_ai.core.interfaces.inputs.config_reader_port import ConfigReaderPort

_CONFIG_FILENAME = ".struct-ia.yaml"


class YamlConfigReader(ConfigReaderPort):
    """Concrete adapter: reads .struct-ia.yaml with PyYAML and validates with Pydantic."""

    def read(self, project_root: Path) -> StructIaConfig:
        config_path = project_root / _CONFIG_FILENAME

        if not config_path.exists():
            raise ConfigNotFoundError(config_path)

        try:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise InvalidConfigError(
                path=config_path,
                detail=str(error),
            ) from error

        if not isinstance(raw, dict):
            raise InvalidConfigError(
                path=config_path,
                detail="Configuration file must be a YAML mapping at the root level.",
            )

        try:
            return StructIaConfig(**raw)
        except (ValidationError, TypeError) as error:
            raise InvalidConfigError(
                path=config_path,
                detail=str(error),
            ) from error
