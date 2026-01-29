#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import re
from collections.abc import Callable, Collection, Sequence
from typing import get_args, override

from livestatus import LivestatusColumn, MultiSiteConnection

from cmk.ccc.regex import regex
from cmk.gui import sites
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.groups import GroupType
from cmk.gui.i18n import _
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.type_defs import Choices
from cmk.gui.utils.labels import encode_label_for_livestatus, Label, LABEL_REGEX
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import autocompleter_registry, AutocompleterRegistry, Labels
from cmk.gui.visuals import get_only_sites_from_context, livestatus_query_bare_string
from cmk.gui.watolib.check_mk_automations import get_check_information_cached
from cmk.gui.watolib.groups_io import all_groups


def register(page_registry: PageRegistry, autocompleter_registry_: AutocompleterRegistry) -> None:
    page_registry.register(PageEndpoint("ajax_vs_autocomplete", PageVsAutocomplete()))
    autocompleter_registry_.register_autocompleter(
        "monitored_hostname", monitored_hostname_autocompleter
    )
    autocompleter_registry_.register_autocompleter("allgroups", hostgroup_autocompleter)
    autocompleter_registry_.register_autocompleter("check_cmd", check_command_autocompleter)
    autocompleter_registry_.register_autocompleter(
        "monitored_service_description", monitored_service_description_autocompleter
    )
    autocompleter_registry_.register_autocompleter(
        "kubernetes_labels", kubernetes_labels_autocompleter
    )
    autocompleter_registry_.register_autocompleter("tag_groups", tag_group_autocompleter)
    autocompleter_registry_.register_autocompleter("tag_groups_opt", tag_group_opt_autocompleter)
    autocompleter_registry_.register_autocompleter("label", label_autocompleter)
    autocompleter_registry_.register_autocompleter("check_types", check_types_autocompleter)


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
                h.lower() != value.lower(),  # Exact matches first
                not h.lower().startswith(
                    value.lower()
                ),  # Then choices starting with the input value
                h.lower(),  # Then alphabetically
            ),
        )
        choices = [(h, h) for h in sorted_results]

    if params.get("escape_regex"):
        choices = [(re.escape(val), display) for (val, display) in choices]

    if len(choices) > limit:
        choices.insert(0, (None, _("(Max suggestions reached, be more specific)")))

    if (value, value) not in choices and params["strict"] is False:
        choices.insert(0, (value, value))  # User is allowed to enter anything they want
    return choices


def _sorted_unique_lq(query: str, limit: int, value: str, params: dict) -> Choices:
    """Livestatus query of single column of unique elements.
    Prepare dropdown choices"""

    def _query_callback(sites_live: MultiSiteConnection) -> Collection[LivestatusColumn]:
        return sites_live.query_column_unique(query)

    return live_query_to_choices(_query_callback, limit, value, params)


def _matches_id_or_title(ident: str, choice: tuple[str | None, str]) -> bool:
    return ident.lower() in (choice[0] or "").lower() or ident.lower() in choice[1].lower()


def monitored_hostname_autocompleter(config: Config, value: str, params: dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices
    """
    context = params.get("context", {})
    context.pop("host", None)
    context["hostregex"] = {"host_regex": value or "."}
    query = livestatus_query_bare_string("host", context, ["host_name"], "reload")

    # In case of user errors occuring within livestatus_query_bare_string() (filter validation) the
    # livestatus query cannot be run -> return the given value
    # Rendering of the error msgs is handled in JS
    if user_errors:
        return [(value, value)]
    return _sorted_unique_lq(query, 200, value, params)


def hostgroup_autocompleter(config: Config, value: str, params: dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices
    """
    group_type = params["group_type"]
    if group_type not in (valid_group_types := get_args(GroupType)):
        raise MKUserError(
            "params",
            _("you need to set %s parameter to either %s.")
            % ("group_type", str(valid_group_types)),
        )
    choices: Choices = sorted(
        (v for v in all_groups(group_type) if _matches_id_or_title(value, v)),
        key=lambda a: a[1].lower(),
    )
    # This part should not exists as the optional(not enforce) would better be not having the filter at all
    if not params.get("strict"):
        empty_choice: Choices = [("", "")]
        choices = empty_choice + choices
    return choices


def check_command_autocompleter(config: Config, value: str, params: dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices
    """
    choices: Choices = [
        (x, x)
        for x in sites.live().query_column_unique("GET commands\nCache: reload\nColumns: name\n")
        if value.lower() in x.lower()
    ]
    empty_choices: Choices = [("", "")]
    return empty_choices + choices


def monitored_service_description_autocompleter(
    config: Config, value: str, params: dict
) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the completions_params to get the list of choices
    """
    context = params.get("context", {})
    if not any((context.get("host", {}).get("host"), context.get("hostregex"))) and not params.get(
        "show_independent_of_context", True
    ):
        return []
    context.pop("service", None)
    context["serviceregex"] = {"service_regex": value or "."}
    query = livestatus_query_bare_string("service", context, ["service_description"], "reload")

    # In case of user errors occuring within livestatus_query_bare_string() (filter validation) the
    # livestatus query cannot be run -> return the given value
    # Rendering of the error msgs is handled in JS
    if user_errors:
        return [(value, value)]
    return _sorted_unique_lq(query, 200, value, params)


def kubernetes_labels_autocompleter(config: Config, value: str, params: dict) -> Choices:
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

    return live_query_to_choices(_query_callback, 200, value, params)


def tag_group_autocompleter(config: Config, value: str, params: dict) -> Choices:
    return sorted(
        (v for v in config.tags.get_tag_group_choices() if _matches_id_or_title(value, v)),
        key=lambda a: a[1].lower(),
    )


def tag_group_opt_autocompleter(config: Config, value: str, params: dict) -> Choices:
    grouped: Choices = []

    for tag_group in config.tags.tag_groups:
        if tag_group.id == params["group_id"]:
            grouped.append(("", ""))
            for grouped_tag in tag_group.tags:
                tag_id = "" if grouped_tag.id is None else grouped_tag.id
                if value.lower() in grouped_tag.title.lower() or value == grouped_tag.id:
                    grouped.append((tag_id, grouped_tag.title))
    return grouped


def label_autocompleter(config: Config, value: str, params: dict) -> Choices:
    """Return all known labels to support tagify label input dropdown completion"""
    group_labels: Sequence[str] = params.get("context", {}).get("group_labels", [])
    all_labels: Sequence[tuple[str, str]] = Labels.get_labels(
        world=Labels.World(params["world"]), search_label=value
    )
    # E.g.: [("label:abc", "label:abc"), ("label:xyz", "label:xyz")]
    label_choices: Choices = [((":".join([id_, val])),) * 2 for id_, val in all_labels]

    # Filter out all labels that already exist in the given label group
    if filtered_choices := [
        (id_, val) for id_, val in sorted(set(label_choices)) if id_ not in group_labels
    ]:
        return filtered_choices

    # The user is allowed to enter new labels if they are valid ("<key>:<value>")
    return [(value, value)] if regex(LABEL_REGEX).match(value) else []


def check_types_autocompleter(config: Config, value: str, params: dict) -> Choices:
    return [
        (str(cn), (str(cn) + " - " + c["title"]))
        for (cn, c) in get_check_information_cached(debug=config.debug).items()
        if not cn.is_management_name()
    ]


def validate_autocompleter_data(api_request: dict[str, object]) -> None:
    params = api_request.get("params")
    if params is None:
        raise MKUserError("params", _('You need to set the "%s" parameter.') % "params")

    value = api_request.get("value")
    if value is None:
        raise MKUserError("params", _('You need to set the "%s" parameter.') % "value")

    ident = api_request.get("ident")
    if ident is None:
        raise MKUserError("ident", _('You need to set the "%s" parameter.') % "ident")


class PageVsAutocomplete(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        api_request = ctx.request.get_request()
        validate_autocompleter_data(api_request)
        ident = api_request["ident"]

        completer = autocompleter_registry.get(ident)
        if completer is None:
            raise MKUserError("ident", _("Invalid ident: %s") % ident)

        result_data = completer(ctx.config, api_request["value"], api_request["params"])

        # Check for correct result_data format
        assert isinstance(result_data, list)
        if result_data:
            assert isinstance(result_data[0], list | tuple)
            assert len(result_data[0]) == 2

        return {"choices": result_data}
