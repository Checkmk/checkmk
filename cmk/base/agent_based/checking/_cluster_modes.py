#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Compute the cluster check function from the plugin and parameters."""

from typing import (
    Any,
    Literal,
    Mapping,
)

from cmk.base.api.agent_based.checking_classes import (
    CheckFunction,
    CheckPlugin,
    CheckResult,
    Result,
    State,
)


def _unfit_for_clustering(**_kw) -> CheckResult:
    """A cluster_check_function that displays a generic warning"""
    yield Result(
        state=State.UNKNOWN,
        summary=("This service is not ready to handle clustered data. "
                 "Please change your configuration."),
    )


def get_cluster_check_function(
    *,
    mode=Literal['native'],  # , 'worst', 'failover', 'best'],
    clusterization_parameters: Mapping[str, Any],
    plugin: CheckPlugin,
) -> CheckFunction:
    if mode == 'native':
        return plugin.cluster_check_function or _unfit_for_clustering

    raise NotImplementedError()
