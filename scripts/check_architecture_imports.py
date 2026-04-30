import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
PLUGINS_DIR = ROOT / "plugins"


def should_ignore(path: Path) -> bool:
    return "__pycache__" in path.parts or path.suffix != ".py"


def scan():
    violations = []
    for py_file in SRC_DIR.rglob("*.py"):
        if should_ignore(py_file):
            continue
        rel = py_file.relative_to(ROOT).as_posix()
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            stripped = line.strip()
            if not (stripped.startswith("from ") or stripped.startswith("import ")):
                continue
            if "plugins." in stripped:
                allowed = "extension_bridge" in rel or rel == "src/ui/main.py"
                if not allowed:
                    violations.append(f"{rel}: import proibido de plugins -> {stripped}")
    for py_file in PLUGINS_DIR.rglob("*.py"):
        if should_ignore(py_file):
            continue
        rel = py_file.relative_to(ROOT).as_posix()
        text = py_file.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            stripped = line.strip()
            if not (stripped.startswith("from ") or stripped.startswith("import ")):
                continue
            if "src.ui." in stripped:
                violations.append(f"{rel}: plugin não deve importar UI concreta -> {stripped}")
    return violations


def main():
    violations = scan()
    if violations:
        print("Architecture import violations:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("Architecture import check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
