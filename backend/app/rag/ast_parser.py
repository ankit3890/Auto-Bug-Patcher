"""
AutoBug AI — AST Parser
========================
Tree-sitter based AST extraction for multiple programming languages.
Extracts functions, classes, imports, and builds basic call graphs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CodeSymbol:
    name: str
    kind: str          # "function" | "class" | "method" | "variable"
    file: str
    start_line: int
    end_line: int
    body: str          # Raw source text of the symbol
    docstring: str = ""
    decorators: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)  # names this symbol calls


@dataclass
class ParseResult:
    file: str
    language: str
    symbols: list[CodeSymbol]
    imports: list[str]
    errors: list[str]


LANGUAGE_PARSERS: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "tsx",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
}


class ASTParser:
    """
    Multi-language AST parser using tree-sitter.
    Falls back to regex-based heuristics if tree-sitter is unavailable
    for a given language.
    """

    def parse_file(self, file_path: str) -> ParseResult:
        """Parse a source file and extract symbols."""
        path = Path(file_path)
        ext = path.suffix.lower()
        language = LANGUAGE_PARSERS.get(ext)

        if language is None:
            return ParseResult(
                file=file_path, language="unknown", symbols=[], imports=[], errors=[]
            )

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            return ParseResult(
                file=file_path, language=language, symbols=[], imports=[],
                errors=[str(exc)]
            )

        try:
            return self._parse_with_treesitter(file_path, language, content)
        except Exception as exc:
            logger.debug("tree-sitter parse failed for %s: %s — falling back", file_path, exc)
            return self._parse_with_regex(file_path, language, content)

    def parse_content(self, content: str, language: str, file_path: str = "<string>") -> ParseResult:
        """Parse raw source code content."""
        try:
            return self._parse_with_treesitter(file_path, language, content)
        except Exception:
            return self._parse_with_regex(file_path, language, content)

    # ------------------------------------------------------------------
    # Tree-sitter implementation
    # ------------------------------------------------------------------

    def _parse_with_treesitter(self, file_path: str, language: str, content: str) -> ParseResult:
        """Parse using tree-sitter (requires tree-sitter + language grammars installed)."""
        import tree_sitter_languages  # type: ignore

        tree_sitter_languages.get_language(language)
        parser = tree_sitter_languages.get_parser(language)
        tree = parser.parse(content.encode("utf-8"))

        symbols: list[CodeSymbol] = []
        imports: list[str] = []
        errors: list[str] = []

        lines = content.splitlines()

        def get_text(node: Any) -> str:
            return content[node.start_byte:node.end_byte]

        def get_line_text(start: int, end: int) -> str:
            return "\n".join(lines[start:end])

        def traverse(node: Any) -> None:
            if node.type in ("function_definition", "function_declaration", "method_definition"):
                name_node = node.child_by_field_name("name")
                name = get_text(name_node) if name_node else "anonymous"
                body = get_text(node)
                symbols.append(CodeSymbol(
                    name=name,
                    kind="function",
                    file=file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    body=body,
                ))
            elif node.type in ("class_definition", "class_declaration"):
                name_node = node.child_by_field_name("name")
                name = get_text(name_node) if name_node else "AnonymousClass"
                body = get_text(node)
                symbols.append(CodeSymbol(
                    name=name,
                    kind="class",
                    file=file_path,
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    body=body,
                ))
            elif node.type in ("import_statement", "import_from_statement",
                               "import_declaration"):
                imports.append(get_text(node).strip())

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return ParseResult(
            file=file_path, language=language,
            symbols=symbols, imports=imports, errors=errors,
        )

    # ------------------------------------------------------------------
    # Regex fallback
    # ------------------------------------------------------------------

    def _parse_with_regex(self, file_path: str, language: str, content: str) -> ParseResult:
        """Simple regex-based symbol extractor as fallback."""
        import re

        symbols: list[CodeSymbol] = []
        imports: list[str] = []
        lines = content.splitlines()

        if language == "python":
            func_re = re.compile(r"^(\s*)def (\w+)\s*\(")
            class_re = re.compile(r"^(\s*)class (\w+)")
            import_re = re.compile(r"^\s*(import .+|from .+ import .+)")
            for i, line in enumerate(lines):
                m = func_re.match(line)
                if m:
                    symbols.append(CodeSymbol(
                        name=m.group(2), kind="function", file=file_path,
                        start_line=i + 1, end_line=i + 1, body=line,
                    ))
                m = class_re.match(line)
                if m:
                    symbols.append(CodeSymbol(
                        name=m.group(2), kind="class", file=file_path,
                        start_line=i + 1, end_line=i + 1, body=line,
                    ))
                m = import_re.match(line)
                if m:
                    imports.append(m.group(1).strip())

        elif language in ("javascript", "typescript", "tsx"):
            func_re = re.compile(r"(?:function|const|let|var)\s+(\w+)\s*(?:=\s*(?:async\s*)?\(|\()")
            class_re = re.compile(r"class\s+(\w+)")
            import_re = re.compile(r"^import .+")
            for i, line in enumerate(lines):
                for m in func_re.finditer(line):
                    symbols.append(CodeSymbol(
                        name=m.group(1), kind="function", file=file_path,
                        start_line=i + 1, end_line=i + 1, body=line,
                    ))
                m = class_re.search(line)
                if m:
                    symbols.append(CodeSymbol(
                        name=m.group(1), kind="class", file=file_path,
                        start_line=i + 1, end_line=i + 1, body=line,
                    ))
                if import_re.match(line):
                    imports.append(line.strip())

        return ParseResult(
            file=file_path, language=language,
            symbols=symbols, imports=imports, errors=[],
        )
