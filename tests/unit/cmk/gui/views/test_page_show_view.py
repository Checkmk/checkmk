#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping
from typing import override

import pytest

from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.config import Config, RequestCacheConfig
from cmk.gui.data_source import data_source_registry
from cmk.gui.http import request
from cmk.gui.type_defs import VisualContext
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view import View
from cmk.gui.views.page_show_view import _filter_form_filters, _get_needed_regular_columns
from cmk.gui.views.store import get_all_views
from cmk.gui.visuals.filter import Filter
from cmk.gui.visuals.filter.components import FilterComponent
from cmk.web.utils.request_cache import RequestCache


def test_get_needed_regular_columns(view: View) -> None:
    class SomeFilter(Filter):
        @override
        def components(
            self, _request_cache: RequestCache[RequestCacheConfig]
        ) -> Iterable[FilterComponent]:
            return []

        @override
        def columns_for_filter_table(self, context: VisualContext) -> Iterable[str]:
            return ["some_column"]

    columns = _get_needed_regular_columns(
        [
            SomeFilter(
                ident="some_filter",
                title="Some filter",
                sort_index=1,
                info="info",
                htmlvars=[],
                link_columns=[],
            )
        ],
        view,
    )
    assert sorted(columns) == sorted(
        [
            "host_accept_passive_checks",
            "host_acknowledged",
            "host_action_url_expanded",
            "host_active_checks_enabled",
            "host_address",
            "host_check_command",
            "host_check_type",
            "host_comments_with_extra_info",
            "host_custom_variable_names",
            "host_custom_variable_values",
            "host_downtimes",
            "host_downtimes_with_extra_info",
            "host_filename",
            "host_has_been_checked",
            "host_icon_image",
            "host_in_check_period",
            "host_in_notification_period",
            "host_in_service_period",
            "host_is_flapping",
            "host_modified_attributes_list",
            "host_name",
            "host_notes_url_expanded",
            "host_notifications_enabled",
            "host_num_services_crit",
            "host_num_services_ok",
            "host_num_services_pending",
            "host_num_services_unknown",
            "host_num_services_warn",
            "host_perf_data",
            "host_pnpgraph_present",
            "host_scheduled_downtime_depth",
            "host_staleness",
            "host_state",
            "some_column",
        ]
    )


def _view_opened_with(view_name: str, url_vars: Mapping[str, str]) -> View:
    view_spec = get_all_views()[(UserId.builtin(), view_name)].copy()
    for var, value in url_vars.items():
        request.set_var(var, value)
    infos = data_source_registry[view_spec["datasource"]]().infos
    request_cache = RequestCache(Config())
    context = visuals.active_context_from_request(infos, view_spec["context"], request_cache)
    return View(view_name, view_spec, context, UserPermissions({}, {}, {}, []), request_cache)


@pytest.mark.usefixtures("request_context")
def test_the_filter_form_lists_a_filter_carried_by_a_link() -> None:
    view = _view_opened_with("searchhost", {"hst1": "on", "filled_in": "filter"})

    listed = {filter_.ident for filter_ in _filter_form_filters(view)}

    assert "hoststate" in listed
    assert view.context["hoststate"]["hst1"] == "on"
    assert {"hostregex", "host_labels"} <= listed


@pytest.mark.usefixtures("request_context")
def test_the_filter_form_round_trips_the_merged_context() -> None:
    view = _view_opened_with("searchhost", {"hst1": "on", "filled_in": "filter"})
    listed = _filter_form_filters(view)

    submitted_vars = {
        var: value
        for filter_ in listed
        for var, value in view.context.get(filter_.ident, {}).items()
    }
    request.del_vars("hst")
    for var, value in submitted_vars.items():
        request.set_var(var, value)
    request.set_var("_active", ";".join(sorted(f.ident for f in listed)))

    resubmitted = visuals.active_context_from_request(view.datasource.infos, {}, view.request_cache)

    assert {ident: vars_ for ident, vars_ in resubmitted.items() if any(vars_.values())} == {
        ident: vars_ for ident, vars_ in view.context.items() if any(vars_.values())
    }
