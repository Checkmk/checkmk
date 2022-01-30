#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.utils.kube_deployment_strategy import (
    Recreate,
    RollingUpdate,
    strategy_text,
)


def test_rolling_update_text() -> None:
    assert (
        strategy_text(RollingUpdate(type_="RollingUpdate", max_surge="25%", max_unavailable="25%"))
        == "RollingUpdate (max surge: 25%, max unavailable: 25%)"
    )
    assert strategy_text(Recreate(type_="Recreate")) == "Recreate"
