"""
Every source file and the public documents carry the same copyright line, so the authorship
stated in NOTICE cannot drift from what the individual files say.

Copyright 2026 Harrison Cormier, Ashley Pacek and Varvara Blinova.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LINE = "Copyright 2026 Harrison Cormier, Ashley Pacek and Varvara Blinova"
DOCUMENTS = ["README.md", "SOURCES.md", "NOTICE"]
SOURCE_FILES = sorted(str(p.relative_to(ROOT)) for folder in (".", "tests", "scripts") for p in (ROOT / folder).glob("*.py"))


@pytest.mark.parametrize("name", DOCUMENTS + SOURCE_FILES)
def test_file_carries_the_copyright_line(name):
    assert LINE in (ROOT / name).read_text(encoding="utf-8")


def test_every_python_file_is_covered():
    assert {"app.py", "tire_model.py"} <= set(SOURCE_FILES) and len(SOURCE_FILES) >= 6
