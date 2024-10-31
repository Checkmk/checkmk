#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.gui.type_defs import Choices

from ._graph_templates import (
    get_graph_template_choices,
    graph_and_single_metric_templates_choices_for_context,
    GraphTemplateChoice,
)
from ._metrics import registered_metrics
from ._valuespecs import metrics_of_query


def metrics_autocompleter(value: str, params: dict) -> Choices:
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
        (v for v in metrics if _matches_id_or_title(value, v)),
        key=lambda a: a[1].lower(),
    )


def graph_templates_autocompleter(value_entered_by_user: str, params: dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the
    completions_params to get the list of choices"""
    if not params.get("context") and params.get("show_independent_of_context") is True:
        _sorted_matching_graph_template_choices(
            value_entered_by_user,
            get_graph_template_choices(),
        )

    graph_template_choices, single_metric_template_choices = (
        graph_and_single_metric_templates_choices_for_context(params["context"])
    )
    return _sorted_matching_graph_template_choices(
        value_entered_by_user,
        graph_template_choices,
    ) + _sorted_matching_graph_template_choices(
        value_entered_by_user,
        single_metric_template_choices,
    )


def _matches_id_or_title(ident: str, choice: tuple[str | None, str]) -> bool:
    return ident.lower() in (choice[0] or "").lower() or ident.lower() in choice[1].lower()


def _sorted_matching_graph_template_choices(
    value_entered_by_user: str,
    all_choices: Iterable[GraphTemplateChoice],
) -> Choices:
    return [
        (graph_template_choice.id, graph_template_choice.title)
        for graph_template_choice in sorted(
            (
                graph_template_choice
                for graph_template_choice in all_choices
                if value_entered_by_user.lower() in graph_template_choice.id.lower()
                or value_entered_by_user.lower() in graph_template_choice.title.lower()
            ),
            key=lambda graph_template_choice: graph_template_choice.title,
        )
    ]
