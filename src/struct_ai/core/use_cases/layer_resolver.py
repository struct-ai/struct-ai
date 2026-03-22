"""
Pure resolution of file paths and import module names to Clean Architecture layers.
No I/O; string manipulation only.
"""

from enum import Enum
from typing import Optional


# Layer order: lower index = lower layer. A layer may only import same or lower.
class Layer(int, Enum):
    DOMAIN = 0  # core
    INFRASTRUCTURE = 1  # adapters
    ENTRYPOINTS = 2  # entrypoints


# Segment names in path that identify each layer (order matches Layer enum).
_LAYER_SEGMENTS = ("core", "adapters", "entrypoints")

# Package root; only imports under this are checked for layer violations.
_PROJECT_PACKAGE = "struct_ai"


def _normalize_path(file_path: str) -> str:
    """
    Normalize path for layer and package resolution.

    - Converts backslashes to forward slashes.
    - Trims to project source when possible: after the first ``/src/`` segment
      (e.g. ``/repo/src/struct_ai/core/...`` → ``struct_ai/core/...``).
    - Strips a leading ``src/`` when present (repo-relative layout).
    - Keeps only the path from the first ``struct_ai/`` onward so absolute
      filesystem paths (e.g. ``/home/repo/struct_ai/core/...``) resolve like
      repo-relative paths.
    """
    normalized = file_path.replace("\\", "/").strip()
    if "/src/" in normalized:
        normalized = normalized.split("/src/", 1)[1]
    elif normalized.startswith("src/"):
        normalized = normalized[4:]
    marker = f"{_PROJECT_PACKAGE}/"
    if marker in normalized:
        normalized = normalized[normalized.find(marker) :]
    return normalized.lstrip("/")


def path_to_layer(file_path: str) -> Optional[Layer]:
    """
    Map a file path to its layer.

    Only the segment immediately after ``struct_ai`` defines the layer
    (``struct_ai/core/...``, ``struct_ai/adapters/...``, ``struct_ai/entrypoints/...``).
    This avoids misclassifying paths where ``core``, ``adapters``, or ``entrypoints``
    appear in unrelated parent directories.
    """
    normalized = _normalize_path(file_path)
    parts = [segment for segment in normalized.split("/") if segment]
    try:
        package_index = parts.index(_PROJECT_PACKAGE)
    except ValueError:
        return None
    if package_index + 1 >= len(parts):
        return None
    layer_segment = parts[package_index + 1]
    if layer_segment in _LAYER_SEGMENTS:
        return Layer(_LAYER_SEGMENTS.index(layer_segment))
    return None


def _module_to_path(module_name: str) -> str:
    """Convert dotted module name to path-like string (e.g. struct_ai.core.foo -> struct_ai/core/foo)."""
    return module_name.replace(".", "/")


def _current_package_from_path(file_path: str) -> str:
    """
    Derive current package from file path.

    Uses the same normalization as path_to_layer so absolute paths and
    ``.../src/struct_ai/...`` layouts yield ``struct_ai.core.entities.foo``.
    """
    normalized = _normalize_path(file_path)
    if normalized.endswith(".py"):
        normalized = normalized[:-3]
    return normalized.replace("/", ".")


def _resolve_relative_module(current_package: str, module_name: str) -> Optional[str]:
    """
    Resolve relative import to absolute module name.
    E.g. current_package='struct_ai.core.entities', module_name='..interfaces.foo' -> 'struct_ai.core.interfaces.foo'
    """
    if not module_name.startswith("."):
        return module_name
    # Count leading dots and get the rest (e.g. '...bar' -> level=3, rest='bar')
    level = 0
    i = 0
    while i < len(module_name) and module_name[i] == ".":
        level += 1
        i += 1
    rest = module_name[i:].lstrip(".")  # e.g. 'interfaces.foo' or ''
    parts = current_package.split(".")
    # Go up 'level' times (e.g. struct_ai.core.entities + .. -> struct_ai.core)
    for _ in range(level):
        if not parts:
            return None
        parts.pop()
    if not parts:
        return None
    base = ".".join(parts)
    if rest:
        return f"{base}.{rest}" if base else rest
    return base


def resolved_import_path_to_layer(file_path: str, module_name: str) -> Optional[Layer]:
    """
    Resolve an import (given current file path and import module_name) to the target layer.
    Returns None for external modules (outside struct_ai) or if resolution fails.
    """
    if module_name.startswith("."):
        current_package = _current_package_from_path(file_path)
        absolute_module = _resolve_relative_module(current_package, module_name)
        if absolute_module is None:
            return None
        if absolute_module != _PROJECT_PACKAGE and not absolute_module.startswith(
            _PROJECT_PACKAGE + "."
        ):
            return None
        path_like = _module_to_path(absolute_module)
        return path_to_layer(path_like)
    # Absolute import
    if (
        not module_name.startswith(_PROJECT_PACKAGE + ".")
        and module_name != _PROJECT_PACKAGE
    ):
        return None
    path_like = _module_to_path(module_name)
    return path_to_layer(path_like)
