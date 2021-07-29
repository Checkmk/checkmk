#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import cmk.base.agent_based.checking._cluster_modes as cluster_modes

from cmk.base.api.agent_based.checking_classes import CheckResult, CheckPlugin, Result, State


def _get_test_check_plugin(**kwargs) -> CheckPlugin:
    return CheckPlugin(**{  # type: ignore[arg-type]
        **{
            'name': None,
            'sections': None,
            'service_name': None,
            'discovery_function': None,
            'discovery_default_parameters': None,
            'discovery_ruleset_name': None,
            'discovery_ruleset_type': None,
            'check_function': None,
            'check_default_parameters': None,
            'check_ruleset_name': None,
            'cluster_check_function': None,
            'module': None,
        },
        **kwargs,
    })


def _simple_check(item, section) -> CheckResult:
    yield Result(state=State.OK, summary="I handle clusters")


def test_get_cluster_check_function_naitive_missing():
    plugin = _get_test_check_plugin(cluster_check_function=None)

    cc_function = cluster_modes.get_cluster_check_function(
        mode='native',
        clusterization_parameters={},
        plugin=plugin,
    )

    assert list(cc_function()) == [
        Result(state=State.UNKNOWN,
               summary=("This service is not ready to handle clustered data. "
                        "Please change your configuration.")),
    ]


def test_get_cluster_check_function_naitive_ok():
    plugin = _get_test_check_plugin(cluster_check_function=_simple_check)

    cc_function = cluster_modes.get_cluster_check_function(
        mode='native',
        clusterization_parameters={},
        plugin=plugin,
    )

    assert cc_function is _simple_check
