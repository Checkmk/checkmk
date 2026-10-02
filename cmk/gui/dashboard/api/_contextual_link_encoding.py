#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

from cmk.gui.type_defs import FilterHTTPVariables, FilterName
from cmk.livestatus_client import LivestatusColumn

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
    filters: Sequence[FilterName] | None = None

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
    values: Mapping[FilterName, FilterHTTPVariables] | None = None,
) -> LinkProperties:
    """One map per link: the native click key, or the configured filters valued from what the
    clicked element knows."""
    known = native_key if values is None else values
    return LinkProperties(
        links=[
            _encoded(native_key)
            if link.filters is None
            else {name: _encoded_filter(known.get(name)) for name in link.filters}
            for link in links
        ]
    )


def clicked_object_values(
    row: Mapping[str, LivestatusColumn],
) -> dict[FilterName, FilterHTTPVariables]:
    """What a custom link may carry beyond the native key of a clicked host or service row:
    the states and the folder."""
    values: dict[FilterName, FilterHTTPVariables] = {
        "hoststate": {_state_variable("hst", row["host_state"], row["host_has_been_checked"]): "on"}
    }
    if "service_state" in row:
        values["svcstate"] = {
            _state_variable("st", row["service_state"], row["service_has_been_checked"]): "on"
        }
    if (folder := _folder_path(str(row["host_filename"]))) is not None:
        values["wato_folder"] = {"wato_folder": folder}
    return values


def _state_variable(
    prefix: str, state: LivestatusColumn, has_been_checked: LivestatusColumn
) -> str:
    return f"{prefix}p" if has_been_checked != 1 else f"{prefix}{int(str(state))}"


def _folder_path(filename: str) -> str | None:
    # Setup writes one hosts.mk per folder below /wato, so the path between them is the folder.
    path = PurePosixPath(filename)
    if path.name != "hosts.mk" or path.parts[:2] != ("/", "wato"):
        return None
    folder = path.relative_to("/wato").parent
    return "" if folder == PurePosixPath(".") else str(folder)


def _encoded(key: Mapping[FilterName, FilterHTTPVariables]) -> dict[FilterName, FilterResult]:
    return {
        filter_name: EncodedFilter(status="encoded", variables=dict(variables))
        for filter_name, variables in key.items()
    }


def _encoded_filter(variables: FilterHTTPVariables | None) -> FilterResult:
    if variables is None:
        return DroppedFilter(status="dropped", reason="no_value")
    return EncodedFilter(status="encoded", variables=dict(variables))
