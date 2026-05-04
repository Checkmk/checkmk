#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bi.packs import BIAggregationPacks
from cmk.gui.hooks import request_memoize
from cmk.gui.valuespec import DropdownChoiceEntries

from ._filesystem import get_bi_config_path


def get_aggregation_group_trees() -> list[str]:
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
    bi_packs = BIAggregationPacks(get_bi_config_path())
    bi_packs.load_config()
    return bi_packs
