#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Union

from cmk.base.plugins.agent_based.utils.kube import (
    DisplayableStrategy,
    OnDelete,
    Recreate,
    RollingUpdate,
    StatefulSetRollingUpdate,
)
from cmk.base.plugins.agent_based.utils.kube_strategy import strategy_text


def test_strategy_text() -> None:
    assert (
        strategy_text(RollingUpdate(max_surge="25%", max_unavailable="25%"))
        == "RollingUpdate (max surge: 25%, max unavailable: 25%)"
    )
    assert strategy_text(Recreate()) == "Recreate"
    assert strategy_text(OnDelete()) == "OnDelete"
    assert (
        strategy_text(StatefulSetRollingUpdate(partition=0)) == "RollingUpdate (partitioned at: 0)"
    )


def test_strategy_is_displayable() -> None:
    """

    Any entry of DisplayableStrategy needs to be handled by strategy_text. By
    default, strategy_text will simply display type_. If this is the intended
    behaviour or you have reworked strategy_text to handle the new strategy,
    then you may add it here.
    """
    assert DisplayableStrategy == Union[RollingUpdate, Recreate, OnDelete, StatefulSetRollingUpdate]
