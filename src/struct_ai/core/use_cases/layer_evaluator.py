"""
Pure evaluator: checks a file's imports against Clean Architecture layer rules.
Returns RuleType.LAYER_VIOLATION if a lower layer imports a higher layer, else None.
"""
from typing import List, Optional

from struct_ai.core.entities.imports import ImportDependency
from struct_ai.core.entities.rule_type import RuleType
from struct_ai.core.use_cases.layer_resolver import (
    path_to_layer,
    resolved_import_path_to_layer,
)


def evaluate_layer_rules(
    file_path: str,
    imports: List[ImportDependency],
) -> Optional[RuleType]:
    """
    Analyze imports against the current file's layer. Pure function: no side effects.

    Returns RuleType.LAYER_VIOLATION if any import targets a higher layer
    (e.g. Domain importing Infrastructure). Returns None if the architecture
    is respected or if the file is outside project layers.
    """
    current_layer = path_to_layer(file_path)
    if current_layer is None:
        return None

    for dependency in imports:
        target_layer = resolved_import_path_to_layer(file_path, dependency.module_name)
        if target_layer is None:
            continue
        if current_layer < target_layer:
            return RuleType.LAYER_VIOLATION

    return None
