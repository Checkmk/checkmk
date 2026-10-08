#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from urllib.parse import parse_qsl, urlsplit

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.dashboard.view_drilldown import (
    column_drilldown_targets,
    column_drilldowns,
    inherited_column_link,
)
from cmk.gui.permissions import permission_registry
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

_HOST_ROW: Row = {"site": "heute_site", "host_name": "heute"}
_SERVICE_ROW: Row = {**_HOST_ROW, "service_description": "CPU load"}
_HOST_DOWNTIME_ROW: Row = {**_HOST_ROW, "service_description": ""}
_CONTEXT: VisualContext = {"opthostgroup": {"opthost_group": "linux"}}


@pytest.fixture(name="admin_permissions")
def fixture_admin_permissions(load_config: Config, with_admin_login: UserId) -> UserPermissions:
    return UserPermissions(
        load_config.roles, permission_registry, {with_admin_login: ["admin"]}, []
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


def _view_spec(name: str) -> ViewSpec:
    return multisite_builtin_views[name].copy()


def _url_of_first_column(
    view_spec: ViewSpec,
    link: ContextualLinkEntryConfig,
    row: Row,
    user_permissions: UserPermissions,
) -> tuple[str, dict[str, str]]:
    drilldowns = column_drilldowns(view_spec, {0: link}, _CONTEXT, user_permissions)
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
def test_column_drilldowns_offers_none_on_a_datasource_without_hosts_or_services(
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


def test_column_drilldown_targets_reads_back_what_the_editor_stored() -> None:
    column_links = {2: inherited_column_link(("dashboards", "main"))}

    assert column_drilldown_targets(column_links) == {2: ("dashboards", "main")}


def test_column_drilldown_targets_leaves_out_a_link_with_filters() -> None:
    custom = _inherited()
    custom["filters"] = [ContextFilterConfig(filter_id="host")]

    assert column_drilldown_targets({0: custom}) == {}
