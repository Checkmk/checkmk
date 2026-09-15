#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from pathlib import Path

import pytest
from extract_os_packages import main

MK_FILE = """\
DISTRO_CODE = jammy
OS_PACKAGES = base-a base-b # the baseline
OS_PACKAGES += libcap2 # capabilities
OS_PACKAGES +=
OS_PACKAGES += curl wget
  OS_PACKAGES += indented
OTHER_VAR += ignored
"""


def test_os_packages_are_collected_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mk_file = tmp_path / "UBUNTU_22.04.mk"
    mk_file.write_text(MK_FILE)
    output = tmp_path / "packages.txt"
    monkeypatch.setattr(sys, "argv", ["extract_os_packages.py", str(mk_file), str(output), ", "])

    assert main() == 0

    assert output.read_text() == "base-a, base-b, libcap2, curl, wget, indented\n"


def test_plain_assignment_resets_earlier_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mk_file = tmp_path / "distro.mk"
    mk_file.write_text("OS_PACKAGES += old\nOS_PACKAGES = fresh\n")
    output = tmp_path / "packages.txt"
    monkeypatch.setattr(sys, "argv", ["extract_os_packages.py", str(mk_file), str(output), " "])

    main()

    assert output.read_text() == "fresh\n"


def test_wrong_argument_count_is_a_usage_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["extract_os_packages.py", "only.mk"])

    assert main() == 2

    assert "usage:" in capsys.readouterr().err
