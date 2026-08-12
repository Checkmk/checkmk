#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.visuals.filter import filter_registry

# `monitor_all_hosts.py` and `monitor_host_services.py` reserve these URL query parameters:
# `cols`/`sort`/`limit` for their non-filter display state, `filter`/`q` for their own
# column-filter tree and applied search text. Filter variables are otherwise page-scoped, but
# `_active_filter_flag` walks every URL variable in the request and reverse-maps it through
# this registry - so a filter that ever claimed one of these names would silently activate
# itself the moment either page reads legacy filter vars.
#
# This only sees whichever edition's filters got loaded into the shared `filter_registry`
# singleton for this test target (`EDITION` in the bazel `py_cmk_test`) - a pro/cloud/ultimate/
# ultimatemt-only filter never runs through this community-only target. Keep this mirrored in
# tests/unit/cmk/gui/nonfree/{pro,cloud,ultimate,ultimatemt}/visuals/filter/, since each of
# those editions registers a different extra set of filters into that same registry.
RESERVED_URL_VARS = {"cols", "sort", "limit", "filter", "q"}


def test_no_filter_htmlvar_collides_with_a_reserved_table_state_name() -> None:
    # An empty registry would make the loop below vacuously pass - assert plugin loading
    # actually ran before trusting the absence of collisions.
    assert filter_registry, "filter_registry is empty - plugin loading is broken for this edition"
    for filt in filter_registry.values():
        collisions = RESERVED_URL_VARS.intersection(filt.htmlvars)
        assert not collisions, (
            f"Filter {filt.ident!r} uses reserved URL variable(s) {sorted(collisions)} "
            f"(htmlvars={filt.htmlvars}); rename it or the table-state key it collides with."
        )
