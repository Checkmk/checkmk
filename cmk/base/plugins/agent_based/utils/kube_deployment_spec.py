#!/usr/bin/env python3
# -*- coding: utf-8 -*
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Union

from .k8s import Recreate, RollingUpdate


def strategy_text(deployment_strategy: Union[RollingUpdate, Recreate]) -> str:
    if isinstance(deployment_strategy, RollingUpdate):
        return (
            f"{deployment_strategy.type_} "
            f"(max surge: {deployment_strategy.max_surge}, "
            f"max unavailable: {deployment_strategy.max_unavailable})"
        )
    return deployment_strategy.type_
