#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.visuals.filter import filter_registry

# `monitor_all_hosts.py` and `monitor_host_services.py` reserve these three URL query
# parameters for their non-filter display state (visible columns, sort, row limit). Filter
# variables are otherwise page-scoped, but `_active_filter_flag` walks every URL variable in
# the request and reverse-maps it through this registry - so a filter that ever claimed one of
# these names would silently activate itself the moment either page reads legacy filter vars.
RESERVED_URL_VARS = {"cols", "sort", "limit"}


def test_no_filter_htmlvar_collides_with_a_reserved_table_state_name() -> None:
    for filt in filter_registry.values():
        collisions = RESERVED_URL_VARS.intersection(filt.htmlvars)
        assert not collisions, (
            f"Filter {filt.ident!r} uses reserved URL variable(s) {sorted(collisions)} "
            f"(htmlvars={filt.htmlvars}); rename it or the table-state key it collides with."
        )
