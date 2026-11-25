#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from typing import Literal

from cmk.ccc.site import SiteId
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import translations as translations_v1
from cmk.graphing_engine import metric_attributes, parse_performance_data, translate_metric_names
from cmk.graphing_engine import MetricName as EngineMetricName
from cmk.gui.autocompleters import AutocompleterFunc
from cmk.gui.config import Config
from cmk.gui.i18n import translate_to_current_language
from cmk.gui.log import logger
from cmk.gui.site_config import enabled_sites
from cmk.gui.type_defs import VisualContext
from cmk.web.utils.choices import Choice

from ._decoding import context_from_json, ensure_type
from ._metric_spec import registered_metric_ids_and_titles
from ._plugins import registered_metrics, registered_translations

type LivestatusQueryFunc = Callable[
    [Literal["host", "service"], VisualContext, list[str]], Sequence[Mapping[str, object]]
]
type EnabledSiteIdsFunc = Callable[[], Sequence[SiteId]]


def _metrics_of_object(
    check_command: object,
    perf_data: object,
    rrd_metrics: object,
    registered_metrics: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    *,
    debug: bool,
) -> Iterator[Choice]:
    raw = parse_performance_data(
        ensure_type(perf_data, str),
        ensure_type(check_command, str),
        [EngineMetricName(ensure_type(name, str)) for name in ensure_type(rrd_metrics, list)],
        debug=debug,
        logger=logger,
    )
    for metric_name in translate_metric_names(
        raw.check_command, list(raw.values), registered_translations
    ):
        yield (
            metric_name,
            metric_attributes(metric_name, translate_to_current_language, registered_metrics).title,
        )


def metrics_of_query(
    context: VisualContext,
    registered_metrics: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    livestatus_query: LivestatusQueryFunc,
    *,
    debug: bool,
) -> Iterator[Choice]:
    columns = [
        "host_name",
        "service_check_command",
        "service_perf_data",
        "service_metrics",
        "host_check_command",
        "host_perf_data",
        "host_metrics",
    ]
    host_rows: dict[tuple[object, object], Mapping[str, object]] = {}
    for row in livestatus_query("service", context, columns):
        yield from _metrics_of_object(
            row["service_check_command"],
            row["service_perf_data"],
            row["service_metrics"],
            registered_metrics,
            registered_translations,
            debug=debug,
        )
        host_rows[(row.get("site"), row["host_name"])] = row

    for row in host_rows.values():
        yield from _metrics_of_object(
            row["host_check_command"],
            row["host_perf_data"],
            row["host_metrics"],
            registered_metrics,
            registered_translations,
            debug=debug,
        )


def _matches_id_or_title(ident: str, choice: tuple[str | None, str]) -> bool:
    return ident.lower() in (choice[0] or "").lower() or ident.lower() in choice[1].lower()


def _metric_choices(
    params: Mapping[str, object],
    registered_metrics: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    livestatus_query: LivestatusQueryFunc,
    enabled_site_ids: EnabledSiteIdsFunc,
    *,
    debug: bool,
) -> Iterable[Choice]:
    context = context_from_json(params.get("context", {}))
    host = context.get("host", {}).get("host", "")
    service = context.get("service", {}).get("service", "")
    if not params.get("show_independent_of_context") and not all((host, service)):
        return ()

    if context:
        return metrics_of_query(
            context,
            registered_metrics,
            registered_translations,
            livestatus_query,
            debug=debug,
        )

    match params.get("metrics_without_context", "registered"):
        case "registered":
            return registered_metric_ids_and_titles(registered_metrics)
        case "monitored":
            return metrics_of_query(
                {"sites": {"sites": "|".join(enabled_site_ids())}},
                registered_metrics,
                registered_translations,
                livestatus_query,
                debug=debug,
            )
        case other:
            raise ValueError(f"unknown metrics without context: {other!r}")


def _metrics_autocompleter(
    value: str,
    params: Mapping[str, object],
    registered_metrics: Mapping[str, metrics_v1.Metric],
    registered_translations: Sequence[translations_v1.Translation],
    livestatus_query: LivestatusQueryFunc,
    enabled_site_ids: EnabledSiteIdsFunc,
    *,
    debug: bool,
) -> list[Choice]:
    choices = _metric_choices(
        params,
        registered_metrics,
        registered_translations,
        livestatus_query,
        enabled_site_ids,
        debug=debug,
    )
    return sorted(
        (choice for choice in set(choices) if _matches_id_or_title(value, choice)),
        key=lambda choice: choice[1].lower(),
    )


def monitored_metrics_autocompleter(livestatus_query: LivestatusQueryFunc) -> AutocompleterFunc:
    def autocompleter(config: Config, value: str, params: dict[str, object]) -> list[Choice]:
        return _metrics_autocompleter(
            value,
            params,
            registered_metrics(),
            registered_translations(),
            livestatus_query,
            lambda: list(enabled_sites(config.sites)),
            debug=config.debug,
        )

    return autocompleter
