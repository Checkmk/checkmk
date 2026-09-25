#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cmk.gui.type_defs import FilterHTTPVariables, FilterName

from .model.contextual_link import VisualLocation
from .model.link_properties import EncodedFilter, FilterResult, LinkProperties, ResolvedLink


@dataclass(frozen=True)
class EffectiveLink:
    title: str
    location: VisualLocation
    include_context: bool
    include_time_range: bool
    show_filter_form: bool
    # TODO: add the configured filters once all filters are defined.

    def to_api(self) -> ResolvedLink:
        return ResolvedLink(
            title=self.title,
            location=self.location,
            include_context=self.include_context,
            include_time_range=self.include_time_range,
            show_filter_form=self.show_filter_form,
        )


def link_properties_for(
    links: Sequence[EffectiveLink],
    native_key: Mapping[FilterName, FilterHTTPVariables],
) -> LinkProperties:
    """One map per link holding the native click key."""
    encoded: dict[FilterName, FilterResult] = {
        filter_name: EncodedFilter(status="encoded", variables=dict(variables))
        for filter_name, variables in native_key.items()
    }
    return LinkProperties(links=[dict(encoded) for _link in links])
