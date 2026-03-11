"""
Unit tests for PythonAstAdapter.

They ensure that parse_code() returns the correct list of ImportDependency
for valid Python code (including edge cases) and raises InvalidCodeError
for invalid syntax.
"""

import pytest

from struct_ai.adapters.parsers.python_ast_adapter import PythonAstAdapter
from struct_ai.core.exceptions.exceptions import InvalidCodeError


@pytest.fixture
def adapter():
    """Shared PythonAstAdapter instance."""
    return PythonAstAdapter()


# --- Happy path ---


def test_parse_code_returns_empty_list_when_no_imports(adapter):
    """Code with no import statements returns an empty list."""
    result = adapter.parse_code("x = 1\n")
    assert result == []


def test_parse_code_returns_empty_list_for_empty_string(adapter):
    """Empty string raises SyntaxError and thus InvalidCodeError (empty is invalid)."""
    with pytest.raises(InvalidCodeError):
        adapter.parse_code("")


def test_parse_code_single_import(adapter):
    """Single 'import os' returns one ImportDependency with correct fields."""
    result = adapter.parse_code("import os\n")
    assert len(result) == 1
    assert result[0].module_name == "os"
    assert result[0].line_number == 1
    assert result[0].names == ["os"]


def test_parse_code_from_import_single_name(adapter):
    """'from foo import bar' returns one entry with module foo and name bar."""
    result = adapter.parse_code("from foo import bar\n")
    assert len(result) == 1
    assert result[0].module_name == "foo"
    assert result[0].line_number == 1
    assert result[0].names == ["bar"]


def test_parse_code_from_import_multiple_names(adapter):
    """'from foo import bar, baz' returns two entries, same module and line."""
    result = adapter.parse_code("from foo import bar, baz\n")
    assert len(result) == 2
    assert result[0].module_name == "foo"
    assert result[0].line_number == 1
    assert result[0].names == ["bar"]
    assert result[1].module_name == "foo"
    assert result[1].line_number == 1
    assert result[1].names == ["baz"]


def test_parse_code_mixed_import_and_from_import(adapter):
    """Mix of 'import' and 'from ... import' returns all entries with correct data."""
    code = "import os\nfrom sys import path\n"
    result = adapter.parse_code(code)
    assert len(result) == 2
    modules = {r.module_name for r in result}
    assert "os" in modules
    assert "sys" in modules
    line_numbers = {r.line_number for r in result}
    assert line_numbers == {1, 2}


def test_parse_code_line_numbers_reflect_source_lines(adapter):
    """Imports on later lines have correct line_number."""
    code = "\n\nimport os\n"
    result = adapter.parse_code(code)
    assert len(result) == 1
    assert result[0].module_name == "os"
    assert result[0].line_number == 3


# --- Edge cases (aliases, multi-module, relative, star, nested) ---


def test_parse_code_import_with_alias(adapter):
    """'import os as operating_system' stores module os and local name operating_system."""
    result = adapter.parse_code("import os as operating_system\n")
    assert len(result) == 1
    assert result[0].module_name == "os"
    assert result[0].names == ["operating_system"]


def test_parse_code_import_multiple_modules(adapter):
    """'import a, b' returns two entries."""
    result = adapter.parse_code("import a, b\n")
    assert len(result) == 2
    module_names = sorted(r.module_name for r in result)
    assert module_names == ["a", "b"]
    assert result[0].line_number == result[1].line_number == 1


def test_parse_code_relative_import_dot_only(adapter):
    """'from . import something' has module_name '.'."""
    result = adapter.parse_code("from . import something\n")
    assert len(result) == 1
    assert result[0].module_name == "."
    assert result[0].names == ["something"]


def test_parse_code_relative_import_dot_dot_module(adapter):
    """'from ..pkg import x' has module_name '..pkg'."""
    result = adapter.parse_code("from ..pkg import x\n")
    assert len(result) == 1
    assert result[0].module_name == "..pkg"
    assert result[0].names == ["x"]


def test_parse_code_from_import_with_star_ignored(adapter):
    """'from foo import *' produces no ImportDependency (star is skipped)."""
    result = adapter.parse_code("from foo import *\n")
    assert result == []


def test_parse_code_imports_inside_function_included(adapter):
    """Imports inside a function are collected (ast.walk visits all nodes)."""
    code = """
def f():
    import x
"""
    result = adapter.parse_code(code)
    assert len(result) == 1
    assert result[0].module_name == "x"
    assert result[0].names == ["x"]


# --- Invalid code (InvalidCodeError) ---


def test_parse_code_invalid_syntax_raises_invalid_code_error(adapter):
    """Invalid Python source raises InvalidCodeError, not SyntaxError."""
    with pytest.raises(InvalidCodeError):
        adapter.parse_code("def f(\n")


def test_parse_code_invalid_syntax_exception_contains_message_in_log(adapter):
    """InvalidCodeError.log contains the original error message."""
    code = "x = (\n"
    with pytest.raises(InvalidCodeError) as exc_info:
        adapter.parse_code(code)
    assert "message" in exc_info.value.log
    assert exc_info.value.log["message"] is not None


def test_parse_code_invalid_syntax_exception_contains_lines_in_log(adapter):
    """InvalidCodeError.log contains the code lines."""
    code = "line one\nline two ( broken\n"
    with pytest.raises(InvalidCodeError) as exc_info:
        adapter.parse_code(code)
    assert "lines" in exc_info.value.log
    assert exc_info.value.log["lines"] == ["line one", "line two ( broken", ""]
