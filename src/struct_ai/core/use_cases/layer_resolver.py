"""Pure resolution of file paths and import module names to architectural layer levels.

No I/O; string manipulation only. All public functions accept an optional
``config`` parameter so they work with any project layout, not just struct_ai.
When omitted, ``DEFAULT_CONFIG`` (the built-in struct_ai layout) is used.
"""

from typing import Optional

from struct_ai.core.entities.config import DEFAULT_CONFIG, StructIaConfig


def _normalize_path(file_path: str, project_package: str) -> str:
    """Normalize a file path for layer resolution.

    - Converts backslashes to forward slashes.
    - Strips filesystem noise before ``/src/<project_package>/`` (repository
      layout convention) without mangling paths where ``src`` is itself part
      of a configured layer path (e.g. ``paths: ["src/core"]``).
    - Keeps only the path from the first ``{project_package}/`` onward so
      absolute filesystem paths resolve the same as repo-relative ones.
    """
    normalized = file_path.replace("\\", "/").strip()
    src_package_marker = f"/src/{project_package}/"
    if src_package_marker in normalized:
        tail = normalized.split(src_package_marker, 1)[1]
        normalized = f"{project_package}/{tail}"
    elif normalized.startswith(f"src/{project_package}/"):
        normalized = normalized[4:]  # strip leading "src/"
    marker = f"{project_package}/"
    if marker in normalized:
        normalized = normalized[normalized.find(marker) :]
    return normalized.lstrip("/")


def path_to_layer(
    file_path: str,
    config: StructIaConfig = DEFAULT_CONFIG,
) -> Optional[int]:
    """Map a file path to its layer level (0 = lowest / most foundational).

    Only the path segment(s) immediately after ``config.project_package`` define
    the layer, so unrelated parent directories with the same names are ignored.

    Returns ``None`` when the file does not belong to any configured layer.
    """
    normalized = _normalize_path(file_path, config.project_package)
    parts = [segment for segment in normalized.split("/") if segment]

    try:
        package_index = parts.index(config.project_package)
    except ValueError:
        return None

    if package_index + 1 >= len(parts):
        return None

    # Path relative to the project package root (e.g. "core/entities/foo.py")
    path_after_package = "/".join(parts[package_index + 1 :])

    for level, layer in enumerate(config.layers):
        for layer_path in layer.paths:
            if path_after_package == layer_path or path_after_package.startswith(
                layer_path + "/"
            ):
                return level

    return None


def _module_to_path(module_name: str) -> str:
    """Convert dotted module name to a path-like string (dots → slashes)."""
    return module_name.replace(".", "/")


def _current_package_from_path(file_path: str, project_package: str) -> str:
    """Derive current dotted package name from a file path."""
    normalized = _normalize_path(file_path, project_package)
    if normalized.endswith(".py"):
        normalized = normalized[:-3]
    return normalized.replace("/", ".")


def _resolve_relative_module(current_package: str, module_name: str) -> Optional[str]:
    """Resolve a relative import to an absolute module name.

    E.g. current_package='struct_ai.core.entities', module_name='..interfaces.foo'
    → 'struct_ai.core.interfaces.foo'
    """
    if not module_name.startswith("."):
        return module_name
    level = 0
    i = 0
    while i < len(module_name) and module_name[i] == ".":
        level += 1
        i += 1
    rest = module_name[i:].lstrip(".")
    parts = current_package.split(".")
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


def resolved_import_path_to_layer(
    file_path: str,
    module_name: str,
    config: StructIaConfig = DEFAULT_CONFIG,
) -> Optional[int]:
    """Resolve an import to the target layer level.

    Returns ``None`` for external modules (outside the configured project
    package) or when resolution fails.
    """
    if module_name.startswith("."):
        current_package = _current_package_from_path(file_path, config.project_package)
        absolute_module = _resolve_relative_module(current_package, module_name)
        if absolute_module is None:
            return None
        if absolute_module != config.project_package and not absolute_module.startswith(
            config.project_package + "."
        ):
            return None
        return path_to_layer(_module_to_path(absolute_module), config)

    if (
        not module_name.startswith(config.project_package + ".")
        and module_name != config.project_package
    ):
        return None

    return path_to_layer(_module_to_path(module_name), config)
