#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from http import HTTPStatus

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.painter import PainterContext
from cmk.gui.permissions import all_permissions
from cmk.gui.type_defs import (
    ColumnSpec,
    ContextFilterConfig,
    ContextualLinkEntryConfig,
    ContextualLinkLocationConfig,
    PainterParameters,
    VisualLinkSpec,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.page_edit_view import (
    join_painters_of_datasource,
    view_editor_column_spec,
    view_editor_general_properties,
)
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.ruleset_matcher.tags import (
    AuxTagSpec,
    GroupedTagSpec,
    TagConfig,
    TagConfigSpec,
    TagGroupID,
    TagGroupSpec,
    TagID,
)
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context


def _link(
    location: ContextualLinkLocationConfig,
    *filters: ContextFilterConfig,
    include_context: bool = True,
) -> ContextualLinkEntryConfig:
    return ContextualLinkEntryConfig(
        title=location[1],
        location=location,
        filters=list(filters),
        include_context=include_context,
        include_time_range=True,
        show_filter_form=False,
    )


def _a_join_painter_name() -> str:
    # Any real join painter will do; picking one at runtime keeps the test from
    # failing on an unrelated "unknown painter" validation error.
    return sorted(join_painters_of_datasource("hosts"))[0]


@pytest.fixture(name="painter_context")
def fixture_painter_context() -> PainterContext:
    return make_painter_context(UserPermissions({}, {}, {}, []))


@pytest.mark.usefixtures("request_context")
def test_a_column_without_painter_parameters_gets_empty_parameters(
    painter_context: PainterContext,
) -> None:
    vs = view_editor_column_spec("columns", "hosts", painter_context)

    value = vs.value_from_json(
        {"columns": [["column", {"painter_spec": "alias", "column_title": ""}]]}
    )

    assert value["columns"] == [
        ColumnSpec(
            _column_type="column", name="alias", parameters=PainterParameters(), column_title=""
        )
    ]


@pytest.mark.usefixtures("request_context")
def test_a_column_without_a_chosen_painter_is_a_user_error_at_the_painter(
    painter_context: PainterContext,
) -> None:
    vs = view_editor_column_spec("columns", "hosts", painter_context)
    value = vs.value_from_json(
        {"columns": [["column", {"painter_spec": None, "column_title": ""}]]}
    )

    with pytest.raises(MKUserError) as excinfo:
        vs.validate_value(value, "columns")

    assert "painter_spec" in (excinfo.value.varname or "")


@pytest.mark.usefixtures("suppress_license_expiry_header", "patch_theme", "suppress_license_banner")
def test_cloning_a_builtin_view_opens_the_view_editor_with_its_column_editor(
    logged_in_admin_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table("contactgroups", [])
    mock_livestatus.expect_query("GET contactgroups\nCache: reload\nColumns: name alias\n")

    with mock_livestatus():
        response = logged_in_admin_wsgi_app.get(
            "/NO_SITE/check_mk/edit_view.py?mode=clone&load_name=allhosts&owner=",
            status=HTTPStatus.OK,
        )

    assert "Add column" in response.text


@pytest.mark.usefixtures("request_context")
def test_column_spec_join_column_without_join_value_is_a_user_error(
    painter_context: PainterContext,
) -> None:
    # Adding a "Joined column" in the view editor without filling in the service it
    # joins on. The user must get a validation error on that field, not a crash.
    vs = view_editor_column_spec("columns", "hosts", painter_context)

    with pytest.raises(MKUserError) as excinfo:
        vs.validate_value(
            {
                "columns": [
                    ColumnSpec(
                        _column_type="join_column",
                        name=_a_join_painter_name(),
                        join_value="",
                        column_title="",
                    )
                ]
            },
            "columns",
        )

    # The error must point at the join value field, not at some unrelated element.
    assert "join_value" in (excinfo.value.varname or "")


@pytest.mark.usefixtures("request_context")
def test_the_view_editor_offers_the_automatic_page_reload() -> None:
    properties = view_editor_general_properties("hosts", allow_browser_reload=True)

    assert "browser_reload" in properties.default_value()


@pytest.mark.usefixtures("request_context")
def test_the_view_editor_without_browser_reload_hides_the_automatic_page_reload() -> None:
    properties = view_editor_general_properties("hosts", allow_browser_reload=False)

    assert "browser_reload" not in properties.default_value()


@pytest.fixture(name="admin_painter_context")
def fixture_admin_painter_context(load_config: Config, with_admin_login: UserId) -> PainterContext:
    return make_painter_context(
        UserPermissions(
            load_config.roles,
            all_permissions(),
            {with_admin_login: ["admin"]},
            [],
        )
    )


@pytest.fixture(name="tagged_painter_context")
def fixture_tagged_painter_context(admin_painter_context: PainterContext) -> PainterContext:
    tags = TagConfig.from_config(
        TagConfigSpec(
            tag_groups=[
                TagGroupSpec(
                    id=TagGroupID("criticality"),
                    title="Criticality",
                    tags=[GroupedTagSpec(id=TagID("prod"), title="Productive", aux_tags=[])],
                )
            ],
            aux_tags=[
                AuxTagSpec(id=TagID(f"aux{index}"), title=f"Aux {index}") for index in range(4)
            ],
        )
    )
    return dataclasses.replace(
        admin_painter_context,
        config=dataclasses.replace(admin_painter_context.config, tags=tags),
    )


def _columns(painter: str, drilldown: ContextualLinkEntryConfig) -> dict[str, list[object]]:
    return {"columns": [(ColumnSpec(painter), drilldown)]}


@pytest.mark.usefixtures("request_context")
def test_view_editor_column_spec_with_drilldown_keeps_a_drilldown_apart_from_the_link(
    admin_painter_context: PainterContext,
) -> None:
    vs = view_editor_column_spec("columns", "hosts", admin_painter_context, with_drilldown=True)
    value = {
        "columns": [
            (
                ColumnSpec(
                    "host",
                    parameters=PainterParameters(color_choices=[]),
                    column_title="",
                    _column_type="column",
                ),
                _link(("dashboards", "main")),
            )
        ]
    }

    assert vs.transform_value(value) == value


@pytest.mark.usefixtures("request_context")
def test_view_editor_column_spec_with_drilldown_keeps_a_custom_drilldown(
    admin_painter_context: PainterContext,
) -> None:
    vs = view_editor_column_spec("columns", "hosts", admin_painter_context, with_drilldown=True)
    value = {
        "columns": [
            (
                ColumnSpec(
                    "host",
                    parameters=PainterParameters(color_choices=[]),
                    column_title="",
                    _column_type="column",
                ),
                _link(
                    ("views", "allhosts"),
                    ContextFilterConfig(filter_id="host_labels", key="cmk/os_family"),
                    ContextFilterConfig(filter_id="wato_folder"),
                    include_context=False,
                ),
            )
        ]
    }

    assert vs.transform_value(value) == value


@pytest.mark.usefixtures("request_context")
def test_view_editor_column_spec_with_drilldown_keeps_a_link_to_a_view(
    admin_painter_context: PainterContext,
) -> None:
    vs = view_editor_column_spec("columns", "hosts", admin_painter_context, with_drilldown=True)
    value = {
        "columns": [
            (
                ColumnSpec(
                    "host",
                    parameters=PainterParameters(color_choices=[]),
                    link_spec=VisualLinkSpec("views", "host"),
                    column_title="",
                    _column_type="column",
                ),
                None,
            )
        ]
    }

    assert vs.transform_value(value) == value


@pytest.mark.parametrize(
    "datasource, painter, drilldown",
    [
        pytest.param(
            "services",
            "alias",
            _link(
                ("views", "allhosts"),
                ContextFilterConfig(filter_id="host_tags", key="criticality"),
                ContextFilterConfig(filter_id="service_tags", key="criticality"),
                ContextFilterConfig(filter_id="host_auxtags", key="aux0"),
            ),
            id="tag keys of the tag config",
        ),
        pytest.param(
            "hosts",
            "alias",
            _link(
                ("views", "allhosts"),
                ContextFilterConfig(filter_id="host_labels", key="cmk/os_family"),
                ContextFilterConfig(filter_id="host_labels", key="env"),
            ),
            id="one label filter with two keys",
        ),
        pytest.param(
            "hostgroups",
            "hg_name",
            _link(("views", "hostgroup"), ContextFilterConfig(filter_id="hostgroup")),
            id="host group view from host groups",
        ),
        pytest.param(
            "hosts",
            "alias",
            _link(
                ("views", "host"),
                ContextFilterConfig(filter_id="wato_folder"),
                include_context=True,
            ),
            id="target object named by the context",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_view_editor_column_spec_with_drilldown_accepts(
    tagged_painter_context: PainterContext,
    datasource: str,
    painter: str,
    drilldown: ContextualLinkEntryConfig,
) -> None:
    vs = view_editor_column_spec("columns", datasource, tagged_painter_context, with_drilldown=True)

    vs.validate_value(_columns(painter, drilldown), "columns")


@pytest.mark.parametrize(
    "datasource, painter, drilldown, field",
    [
        pytest.param(
            "hosts", "alias", _link(("views", "service")), "link_spec", id="unfillable view"
        ),
        pytest.param(
            "hostgroups",
            "hg_name",
            _link(("views", "allhosts")),
            "link_spec",
            id="inherited without hosts",
        ),
        pytest.param(
            "mkeventd_events",
            "event_id",
            _link(("dashboards", "main"), ContextFilterConfig(filter_id="event_state")),
            "filters",
            id="view-only filter to a dashboard",
        ),
        pytest.param(
            "hosts",
            "alias",
            _link(
                ("views", "host"),
                ContextFilterConfig(filter_id="wato_folder"),
                include_context=False,
            ),
            "filters",
            id="target object named by nothing",
        ),
        pytest.param(
            "hosts",
            "alias",
            _link(("views", "not_a_view"), ContextFilterConfig(filter_id="wato_folder")),
            "target",
            id="unknown target",
        ),
        pytest.param(
            "hosts",
            "alias",
            _link(
                ("views", "allhosts"),
                ContextFilterConfig(filter_id="wato_folder"),
                ContextFilterConfig(filter_id="wato_folder"),
            ),
            "filters",
            id="filter twice",
        ),
        pytest.param(
            "hosts",
            "alias",
            _link(("views", "allhosts"), ContextFilterConfig(filter_id="host_labels", key="")),
            "filters",
            id="label filter without a key",
        ),
        pytest.param(
            "hosts",
            "alias",
            _link(
                ("views", "allhosts"), ContextFilterConfig(filter_id="host_labels", key="os:family")
            ),
            "filters",
            id="label key with a colon",
        ),
        pytest.param(
            "services",
            "alias",
            _link(("views", "allhosts"), ContextFilterConfig(filter_id="host_tags", key="nope")),
            "filters",
            id="tag group the tag config lacks",
        ),
        pytest.param(
            "services",
            "alias",
            _link(("views", "allhosts"), ContextFilterConfig(filter_id="service_tags", key="nope")),
            "filters",
            id="service tag group the tag config lacks",
        ),
        pytest.param(
            "services",
            "alias",
            _link(("views", "allhosts"), ContextFilterConfig(filter_id="host_auxtags", key="nope")),
            "filters",
            id="aux tag the tag config lacks",
        ),
        pytest.param(
            "services",
            "alias",
            _link(
                ("views", "allhosts"),
                *(ContextFilterConfig(filter_id="host_auxtags", key=f"aux{i}") for i in range(4)),
            ),
            "filters",
            id="more aux tags than the target reads",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_view_editor_column_spec_with_drilldown_rejects(
    tagged_painter_context: PainterContext,
    datasource: str,
    painter: str,
    drilldown: ContextualLinkEntryConfig,
    field: str,
) -> None:
    vs = view_editor_column_spec("columns", datasource, tagged_painter_context, with_drilldown=True)

    with pytest.raises(MKUserError) as excinfo:
        vs.validate_value(_columns(painter, drilldown), "columns")

    assert field in (excinfo.value.varname or "")


@pytest.mark.usefixtures("request_context")
def test_view_editor_column_spec_with_drilldown_rejects_a_target_the_author_may_not_open(
    painter_context: PainterContext,
) -> None:
    vs = view_editor_column_spec("columns", "hosts", painter_context, with_drilldown=True)

    with pytest.raises(MKUserError) as excinfo:
        vs.validate_value(
            _columns(
                "alias", _link(("dashboards", "main"), ContextFilterConfig(filter_id="wato_folder"))
            ),
            "columns",
        )

    assert "target" in (excinfo.value.varname or "")
