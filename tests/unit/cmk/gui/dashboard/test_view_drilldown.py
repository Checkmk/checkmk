#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from urllib.parse import parse_qsl, urlsplit

import pytest

from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.config import Config
from cmk.gui.dashboard.view_drilldown import column_drilldowns
from cmk.gui.http import request
from cmk.gui.permissions import all_permissions
from cmk.gui.type_defs import (
    ContextFilterConfig,
    ContextualLinkEntryConfig,
    ContextualLinkLocationConfig,
    Row,
    ViewSpec,
    VisualContext,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.store import multisite_builtin_views
from cmk.shared_typing.drill_up_button import DrillUpButton
from cmk.web.utils.request_cache import RequestCache

_HOST_ROW: Row = {"site": "heute_site", "host_name": "heute"}
_SERVICE_ROW: Row = {**_HOST_ROW, "service_description": "CPU load"}
_HOST_DOWNTIME_ROW: Row = {**_HOST_ROW, "service_description": ""}
_CUSTOM_HOST_ROW: Row = {
    **_HOST_ROW,
    "host_filename": "/wato/servers/hosts.mk",
    "host_groups": ["web"],
    "host_labels": {"cmk/os_family": "linux", "env": "prod"},
    "host_tags": {"criticality": "prod"},
    "host_state": 0,
    "host_has_been_checked": 1,
}
_CONTEXT: VisualContext = {"opthostgroup": {"opthost_group": "linux"}}
_MAIN = DrillUpButton(title="Main")


@pytest.fixture(name="admin_permissions")
def fixture_admin_permissions(load_config: Config, with_admin_login: UserId) -> UserPermissions:
    return UserPermissions(
        load_config.roles,
        all_permissions(),
        {with_admin_login: ["admin"]},
        [],
    )


def _inherited(
    location: ContextualLinkLocationConfig = ("views", "host"), *, include_context: bool = True
) -> ContextualLinkEntryConfig:
    return ContextualLinkEntryConfig(
        title=location[1],
        location=location,
        filters=[],
        include_context=include_context,
        include_time_range=True,
        show_filter_form=False,
    )


def _custom(
    *filters: ContextFilterConfig,
    location: ContextualLinkLocationConfig = ("views", "allhosts"),
    include_context: bool = False,
) -> ContextualLinkEntryConfig:
    return ContextualLinkEntryConfig(
        title=location[1],
        location=location,
        filters=list(filters),
        include_context=include_context,
        include_time_range=True,
        show_filter_form=False,
    )


def _view_spec(name: str) -> ViewSpec:
    return multisite_builtin_views[name].copy()


def _url_of_first_column(
    view_spec: ViewSpec,
    link: ContextualLinkEntryConfig,
    row: Row,
    user_permissions: UserPermissions,
    drilled_from: DrillUpButton | None = None,
) -> tuple[str, dict[str, str]]:
    drilldowns = column_drilldowns(
        view_spec, {0: link}, _CONTEXT, user_permissions, drilled_from=drilled_from
    )
    url = drilldowns[0].url(row)
    assert url is not None
    parts = urlsplit(url)
    return parts.path, dict(parse_qsl(parts.query, keep_blank_values=True))


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_link_carries_the_context_and_the_clicked_host(
    admin_permissions: UserPermissions,
) -> None:
    path, variables = _url_of_first_column(
        _view_spec("allhosts"), _inherited(), _HOST_ROW, admin_permissions
    )

    assert (path, variables) == (
        "view.py",
        {
            "view_name": "host",
            "opthost_group": "linux",
            "site": "heute_site",
            "host": "heute",
            "filled_in": "filter",
            "_show_filter_form": "0",
        },
    )


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_link_carries_the_service_of_a_service_row(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("allservices"), _inherited(), _SERVICE_ROW, admin_permissions
    )

    assert variables["service"] == "CPU load"


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_link_of_a_host_row_carries_no_service(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("downtimes"), _inherited(), _HOST_DOWNTIME_ROW, admin_permissions
    )

    assert "service" not in variables


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_leaves_a_host_row_unlinked_to_a_service_view(
    admin_permissions: UserPermissions,
) -> None:
    drilldowns = column_drilldowns(
        _view_spec("downtimes"), {0: _inherited(("views", "service"))}, _CONTEXT, admin_permissions
    )

    assert drilldowns[0].url(_HOST_DOWNTIME_ROW) is None


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_clicked_host_wins_over_the_host_in_the_context(
    admin_permissions: UserPermissions,
) -> None:
    drilldowns = column_drilldowns(
        _view_spec("allhosts"),
        {0: _inherited()},
        {"host": {"host": "morgen"}},
        admin_permissions,
    )

    url = drilldowns[0].url(_HOST_ROW)

    assert url is not None
    assert dict(parse_qsl(urlsplit(url).query))["host"] == "heute"


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_link_keeps_its_target_over_the_context(
    admin_permissions: UserPermissions,
) -> None:
    drilldowns = column_drilldowns(
        _view_spec("allhosts"),
        {0: _inherited()},
        {"crafted": {"view_name": "other"}},
        admin_permissions,
    )

    url = drilldowns[0].url(_HOST_ROW)

    assert url is not None
    assert dict(parse_qsl(urlsplit(url).query))["view_name"] == "host"


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_link_without_context_carries_only_the_clicked_host(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("allhosts"), _inherited(include_context=False), _HOST_ROW, admin_permissions
    )

    assert "opthost_group" not in variables


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_link_to_a_dashboard_opens_the_dashboard_page(
    admin_permissions: UserPermissions,
) -> None:
    path, variables = _url_of_first_column(
        _view_spec("allhosts"), _inherited(("dashboards", "main")), _HOST_ROW, admin_permissions
    )

    assert (path, variables["name"]) == ("dashboard.py", "main")


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_link_to_a_stored_owner_names_that_owner(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("allhosts"),
        _inherited(("views", "host", UserId.builtin())),
        _HOST_ROW,
        admin_permissions,
    )

    assert variables["owner"] == ""


@pytest.mark.usefixtures("load_config", "request_context")
def test_column_drilldowns_withholds_a_target_the_viewer_may_not_open() -> None:
    drilldowns = column_drilldowns(
        _view_spec("allhosts"), {0: _inherited()}, _CONTEXT, UserPermissions({}, {}, {}, [])
    )

    assert drilldowns == {}


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_offers_no_inherited_link_on_a_datasource_without_hosts_or_services(
    admin_permissions: UserPermissions,
) -> None:
    view_spec = _view_spec("allhosts")
    view_spec["datasource"] = "hostgroups"

    drilldowns = column_drilldowns(view_spec, {0: _inherited()}, _CONTEXT, admin_permissions)

    assert drilldowns == {}


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_offers_none_on_a_datasource_that_is_not_registered(
    admin_permissions: UserPermissions,
) -> None:
    view_spec = _view_spec("allhosts")
    view_spec["datasource"] = "not_a_registered_datasource"

    drilldowns = column_drilldowns(view_spec, {0: _inherited()}, _CONTEXT, admin_permissions)

    assert drilldowns == {}


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_drops_a_link_whose_painter_is_gone(
    admin_permissions: UserPermissions,
) -> None:
    view_spec = _view_spec("allhosts")

    drilldowns = column_drilldowns(
        view_spec, {len(view_spec["painters"]): _inherited()}, _CONTEXT, admin_permissions
    )

    assert drilldowns == {}


# fmt: off
@pytest.mark.parametrize(
    "view_name, columns",
    [
        pytest.param("allhosts", ["host_name"], id="host row"),
        pytest.param("allservices", ["host_name", "service_description"], id="service row"),
    ],
)
# fmt: on
@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_reads_the_columns_naming_the_row(
    admin_permissions: UserPermissions, view_name: str, columns: list[str]
) -> None:
    drilldowns = column_drilldowns(
        _view_spec(view_name), {0: _inherited()}, _CONTEXT, admin_permissions
    )

    assert drilldowns[0].columns == columns


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_custom_link_carries_only_its_filters_valued_from_the_row(
    admin_permissions: UserPermissions,
) -> None:
    path, variables = _url_of_first_column(
        _view_spec("allhosts"),
        _custom(
            ContextFilterConfig(filter_id="host_labels", key="cmk/os_family"),
            ContextFilterConfig(filter_id="wato_folder"),
        ),
        _CUSTOM_HOST_ROW,
        admin_permissions,
    )

    assert (path, variables) == (
        "view.py",
        {
            "view_name": "allhosts",
            "host_labels_count": "1",
            "host_labels_1_vs_count": "1",
            "host_labels_1_bool": "and",
            "host_labels_indexof_1": "1",
            "host_labels_1_vs_1_bool": "and",
            "host_labels_1_vs_1_vs": "cmk/os_family:linux",
            "host_labels_1_vs_indexof_1": "1",
            "wato_folder": "servers",
            "filled_in": "filter",
            "_show_filter_form": "0",
        },
    )


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_custom_link_combines_label_keys_in_one_group(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("allhosts"),
        _custom(
            ContextFilterConfig(filter_id="host_labels", key="cmk/os_family"),
            ContextFilterConfig(filter_id="host_labels", key="env"),
        ),
        _CUSTOM_HOST_ROW,
        admin_permissions,
    )

    assert (
        variables["host_labels_count"],
        variables["host_labels_1_vs_1_vs"],
        variables["host_labels_1_vs_2_vs"],
    ) == ("1", "cmk/os_family:linux", "env:prod")


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_custom_link_url_reads_back_as_its_filters(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("allhosts"),
        _custom(
            ContextFilterConfig(filter_id="host_labels", key="cmk/os_family"),
            ContextFilterConfig(filter_id="host_tags", key="criticality"),
            ContextFilterConfig(filter_id="wato_folder"),
            ContextFilterConfig(filter_id="hoststate"),
        ),
        _CUSTOM_HOST_ROW,
        admin_permissions,
    )
    for variable, value in variables.items():
        request.set_var(variable, value)

    context = visuals.active_context_from_request(["host"], {}, RequestCache(Config()))

    assert set(context) == {"host_labels", "host_tags", "wato_folder", "hoststate"}


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_custom_link_filter_wins_over_the_context(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("allhosts"),
        _custom(ContextFilterConfig(filter_id="opthostgroup"), include_context=True),
        _CUSTOM_HOST_ROW,
        admin_permissions,
    )

    assert variables["opthost_group"] == "web"


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_custom_link_leaves_out_and_names_a_filter_the_row_has_no_value_for(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("allhosts"),
        _custom(
            ContextFilterConfig(filter_id="host_labels", key="cmk/kubernetes"),
            ContextFilterConfig(filter_id="host"),
        ),
        _CUSTOM_HOST_ROW,
        admin_permissions,
    )

    assert "host_labels_count" not in variables
    assert variables["host"] == "heute"
    assert variables["_dropped_filters"] == "host_labels:no_such_key:cmk/kubernetes"


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_custom_link_carries_the_label_keys_the_row_has_and_names_the_others(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("allhosts"),
        _custom(
            ContextFilterConfig(filter_id="host_labels", key="cmk/os_family"),
            ContextFilterConfig(filter_id="host_labels", key="cmk/kubernetes"),
        ),
        _CUSTOM_HOST_ROW,
        admin_permissions,
    )

    assert variables["host_labels_1_vs_1_vs"] == "cmk/os_family:linux"
    assert variables["_dropped_filters"] == "host_labels:no_such_key:cmk/kubernetes"


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_custom_link_names_no_filter_the_context_carries_instead(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("allhosts"),
        _custom(ContextFilterConfig(filter_id="opthostgroup"), include_context=True),
        {**_CUSTOM_HOST_ROW, "host_groups": []},
        admin_permissions,
    )

    assert variables["opthost_group"] == "linux"
    assert "_dropped_filters" not in variables


@pytest.mark.parametrize(
    "link, context, host",
    [
        pytest.param(
            _custom(ContextFilterConfig(filter_id="host"), location=("views", "host")),
            {},
            "heute",
            id="from its filter",
        ),
        pytest.param(
            _custom(
                ContextFilterConfig(filter_id="wato_folder"),
                location=("views", "host"),
                include_context=True,
            ),
            {"host": {"host": "morgen"}},
            "morgen",
            id="from the context",
        ),
        pytest.param(
            _custom(ContextFilterConfig(filter_id="wato_folder"), location=("views", "host")),
            {},
            None,
            id="unnamed",
        ),
        pytest.param(
            _custom(
                ContextFilterConfig(filter_id="wato_folder"),
                location=("views", "host"),
                include_context=True,
            ),
            {"host": {"host": ""}},
            None,
            id="empty in the context",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_custom_link_to_a_host_view_links_even_without_the_host(
    admin_permissions: UserPermissions,
    link: ContextualLinkEntryConfig,
    context: VisualContext,
    host: str | None,
) -> None:
    url = column_drilldowns(_view_spec("allhosts"), {0: link}, context, admin_permissions)[0].url(
        _CUSTOM_HOST_ROW
    )

    assert url is not None
    assert dict(parse_qsl(urlsplit(url).query)).get("host") == host


@pytest.mark.parametrize(
    "datasource, link, columns",
    [
        pytest.param(
            "hosts",
            _custom(
                ContextFilterConfig(filter_id="host_labels", key="cmk/os_family"),
                ContextFilterConfig(filter_id="wato_folder"),
            ),
            ["host_labels", "host_filename"],
            id="its filters",
        ),
        pytest.param(
            "hosts",
            _custom(
                ContextFilterConfig(filter_id="log_class"),
                ContextFilterConfig(filter_id="wato_folder"),
            ),
            ["host_filename"],
            id="filter its data source lacks",
        ),
        pytest.param(
            "mkeventd_events",
            _custom(
                ContextFilterConfig(filter_id="event_state"),
                ContextFilterConfig(filter_id="host"),
                location=("dashboards", "main"),
            ),
            ["host_name"],
            id="no view-only filter to a dashboard",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_custom_link_reads_the_columns_of_the_filters_it_carries(
    admin_permissions: UserPermissions,
    datasource: str,
    link: ContextualLinkEntryConfig,
    columns: list[str],
) -> None:
    view_spec = _view_spec("allhosts")
    view_spec["datasource"] = datasource

    drilldowns = column_drilldowns(view_spec, {0: link}, _CONTEXT, admin_permissions)

    assert drilldowns[0].columns == columns


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_custom_link_names_a_filter_it_cannot_carry(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("allhosts"),
        _custom(ContextFilterConfig(filter_id="log_class")),
        _CUSTOM_HOST_ROW,
        admin_permissions,
    )

    assert variables["_dropped_filters"] == "log_class:not_available"


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_custom_link_drills_down_from_a_host_group(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("hostgroups"),
        _custom(ContextFilterConfig(filter_id="hostgroup"), location=("views", "hostgroup")),
        {"site": "heute_site", "hostgroup_name": "linux"},
        admin_permissions,
    )

    assert variables["hostgroup"] == "linux"


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_inherited_link_names_the_dashboard_it_leaves(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("allhosts"), _inherited(), _HOST_ROW, admin_permissions, _MAIN
    )

    assert variables["_drilled_from"] == "Main"


@pytest.mark.usefixtures("request_context")
def test_column_drilldowns_custom_link_names_the_dashboard_it_leaves(
    admin_permissions: UserPermissions,
) -> None:
    _path, variables = _url_of_first_column(
        _view_spec("allhosts"),
        _custom(ContextFilterConfig(filter_id="host")),
        _CUSTOM_HOST_ROW,
        admin_permissions,
        _MAIN,
    )

    assert variables["_drilled_from"] == "Main"
