#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import Final

from cmk.gui.http import request
from cmk.gui.type_defs import VisualContext

_NON_DEFAULT_KEYS_TO_IGNORE: Final = frozenset(
    {"_csrf_token", "_active", "_apply", "selection", "filled_in", "view_name"}
)
_NON_DEFAULT_KEY_REGEX: Final = re.compile(r".*(_op|_bool|_count|_indexof_\d+)$")
_COUNT_KEY_REGEX: Final = re.compile(r".*_count$")
_OP_KEY_REGEX: Final = re.compile(r".*_op$")


def check_if_non_default_filter_in_request(ctx: VisualContext) -> bool:
    if request.var("filled_in") != "filter" or request.var("_active") == "":
        return False

    ctx_keys = set(ctx.keys())
    request_arg_keys = request.args.keys() - _NON_DEFAULT_KEYS_TO_IGNORE

    for active_key in (request.var("_active") or "").split(";"):
        if active_key in ctx:
            ctx_keys.discard(active_key)
            request_arg_keys.discard(active_key)

            if ctx_sub_keys := ctx[active_key].keys():
                request_arg_keys -= ctx_sub_keys
                for sub_key in ctx_sub_keys:
                    given = request.var(sub_key) or ""
                    default = ctx[active_key][sub_key] or ""
                    default = "is" if _OP_KEY_REGEX.match(sub_key) and default == "" else default

                    # Variables with the `_count` suffix and a value of "" are valid as they
                    # can also increase the count.
                    if given != default and not _COUNT_KEY_REGEX.match(sub_key):
                        return True

            # First request check: only hit if key in _active and ctx without sub keys.
            elif request.var(active_key):
                return True

        # Second request check: hit if key found in _active but not in context.
        elif request.var(active_key):
            return True

    # If any request args remain and are not default keys, a filter must exist.
    if any(key for key in request_arg_keys if not _NON_DEFAULT_KEY_REGEX.match(key)):
        return True

    # If any context keys remain post-processing, a filter must exist.
    return bool(ctx_keys)
