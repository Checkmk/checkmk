#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.gui.autocompleters import AutocompleterFunc
from cmk.gui.config import Config
from cmk.gui.type_defs import Choices

from ._from_api import metrics_from_api
from ._graph_codec import context_from_json
from ._metrics import registered_metric_ids_and_titles
from ._plugins import registered_metrics, registered_translations
from ._valuespecs import LivestatusQueryFunc, metrics_of_query


def metrics_autocompleter(
    value: str,
    params: Mapping[str, object],
    livestatus_query: LivestatusQueryFunc,
) -> Choices:
    context = context_from_json(params.get("context", {}))
    host = context.get("host", {}).get("host", "")
    service = context.get("service", {}).get("service", "")
    if not params.get("show_independent_of_context") and not all((host, service)):
        return []

    if context:
        metrics = set(
            metrics_of_query(
                context, registered_metrics(), registered_translations(), livestatus_query
            )
        )
    else:
        metrics = set(registered_metric_ids_and_titles(metrics_from_api))

    return sorted(
        (v for v in metrics if _matches_id_or_title(value, v)),
        key=lambda a: a[1].lower(),
    )


def monitored_metrics_autocompleter(livestatus_query: LivestatusQueryFunc) -> AutocompleterFunc:
    def autocompleter(config: Config, value: str, params: dict[str, object]) -> Choices:  # noqa: ARG001
        return metrics_autocompleter(value, params, livestatus_query=livestatus_query)

    return autocompleter


def _matches_id_or_title(ident: str, choice: tuple[str | None, str]) -> bool:
    return ident.lower() in (choice[0] or "").lower() or ident.lower() in choice[1].lower()
