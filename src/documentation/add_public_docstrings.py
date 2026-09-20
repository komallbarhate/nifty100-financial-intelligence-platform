"""Add one-line docstrings to public functions that do not already have one."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def make_docstring(function_name: str) -> str:
    """Create a concise one-line docstring from a function name."""
    words = function_name.replace("_", " ").strip()
    if function_name == "main":
        return "Run the main workflow."
    if function_name == "run":
        return "Run the workflow."
    if function_name.startswith("get_"):
        return f"Return {words[4:]}."
    if function_name.startswith("load_"):
        return f"Load {words[5:]}."
    if function_name.startswith("calculate_"):
        return f"Calculate {words[10:]}."
    if function_name.startswith("create_"):
        return f"Create {words[7:]}."
    if function_name.startswith("build_"):
        return f"Build {words[6:]}."
    if function_name.startswith("save_"):
        return f"Save {words[5:]}."
    if function_name.startswith("find_"):
        return f"Find {words[5:]}."
    if function_name.startswith("validate_"):
        return f"Validate {words[9:]}."
    if function_name.startswith("normalize_"):
        return f"Normalize {words[10:]}."
    if function_name.startswith("classify_"):
        return f"Classify {words[9:]}."
    if function_name.startswith("format_"):
        return f"Format {words[7:]}."
    if function_name.startswith("apply_"):
        return f"Apply {words[6:]}."
    if function_name.startswith("check_"):
        return f"Check {words[6:]}."
    return f"Process {words}."


def find_missing_functions(path: Path) -> list[tuple[int, int, str]]:
    """Find public functions without docstrings in a Python file."""
    source = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(path))
    missing = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        if node.name.startswith("_"):
            continue

        if ast.get_docstring(node) is not None:
            continue

        if not node.body:
            continue

        first_body_node = node.body[0]
        missing.append(
            (
                first_body_node.lineno,
                node.col_offset,
                node.name,
            )
        )

    return missing


def add_docstrings(path: Path) -> int:
    """Add missing one-line docstrings to a Python file."""
    source = path.read_text(encoding="utf-8-sig")
    lines = source.splitlines(keepends=True)

    missing = find_missing_functions(path)

    for body_line, col_offset, function_name in sorted(
        missing,
        key=lambda item: item[0],
        reverse=True,
    ):
        index = body_line - 1
        indentation = " " * (col_offset + 4)
        docstring = make_docstring(function_name)

        newline = "\n"
        if index < len(lines) and lines[index].endswith("\r\n"):
            newline = "\r\n"

        lines.insert(
            index,
            f'{indentation}"""{docstring}"""{newline}',
        )

    if missing:
        path.write_text("".join(lines), encoding="utf-8")

    return len(missing)


def main() -> None:
    """Add missing public-function docstrings across the source tree."""
    total = 0

    for path in sorted(ROOT.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue

        count = add_docstrings(path)

        if count:
            print(f"{path}: added {count} docstrings")
            total += count

    print(f"Total docstrings added: {total}")


if __name__ == "__main__":
    main()
