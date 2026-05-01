from pathlib import Path
import ast
import inspect

ROOT = Path(__file__).resolve().parents[1]

SOURCES = {
    "Predicates Reference": ROOT / "astanalyzer" / "predicates.py",
    "Tools Reference": ROOT / "astanalyzer" / "tools.py",
}

OUT_DIR = ROOT / "docs" / "reference"


def extract_items(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))

    items = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if node.name.startswith("_"):
                continue

            doc = ast.get_docstring(node) or "No documentation available."

            if isinstance(node, ast.FunctionDef):
                args = [arg.arg for arg in node.args.args]

                # include keyword-only arguments
                kwonly = [arg.arg for arg in node.args.kwonlyargs]
                all_args = args + kwonly

                signature = f"{node.name}({', '.join(all_args)})"
                kind = "function"

            else:
                signature = node.name
                kind = "class"

            items.append({
                "name": node.name,
                "signature": signature,
                "doc": inspect.cleandoc(doc),
                "kind": kind,
            })

    return items


def render(title: str, items: list[dict]) -> str:
    lines = [
        "[Back to Matcher Helpers](../matcher-helpers.md) | [Back to Rule DSL](../rule-dsl.md) | [Back to README](../../README.md)",
        "",
        f"# {title}",
        "",
        "> This file is generated automatically. Do not edit it manually.",
        "",
    ]

    for item in items:
        lines.extend([
            f"## `{item['name']}`",
            "",
            f"**Type:** {item['kind']}",
            "",
            "```python",
            item["signature"],
            "```",
            "",
            item["doc"],
            "",
            "---",
            "",
        ])

    # footer (doporučeno)
    lines.extend([
        "",
        "[Back to Matcher Helpers](../matcher-helpers.md) | [Back to Rule DSL](../rule-dsl.md) | [Back to README](../../README.md)",
    ])

    return "\n".join(lines)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for title, source in SOURCES.items():
        items = extract_items(source)
        output = OUT_DIR / f"{source.stem}.md"
        output.write_text(render(title, items), encoding="utf-8")
        print(f"Generated {output}")


if __name__ == "__main__":
    main()