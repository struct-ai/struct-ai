"""Tests for the layer rules evaluator."""

from struct_ai.core.entities.imports import ImportDependency
from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.use_cases.layer_evaluator import (
    evaluate_layer_rules,
    find_first_layer_violation,
)


def _imp(
    module_name: str, line: int = 1, names: list[str] | None = None
) -> ImportDependency:
    return ImportDependency(
        module_name=module_name,
        line_number=line,
        names=names or [module_name.split(".")[-1]],
    )


def describe_evaluate_layer_rules() -> None:
    def it_returns_none_when_no_imports() -> None:
        assert evaluate_layer_rules("struct_ai/core/entities/foo.py", []) is None

    def it_returns_none_when_only_external_imports() -> None:
        imports = [_imp("os"), _imp("sys"), _imp("requests")]
        assert evaluate_layer_rules("struct_ai/core/entities/foo.py", imports) is None

    def it_returns_violation_when_domain_imports_infrastructure() -> None:
        imports = [_imp("struct_ai.adapters.parsers.python_ast_adapter")]
        result = evaluate_layer_rules("struct_ai/core/entities/foo.py", imports)
        assert result == RuleType.LAYER_VIOLATION

    def it_returns_none_for_infrastructure_importing_domain() -> None:
        imports = [_imp("struct_ai.core.entities.foo")]
        result = evaluate_layer_rules("struct_ai/adapters/parsers/bar.py", imports)
        assert result is None

    def it_returns_none_when_file_is_outside_layers() -> None:
        imports = [_imp("struct_ai.adapters.parsers.python_ast_adapter")]
        result = evaluate_layer_rules("some/random/file.py", imports)
        assert result is None


def describe_find_first_layer_violation() -> None:
    def it_returns_none_when_no_violation() -> None:
        imports = [_imp("os", line=1), _imp("sys", line=2)]
        result = find_first_layer_violation("struct_ai/core/entities/foo.py", imports)
        assert result is None

    def it_returns_first_offending_import_in_line_order() -> None:
        early = _imp("struct_ai.adapters.parsers.bar", line=1)
        late = _imp("struct_ai.adapters.parsers.baz", line=5)
        imports = [late, early]  # reversed order in list
        result = find_first_layer_violation("struct_ai/core/entities/foo.py", imports)
        assert result is not None
        rule_type, offending = result
        assert rule_type == RuleType.LAYER_VIOLATION
        assert offending.line_number == 1  # early is returned first

    def it_returns_violation_type_and_import() -> None:
        violating = _imp("struct_ai.adapters.parsers.python_ast_adapter", line=3)
        result = find_first_layer_violation(
            "struct_ai/core/entities/foo.py", [violating]
        )
        assert result is not None
        rule_type, offending = result
        assert rule_type == RuleType.LAYER_VIOLATION
        assert offending is violating
