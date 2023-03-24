#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.base.check_legacy_includes.netapp_api import get_and_try_cast_to_int


def test_get_and_try_cast_to_int_ok() -> None:
    assert get_and_try_cast_to_int("ok", {"ok": "1"}) == 1


def test_get_and_try_cast_to_int_default() -> None:
    assert get_and_try_cast_to_int("key_not_available", {}, 2) == 2


def test_get_and_try_cast_to_int_broken() -> None:
    with pytest.raises(RuntimeError) as e:
        get_and_try_cast_to_int("broken", {"broken": "1,2,3,4,5"})
    assert "NetApp Firmware" in str(e.value)
