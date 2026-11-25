#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Iterator, Mapping, Sequence
from typing import Literal

from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import metric_attributes, parse_performance_data, translate_metric_names
from cmk.graphing_engine import MetricName as EngineMetricName
from cmk.gui.autocompleters import AutocompleterFunc
from cmk.gui.config import Config
from cmk.gui.i18n import translate_to_current_language
from cmk.gui.log import logger
from cmk.gui.type_defs import VisualContext
from cmk.web.utils.choices import Choice

from ._decoding import context_from_json, ensure_type
from ._metric_spec import registered_metric_ids_and_titles
from ._plugins import registered_metrics, registered_translations

type LivestatusQueryFunc = Callable[
    [Literal["host", "service"], VisualContext, list[str]], Sequence[Mapping[str, object]]
]


def _metric_choices(
    check_command: str,
    raw_metric_names: Sequence[EngineMetricName],
    registered_metrics: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
) -> Iterator[Choice]:
    for metric_name in translate_metric_names(
        check_command, raw_metric_names, registered_translations
    ):
        yield (
            metric_name,
            metric_attributes(metric_name, translate_to_current_language, registered_metrics).title,
        )


def _engine_metric_names(raw: object) -> Iterator[EngineMetricName]:
    for name in ensure_type(raw, list):
        yield EngineMetricName(ensure_type(name, str))


def metrics_of_query(
    context: VisualContext,
    registered_metrics: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    livestatus_query: LivestatusQueryFunc,
    *,
    debug: bool,
) -> Iterator[Choice]:
    # Fetch host data with the *same* query. This saves one round trip. And head
    # host has at least one service
    columns = [
        "service_check_command",
        "service_perf_data",
        "service_metrics",
        "host_check_command",
        "host_metrics",
    ]

    row: Mapping[str, object] = {}
    for row in livestatus_query("service", context, columns):
        raw = parse_performance_data(
            ensure_type(row["service_perf_data"], str),
            ensure_type(row["service_check_command"], str),
            debug=debug,
            logger=logger,
        )
        yield from _metric_choices(
            raw.check_command,
            [*raw.values, *_engine_metric_names(row["service_metrics"])],
            registered_metrics,
            registered_translations,
        )

    if row.get("host_check_command"):
        yield from _metric_choices(
            str(row["host_check_command"]),
            list(_engine_metric_names(row["host_metrics"])),
            registered_metrics,
            registered_translations,
        )


def _matches_id_or_title(ident: str, choice: tuple[str | None, str]) -> bool:
    return ident.lower() in (choice[0] or "").lower() or ident.lower() in choice[1].lower()


def _metrics_autocompleter(
    value: str,
    params: Mapping[str, object],
    registered_metrics: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    livestatus_query: LivestatusQueryFunc,
    *,
    debug: bool,
) -> list[Choice]:
    context = context_from_json(params.get("context", {}))
    host = context.get("host", {}).get("host", "")
    service = context.get("service", {}).get("service", "")
    if not params.get("show_independent_of_context") and not all((host, service)):
        return []

    if context:
        metrics = set(
            metrics_of_query(
                context,
                registered_metrics,
                registered_translations,
                livestatus_query,
                debug=debug,
            )
        )
    else:
        metrics = set(registered_metric_ids_and_titles(registered_metrics))

    return sorted(
        (v for v in metrics if _matches_id_or_title(value, v)),
        key=lambda a: a[1].lower(),
    )


def monitored_metrics_autocompleter(livestatus_query: LivestatusQueryFunc) -> AutocompleterFunc:
    def autocompleter(config: Config, value: str, params: dict[str, object]) -> list[Choice]:
        return _metrics_autocompleter(
            value,
            params,
            registered_metrics(),
            registered_translations(),
            livestatus_query,
            debug=config.debug,
        )

    return autocompleter
