#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from itertools import chain
from typing import Callable, Collection, Dict, Iterable, Mapping, Tuple

from livestatus import LivestatusColumn, MultiSiteConnection

from cmk.utils.type_defs import MetricName

import cmk.gui.mkeventd as mkeventd
import cmk.gui.sites as sites
import cmk.gui.watolib as watolib
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import active_config
from cmk.gui.i18n import _
from cmk.gui.pages import AjaxPage, page_registry
from cmk.gui.plugins.metrics.utils import (
    get_graph_templates,
    graph_info,
    metric_info,
    metrics_of_query,
    registered_metrics,
    translated_metrics_from_row,
)
from cmk.gui.plugins.visuals.utils import (
    get_only_sites_from_context,
    livestatus_query_bare,
    livestatus_query_bare_string,
)
from cmk.gui.query_filters import sites_options
from cmk.gui.type_defs import Choices
from cmk.gui.utils.labels import encode_label_for_livestatus, Label
from cmk.gui.valuespec import autocompleter_registry


def __live_query_to_choices(
    query_callback: Callable[[MultiSiteConnection], Collection[LivestatusColumn]],
    limit: int,
    value: str,
    params: Dict,
) -> Choices:
    selected_sites = get_only_sites_from_context(params.get("context", {}))
    with sites.only_sites(selected_sites), sites.set_limit(limit):
        query_result = query_callback(sites.live())
        choices = [(h, h) for h in sorted(query_result, key=lambda h: h.lower())]

    if len(choices) > limit:
        choices.insert(0, (None, _("(Max suggestions reached, be more specific)")))

    if (value, value) not in choices and params["strict"] is False:
        choices.insert(0, (value, value))  # User is allowed to enter anything they want
    return choices


def _filter_choices(value: str, choices: Choices) -> Choices:
    value_to_search = value.lower()
    return [(value, title) for value, title in choices if value_to_search in title.lower()]


def _sorted_unique_lq(query: str, limit: int, value: str, params: Dict) -> Choices:
    """Livestatus query of single column of unique elements.
    Prepare dropdown choices"""

    def _query_callback(sites_live: MultiSiteConnection) -> Collection[LivestatusColumn]:
        return sites_live.query_column_unique(query)

    return __live_query_to_choices(_query_callback, limit, value, params)


@autocompleter_registry.register_expression("monitored_hostname")
def monitored_hostname_autocompleter(value: str, params: Dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices"""
    context = params.get("context", {})
    context.pop("host", None)
    context["hostregex"] = {"host_regex": value or "."}
    query = livestatus_query_bare_string("host", context, ["host_name"], "reload")

    return _sorted_unique_lq(query, 200, value, params)


@autocompleter_registry.register_expression("config_hostname")
def config_hostname_autocompleter(value: str, params: Dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices"""
    all_hosts: Dict[str, watolib.CREHost] = watolib.Host.all()
    match_pattern = re.compile(value, re.IGNORECASE)
    match_list: Choices = []
    for host_name, host_object in all_hosts.items():
        if match_pattern.search(host_name) is not None and host_object.may("read"):
            match_list.append((host_name, host_name))

    if not any(x[0] == value for x in match_list):
        match_list.insert(0, (value, value))  # User is allowed to enter anything they want

    return match_list


@autocompleter_registry.register_expression("sites")
def sites_autocompleter(value: str, params: Dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices"""

    choices: Choices = sorted(
        (v for v in sites_options() if value.lower() in v[1].lower()),
        key=lambda a: a[1].lower(),
    )

    # This part should not exists as the optional(not enforce) would better be not having the filter at all
    if not params.get("strict"):
        empty_choice: Choices = [("", "All Sites")]
        choices = empty_choice + choices
    return choices


@autocompleter_registry.register_expression("allgroups")
def hostgroup_autocompleter(value: str, params: Dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices"""
    group_type = params["group_type"]
    choices: Choices = sorted(
        (v for v in sites.all_groups(group_type) if value.lower() in v[1].lower()),
        key=lambda a: a[1].lower(),
    )
    # This part should not exists as the optional(not enforce) would better be not having the filter at all
    if not params.get("strict"):
        empty_choice: Choices = [("", "")]
        choices = empty_choice + choices
    return choices


@autocompleter_registry.register_expression("check_cmd")
def check_command_autocompleter(value: str, params: Dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices"""
    choices: Choices = [
        (x, x)
        for x in sites.live().query_column_unique("GET commands\nCache: reload\nColumns: name\n")
        if value.lower() in x.lower()
    ]
    empty_choices: Choices = [("", "")]
    return empty_choices + choices


@autocompleter_registry.register_expression("service_levels")
def service_levels_autocompleter(value: str, params: Dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices"""
    choices: Choices = mkeventd.service_levels()
    empty_choices: Choices = [("", "")]
    return empty_choices + _filter_choices(value, choices)


@autocompleter_registry.register_expression("syslog_facilities")
def syslog_facilities_autocompleter(value: str, params: Dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices"""
    choices: Choices = [(str(v), title) for v, title in mkeventd.syslog_facilities]
    empty_choices: Choices = [("", "")]
    return empty_choices + _filter_choices(value, choices)


@autocompleter_registry.register_expression("monitored_service_description")
def monitored_service_description_autocompleter(value: str, params: Dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices"""
    context = params.get("context", {})
    if not any((context.get("host", {}).get("host"), context.get("hostregex"))) and not params.get(
        "show_independent_of_context", True
    ):
        return []
    context.pop("service", None)
    context["serviceregex"] = {"service_regex": value or "."}
    query = livestatus_query_bare_string("service", context, ["service_description"], "reload")
    result = _sorted_unique_lq(query, 200, value, params)
    return result


@autocompleter_registry.register_expression("wato_folder_choices")
def wato_folder_choices_autocompleter(value: str, params: Dict) -> Choices:
    return watolib.Folder.folder_choices_fulltitle()


@autocompleter_registry.register_expression("kubernetes_labels")
def kubernetes_labels_autocompleter(value: str, params: Dict) -> Choices:
    filter_id = params["group_type"]
    object_type = filter_id.removeprefix("kubernetes_")
    label_name = f"cmk/kubernetes/{object_type}"

    def _query_callback(sites_live: MultiSiteConnection) -> Collection[LivestatusColumn]:
        """
        we search for hosts having a certain label
        ('cmk/kubernets/object:{object_type}') and want a list of unique labels
        values of labels with the key label_name.
        """
        label_filter = encode_label_for_livestatus(
            column="labels",
            label=Label("cmk/kubernetes/object", object_type, False),
        )
        query = f"GET hosts\nColumns: labels\n{label_filter}"

        query_result = sites_live.query_column(query)
        label_values = set()
        for element in query_result:
            for label_key, label_value in element.items():
                if label_key == label_name:
                    label_values.add(label_value)
        return label_values

    return __live_query_to_choices(_query_callback, 200, value, params)


@autocompleter_registry.register_expression("monitored_metrics")
def metrics_autocompleter(value: str, params: Dict) -> Choices:
    context = params.get("context", {})
    host = context.get("host", {}).get("host", "")
    service = context.get("service", {}).get("service", "")
    if not params.get("show_independent_of_context") and not all((host, service)):
        return []

    if context:
        metrics = set(metrics_of_query(context))
    else:
        metrics = set(registered_metrics())

    return sorted(
        (v for v in metrics if value.lower() in v[1].lower() or value == v[0]),
        key=lambda a: a[1].lower(),
    )


@autocompleter_registry.register_expression("tag_groups")
def tag_group_autocompleter(value: str, params: Dict) -> Choices:
    return sorted(
        (v for v in active_config.tags.get_tag_group_choices() if value.lower() in v[1].lower()),
        key=lambda a: a[1].lower(),
    )


@autocompleter_registry.register_expression("tag_groups_opt")
def tag_group_opt_autocompleter(value: str, params: Dict) -> Choices:
    grouped: Choices = []

    for tag_group in active_config.tags.tag_groups:
        if tag_group.id == params["group_id"]:
            grouped.append(("", ""))
            for grouped_tag in tag_group.tags:
                tag_id = "" if grouped_tag.id is None else grouped_tag.id
                if value.lower() in grouped_tag.title:
                    grouped.append((tag_id, grouped_tag.title))
    return grouped


def _graph_choices_from_livestatus_row(row) -> Iterable[Tuple[str, str]]:
    def _metric_title_from_id(metric_or_graph_id: MetricName) -> str:
        metric_id = metric_or_graph_id.replace("METRIC_", "")
        return str(metric_info.get(metric_id, {}).get("title", metric_id))

    def _graph_template_title(graph_template: Mapping) -> str:
        return str(graph_template.get("title", "")) or _metric_title_from_id(graph_template["id"])

    yield from (
        (
            template["id"],
            _graph_template_title(template),
        )
        for template in get_graph_templates(translated_metrics_from_row(row))
    )


@autocompleter_registry.register_expression("available_graphs")
def graph_templates_autocompleter(value: str, params: Dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the
    completions_params to get the list of choices"""
    if not params.get("context") and params.get("show_independent_of_context") is True:
        choices: Iterable[Tuple[str, str]] = (
            (
                graph_id,
                str(
                    graph_details.get(
                        "title",
                        graph_id,
                    )
                ),
            )
            for graph_id, graph_details in graph_info.items()
        )

    else:
        columns = [
            "service_check_command",
            "service_perf_data",
            "service_metrics",
        ]

        choices = set(
            chain.from_iterable(
                _graph_choices_from_livestatus_row(row)
                for row in livestatus_query_bare("service", params["context"], columns)
            )
        )

    return sorted((v for v in choices if value.lower() in v[1].lower()), key=lambda a: a[1].lower())


def validate_autocompleter_data(api_request):
    params = api_request.get("params")
    if params is None:
        raise MKUserError("params", _('You need to set the "%s" parameter.') % "params")

    value = api_request.get("value")
    if value is None:
        raise MKUserError("params", _('You need to set the "%s" parameter.') % "value")

    ident = api_request.get("ident")
    if ident is None:
        raise MKUserError("ident", _('You need to set the "%s" parameter.') % "ident")


@page_registry.register_page("ajax_vs_autocomplete")
class PageVsAutocomplete(AjaxPage):
    def page(self):
        api_request = self.webapi_request()
        validate_autocompleter_data(api_request)
        ident = api_request["ident"]

        completer = autocompleter_registry.get(ident)
        if completer is None:
            raise MKUserError("ident", _("Invalid ident: %s") % ident)

        result_data = completer(api_request["value"], api_request["params"])

        # Check for correct result_data format
        assert isinstance(result_data, list)
        if result_data:
            assert isinstance(result_data[0], (list, tuple))
            assert len(result_data[0]) == 2

        return {"choices": result_data}
