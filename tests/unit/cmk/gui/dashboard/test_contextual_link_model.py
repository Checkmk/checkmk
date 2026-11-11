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
    SitesContextFilter,
    WatoFoldersContextFilter,
)
from cmk.gui.dashboard.api.model.contextual_link import (
    AuxTagKeyOption,
    contextual_link_from_internal,
    contextual_link_to_internal,
    ContextualLink,
    ContextualLinkCustom,
    ContextualLinkInherited,
    ContextualLinkNone,
    ContextualLinkSpec,
    LabelKeyOption,
    TagGroupKeyOption,
    targetless_contextual_link_from_internal,
    TargetlessContextualLinkSpec,
    VisualLocation,
)
from cmk.gui.dashboard.api.model.widget_content._base import BaseWidgetContent
from cmk.gui.dashboard.api.model.widget_content.graph import (
    CombinedGraphContent,
    PerformanceGraphContent,
    SingleTimeseriesContent,
)
from cmk.gui.dashboard.api.model.widget_content.inventory import InventoryContent
from cmk.gui.dashboard.api.model.widget_content.metric import (
    AverageScatterplotContent,
    TopListContent,
)
from cmk.gui.dashboard.api.model.widget_content.overview import SiteOverviewContent
from cmk.gui.dashboard.api.model.widget_content.state import (
    HostStateContent,
    ServiceStateContent,
)
from cmk.gui.dashboard.api.model.widget_content.stats import HostStatsContent, ServiceStatsContent
from cmk.gui.dashboard.type_defs import (
    ContextFilterConfig,
    ContextualLinkCustomConfig,
    StatsDashletConfig,
)
from cmk.gui.type_defs import ContextualLinkEntryConfig
from cmk.gui.views.drilldown_filters import filter_drilldown
from cmk.gui.visuals.filter import filter_registry
from tests.testlib.unit.gui.web_test_app import SetConfig

# The options read the site config, such as whether Setup is on.
pytestmark = pytest.mark.usefixtures("request_context")

_VIEW = VisualLocation(type="views", name="searchhost")
_DASHBOARD = VisualLocation(type="dashboards", name="linux")

_AGGREGATE_HOST_FILTERS = ["sites", "wato_folders", "hostgroups", "hoststate", "host_labels"]
_SERVICE_ONLY_FILTERS = {"svcstate", "svchardstate", "service_labels", "service", "optservicegroup"}


def _inherited(location: VisualLocation) -> ContextualLinkInherited:
    return ContextualLinkInherited(
        type="inherited",
        location=location,
        include_context=True,
        include_time_range=True,
        show_filter_form=False,
    )


def test_a_target_is_stored_by_its_name() -> None:
    stored = contextual_link_to_internal(_inherited(_VIEW))

    assert stored is not None and stored["type"] == "inherited"
    assert stored["location"] == ("views", "searchhost")


def test_a_target_stored_with_the_owner_of_its_copy_loads_by_its_name() -> None:
    link = _inherited(_VIEW)
    stored = contextual_link_to_internal(link)
    assert stored is not None and stored["type"] == "inherited"
    stored["location"] = ("views", "searchhost", UserId("harry"))

    assert contextual_link_from_internal(stored, AGGREGATE_HOST_FILTER_ADAPTER) == link


@pytest.mark.parametrize("location", [_VIEW, _DASHBOARD])
def test_an_inherited_link_round_trips_its_target(location: VisualLocation) -> None:
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
                location=_DASHBOARD,
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
                location=_VIEW,
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


def test_a_single_value_filter_does_not_load_as_an_aggregate_filter() -> None:
    with pytest.raises(ValidationError):
        AGGREGATE_HOST_FILTER_ADAPTER.validate_python(ContextFilterConfig(filter_id="siteopt"))


def test_a_stored_statistics_link_reads_its_single_value_filters_as_multi_value_ones() -> None:
    stored = ContextualLinkCustomConfig(
        type="custom",
        links=[
            ContextualLinkEntryConfig(
                title="Problem services",
                location=("views", "searchsvc"),
                filters=[
                    ContextFilterConfig(filter_id="siteopt"),
                    ContextFilterConfig(filter_id="wato_folder"),
                    ContextFilterConfig(filter_id="optservicegroup"),
                    ContextFilterConfig(filter_id="hoststate"),
                ],
                include_context=False,
                include_time_range=False,
                show_filter_form=False,
            )
        ],
    )

    link = ServiceStatsContent.from_internal(
        StatsDashletConfig(type="servicestats", contextual_link=stored)
    ).contextual_link

    assert isinstance(link, ContextualLinkCustom)
    assert link.links[0].filters == [
        SitesContextFilter(filter_id="sites"),
        WatoFoldersContextFilter(filter_id="wato_folders"),
        HostStateContextFilter(filter_id="hoststate"),
    ]


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
    assert options.filters[:4] == ["siteopt", "wato_folder", "hoststate", "opthostgroup"]
    assert {
        "host",
        "site",
        "host_check_command_exact",
        "kubernetes_namespace",
        "host_labels",
    } <= set(options.filters)


@pytest.mark.parametrize(
    "content, filters",
    [
        pytest.param(HostStatsContent, _AGGREGATE_HOST_FILTERS, id="host statistics"),
        pytest.param(
            ServiceStatsContent,
            [*_AGGREGATE_HOST_FILTERS, "svcstate", "svchardstate", "service_labels"],
            id="service statistics",
        ),
    ],
)
def test_a_statistics_click_offers_only_filters_that_take_the_values_of_all_its_objects(
    content: type[BaseWidgetContent], filters: list[str]
) -> None:
    options = content.contextual_link_options()

    assert options is not None
    assert options.filters == filters


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(SiteOverviewContent, id="site overview"),
        pytest.param(HostStateContent, id="host state"),
        pytest.param(InventoryContent, id="inventory"),
    ],
)
def test_a_host_click_offers_the_multi_value_host_filters_but_no_service_filter(
    content: type[BaseWidgetContent],
) -> None:
    options = content.contextual_link_options()

    assert options is not None
    assert set(_AGGREGATE_HOST_FILTERS) <= set(options.filters)
    assert not _SERVICE_ONLY_FILTERS & set(options.filters)


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


def test_an_inventory_click_may_carry_the_host_name_in_a_custom_link() -> None:
    options = InventoryContent.contextual_link_options()

    assert options is not None
    assert options.modes == ["default", "inherited", "custom"]
    assert "host" in options.filters


def test_a_top_list_offers_a_custom_link_with_the_filters_of_its_host_and_service() -> None:
    options = TopListContent.contextual_link_options()

    assert options is not None
    assert options.modes == ["default", "inherited", "custom"]
    assert {"host", "host_labels", "wato_folder", "service", "svcstate"} <= set(options.filters)


@pytest.mark.parametrize(
    "content",
    [
        SingleTimeseriesContent,
        PerformanceGraphContent,
        CombinedGraphContent,
        AverageScatterplotContent,
    ],
)
def test_a_graph_offers_no_built_in_link_but_the_filters_of_a_service_it_draws(
    content: type[BaseWidgetContent],
) -> None:
    options = content.contextual_link_options()

    assert options is not None
    assert options.modes == ["inherited", "custom"]
    assert {"host", "host_labels", "service", "service_labels"} <= set(options.filters)


def test_a_graph_without_a_stored_link_links_nowhere() -> None:
    assert targetless_contextual_link_from_internal(
        None, OBJECT_SERVICE_FILTER_ADAPTER
    ) == ContextualLinkNone(type="none")


def test_a_graph_link_round_trips() -> None:
    link: TargetlessContextualLinkSpec[ObjectServiceContextFilter] = _inherited(_DASHBOARD)

    assert (
        targetless_contextual_link_from_internal(
            contextual_link_to_internal(link), OBJECT_SERVICE_FILTER_ADAPTER
        )
        == link
    )
