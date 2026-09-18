#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The deprecated `cmk.inventory_ui.v1_unstable` namespace must stay a faithful alias.

Plug-ins written against Checkmk 2.5 still import it.
It is removed in Checkmk 3.1.
"""

from cmk.inventory_ui import v1 as stable
from cmk.inventory_ui import v1_unstable as unstable


def test_alias_exposes_the_same_names() -> None:
    assert {n for n in vars(unstable) if not n.startswith("_")} == set(stable.__all__)


def test_alias_exposes_the_same_objects() -> None:
    assert [n for n in stable.__all__ if getattr(unstable, n) is not getattr(stable, n)] == []
