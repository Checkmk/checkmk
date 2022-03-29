#!/usr/bin/env python3
# -*- coding: utf-8 -*
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.utils.kube import (
    DisplayableStrategy,
    RollingUpdate,
    StatefulSetRollingUpdate,
)


def strategy_text(strategy: DisplayableStrategy) -> str:
    """Used for Deployment, StatefulSet and DaemonSet"""

    if isinstance(strategy, RollingUpdate):
        return (
            f"{strategy.type_} "
            f"(max surge: {strategy.max_surge}, "
            f"max unavailable: {strategy.max_unavailable})"
        )
    if isinstance(strategy, StatefulSetRollingUpdate):
        return f"RollingUpdate (partitioned at: {strategy.partition})"
    return strategy.type_
