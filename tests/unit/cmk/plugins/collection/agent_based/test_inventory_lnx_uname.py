#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Attributes
from cmk.plugins.collection.agent_based.lnx_uname import inventory_lnx_uname, parse_lnx_uname


@pytest.fixture(name="section", scope="module")
def _get_section() -> Mapping[str, str]:
    return parse_lnx_uname([["x86_64"], ["5.4.0-99-generic"]])


def test_inventory_solaris_uname(section: Mapping[str, str]) -> None:
    assert list(inventory_lnx_uname(section)) == [
        Attributes(
            path=["software", "os"],
            inventory_attributes={
                "arch": "x86_64",
                "kernel_version": "5.4.0-99-generic",
            },
        ),
    ]
