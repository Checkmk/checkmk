#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from itertools import chain
from typing import Dict, Iterable, Mapping, Tuple

from cmk.utils.type_defs import MetricName

import cmk.gui.sites as sites
import cmk.gui.watolib as watolib
from cmk.gui.exceptions import MKUserError
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
from cmk.gui.type_defs import Choices
from cmk.gui.valuespec import autocompleter_registry


def _sorted_unique_lq(query: str, limit: int, value: str, params: Dict) -> Choices:
    """Livestatus query of single column of unique elements.
    Prepare dropdown choices"""
    selected_sites = get_only_sites_from_context(params.get("context", {}))
    with sites.only_sites(selected_sites), sites.set_limit(limit):
        choices = [
            (h, h) for h in sorted(sites.live().query_column_unique(query), key=lambda h: h.lower())
        ]

    if len(choices) > limit:
        choices.insert(0, (None, _("(Max suggestions reached, be more specific)")))

    if (value, value) not in choices and params["strict"] == "False":
        choices.insert(0, (value, value))  # User is allowed to enter anything they want
    return choices


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


@autocompleter_registry.register_expression("allgroups")
def hostgroup_autocompleter(value: str, params: Dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices"""
    group_type = params["group_type"]
    # Have something without ifs
    group_type = (
        "contact" if "_contact" in group_type else "host" if "host" in group_type else "service"
    )
    choices: Choices = sorted(
        (v for v in sites.all_groups(group_type) if value.lower() in v[1].lower()),
        key=lambda a: a[1].lower(),
    )
    # This part should not exists as the optional(not enforce) would better be not having the filter at all
    if not params.get("strict"):
        empty_choice: Choices = [("", "")]
        choices = empty_choice + choices
    return choices


@autocompleter_registry.register_expression("monitored_service_description")
def monitored_service_description_autocompleter(value: str, params: Dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices"""
    context = params.get("context", {})
    if not any((context.get("host"), context.get("hostregex"))) and params["strict"] == "withHost":
        return []
    context.pop("service", None)
    context["serviceregex"] = {"service_regex": value or "."}
    query = livestatus_query_bare_string("service", context, ["service_description"], "reload")

    return _sorted_unique_lq(query, 200, value, params)


@autocompleter_registry.register_expression("monitored_metrics")
def metrics_autocompleter(value: str, params: Dict) -> Choices:
    context = params.get("context", {})
    host = context.get("host", {}).get("host", "")
    service = context.get("service", {}).get("service", "")
    if params.get("strict") == "withSource" and not all((host, service)):
        return []

    if context:
        metrics = set(metrics_of_query(context))
    else:
        metrics = set(registered_metrics())

    return sorted((v for v in metrics if value.lower() in v[1].lower()), key=lambda a: a[1].lower())


def _graph_choices_from_livestatus_row(row) -> Iterable[Tuple[str, str]]:
    def _metric_title_from_id(metric_or_graph_id: MetricName) -> str:
        metric_id = metric_or_graph_id.replace("METRIC_", "")
        return str(metric_info.get(metric_id, {}).get("title", metric_id))

    def _graph_template_title(graph_template: Mapping) -> str:
        return str(graph_template.get("title")) or _metric_title_from_id(graph_template["id"])

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
    if not params.get("context") and params.get("strict", "False") == "False":
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


@page_registry.register_page("ajax_vs_autocomplete")
class PageVsAutocomplete(AjaxPage):
    def page(self):
        api_request = self.webapi_request()
        validate_autocompleter_data(api_request)
        ident = api_request["ident"]
        if not ident:
            raise MKUserError("ident", _('You need to set the "%s" parameter.') % "ident")

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
