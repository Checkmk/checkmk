#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.gui.dashboard.api._contextual_link_encoding import (
    EffectiveLink,
    link_columns,
    link_properties_for,
    with_link_columns,
)
from cmk.gui.dashboard.api.model.contextual_link import VisualLocation
from cmk.gui.dashboard.api.model.link_properties import DroppedFilter, EncodedFilter
from cmk.gui.type_defs import ContextFilterConfig

_DOWN_PART_KEY = {
    "hoststate": {"hst1": "on"},
    "host_scheduled_downtime_depth": {"is_host_scheduled_downtime_depth": "0"},
}


_HOST_ROW = {
    "site": "heute",
    "host_name": "web01",
    "host_filename": "/wato/linux/hosts.mk",
    "host_labels": {"cmk/os_family": "linux", "env": "prod"},
}


def _link(
    title: str = "All hosts", filters: Sequence[ContextFilterConfig] | None = None
) -> EffectiveLink:
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
    properties = link_properties_for([_link(filters=[{"filter_id": "hoststate"}])], _DOWN_PART_KEY)

    assert properties.links == [
        {"hoststate": EncodedFilter(status="encoded", variables={"hst1": "on"})}
    ]


def test_a_custom_link_drops_a_filter_the_element_has_no_value_for() -> None:
    properties = link_properties_for([_link(filters=[{"filter_id": "siteopt"}])], _DOWN_PART_KEY)

    assert properties.links == [{"siteopt": DroppedFilter(status="dropped", reason="no_value")}]


def test_a_custom_link_takes_its_values_beyond_the_native_key_from_the_row() -> None:
    properties = link_properties_for(
        [_link(), _link(filters=[{"filter_id": "wato_folder"}])], _DOWN_PART_KEY, _HOST_ROW
    )

    assert "wato_folder" not in properties.links[0]
    assert properties.links[1] == {
        "wato_folder": EncodedFilter(status="encoded", variables={"wato_folder": "linux"})
    }


def test_a_custom_link_carries_a_label_instead_of_the_host() -> None:
    properties = link_properties_for(
        [_link(filters=[{"filter_id": "host_labels", "key": "cmk/os_family"}])],
        {"host": {"host": "web01"}},
        _HOST_ROW,
    )

    (link,) = properties.links
    assert list(link) == ["host_labels"]
    assert isinstance(label := link["host_labels"], EncodedFilter)
    assert label.variables["host_labels_1_vs_1_vs"] == "cmk/os_family:linux"


def test_a_custom_link_combines_two_label_keys_into_one_group() -> None:
    properties = link_properties_for(
        [
            _link(
                filters=[
                    {"filter_id": "host_labels", "key": "cmk/os_family"},
                    {"filter_id": "host_labels", "key": "env"},
                ]
            )
        ],
        {},
        _HOST_ROW,
    )

    assert isinstance(label := properties.links[0]["host_labels"], EncodedFilter)
    assert label.variables["host_labels_1_vs_count"] == "2"


def test_a_custom_link_drops_a_label_key_the_host_lacks() -> None:
    properties = link_properties_for(
        [_link(filters=[{"filter_id": "host_labels", "key": "cmk/kubernetes"}])], {}, _HOST_ROW
    )

    assert properties.links == [
        {"host_labels": DroppedFilter(status="dropped", reason="no_such_key")}
    ]


def test_a_custom_link_drops_a_filter_this_edition_lacks() -> None:
    properties = link_properties_for(
        [_link(filters=[{"filter_id": "no_such_filter"}])], {}, _HOST_ROW
    )

    assert properties.links == [
        {"no_such_filter": DroppedFilter(status="dropped", reason="not_available")}
    ]


@pytest.mark.parametrize(
    "filters, expected",
    [
        pytest.param([], [], id="nothing configured"),
        pytest.param([{"filter_id": "siteopt"}], [], id="the site comes with every row"),
        pytest.param(
            [{"filter_id": "host_labels", "key": "env"}, {"filter_id": "wato_folder"}],
            ["host_filename", "host_labels"],
            id="each configured filter's columns",
        ),
    ],
)
def test_link_columns_name_what_the_configured_filters_read(
    filters: Sequence[ContextFilterConfig], expected: Sequence[str]
) -> None:
    assert link_columns([_link(), _link(filters=filters)]) == expected


def test_with_link_columns_appends_only_what_the_widget_does_not_query() -> None:
    links = [_link(filters=[{"filter_id": "host_labels", "key": "env"}, {"filter_id": "host"}])]

    assert with_link_columns(["host_name", "host_state"], links) == [
        "host_name",
        "host_state",
        "host_labels",
    ]
