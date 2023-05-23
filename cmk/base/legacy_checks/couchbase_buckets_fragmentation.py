#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import (
    check_levels,
    discover,
    get_percent_human_readable,
    LegacyCheckDefinition,
)
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.utils.couchbase import parse_couchbase_lines


def check_couchbase_buckets_fragmentation(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    docs_fragmentation = data.get("couch_docs_fragmentation")
    if docs_fragmentation is not None:
        yield check_levels(
            docs_fragmentation,
            "docs_fragmentation",
            params.get("docs"),
            infoname="Documents fragmentation",
            human_readable_func=get_percent_human_readable,
        )

    views_fragmentation = data.get("couch_views_fragmentation")
    if views_fragmentation is not None:
        yield check_levels(
            views_fragmentation,
            "views_fragmentation",
            params.get("views"),
            infoname="Views fragmentation",
            human_readable_func=get_percent_human_readable,
        )


check_info["couchbase_buckets_fragmentation"] = LegacyCheckDefinition(
    parse_function=parse_couchbase_lines,
    discovery_function=discover(lambda _k, v: "couch_docs_fragmentation" in v),
    check_function=check_couchbase_buckets_fragmentation,
    service_name="Couchbase Bucket %s Fragmentation",
    check_ruleset_name="couchbase_fragmentation",
)
