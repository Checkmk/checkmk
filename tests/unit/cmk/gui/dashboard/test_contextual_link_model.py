#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from pydantic import ValidationError

from cmk.ccc.user import UserId
from cmk.gui.dashboard.api.model.context_filters import (
    AGGREGATE_HOST_FILTER_ADAPTER,
    AGGREGATE_SERVICE_FILTER_ADAPTER,
    AggregateServiceContextFilter,
    HostNameContextFilter,
    HostStateContextFilter,
    OBJECT_HOST_FILTER_ADAPTER,
    ServiceStateContextFilter,
)
from cmk.gui.dashboard.api.model.contextual_link import (
    contextual_link_from_internal,
    contextual_link_to_internal,
    ContextualLink,
    ContextualLinkCustom,
    ContextualLinkInherited,
    ContextualLinkSpec,
    VisualLocation,
)
from cmk.gui.dashboard.api.model.widget_content.inventory import InventoryContent
from cmk.gui.dashboard.api.model.widget_content.state import (
    HostStateContent,
    ServiceStateContent,
)
from cmk.gui.dashboard.type_defs import ContextFilterConfig

_BY_NAME = VisualLocation(type="views", name="searchhost", owner=None)
_BUILT_IN_VIEW = VisualLocation(type="views", name="searchhost", owner=UserId.builtin())
_OWNED_DASHBOARD = VisualLocation(type="dashboards", name="linux", owner=UserId("harry"))


def _inherited(location: VisualLocation) -> ContextualLinkInherited:
    return ContextualLinkInherited(
        type="inherited",
        location=location,
        include_context=True,
        include_time_range=True,
        show_filter_form=False,
    )


def test_a_built_in_target_is_stored_with_the_empty_owner() -> None:
    stored = contextual_link_to_internal(_inherited(_BUILT_IN_VIEW))

    assert stored is not None and stored["type"] == "inherited"
    assert stored["location"] == ("views", "searchhost", UserId.builtin())


def test_a_target_without_owner_is_stored_without_one() -> None:
    stored = contextual_link_to_internal(_inherited(_BY_NAME))

    assert stored is not None and stored["type"] == "inherited"
    assert stored["location"] == ("views", "searchhost")


@pytest.mark.parametrize("location", [_BY_NAME, _BUILT_IN_VIEW, _OWNED_DASHBOARD])
def test_an_inherited_link_round_trips_its_owner(location: VisualLocation) -> None:
    link = _inherited(location)

    assert (
        contextual_link_from_internal(
            contextual_link_to_internal(link), AGGREGATE_HOST_FILTER_ADAPTER
        )
        == link
    )


def test_a_custom_link_round_trips_its_entries() -> None:
    link: ContextualLinkSpec[AggregateServiceContextFilter] = ContextualLinkCustom(
        type="custom",
        links=[
            ContextualLink(
                title="Problem services",
                location=_OWNED_DASHBOARD,
                filters=[
                    HostStateContextFilter(filter_id="hoststate"),
                    ServiceStateContextFilter(filter_id="svcstate"),
                ],
                include_context=False,
                include_time_range=True,
                show_filter_form=False,
            )
        ],
    )

    assert (
        contextual_link_from_internal(
            contextual_link_to_internal(link), AGGREGATE_SERVICE_FILTER_ADAPTER
        )
        == link
    )


def test_a_service_filter_does_not_load_as_a_host_filter() -> None:
    with pytest.raises(ValidationError):
        AGGREGATE_HOST_FILTER_ADAPTER.validate_python(ContextFilterConfig(filter_id="svcstate"))


def test_an_object_host_filter_loads_the_host_name() -> None:
    assert OBJECT_HOST_FILTER_ADAPTER.validate_python(
        ContextFilterConfig(filter_id="host")
    ) == HostNameContextFilter(filter_id="host")


def test_the_host_name_does_not_load_as_an_aggregate_filter() -> None:
    with pytest.raises(ValidationError):
        AGGREGATE_HOST_FILTER_ADAPTER.validate_python(ContextFilterConfig(filter_id="host"))


def test_a_host_state_click_may_carry_the_host_name() -> None:
    options = HostStateContent.contextual_link_options()

    assert options is not None
    assert options.filters == ["siteopt", "wato_folder", "hoststate", "opthostgroup", "host"]
    assert options.single_infos == ["host"]


def test_a_service_state_click_may_carry_the_host_and_the_service_name() -> None:
    options = ServiceStateContent.contextual_link_options()

    assert options is not None
    assert {"host", "service", "svcstate"} <= set(options.filters)
    assert options.single_infos == ["host", "service"]


def test_an_inventory_click_may_carry_the_host_name_in_a_custom_link() -> None:
    options = InventoryContent.contextual_link_options()

    assert options is not None
    assert options.modes == ["default", "inherited", "custom"]
    assert "host" in options.filters
    assert options.single_infos == ["host"]
