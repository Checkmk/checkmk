#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List
from .agent_based_api.v0.type_defs import DiscoveryGenerator, Parameters

from .agent_based_api.v0 import register, Service
from .utils import ps


def discover_ps(params: List[Parameters], section: ps.Section) -> DiscoveryGenerator:
    inventory_specs = ps.get_discovery_specs(params)

    for process_info, command_line in section[1]:
        for servicedesc, pattern, userspec, cgroupspec, _labels, default_params in inventory_specs:
            if not ps.process_attributes_match(process_info, userspec, cgroupspec):
                continue
            matches = ps.process_matches(command_line, pattern)
            if not matches:
                continue  # skip not matched lines

            # User capturing on rule
            if userspec is False:
                i_userspec = process_info.user
            else:
                i_userspec = userspec

            i_servicedesc = servicedesc.replace("%u", i_userspec or "")

            # Process capture
            match_groups = matches.groups() if hasattr(matches, 'groups') else ()

            i_servicedesc = ps.replace_service_description(i_servicedesc, match_groups, pattern)

            # Problem here: We need to instantiate all subexpressions
            # with their actual values of the found process.
            inv_params = {
                "process": pattern,
                "match_groups": match_groups,
                "user": i_userspec,
                "cgroup": cgroupspec,
            }

            # default_params is either a clean dict with optional
            # parameters to set as default or - from version 1.2.4 - the
            # dict from the rule itself. In the later case we need to remove
            # the keys that do not specify default parameters
            for key, value in default_params.items():
                if key not in ("descr", "match", "user", "perfdata"):
                    inv_params[key] = value

            yield Service(
                item=i_servicedesc,
                parameters=inv_params,
            )


# Currently a dummy registration to allow passing the host_label_function parameters
# proper migration is WIP!
def _mock_check(item, section):
    return
    yield  # pylint: disable=unreachable


register.check_plugin(
    name="ps",
    service_name="Process %s",
    discovery_function=discover_ps,
    discovery_ruleset_name="inventory_processes_rules",
    discovery_default_parameters={},
    check_function=_mock_check,
)
