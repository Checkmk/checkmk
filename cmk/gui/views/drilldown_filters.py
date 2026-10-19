#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The filters a drill-down may carry, each valued from the clicked row."""

from collections import Counter
from collections.abc import Iterable, Iterator

from cmk.gui.data_source import ABCDataSource
from cmk.gui.type_defs import ContextualLinkTargetType, FilterName, InfoName
from cmk.gui.visuals import info_params
from cmk.gui.visuals.filter import Filter, filter_registry
from cmk.gui.visuals.filter.drilldowns import AuxTagKey, Drilldown, FilterKey
from cmk.gui.visuals.info import visual_info_registry


def filter_drilldown(filter_name: FilterName) -> Drilldown | None:
    """How a drill-down values the filter from a row; None for a filter it can't carry, or
    one this edition lacks."""
    return None if (filter_ := filter_registry.get(filter_name)) is None else filter_.drilldown


def filter_key(filter_name: FilterName) -> FilterKey | None:
    """The key the filter takes, such as a label key; None for a filter that takes none."""
    return None if (drilldown := filter_drilldown(filter_name)) is None else drilldown.key


def exceeded_aux_tag_limits(filter_names: Iterable[FilterName]) -> Iterator[int]:
    """The field count of each aux tag filter listed more often than it has fields."""
    for filter_name, count in Counter(filter_names).items():
        if isinstance(key := filter_key(filter_name), AuxTagKey) and count > key.max_count:
            yield key.max_count


def drilldown_filters(
    data_source: ABCDataSource, target_type: ContextualLinkTargetType
) -> list[FilterName]:
    return [
        filter_name
        for filter_name, filter_ in sorted(filter_registry.items(), key=_menu_order)
        if filter_.drilldown is not None
        and filter_.available()
        and filter_.info in data_source.infos
        # A dashboard's context takes only host and service filters.
        and (target_type == "views" or filter_.info in ("host", "service"))
        # A Stats query counts log entries per object, so a log filter would split its counts.
        and not (filter_.info == "log" and "Stats:" in data_source.add_headers)
    ]


def _menu_order(item: tuple[FilterName, Filter]) -> tuple[int, str]:
    """The order the filter menus list the filters in."""
    return item[1].sort_index, item[1].title


def filled_single_infos(filter_names: Iterable[FilterName]) -> set[InfoName]:
    """The infos whose single-object filters are all among the filters."""
    names = set(filter_names)
    return {
        ident
        for ident in visual_info_registry
        if (single_info_filters := info_params(ident)) and set(single_info_filters) <= names
    }
