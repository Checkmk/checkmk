#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.valuespec import DropdownChoiceEntries

from cmk.bi.compiler import BICompiler
from cmk.bi.lib import SitesCallback
from cmk.bi.packs import BIAggregationPacks

from .bi_manager import all_sites_with_id_and_online, bi_livestatus_query, BIManager
from .foldable_tree_renderer import FoldableTreeRendererTree

__all__ = [
    "BIManager",
    "FoldableTreeRendererTree",
    "is_part_of_aggregation",
    "get_aggregation_group_trees",
    "aggregation_group_choices",
    "get_cached_bi_packs",
]


def is_part_of_aggregation(host, service) -> bool:  # type:ignore[no-untyped-def]
    if BIAggregationPacks.get_num_enabled_aggregations() == 0:
        return False
    return _get_cached_bi_compiler().is_part_of_aggregation(host, service)


@request_memoize()
def _get_cached_bi_compiler() -> BICompiler:
    return BICompiler(
        BIManager.bi_configuration_file(),
        SitesCallback(all_sites_with_id_and_online, bi_livestatus_query, _),
    )


def get_aggregation_group_trees():
    # Here we have to deal with weird legacy
    # aggregation group definitions:
    # - "GROUP"
    # - ["GROUP_1", "GROUP2", ..]

    return get_cached_bi_packs().get_aggregation_group_trees()


def aggregation_group_choices() -> DropdownChoiceEntries:
    """Returns a sorted list of aggregation group names"""
    return get_cached_bi_packs().get_aggregation_group_choices()


@request_memoize()
def get_cached_bi_packs() -> BIAggregationPacks:
    bi_packs = BIAggregationPacks(BIManager.bi_configuration_file())
    bi_packs.load_config()
    return bi_packs
