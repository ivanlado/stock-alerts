"""Pre-commit check: requirements.txt lists exactly the packages src/ imports.

Only the package NAMES are compared, never the versions. Regenerating the file
on every commit (what the hook did before) re-pinned every package to the
latest release on PyPI, so an unrelated commit would silently upgrade pandas in
CI. Here the pins stay as written, and the check fails only when an import was
added or removed without updating the file -- which is the mistake worth
catching.

pipreqs does the import-to-package mapping (``import dotenv`` is the
``python-dotenv`` package). It asks PyPI for that, so the check needs network.
"""

import re
import subprocess
import sys
from pathlib import Path

REQUIREMENTS = Path("requirements.txt")


def _names(lines: list[str]) -> set[str]:
    """Package names, lowercased, with any version specifier cut off."""
    names = set()
    for line in lines:
        line = line.split("#", 1)[0].strip()
        if line:
            names.add(re.split(r"[=<>~!\s\[]", line, maxsplit=1)[0].lower())
    return names


def main() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pipreqs.pipreqs", "src", "--print", "--mode", "no-pin"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr)
        return result.returncode

    imported = _names(result.stdout.splitlines())
    listed = _names(REQUIREMENTS.read_text(encoding="utf-8").splitlines())

    missing = sorted(imported - listed)
    unused = sorted(listed - imported)
    if missing:
        print(f"Imported but not in requirements.txt: {', '.join(missing)}")
    if unused:
        print(f"In requirements.txt but no longer imported: {', '.join(unused)}")
    return 1 if missing or unused else 0


if __name__ == "__main__":
    sys.exit(main())
