#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path

import pytest

from cmk.repo_checks.python_extension_checker import (
    has_python_extension_violation,
    is_executable_wrapper,
    is_python_source,
    is_text_file,
)


@pytest.mark.parametrize(
    "content, expected",
    [
        ("#!/usr/bin/env python3\n", True),
        ("import os\n", True),
        ("def foo():\n    pass\n", True),
        ("class Foo:\n    pass\n", True),
        ("", False),
        ("just some prose without code\n", False),
        ("key = value\nother stuff", False),
    ],
)
def test_is_python_source(content: str, expected: bool) -> None:
    assert is_python_source(content) is expected


def test_is_text_file(tmp_path: Path) -> None:
    text = tmp_path / "text"
    text.write_text("hello world\n")
    assert is_text_file(text) is True

    binary = tmp_path / "binary"
    binary.write_bytes(b"\xff\xfe\x00\x01\x02")
    assert is_text_file(binary) is False


def test_is_executable_wrapper() -> None:
    wrapper = (
        "#!/usr/bin/env python3\n"
        "# Copyright (C) 2026 Checkmk GmbH\n"
        "from cmk.base.foo import main\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )
    assert is_executable_wrapper(wrapper) is True
    # Missing the cmk import disqualifies it as a recognized wrapper.
    assert is_executable_wrapper("#!/usr/bin/env python3\nprint('hi')\n") is False


def test_violation_python_file_without_extension(tmp_path: Path) -> None:
    script = tmp_path / "some_script"
    script.write_text("#!/usr/bin/env python3\nimport sys\nprint(sys.argv)\n")
    assert has_python_extension_violation(script) is True


def test_no_violation_for_dot_py(tmp_path: Path) -> None:
    script = tmp_path / "some_script.py"
    script.write_text("import sys\n")
    assert has_python_extension_violation(script) is False


def test_no_violation_for_non_python_text(tmp_path: Path) -> None:
    doc = tmp_path / "notes"
    doc.write_text("just a plain text note, no code here\n")
    assert has_python_extension_violation(doc) is False


def test_no_violation_for_ignored_suffix(tmp_path: Path) -> None:
    conf = tmp_path / "settings.yaml"
    conf.write_text("import: this looks like python but is yaml\n")
    assert has_python_extension_violation(conf) is False
