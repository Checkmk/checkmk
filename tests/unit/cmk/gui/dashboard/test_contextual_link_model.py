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
    HostAttributeContextFilter,
    HostLabelContextFilter,
    HostNameContextFilter,
    HostStateContextFilter,
    OBJECT_HOST_FILTER_ADAPTER,
    OBJECT_SERVICE_FILTER_ADAPTER,
    ObjectServiceContextFilter,
    ServiceStateContextFilter,
    ServiceTagContextFilter,
)
from cmk.gui.dashboard.api.model.contextual_link import (
    AuxTagKeyOption,
    contextual_link_from_internal,
    contextual_link_to_internal,
    ContextualLink,
    ContextualLinkCustom,
    ContextualLinkInherited,
    ContextualLinkSpec,
    LabelKeyOption,
    TagGroupKeyOption,
    VisualLocation,
)
from cmk.gui.dashboard.api.model.widget_content.inventory import InventoryContent
from cmk.gui.dashboard.api.model.widget_content.metric import TopListContent
from cmk.gui.dashboard.api.model.widget_content.state import (
    HostStateContent,
    ServiceStateContent,
)
from cmk.gui.dashboard.type_defs import ContextFilterConfig
from cmk.gui.views.drilldown_filters import filter_drilldown
from cmk.gui.visuals.filter import filter_registry
from tests.testlib.unit.gui.web_test_app import SetConfig

# The options read the site config, such as whether Setup is on.
pytestmark = pytest.mark.usefixtures("request_context")

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


def test_a_custom_link_round_trips_its_keyed_filters() -> None:
    link: ContextualLinkSpec[ObjectServiceContextFilter] = ContextualLinkCustom(
        type="custom",
        links=[
            ContextualLink(
                title="Same OS",
                location=_BY_NAME,
                filters=[
                    HostLabelContextFilter(filter_id="host_labels", key="cmk/os_family"),
                    ServiceTagContextFilter(filter_id="service_tags", key="tier"),
                    HostAttributeContextFilter(filter_id="kubernetes_namespace"),
                ],
                include_context=False,
                include_time_range=False,
                show_filter_form=False,
            )
        ],
    )

    stored = contextual_link_to_internal(link)

    assert stored is not None and stored["type"] == "custom"
    assert stored["links"][0]["filters"][0] == {"filter_id": "host_labels", "key": "cmk/os_family"}
    assert contextual_link_from_internal(stored, OBJECT_SERVICE_FILTER_ADAPTER) == link


def test_a_label_filter_does_not_load_without_its_key() -> None:
    with pytest.raises(ValidationError):
        OBJECT_HOST_FILTER_ADAPTER.validate_python(ContextFilterConfig(filter_id="host_labels"))


def test_a_label_does_not_load_as_an_aggregate_filter() -> None:
    with pytest.raises(ValidationError):
        AGGREGATE_HOST_FILTER_ADAPTER.validate_python(
            ContextFilterConfig(filter_id="host_labels", key="cmk/os_family")
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
    assert options.filters[:5] == ["siteopt", "wato_folder", "hoststate", "opthostgroup", "host"]
    assert {"site", "host_check_command_exact", "kubernetes_namespace", "host_labels"} <= set(
        options.filters
    )
    assert options.single_infos == ["host"]


def test_a_host_state_click_names_the_key_of_each_keyed_filter() -> None:
    options = HostStateContent.contextual_link_options()

    assert options is not None
    assert options.filter_keys == {
        "host_labels": LabelKeyOption(type="label", object_type="host"),
        "host_tags": TagGroupKeyOption(type="tag_group"),
        "host_auxtags": AuxTagKeyOption(type="aux_tag", max_count=3),
    }


def test_a_service_state_click_names_whose_labels_a_label_key_names() -> None:
    options = ServiceStateContent.contextual_link_options()

    assert options is not None
    assert options.filter_keys["service_labels"] == LabelKeyOption(
        type="label", object_type="service"
    )


def test_a_click_offers_only_filters_a_drill_down_can_value() -> None:
    # The service object's filters hold those of every other widget.
    options = ServiceStateContent.contextual_link_options()

    assert options is not None
    assert [f for f in options.filters if filter_drilldown(f) is None] == []


def test_a_click_offers_only_filters_this_edition_has() -> None:
    options = ServiceStateContent.contextual_link_options()

    assert options is not None
    assert set(options.filters) <= set(filter_registry)


def test_a_click_offers_no_filter_switched_off_on_this_site(set_config: SetConfig) -> None:
    with set_config(wato_enabled=False):
        options = HostStateContent.contextual_link_options()

    assert options is not None
    assert "siteopt" in options.filters
    assert "wato_folder" not in options.filters


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


def test_a_top_list_offers_a_custom_link_with_the_filters_of_its_host() -> None:
    options = TopListContent.contextual_link_options()

    assert options is not None
    assert options.modes == ["default", "inherited", "custom"]
    assert {"host", "host_labels", "wato_folder"} <= set(options.filters)
    assert "service" not in options.filters


def test_a_top_list_click_names_its_host() -> None:
    options = TopListContent.contextual_link_options()

    assert options is not None
    assert options.single_infos == ["host"]
