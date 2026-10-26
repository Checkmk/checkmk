# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from unittest.mock import Mock

import pytest
from qemu_windows.guest import Guest, GuestError, PASSWORD, ps_quote
from qemu_windows.qga import Qga


def test_default_password_is_accepted() -> None:
    guest = Guest(Mock(spec=Qga), lambda: None)

    assert guest.password == PASSWORD


def test_password_that_would_need_escaping_is_rejected() -> None:
    with pytest.raises(GuestError, match="letters, digits and '!'"):
        Guest(Mock(spec=Qga), lambda: None, password="a%b")


def test_powershell_literal_doubles_single_quotes() -> None:
    assert ps_quote(r"C:\it's") == r"'C:\it''s'"
