"""Tests for YamlConfigReader."""

from pathlib import Path

import pytest

from struct_ai.adapters.config.yaml_config_reader import YamlConfigReader
from struct_ai.core.exceptions.exceptions import ConfigNotFoundError, InvalidConfigError

_VALID_YAML = """\
project_package: my_app
layers:
  - name: domain
    paths:
      - core
  - name: infrastructure
    paths:
      - adapters
  - name: entrypoints
    paths:
      - entrypoints
"""


def describe_YamlConfigReader() -> None:
    def describe_read() -> None:
        def it_parses_a_valid_config_file(tmp_path: Path) -> None:
            (tmp_path / ".struct-ia.yaml").write_text(_VALID_YAML, encoding="utf-8")
            config = YamlConfigReader().read(tmp_path)
            assert config.project_package == "my_app"
            assert len(config.layers) == 3
            assert config.layers[0].name == "domain"
            assert config.layers[0].paths == ["core"]
            assert config.layers[1].name == "infrastructure"
            assert config.layers[2].name == "entrypoints"

        def it_raises_config_not_found_when_file_is_absent(tmp_path: Path) -> None:
            with pytest.raises(ConfigNotFoundError):
                YamlConfigReader().read(tmp_path)

        def it_raises_invalid_config_on_malformed_yaml(tmp_path: Path) -> None:
            (tmp_path / ".struct-ia.yaml").write_text(
                "project_package: [\ninvalid yaml", encoding="utf-8"
            )
            with pytest.raises(InvalidConfigError) as exc_info:
                YamlConfigReader().read(tmp_path)
            assert exc_info.value.path == tmp_path / ".struct-ia.yaml"

        def it_raises_invalid_config_when_yaml_is_not_a_mapping(
            tmp_path: Path,
        ) -> None:
            (tmp_path / ".struct-ia.yaml").write_text(
                "- just\n- a\n- list\n", encoding="utf-8"
            )
            with pytest.raises(InvalidConfigError):
                YamlConfigReader().read(tmp_path)

        def it_raises_invalid_config_when_required_fields_are_missing(
            tmp_path: Path,
        ) -> None:
            (tmp_path / ".struct-ia.yaml").write_text(
                "project_package: my_app\n", encoding="utf-8"
            )
            with pytest.raises(InvalidConfigError):
                YamlConfigReader().read(tmp_path)

        def it_raises_invalid_config_when_layers_list_is_empty(
            tmp_path: Path,
        ) -> None:
            yaml_content = "project_package: my_app\nlayers: []\n"
            (tmp_path / ".struct-ia.yaml").write_text(yaml_content, encoding="utf-8")
            with pytest.raises(InvalidConfigError):
                YamlConfigReader().read(tmp_path)

        def it_produces_a_frozen_immutable_config(tmp_path: Path) -> None:
            (tmp_path / ".struct-ia.yaml").write_text(_VALID_YAML, encoding="utf-8")
            config = YamlConfigReader().read(tmp_path)
            with pytest.raises(Exception):
                config.project_package = "other"  # Pydantic frozen model raises at runtime
