import ast
from typing import List

from struct_ai.core.entities.imports import ImportDependency
from struct_ai.core.exceptions.exceptions import InvalidCodeError
from struct_ai.core.interfaces.outputs.code_parser_port import CodeParserPort


class PythonAstAdapter(CodeParserPort):
    """
    Adapter for the Python AST parser.
    """

    def parse_code(self, code: str) -> List[ImportDependency]:
        """
        Parse the code and return the imports.
        Raises InvalidCodeError if the code is invalid; in case of SyntaxError,
        the lines of the code are provided in the exception.
        """
        if code.strip() == "":
            raise InvalidCodeError(message="Empty code", lines=[""])
        lines = code.split("\n")

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise InvalidCodeError(message=str(e), lines=lines) from e
        return self._collect_imports_from_tree(tree)

    def _collect_imports_from_tree(self, tree: ast.AST) -> List[ImportDependency]:
        """Walk the AST and collect all ImportDependency from Import and ImportFrom nodes."""
        imports: List[ImportDependency] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(self._import_node_to_dependencies(node))
            elif isinstance(node, ast.ImportFrom):
                imports.extend(self._import_from_node_to_dependencies(node))
        return sorted(
            imports,
            key=lambda dependency: (
                dependency.line_number,
                dependency.module_name,
                tuple(dependency.names),
            ),
        )

    def _import_node_to_dependencies(self, node: ast.Import) -> List[ImportDependency]:
        """Convert a single ast.Import node into a list of ImportDependency."""
        result: List[ImportDependency] = []
        for alias in node.names:
            local_name = alias.asname if alias.asname else alias.name
            result.append(
                ImportDependency(
                    module_name=alias.name,
                    line_number=node.lineno,
                    names=[local_name],
                )
            )
        return result

    def _import_from_node_to_dependencies(
        self, node: ast.ImportFrom
    ) -> List[ImportDependency]:
        """Convert a single ast.ImportFrom node into a list of ImportDependency."""
        module_str = "." * node.level + (node.module or "")
        result: List[ImportDependency] = []
        for alias in node.names:
            if alias.name == "*":
                continue
            local_name = alias.asname if alias.asname else alias.name
            result.append(
                ImportDependency(
                    module_name=module_str,
                    line_number=node.lineno,
                    names=[local_name],
                )
            )
        return result
