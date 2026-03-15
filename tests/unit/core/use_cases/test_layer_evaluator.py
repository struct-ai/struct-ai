"""
Unit tests for the layer rules evaluator.

They ensure evaluate_layer_rules() returns RuleType.LAYER_VIOLATION when a lower
layer imports a higher layer, and None when the architecture is respected or
imports are external.
"""

import pytest

from struct_ai.core.entities.imports import ImportDependency
from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.use_cases.layer_evaluator import evaluate_layer_rules


def _imp(module_name: str, line: int = 1, names: list[str] | None = None) -> ImportDependency:
    """Build an ImportDependency for tests."""
    return ImportDependency(
        module_name=module_name,
        line_number=line,
        names=names or [module_name.split(".")[-1]],
    )


# --- No imports / external only ---


def test_evaluate_returns_none_when_no_imports() -> None:
    """Empty imports list always yields None."""
    assert evaluate_layer_rules("struct_ai/core/entities/foo.py", []) is None


def test_evaluate_returns_none_when_only_external_imports() -> None:
    """Core file importing only os/sys/requests yields None."""
    imports = [_imp("os"), _imp("sys"), _imp("requests")]
    assert (
        evaluate_layer_rules("struct_ai/core/entities/foo.py", imports) is None
    )


# --- Core layer: same layer or lower → None ---


def test_evaluate_returns_none_when_core_imports_core_absolute() -> None:
    """Core file importing another core module is allowed."""
    imports = [_imp("struct_ai.core.entities.rule_type")]
    assert (
        evaluate_layer_rules("struct_ai/core/entities/foo.py", imports) is None
    )


def test_evaluate_returns_none_when_core_imports_core_relative() -> None:
    """Core file with relative import staying in core is allowed."""
    imports = [_imp("..interfaces.outputs.code_parser_port")]
    assert (
        evaluate_layer_rules("struct_ai/core/entities/bar.py", imports) is None
    )


# --- Core importing higher layer → LAYER_VIOLATION ---


def test_evaluate_returns_layer_violation_when_core_imports_adapters() -> None:
    """Core file importing adapters is a violation."""
    imports = [_imp("struct_ai.adapters.parsers.python_ast_adapter")]
    assert (
        evaluate_layer_rules("struct_ai/core/entities/foo.py", imports)
        == RuleType.LAYER_VIOLATION
    )


def test_evaluate_returns_layer_violation_when_core_imports_entrypoints() -> None:
    """Core file importing entrypoints is a violation."""
    imports = [_imp("struct_ai.entrypoints.cli.main")]
    assert (
        evaluate_layer_rules("struct_ai/core/entities/foo.py", imports)
        == RuleType.LAYER_VIOLATION
    )


def test_evaluate_returns_layer_violation_when_core_relative_imports_adapters() -> None:
    """Core file with relative import resolving to adapters is a violation."""
    # From struct_ai.core.entities, .. goes to struct_ai.core; we need to
    # simulate an import that resolves to adapters. From core/entities,
    # something like ...adapters is not standard; use absolute in test.
    imports = [_imp("struct_ai.adapters.parsers.python_ast_adapter")]
    assert (
        evaluate_layer_rules("struct_ai/core/entities/bar.py", imports)
        == RuleType.LAYER_VIOLATION
    )


# --- Adapters: same or lower → None ---


def test_evaluate_returns_none_when_adapters_imports_core() -> None:
    """Adapters importing core is allowed."""
    imports = [_imp("struct_ai.core.entities.imports")]
    assert (
        evaluate_layer_rules("struct_ai/adapters/parsers/python_ast_adapter.py", imports)
        is None
    )


def test_evaluate_returns_none_when_adapters_imports_adapters() -> None:
    """Adapters importing another adapter is allowed."""
    imports = [_imp("struct_ai.adapters.parsers.other_module")]
    assert (
        evaluate_layer_rules("struct_ai/adapters/parsers/foo.py", imports)
        is None
    )


# --- Adapters importing entrypoints → LAYER_VIOLATION ---


def test_evaluate_returns_layer_violation_when_adapters_imports_entrypoints() -> None:
    """Adapters importing entrypoints is a violation."""
    imports = [_imp("struct_ai.entrypoints.cli.main")]
    assert (
        evaluate_layer_rules("struct_ai/adapters/parsers/foo.py", imports)
        == RuleType.LAYER_VIOLATION
    )


# --- Entrypoints: any internal import allowed → None ---


def test_evaluate_returns_none_when_entrypoints_imports_core() -> None:
    """Entrypoints importing core is allowed."""
    imports = [_imp("struct_ai.core.entities.rule_type")]
    assert (
        evaluate_layer_rules("struct_ai/entrypoints/cli/main.py", imports)
        is None
    )


def test_evaluate_returns_none_when_entrypoints_imports_adapters() -> None:
    """Entrypoints importing adapters is allowed."""
    imports = [_imp("struct_ai.adapters.parsers.python_ast_adapter")]
    assert (
        evaluate_layer_rules("struct_ai/entrypoints/cli/main.py", imports)
        is None
    )


# --- Path robustness ---


def test_evaluate_with_src_prefix_returns_none_for_valid_imports() -> None:
    """Path with src/ prefix is normalized; core importing core still None."""
    imports = [_imp("struct_ai.core.entities.imports")]
    assert (
        evaluate_layer_rules("src/struct_ai/core/entities/foo.py", imports)
        is None
    )


def test_evaluate_with_src_prefix_detects_violation() -> None:
    """Path with src/ prefix still detects core → adapters violation."""
    imports = [_imp("struct_ai.adapters.parsers.python_ast_adapter")]
    assert (
        evaluate_layer_rules("src/struct_ai/core/entities/foo.py", imports)
        == RuleType.LAYER_VIOLATION
    )


def test_evaluate_with_backslashes_normalizes_path() -> None:
    """Path with backslashes is normalized (Windows-style)."""
    imports = [_imp("struct_ai.adapters.parsers.python_ast_adapter")]
    assert (
        evaluate_layer_rules("struct_ai\\core\\entities\\foo.py", imports)
        == RuleType.LAYER_VIOLATION
    )


# --- File outside project layers ---


def test_evaluate_returns_none_when_file_path_outside_project_layers() -> None:
    """File path without core/adapters/entrypoints yields None (no violation)."""
    imports = [_imp("struct_ai.adapters.parsers.python_ast_adapter")]
    assert (
        evaluate_layer_rules("some/other/package/foo.py", imports) is None
    )


# --- First violation wins ---


def test_evaluate_returns_layer_violation_on_first_violating_import() -> None:
    """When multiple imports violate, first one triggers LAYER_VIOLATION."""
    imports = [
        _imp("struct_ai.core.entities.rule_type", line=1),  # ok
        _imp("struct_ai.adapters.parsers.python_ast_adapter", line=2),  # violation
        _imp("struct_ai.entrypoints.cli.main", line=3),  # would also violate
    ]
    assert (
        evaluate_layer_rules("struct_ai/core/entities/foo.py", imports)
        == RuleType.LAYER_VIOLATION
    )
