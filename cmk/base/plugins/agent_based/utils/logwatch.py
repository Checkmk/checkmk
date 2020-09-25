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

from typing import Any, Counter, Dict, Iterable, List, Optional, Sequence, Set, TypedDict

import re

from ..agent_based_api.v1.type_defs import Parameters
from ..agent_based_api.v1 import regex, Result, State as state

ItemData = TypedDict(
    "ItemData",
    {
        'attr': str,
        'lines': List[str],
    },
    total=True,
)

Section = TypedDict(
    "Section",
    {
        'errors': List[str],
        'logfiles': Dict[str, ItemData],
    },
    total=True,
)


def discoverable_items(*sections: Section) -> List[str]:
    """only consider files which are 'ok' on at least one node"""
    return sorted({
        item for node_data in sections for item, item_data in node_data['logfiles'].items()
        if item_data['attr'] == 'ok'
    })


def ec_forwarding_enabled(params: Parameters, item: str) -> bool:
    if 'restrict_logfiles' not in params:
        return True  # matches all logs on this host

    # only logs which match the specified patterns
    return any(re.match(pattern, item) for pattern in params['restrict_logfiles'])


def select_forwarded(
    items: Sequence[str],
    forward_settings: List[Parameters],
    *,
    invert: bool = False,
) -> Set[str]:
    # Is forwarding enabled in general?
    if not (forward_settings and forward_settings[0]):
        return set(items) if invert else set()

    return {
        item for item in items if ec_forwarding_enabled(forward_settings[0], item) is not invert
    }


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


def errors(cluster_section: Dict[Optional[str], Section]) -> Iterable[Result]:
    """
        >>> cluster_section = {
        ...     None: {"errors": ["error w/o node info"]},
        ...     "node": {"errors": ["some error"]},
        ... }
        >>> for r in errors(cluster_section):
        ...     print((r.state, r.summary))
        (<State.UNKNOWN: 3>, 'error w/o node info')
        (<State.UNKNOWN: 3>, '[node] some error')
    """
    for node, node_data in cluster_section.items():
        for error_msg in node_data['errors']:
            yield Result(
                state=state.UNKNOWN,
                summary=error_msg if node is None else "[%s] %s" % (node, error_msg),
            )
