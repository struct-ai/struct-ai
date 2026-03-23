"""Tests for PythonAstAdapter."""

import pytest

from struct_ai.adapters.parsers.python_ast_adapter import PythonAstAdapter
from struct_ai.core.exceptions.exceptions import InvalidCodeError


def describe_PythonAstAdapter() -> None:
    def describe_parse_code() -> None:
        def it_returns_empty_list_when_no_imports() -> None:
            assert PythonAstAdapter().parse_code("x = 1\n") == []

        def it_raises_invalid_code_error_for_empty_string() -> None:
            with pytest.raises(InvalidCodeError):
                PythonAstAdapter().parse_code("")

        def it_parses_single_import() -> None:
            result = PythonAstAdapter().parse_code("import os\n")
            assert len(result) == 1
            assert result[0].module_name == "os"
            assert result[0].line_number == 1
            assert result[0].names == ["os"]

        def it_parses_from_import_single_name() -> None:
            result = PythonAstAdapter().parse_code("from foo import bar\n")
            assert len(result) == 1
            assert result[0].module_name == "foo"
            assert result[0].names == ["bar"]

        def it_parses_from_import_multiple_names() -> None:
            result = PythonAstAdapter().parse_code("from foo import bar, baz\n")
            assert len(result) == 2
            assert result[0].names == ["bar"]
            assert result[1].names == ["baz"]

        def it_parses_mixed_imports() -> None:
            code = "import os\nfrom sys import path\n"
            result = PythonAstAdapter().parse_code(code)
            assert len(result) == 2
            modules = {r.module_name for r in result}
            assert modules == {"os", "sys"}

        def it_records_correct_line_numbers() -> None:
            code = "\n\nimport os\n"
            result = PythonAstAdapter().parse_code(code)
            assert result[0].line_number == 3

        def it_parses_import_with_alias() -> None:
            result = PythonAstAdapter().parse_code("import os as operating_system\n")
            assert result[0].module_name == "os"
            assert result[0].names == ["operating_system"]

        def it_parses_multiple_modules_on_one_line() -> None:
            result = PythonAstAdapter().parse_code("import a, b\n")
            assert len(result) == 2
            assert sorted(r.module_name for r in result) == ["a", "b"]

        def it_parses_relative_import_dot_only() -> None:
            result = PythonAstAdapter().parse_code("from . import something\n")
            assert result[0].module_name == "."
            assert result[0].names == ["something"]

        def it_parses_relative_import_with_dots_and_module() -> None:
            result = PythonAstAdapter().parse_code("from ..pkg import x\n")
            assert result[0].module_name == "..pkg"

        def it_ignores_star_imports() -> None:
            result = PythonAstAdapter().parse_code("from foo import *\n")
            assert result == []

        def it_collects_imports_inside_functions() -> None:
            code = "def f():\n    import x\n"
            result = PythonAstAdapter().parse_code(code)
            assert len(result) == 1
            assert result[0].module_name == "x"

        def it_raises_invalid_code_error_on_syntax_error() -> None:
            with pytest.raises(InvalidCodeError):
                PythonAstAdapter().parse_code("def f(\n")

        def it_includes_message_in_error_log() -> None:
            with pytest.raises(InvalidCodeError) as exc_info:
                PythonAstAdapter().parse_code("x = (\n")
            assert exc_info.value.log["message"] is not None

        def it_includes_lines_in_error_log() -> None:
            code = "line one\nline two ( broken\n"
            with pytest.raises(InvalidCodeError) as exc_info:
                PythonAstAdapter().parse_code(code)
            assert exc_info.value.log["lines"] == ["line one", "line two ( broken", ""]
