#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.gui.type_defs import Choices
from cmk.gui.visuals import livestatus_query_bare

from ._graph_templates import get_graph_template_choices, get_graph_templates
from ._metrics import get_metric_spec, registered_metrics
from ._utils import translated_metrics_from_row
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


def graph_templates_autocompleter(value: str, params: dict) -> Choices:
    """Return the matching list of dropdown choices
    Called by the webservice with the current input field value and the
    completions_params to get the list of choices"""
    if not params.get("context") and params.get("show_independent_of_context") is True:
        choices: Iterable[tuple[str, str]] = get_graph_template_choices()
    else:
        choices = {
            (template.id, template.title or str(get_metric_spec(template.id).title))
            for row in livestatus_query_bare(
                "service",
                params["context"],
                ["service_check_command", "service_perf_data", "service_metrics"],
            )
            for template in get_graph_templates(translated_metrics_from_row(row))
        }

    return sorted(
        (v for v in choices if _matches_id_or_title(value, v)), key=lambda a: a[1].lower()
    )


def _matches_id_or_title(ident: str, choice: tuple[str | None, str]) -> bool:
    return ident.lower() in (choice[0] or "").lower() or ident.lower() in choice[1].lower()
