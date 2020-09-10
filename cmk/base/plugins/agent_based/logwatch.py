#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#########################################################################################
#                                                                                       #
#                                 !!   W A T C H   O U T   !!                           #
#                                                                                       #
#   The logwatch plugin is notorious for being an exception to just about every rule    #
#   or best practice that applies to check plugin development.                          #
#   It is highly discouraged to use this a an example!                                  #
#                                                                                       #
#########################################################################################

from typing import Any, Dict, List

from .agent_based_api.v1.type_defs import Parameters


def compile_params(rules: List[Parameters]) -> Dict[str, Any]:
    compiled_params: Dict[str, Any] = {"reclassify_patterns": []}

    for rule in rules:
        if isinstance(rule, dict):
            compiled_params["reclassify_patterns"].extend(rule["reclassify_patterns"])
            if "reclassify_states" in rule:
                # (mo) wondering during migration: doesn't this mean the last one wins?
                compiled_params["reclassify_states"] = rule["reclassify_states"]
        else:
            compiled_params["reclassify_patterns"].extend(rule)

    return compiled_params
