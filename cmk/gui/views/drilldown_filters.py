#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The filters a drill-down may carry, each valued from the clicked row."""

import re
from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import Literal

from cmk.gui.data_source import ABCDataSource
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.type_defs import ContextFilterConfig, ContextualLinkTargetType, FilterName, InfoName
from cmk.gui.visuals import info_params
from cmk.gui.visuals.filter import Filter, filter_registry
from cmk.gui.visuals.filter.drilldowns import AuxTagKey, Drilldown, FilterKey
from cmk.gui.visuals.info import visual_info_registry

type DropReason = Literal["no_value", "no_such_key", "not_available"]

# The leading underscore keeps it out of the filters' HTTP variables.
DROPPED_FILTERS_VAR = "_dropped_filters"
# The warning names a filter this edition lacks by this ID, which comes from the URL.
_FILTER_ID = re.compile(r"[A-Za-z0-9_]+")
# A dropped key comes from the URL as well, so it may carry neither markup nor a sentence.
_KEY = re.compile(r"[^\s<>&\"']+")


@dataclass(frozen=True)
class Dropped:
    """A filter a drill-down left out, or one key of it."""

    filter_name: FilterName
    reason: DropReason
    key: str | None = None


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


def filter_keys(filters: Iterable[ContextFilterConfig]) -> dict[FilterName, list[str]]:
    """The configured filters, each with its keys: one filter takes all its label keys, tag
    groups or aux tags at once."""
    keys_by_filter: dict[FilterName, list[str]] = {}
    for filter_config in filters:
        keys = keys_by_filter.setdefault(filter_config["filter_id"], [])
        if "key" in filter_config:
            keys.append(filter_config["key"])
    return keys_by_filter


def filled_single_infos(filter_names: Iterable[FilterName]) -> set[InfoName]:
    """The infos whose single-object filters are all among the filters."""
    names = set(filter_names)
    return {
        ident
        for ident in visual_info_registry
        if (single_info_filters := info_params(ident)) and set(single_info_filters) <= names
    }


def drop_reason(keys: Sequence[str]) -> DropReason:
    """Why a filter the row could not value drops: a qualified filter misses its key."""
    return "no_such_key" if keys else "no_value"


def dropped_filters_variable(dropped: Iterable[Dropped]) -> str:
    return ",".join(
        f"{entry.filter_name}:{entry.reason}" + ("" if entry.key is None else f":{entry.key}")
        for entry in dropped
    )


def dropped_filters_warning(request: Request) -> str | None:
    """The warning naming the filters a drill-down to this page left out, and why."""
    if not (variable := request.get_str_input(DROPPED_FILTERS_VAR)):
        return None
    reasons = {
        "no_value": _("the clicked object has no value for it"),
        "no_such_key": _("the clicked object lacks the configured key"),
        "not_available": _("it is not available here"),
    }
    dropped = [
        f"{_filter_title(filter_name)}{f' ({key})' if key else ''}: {reasons[reason]}"
        for filter_name, reason, key in map(_dropped_entry, variable.split(","))
        if reason in reasons
        and _FILTER_ID.fullmatch(filter_name)
        and (not key or _KEY.fullmatch(key))
    ]
    if not dropped:
        return None
    return _(
        "These filters could not be carried over, so this page shows a wider scope than the "
        "clicked object: %(filters)s"
    ) % {"filters": "; ".join(dropped)}


def _dropped_entry(entry: str) -> tuple[str, str, str]:
    """The filter, the reason and the key, empty for a whole filter, of `filter:reason[:key]`."""
    filter_name, _sep, rest = entry.partition(":")
    reason, _sep, key = rest.partition(":")
    return filter_name, reason, key


def _filter_title(filter_name: FilterName) -> str:
    """A filter this edition lacks is named by its ID."""
    return filter_name if (filter_ := filter_registry.get(filter_name)) is None else filter_.title
