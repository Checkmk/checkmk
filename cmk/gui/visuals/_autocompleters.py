#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Autocompleters that depend on the visuals/livestatus layer."""

# mypy: disable-error-code="type-arg"

import re
from collections.abc import Callable, Collection

from livestatus import LivestatusColumn, MultiSiteConnection

from cmk.gui import sites
from cmk.gui.config import Config
from cmk.gui.i18n import _
from cmk.gui.type_defs import Choices
from cmk.gui.utils.labels import encode_label_for_livestatus, Label
from cmk.gui.utils.user_errors import user_errors

from ._livestatus import get_only_sites_from_context, livestatus_query_bare_string


def live_query_to_choices(
    query_callback: Callable[[MultiSiteConnection], Collection[LivestatusColumn]],
    limit: int,
    value: str,
    params: dict,
) -> Choices:
    selected_sites = get_only_sites_from_context(params.get("context", {}))
    with sites.only_sites(selected_sites), sites.set_limit(limit):
        query_result = query_callback(sites.live())
        sorted_results = sorted(
            query_result,
            key=lambda h: (
                h.lower() != value.lower(),
                not h.lower().startswith(value.lower()),
                h.lower(),
            ),
        )
        choices = [(h, h) for h in sorted_results]

    if params.get("escape_regex"):
        choices = [(re.escape(val), display) for (val, display) in choices]

    if len(choices) > limit:
        choices.insert(0, (None, _("(Max suggestions reached, be more specific)")))

    if (value, value) not in choices and params["strict"] is False:
        choices.insert(0, (value, value))
    return choices


def _sorted_unique_lq(query: str, limit: int, value: str, params: dict) -> Choices:
    """Livestatus query of single column of unique elements."""

    def _query_callback(sites_live: MultiSiteConnection) -> Collection[LivestatusColumn]:
        return sites_live.query_column_unique(query)

    return live_query_to_choices(_query_callback, limit, value, params)


def _build_regex_pattern(value: str, *, literal_search: bool) -> str:
    """Build a Livestatus regex pattern from a search value."""
    if not value:
        return "."
    if literal_search:
        return re.escape(value)
    return value


def monitored_hostname_autocompleter(config: Config, value: str, params: dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get
    the list of choices
    """
    context = params.get("context", {})
    context.pop("host", None)
    context["hostregex"] = {"host_regex": value or "."}
    query = livestatus_query_bare_string("host", context, ["host_name"], "reload")

    if user_errors:
        return [(value, value)]
    return _sorted_unique_lq(query, 200, value, params)


def monitored_service_description_autocompleter(
    config: Config, value: str, params: dict
) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get
    the list of choices
    """
    context = params.get("context", {})
    if not any((context.get("host", {}).get("host"), context.get("hostregex"))) and not params.get(
        "show_independent_of_context", True
    ):
        return []
    context.pop("service", None)
    context["serviceregex"] = {
        "service_regex": _build_regex_pattern(
            value, literal_search=params.get("literal_search", False)
        )
    }
    query = livestatus_query_bare_string("service", context, ["service_description"], "reload")

    if user_errors:
        return [(value, value)]
    return _sorted_unique_lq(query, 200, value, params)


def check_command_autocompleter(config: Config, value: str, params: dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get
    the list of choices
    """
    choices: Choices = [
        (x, x)
        for x in sites.live().query_column_unique("GET commands\nCache: reload\nColumns: name\n")
        if value.lower() in x.lower()
    ]
    empty_choices: Choices = [("", "")]
    return empty_choices + choices


def label_autocompleter(config: Config, value: str, params: dict) -> Choices:
    """Return all known labels to support tagify label input dropdown completion"""
    from cmk.ccc.regex import regex
    from cmk.gui.utils.labels import LABEL_REGEX
    from cmk.gui.valuespec import Labels

    group_labels = params.get("context", {}).get("group_labels", [])
    all_labels = Labels.get_labels(world=Labels.World(params["world"]), search_label=value)
    label_choices: Choices = [((":".join([id_, val])),) * 2 for id_, val in all_labels]

    if filtered_choices := [
        (id_, val) for id_, val in sorted(set(label_choices)) if id_ not in group_labels
    ]:
        return filtered_choices

    return [(value, value)] if regex(LABEL_REGEX).match(value) else []


def kubernetes_labels_autocompleter(config: Config, value: str, params: dict) -> Choices:
    filter_id = params["group_type"]
    object_type = filter_id.removeprefix("kubernetes_")
    label_name = f"cmk/kubernetes/{object_type}"

    def _query_callback(sites_live: MultiSiteConnection) -> Collection[LivestatusColumn]:
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

    return live_query_to_choices(_query_callback, 200, value, params)
