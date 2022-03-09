#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest  # type: ignore[import]

from tests.testlib import Check  # type: ignore[import]


def _get_and_try_cast_to_int(key, container, default_value=None):
    return Check("netapp_api_fcp").context["_get_and_try_cast_to_int"](key, container,
                                                                       default_value)


def test_get_and_try_cast_to_int():
    container = {"ok": "1", "broken": "1,2,3,4,5"}

    assert _get_and_try_cast_to_int("ok", container) == 1
    assert _get_and_try_cast_to_int("key_not_available", container, 2) == 2
    with pytest.raises(RuntimeError) as e:
        _get_and_try_cast_to_int("broken", container)
    assert "NetApp Firmware" in str(e.value)
