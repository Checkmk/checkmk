#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.kube.schemata.api import (
    OnDelete,
    Recreate,
    RollingUpdate,
    StatefulSetRollingUpdate,
)
from cmk.plugins.lib.kube_strategy import strategy_text


def test_strategy_text() -> None:
    assert (
        strategy_text(RollingUpdate(max_surge="25%", max_unavailable="25%"))
        == "RollingUpdate (max surge: 25%, max unavailable: 25%)"
    )
    assert strategy_text(Recreate()) == "Recreate"
    assert strategy_text(OnDelete()) == "OnDelete"
    assert (
        strategy_text(StatefulSetRollingUpdate(partition=0, max_unavailable="2"))
        == "RollingUpdate (partitioned at: 0, max unavailable: 2)"
    )
