from pathlib import Path
import shutil

ROOT = Path("astanalyzer")

MOVES = {
    "anchor.py": "core/anchor.py",
    "enums.py": "core/enums.py",
    "kinds.py": "core/kinds.py",
    "rule.py": "core/rule.py",

    "ignore_rules.py": "filtering/ignore_rules.py",
    "policy.py": "filtering/policy.py",
    "rule_filtering.py": "filtering/rule_filtering.py",

    "file_selection.py": "selection/file_selection.py",
    "node_selector.py": "selection/node_selector.py",

    "logging_config.py": "runtime/logging_config.py",
}

REPLACEMENTS = {
    "astanalyzer.core.anchor": "astanalyzer.core.anchor",
    "astanalyzer.core.enums": "astanalyzer.core.enums",
    "astanalyzer.core.kinds": "astanalyzer.core.kinds",
    "astanalyzer.core.rule": "astanalyzer.core.rule",

    "astanalyzer.filtering.ignore_rules": "astanalyzer.filtering.ignore_rules",
    "astanalyzer.filtering.policy": "astanalyzer.filtering.policy",
    "astanalyzer.core.rule_filtering": "astanalyzer.filtering.rule_filtering",

    "astanalyzer.selection.file_selection": "astanalyzer.selection.file_selection",
    "astanalyzer.selection.node_selector": "astanalyzer.selection.node_selector",

    "astanalyzer.runtime.logging_config": "astanalyzer.runtime.logging_config",

    "from ..core.enums import": "from ..core.enums import",
    "from ..core.rule import": "from ..core.rule import",
    "from ..core.anchor import": "from ..core.anchor import",
    "from ..core.kinds import": "from ..core.kinds import",

    "from .core.enums import": "from .core.enums import",
    "from .core.rule import": "from .core.rule import",
    "from .core.anchor import": "from .core.anchor import",
    "from .core.kinds import": "from .core.kinds import",

    "from ..filtering.ignore_rules import": "from ..filtering.ignore_rules import",
    "from ..filtering.policy import": "from ..filtering.policy import",
    "from ..filtering.rule_filtering import": "from ..filtering.rule_filtering import",

    "from .filtering.ignore_rules import": "from .filtering.ignore_rules import",
    "from .filtering.policy import": "from .filtering.policy import",
    "from .filtering.rule_filtering import": "from .filtering.rule_filtering import",

    "from ..selection.file_selection import": "from ..selection.file_selection import",
    "from ..selection.node_selector import": "from ..selection.node_selector import",

    "from .selection.file_selection import": "from .selection.file_selection import",
    "from .selection.node_selector import": "from .selection.node_selector import",

    "from .runtime.logging_config import": "from .runtime.logging_config import",
    "from ..runtime.logging_config import": "from ..runtime.logging_config import",
}


def ensure_packages():
    for package in ["core", "filtering", "selection", "runtime"]:
        path = ROOT / package
        path.mkdir(parents=True, exist_ok=True)
        init = path / "__init__.py"
        if not init.exists():
            init.write_text("", encoding="utf-8")


def move_files():
    for src, dst in MOVES.items():
        src_path = ROOT / src
        dst_path = ROOT / dst

        if not src_path.exists():
            print(f"skip missing: {src_path}")
            continue

        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))
        print(f"moved: {src_path} -> {dst_path}")


def rewrite_imports():
    targets = [
        Path("astanalyzer"),
        Path("tests"),
        Path("tools"),
    ]

    for root in targets:
        if not root.exists():
            continue

        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue

            text = path.read_text(encoding="utf-8")
            original = text

            for old, new in REPLACEMENTS.items():
                text = text.replace(old, new)

            if text != original:
                path.write_text(text, encoding="utf-8")
                print(f"updated imports: {path}")


def main():
    ensure_packages()
    move_files()
    rewrite_imports()
    print("Done. Run: pytest")


if __name__ == "__main__":
    main()