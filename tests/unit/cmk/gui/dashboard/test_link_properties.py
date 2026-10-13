#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.dashboard.api._contextual_link_encoding import EffectiveLink, link_properties_for
from cmk.gui.dashboard.api.model.contextual_link import VisualLocation
from cmk.gui.dashboard.api.model.link_properties import DroppedFilter, EncodedFilter

_DOWN_PART_KEY = {
    "hoststate": {"hst1": "on"},
    "host_scheduled_downtime_depth": {"is_host_scheduled_downtime_depth": "0"},
}


def _link(title: str = "All hosts", filters: Sequence[str] | None = None) -> EffectiveLink:
    return EffectiveLink(
        title=title,
        location=VisualLocation(type="views", name="searchhost", owner=None),
        include_context=True,
        include_time_range=False,
        show_filter_form=True,
        filters=filters,
    )


def test_a_part_carries_its_native_click_key_and_nothing_else() -> None:
    properties = link_properties_for([_link()], _DOWN_PART_KEY)

    assert properties.links == [
        {
            "hoststate": EncodedFilter(status="encoded", variables={"hst1": "on"}),
            "host_scheduled_downtime_depth": EncodedFilter(
                status="encoded", variables={"is_host_scheduled_downtime_depth": "0"}
            ),
        }
    ]


def test_an_element_without_a_key_carries_one_empty_map() -> None:
    assert link_properties_for([_link()], {}).links == [{}]


def test_every_element_carries_one_map_per_link() -> None:
    properties = link_properties_for([_link("All hosts"), _link("Problem hosts")], _DOWN_PART_KEY)

    assert len(properties.links) == 2
    assert properties.links[0] == properties.links[1]


def test_a_custom_link_carries_only_its_configured_filters() -> None:
    properties = link_properties_for([_link(filters=["hoststate"])], _DOWN_PART_KEY)

    assert properties.links == [
        {"hoststate": EncodedFilter(status="encoded", variables={"hst1": "on"})}
    ]


def test_a_custom_link_drops_a_filter_the_element_has_no_value_for() -> None:
    properties = link_properties_for([_link(filters=["siteopt"])], _DOWN_PART_KEY)

    assert properties.links == [{"siteopt": DroppedFilter(status="dropped", reason="no_value")}]


def test_a_custom_link_takes_its_values_beyond_the_native_key() -> None:
    folder = {"wato_folder": {"wato_folder": "linux"}}

    properties = link_properties_for(
        [_link(), _link(filters=["wato_folder"])], _DOWN_PART_KEY, {**_DOWN_PART_KEY, **folder}
    )

    assert "wato_folder" not in properties.links[0]
    assert properties.links[1] == {
        "wato_folder": EncodedFilter(status="encoded", variables={"wato_folder": "linux"})
    }
