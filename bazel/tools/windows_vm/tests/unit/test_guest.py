# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from unittest.mock import Mock

import pytest
from qemu_windows.guest import Guest, GuestError, PASSWORD, ps_quote
from qemu_windows.qga import Qga, QgaError


def test_default_password_is_accepted() -> None:
    guest = Guest(Mock(spec=Qga), lambda: None)

    assert guest.password == PASSWORD


def test_password_that_would_need_escaping_is_rejected() -> None:
    with pytest.raises(GuestError, match="letters, digits and '!'"):
        Guest(Mock(spec=Qga), lambda: None, password="a%b")


def test_powershell_literal_doubles_single_quotes() -> None:
    assert ps_quote(r"C:\it's") == r"'C:\it''s'"


def test_failed_copy_out_of_the_guest_leaves_no_local_file(tmp_path: Path) -> None:
    agent = Mock(spec=Qga)
    agent.execute.side_effect = QgaError("guest-file-open: The system cannot find the file")
    with pytest.raises(GuestError):
        Guest(agent, lambda: None).get("C:\\missing.log", tmp_path / "missing.log")
    assert not list(tmp_path.iterdir())


def test_failed_copy_out_of_the_guest_keeps_the_local_file_it_was_to_replace(
    tmp_path: Path,
) -> None:
    (local := tmp_path / "check_mk.yml").write_text("mine")
    agent = Mock(spec=Qga)
    agent.execute.side_effect = QgaError("guest-file-open: The system cannot find the file")
    with pytest.raises(GuestError):
        Guest(agent, lambda: None).get("C:\\typo\\check_mk.yml", local)
    assert local.read_text() == "mine"
