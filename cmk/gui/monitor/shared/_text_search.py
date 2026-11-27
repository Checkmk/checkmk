#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def contains_wildcard(text: str, query: str) -> bool:
    """Whether ``text`` contains ``query``, ignoring case, with ``*`` matching any text and every
    other character taken literally - the search on what the GUI knows and the core does not, e.g.
    folder titles or sites.

    The parts between the stars are looked up in order, each at its earliest place, which takes
    time linear in the text where a regular expression could backtrack without end.

        >>> contains_wildcard("Data center Munich / Rack 1", "rack*1")
        True
        >>> contains_wildcard("Rack (2)", "(2")
        True
        >>> contains_wildcard("Rack 1", "1*rack")
        False
    """
    haystack = text.lower()
    start = 0
    for part in query.lower().split("*"):
        if (found := haystack.find(part, start)) < 0:
            return False
        start = found + len(part)
    return True
