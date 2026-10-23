#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import override

import pytest

from cmk.gui import hooks
from cmk.gui.watolib.builtin_host_labels import update_builtin_host_labels_file
from cmk.gui.watolib.config_domain_name import (
    configvar_order,
)


def test_builtin_host_labels_hook_registered() -> None:
    assert update_builtin_host_labels_file in [
        hook.handler for hook in hooks.get("pre-activate-changes")
    ]


def test_legacy_configvar_order_access() -> None:
    with pytest.raises(NotImplementedError) as e:
        configvar_order()["x"] = 10
    assert "werk #6911" in "%s" % e


class _EvulToStr:
    @override
    def __str__(self) -> str:
        return "' boom!"
