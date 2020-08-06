#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v0 import register


# Currently a dummy registration to allow passing the host_label_function parameters
# proper migration is WIP!
def _mock_discovery(params, section):
    return
    yield  # pylint: disable=unreachable


def _mock_check(item, section):
    return
    yield  # pylint: disable=unreachable


register.check_plugin(
    name="ps",
    service_name="Process %s",
    discovery_function=_mock_discovery,
    discovery_ruleset_name="inventory_processes_rules",
    discovery_default_parameters={},
    check_function=_mock_check,
)
