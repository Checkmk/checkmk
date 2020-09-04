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

from typing import Any, Counter, Dict, List, TypedDict

import re

from ..agent_based_api.v0 import regex

ItemData = TypedDict(
    "ItemData",
    {
        'attr': str,
        'lines': List[str],
    },
    total=True,
)

SectionLogwatch = TypedDict(
    "SectionLogwatch",
    {
        'errors': List[str],
        'logfiles': Dict[str, ItemData],
    },
    total=True,
)


def reclassify(
    counts: Counter[int],
    patterns: Dict[str, Any],  # all I know right now :-(
    text: str,
    old_level: str,
) -> str:

    # Reclassify state if a given regex pattern matches
    # A match overrules the previous state->state reclassification
    for level, pattern, _ in patterns.get("reclassify_patterns", []):
        reg = regex(pattern, re.UNICODE)
        if reg.search(text):
            # If the level is not fixed like 'C' or 'W' but a pair like (10, 20),
            # then we count how many times this pattern has already matched and
            # assign the levels according to the number of matches of this pattern.
            if isinstance(level, tuple):
                warn, crit = level
                newcount = counts[id(pattern)] + 1
                counts[id(pattern)] = newcount
                if newcount >= crit:
                    return 'C'
                return 'W' if newcount >= warn else 'I'
            return level

    # Reclassify state to another state
    change_state_paramkey = ("%s_to" % old_level).lower()
    return patterns.get("reclassify_states", {}).get(change_state_paramkey, old_level)
