#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.type_defs import ColumnName, ContextFilterConfig, FilterHTTPVariables, FilterName
from cmk.gui.views.drilldown_filters import drop_reason, filter_drilldown, filter_keys
from cmk.gui.visuals.filter import filter_registry
from cmk.gui.visuals.filter.drilldowns import RowValues

from .model.contextual_link import VisualLocation
from .model.link_properties import (
    DroppedFilter,
    EncodedFilter,
    FilterResult,
    LinkProperties,
    ResolvedLink,
)


@dataclass(frozen=True)
class EffectiveLink:
    title: str
    location: VisualLocation
    include_context: bool
    include_time_range: bool
    show_filter_form: bool
    # None carries the native click key, a sequence exactly the filters a custom link configures.
    filters: Sequence[ContextFilterConfig] | None = None

    def to_api(self) -> ResolvedLink:
        return ResolvedLink(
            title=self.title,
            location=self.location,
            include_context=self.include_context,
            include_time_range=self.include_time_range,
            show_filter_form=self.show_filter_form,
        )


def view_link(
    title: str, view_name: str, *, include_context: bool, show_filter_form: bool = False
) -> EffectiveLink:
    """The built-in link of a widget to a built-in view."""
    return EffectiveLink(
        title=title,
        location=VisualLocation(type="views", name=view_name, owner=None),
        include_context=include_context,
        include_time_range=False,
        show_filter_form=show_filter_form,
    )


def link_properties_for(
    links: Sequence[EffectiveLink],
    native_key: Mapping[FilterName, FilterHTTPVariables],
    row: RowValues | None = None,
) -> LinkProperties:
    """One map per link: the native click key, or the configured filters, valued from the
    native key first and then from the row."""
    return LinkProperties(
        links=[
            _encoded(native_key)
            if link.filters is None
            else {
                filter_name: _encoded_filter(filter_name, keys, native_key, row)
                for filter_name, keys in filter_keys(link.filters).items()
            }
            for link in links
        ]
    )


def link_columns(links: Sequence[EffectiveLink]) -> list[ColumnName]:
    """The columns a row needs for the filters the links configure. Not the site, which comes
    with every row."""
    return sorted(
        {
            column
            for link in links
            for filter_config in link.filters or []
            if (drilldown := filter_drilldown(filter_config["filter_id"])) is not None
            for column in drilldown.columns
        }
        - {"site"}
    )


def with_link_columns(
    columns: Sequence[ColumnName], links: Sequence[EffectiveLink]
) -> list[ColumnName]:
    """The columns a widget queries, plus those its links' filters read."""
    return [*columns, *(column for column in link_columns(links) if column not in columns)]


def _encoded(key: Mapping[FilterName, FilterHTTPVariables]) -> dict[FilterName, FilterResult]:
    return {
        filter_name: EncodedFilter(status="encoded", variables=dict(variables))
        for filter_name, variables in key.items()
    }


def _encoded_filter(
    filter_name: FilterName,
    keys: Sequence[str],
    native_key: Mapping[FilterName, FilterHTTPVariables],
    row: RowValues | None,
) -> FilterResult:
    if filter_name not in filter_registry:
        return DroppedFilter(status="dropped", reason="not_available")
    if (variables := native_key.get(filter_name)) is not None:
        return EncodedFilter(status="encoded", variables=dict(variables))
    missing = list(keys)
    if row is not None and (drilldown := filter_drilldown(filter_name)) is not None:
        variables, missing = drilldown.carried(row, keys)
    missing_keys: list[str] | ApiOmitted = missing or ApiOmitted()
    if variables is None:
        return DroppedFilter(status="dropped", reason=drop_reason(keys), missing_keys=missing_keys)
    return EncodedFilter(status="encoded", variables=dict(variables), missing_keys=missing_keys)
