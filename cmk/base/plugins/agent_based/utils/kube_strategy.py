#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
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
        details = f"partitioned at: {strategy.partition}"
        if (max_unavailable := strategy.max_unavailable) is not None:
            details = f"{details}, max unavailable: {max_unavailable}"
        return f"RollingUpdate ({details})"
    return strategy.type_
