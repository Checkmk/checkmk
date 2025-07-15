#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bi.compiler import BICompiler
from cmk.bi.lib import SitesCallback
from cmk.bi.packs import BIAggregationPacks
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _

from .bi_manager import all_sites_with_id_and_online, bi_livestatus_query, BIManager


def is_part_of_aggregation(host: str, service: str) -> bool:
    if BIAggregationPacks.get_num_enabled_aggregations() == 0:
        return False
    return _get_cached_bi_compiler().is_part_of_aggregation(host, service)


@request_memoize()
def _get_cached_bi_compiler() -> BICompiler:
    return BICompiler(
        BIManager.bi_configuration_file(),
        SitesCallback(all_sites_with_id_and_online, bi_livestatus_query, _),
    )
