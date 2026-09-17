"""AST parsing and symbol graph navigation for token-efficient context pruning."""

import ast
import os
from pathlib import Path
from typing import Any


class SymbolExtractor:
    """Extracts symbols, classes, functions, and outlines from source code."""

    @staticmethod
    def outline_python(code: str) -> list[dict[str, Any]]:
        """Parse Python source into a structured list of symbols."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [{"error": f"SyntaxError: {e}"}]

        symbols: list[dict[str, Any]] = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append({
                            "name": item.name,
                            "line_start": item.lineno,
                            "line_end": item.end_lineno or item.lineno,
                            "args": [a.arg for a in item.args.args],
                            "is_async": isinstance(item, ast.AsyncFunctionDef),
                        })
                doc = ast.get_docstring(node) or ""
                symbols.append({
                    "type": "class",
                    "name": node.name,
                    "line_start": node.lineno,
                    "line_end": node.end_lineno or node.lineno,
                    "docstring": doc.splitlines()[0] if doc else "",
                    "methods": methods,
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node) or ""
                symbols.append({
                    "type": "function",
                    "name": node.name,
                    "line_start": node.lineno,
                    "line_end": node.end_lineno or node.lineno,
                    "args": [a.arg for a in node.args.args],
                    "docstring": doc.splitlines()[0] if doc else "",
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                })
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        symbols.append({
                            "type": "variable",
                            "name": target.id,
                            "line_start": node.lineno,
                            "line_end": node.end_lineno or node.lineno,
                        })

        return symbols

    @staticmethod
    def outline_generic(code: str) -> list[dict[str, Any]]:
        """Fallback regex-based outline for other languages (JS/TS, Rust, Go)."""
        import re
        symbols: list[dict[str, Any]] = []
        lines = code.splitlines()

        func_pattern = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(?:function|def|fn|func)\s+([A-Za-z0-9_]+)")
        class_pattern = re.compile(r"^\s*(?:export\s+)?(?:class|struct|interface|type)\s+([A-Za-z0-9_]+)")

        for idx, line in enumerate(lines, start=1):
            m_fn = func_pattern.match(line)
            if m_fn:
                symbols.append({"type": "function", "name": m_fn.group(1), "line_start": idx, "line_end": idx})
                continue
            m_cls = class_pattern.match(line)
            if m_cls:
                symbols.append({"type": "class", "name": m_cls.group(1), "line_start": idx, "line_end": idx})

        return symbols

    @classmethod
    def outline_file(cls, file_path: str) -> str:
        """Return formatted symbol outline of a file without full code dump."""
        p = Path(file_path).expanduser().resolve()
        if not p.exists() or not p.is_file():
            return f"Error: File not found: {file_path}"

        code = p.read_text(encoding="utf-8", errors="replace")
        ext = p.suffix.lower()

        if ext == ".py":
            symbols = cls.outline_python(code)
        else:
            symbols = cls.outline_generic(code)

        if not symbols:
            return f"Outline for {p.name}: (no top-level functions or classes detected)"

        out = [f"Symbol Outline for {p.name} ({len(code.splitlines())} lines):"]
        for s in symbols:
            if "error" in s:
                out.append(f"  [error] {s['error']}")
                continue
            stype = s.get("type", "symbol").upper()
            sname = s.get("name", "")
            l_start = s.get("line_start", 0)
            l_end = s.get("line_end", 0)
            doc = f" - \"{s['docstring']}\"" if s.get("docstring") else ""

            if stype == "CLASS":
                methods = s.get("methods", [])
                out.append(f"  CLASS {sname} (lines {l_start}-{l_end}){doc}")
                for m in methods:
                    async_prefix = "async " if m.get("is_async") else ""
                    args_str = ", ".join(m.get("args", []))
                    out.append(f"    - {async_prefix}{m['name']}({args_str}) (lines {m['line_start']}-{m['line_end']})")
            elif stype == "FUNCTION":
                async_prefix = "async " if s.get("is_async") else ""
                args_str = ", ".join(s.get("args", []))
                out.append(f"  {async_prefix}FUNCTION {sname}({args_str}) (lines {l_start}-{l_end}){doc}")
            elif stype == "VARIABLE":
                out.append(f"  VARIABLE {sname} (line {l_start})")

        return "\n".join(out)

    @classmethod
    def extract_symbol(cls, file_path: str, symbol_name: str) -> str:
        """Extract only the specified function or class implementation from a file."""
        p = Path(file_path).expanduser().resolve()
        if not p.exists() or not p.is_file():
            return f"Error: File not found: {file_path}"

        code = p.read_text(encoding="utf-8", errors="replace")
        lines = code.splitlines()

        if p.suffix.lower() == ".py":
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == symbol_name:
                        start = max(0, node.lineno - 1)
                        end = node.end_lineno if node.end_lineno else len(lines)
                        snippet = lines[start:end]
                        numbered = [f"{i+node.lineno:4d} | {l}" for i, l in enumerate(snippet)]
                        return f"Symbol '{symbol_name}' in {p.name} (lines {node.lineno}-{end}):\n\n" + "\n".join(numbered)
            except Exception as e:
                return f"Error parsing Python AST: {e}"

        # Generic line search fallback
        for idx, line in enumerate(lines):
            if symbol_name in line and any(k in line for k in ("def ", "class ", "function ", "fn ")):
                end_idx = min(len(lines), idx + 40)
                snippet = lines[idx:end_idx]
                numbered = [f"{i+idx+1:4d} | {l}" for i, l in enumerate(snippet)]
                return f"Found symbol '{symbol_name}' in {p.name} around line {idx+1}:\n\n" + "\n".join(numbered)

        return f"Symbol '{symbol_name}' not found in {file_path}"
