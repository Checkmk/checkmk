#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path

import pytest

from cmk.repo_checks.license_header_checker import (
    check_for_license_header_violation,
    is_notification_file,
    needs_enterprise_license,
)

GPL_HEADER = """#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""

ENTERPRISE_HEADER = """#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""


@pytest.mark.parametrize(
    "path, expected",
    [
        ("cmk/base/config.py", False),
        ("non-free/packages/foo/bar.py", True),
        ("cmk/plugins/pro/baz.py", True),
        ("cmk/plugins/cloud/baz.py", True),
        ("some/nonfree/thing.py", True),
        # matches on whole path segments, not substrings
        ("cmk/gui/ultimate.py", False),
    ],
)
def test_needs_enterprise_license(path: str, expected: bool) -> None:
    assert needs_enterprise_license(path) is expected


@pytest.mark.parametrize(
    "path, expected",
    [
        ("notifications/mail.py", True),
        ("packages/cmk-notification-plugins/notifications/mail.py", True),
        ("cmk/base/config.py", False),
    ],
)
def test_is_notification_file(path: str, expected: bool) -> None:
    assert is_notification_file(path) is expected


def _write(base: Path, rel: str, content: str) -> str:
    dst = base / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(content)
    return rel


def test_gpl_header_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    rel = _write(tmp_path, "cmk/example.py", GPL_HEADER)
    assert check_for_license_header_violation(rel) is None


def test_gpl_header_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    rel = _write(tmp_path, "cmk/example.py", "#!/usr/bin/env python3\nprint('no header')\n")
    assert check_for_license_header_violation(rel) == "gpl header not matching"


def test_enterprise_header_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    rel = _write(tmp_path, "non-free/example.py", ENTERPRISE_HEADER)
    assert check_for_license_header_violation(rel) is None


def test_enterprise_path_with_gpl_header_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    rel = _write(tmp_path, "non-free/example.py", GPL_HEADER)
    assert check_for_license_header_violation(rel) == "enterprise header not matching"
