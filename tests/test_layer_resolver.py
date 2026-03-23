"""Tests for layer path and import resolution."""

from struct_ai.core.entities.config import (
    LayerConfig,
    StructIaConfig,
)
from struct_ai.core.use_cases.layer_resolver import (
    path_to_layer,
    resolved_import_path_to_layer,
)

_DOMAIN_LEVEL = 0
_INFRA_LEVEL = 1
_ENTRYPOINTS_LEVEL = 2


def describe_path_to_layer() -> None:
    def it_maps_core_to_domain() -> None:
        assert path_to_layer("struct_ai/core/entities/foo.py") == _DOMAIN_LEVEL

    def it_maps_adapters_to_infrastructure() -> None:
        assert path_to_layer("struct_ai/adapters/parsers/foo.py") == _INFRA_LEVEL

    def it_maps_entrypoints_to_entrypoints() -> None:
        assert path_to_layer("struct_ai/entrypoints/cli/main.py") == _ENTRYPOINTS_LEVEL

    def it_ignores_parent_dirs_named_adapters() -> None:
        path = "/home/user/adapters/work/src/struct_ai/core/entities/foo.py"
        assert path_to_layer(path) == _DOMAIN_LEVEL

    def it_ignores_parent_dirs_named_core() -> None:
        path = "/home/core_user/projects/src/struct_ai/adapters/parsers/foo.py"
        assert path_to_layer(path) == _INFRA_LEVEL

    def it_returns_none_when_package_missing() -> None:
        assert path_to_layer("some/other/package/foo.py") is None
        assert path_to_layer("vendor/core/utils.py") is None

    def it_returns_none_when_layer_not_immediate_child() -> None:
        assert path_to_layer("struct_ai/extra/core/utils/foo.py") is None

    def it_returns_none_for_package_root_only() -> None:
        assert path_to_layer("struct_ai") is None
        assert path_to_layer("struct_ai/__init__.py") is None

    def it_uses_custom_config_with_different_package() -> None:
        custom_config = StructIaConfig(
            project_package="my_app",
            layers=[
                LayerConfig(name="domain", paths=["domain"]),
                LayerConfig(name="infra", paths=["infra"]),
            ],
        )
        assert path_to_layer("my_app/domain/models.py", custom_config) == 0
        assert path_to_layer("my_app/infra/repos.py", custom_config) == 1
        assert path_to_layer("struct_ai/core/foo.py", custom_config) is None

    def it_supports_multi_segment_layer_paths() -> None:
        custom_config = StructIaConfig(
            project_package="my_app",
            layers=[
                LayerConfig(name="domain", paths=["src/core"]),
                LayerConfig(name="infra", paths=["src/adapters"]),
            ],
        )
        assert path_to_layer("my_app/src/core/models.py", custom_config) == 0
        assert path_to_layer("my_app/src/adapters/db.py", custom_config) == 1


def describe_resolved_import_path_to_layer() -> None:
    def it_resolves_absolute_struct_ai_core_import() -> None:
        file_path = "struct_ai/core/entities/foo.py"
        assert (
            resolved_import_path_to_layer(file_path, "struct_ai.adapters.parsers.bar")
            == _INFRA_LEVEL
        )

    def it_returns_none_for_external_module() -> None:
        file_path = "struct_ai/core/entities/foo.py"
        assert resolved_import_path_to_layer(file_path, "os") is None
        assert resolved_import_path_to_layer(file_path, "requests") is None

    def it_resolves_relative_import_upward() -> None:
        file_path = "struct_ai/core/entities/foo.py"
        # "..interfaces.bar" → struct_ai.core.interfaces.bar → still domain layer
        assert (
            resolved_import_path_to_layer(file_path, "..interfaces.bar")
            == _DOMAIN_LEVEL
        )

    def it_uses_custom_config_for_resolution() -> None:
        custom_config = StructIaConfig(
            project_package="my_app",
            layers=[
                LayerConfig(name="domain", paths=["domain"]),
                LayerConfig(name="infra", paths=["infra"]),
            ],
        )
        file_path = "my_app/domain/service.py"
        assert (
            resolved_import_path_to_layer(file_path, "my_app.infra.repo", custom_config)
            == 1
        )
        assert resolved_import_path_to_layer(file_path, "os", custom_config) is None
