#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Final

from cmk.gui.http import request
from cmk.gui.type_defs import VisualContext

_NON_DEFAULT_KEYS_TO_IGNORE: Final = frozenset(
    {
        "_csrf_token",
        "_active",
        "_apply",
        "selection",
        "filled_in",
        "view_name",
    }
)
_NON_DEFAULT_KEY_REGEX: Final = re.compile(r".*(_op|_bool|_count|_indexof_\d+)$")
_COUNT_KEY_REGEX: Final = re.compile(r".*_count$")
_OP_KEY_REGEX: Final = re.compile(r".*_op$")


def requested_filter_is_not_default(mandatory: VisualContext) -> bool:
    """Compare default filters of page with given filter parameters"""
    if request.var("filled_in") != "filter" or request.var("_active") == "":
        return False

    mandatory_not_found = [x for x in mandatory.keys()]

    sub_keys = [x for x in request.args.keys() if x not in _NON_DEFAULT_KEYS_TO_IGNORE]

    for key in (request.var("_active") or "").split(";"):
        if key in mandatory:
            mandatory_not_found = [x for x in mandatory_not_found if key != x]
            sub_keys = [x for x in sub_keys if x != key]

            if len(mandatory_sub := mandatory[key].keys()) > 0:
                # compare each sub_key with the default
                for sub in mandatory_sub:
                    sub_keys = [x for x in sub_keys if x != sub]
                    given = request.var(sub) or ""
                    default = mandatory[key][sub] or ""
                    default = "is" if _OP_KEY_REGEX.match(sub) and default == "" else default

                    # ignore count vars, cause empty vars increase also the count
                    if given != default and not _COUNT_KEY_REGEX.match(sub):
                        return True

            elif request.var(key) and request.var(key) != "":
                return True

        # check if non default request var has a value
        elif request.var(key) and request.var(key) != "":
            return True

    # check for given non default sub keys
    sub_keys = [x for x in sub_keys if not _NON_DEFAULT_KEY_REGEX.match(x)]
    if len(sub_keys) > 0:
        return True

    # check if non default request var has a value
    return bool(mandatory_not_found)
