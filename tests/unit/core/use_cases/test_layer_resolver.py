"""
Unit tests for layer path resolution.

Ensures path_to_layer() only uses struct_ai/<layer>/... and ignores unrelated
path segments (e.g. parent folders named core or adapters).
"""

from struct_ai.core.use_cases.layer_resolver import Layer, path_to_layer


def test_path_to_layer_uses_segment_immediately_after_struct_ai() -> None:
    """Layer is the first path segment after struct_ai, not any later match."""
    assert path_to_layer("struct_ai/core/entities/foo.py") == Layer.DOMAIN
    assert path_to_layer("struct_ai/adapters/parsers/foo.py") == Layer.INFRASTRUCTURE
    assert path_to_layer("struct_ai/entrypoints/cli/main.py") == Layer.ENTRYPOINTS


def test_path_to_layer_parent_dirs_named_adapters_do_not_misclassify() -> None:
    """
    Regression: unrelated ``adapters`` (or ``core``) in parent paths must not
    define the layer; only struct_ai/<layer>/ counts.
    """
    path = "/home/user/adapters/work/src/struct_ai/core/entities/foo.py"
    assert path_to_layer(path) == Layer.DOMAIN


def test_path_to_layer_parent_dirs_named_core_do_not_misclassify() -> None:
    """A ``core`` directory before struct_ai must not be treated as the domain layer."""
    path = "/home/core_user/projects/src/struct_ai/adapters/parsers/foo.py"
    assert path_to_layer(path) == Layer.INFRASTRUCTURE


def test_path_to_layer_returns_none_when_struct_ai_missing() -> None:
    """Paths without the struct_ai package root are not classified."""
    assert path_to_layer("some/other/package/foo.py") is None
    assert path_to_layer("vendor/core/utils.py") is None


def test_path_to_layer_returns_none_when_layer_not_immediate_child() -> None:
    """If the segment after struct_ai is not core/adapters/entrypoints, return None."""
    assert path_to_layer("struct_ai/extra/core/utils/foo.py") is None


def test_path_to_layer_returns_none_for_package_root_only() -> None:
    """struct_ai alone (no layer segment) has no layer."""
    assert path_to_layer("struct_ai") is None
    assert path_to_layer("struct_ai/__init__.py") is None
