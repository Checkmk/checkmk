#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping

from cmk.ccc.exceptions import MKGeneralException, MKTimeout
from cmk.graphing_engine import PerformanceData, Unit
from cmk.gui import sites, visuals
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKMissingDataError
from cmk.gui.graphing import (
    ConvertibleUnitSpecification,
    EvaluatedMetric,
    get_temperature_unit,
    user_specific_unit,
)
from cmk.gui.graphing._unit import user_specific_unit_from_unit_format
from cmk.gui.graphing._unit_format import unit_to_unit_format
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import ColumnName, VisualContext
from cmk.gui.unit_formatter import IECFormatter, NotationFormatter
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.livestatus_client import LivestatusResponse
from cmk.web.utils.urls import makeuri_contextless


def host_table_query(
    context: VisualContext, columns: Iterable[ColumnName]
) -> tuple[list[ColumnName], LivestatusResponse]:
    return _table_query(context, "hosts", columns, ["host"])


def service_table_query(
    context: VisualContext, columns: Iterable[ColumnName]
) -> tuple[list[ColumnName], LivestatusResponse]:
    return _table_query(context, "services", columns, ["host", "service"])


def _table_query(
    context: VisualContext, table: str, columns: Iterable[ColumnName], infos: list[str]
) -> tuple[list[ColumnName], LivestatusResponse]:
    filter_headers, only_sites = visuals.get_filter_headers(infos, context)

    query = f"GET {table}\nColumns: %(cols)s\n%(filter)s" % {
        "cols": " ".join(columns),
        "filter": filter_headers,
    }

    with sites.only_sites(only_sites), sites.prepend_site():
        try:
            rows = sites.live().query(query)
        except MKTimeout:
            raise
        except Exception:
            raise MKGeneralException(_("The query returned no data."))

    return ["site"] + list(columns), rows


def create_host_view_url(context: Mapping[str, str]) -> str:
    return makeuri_contextless(
        request,
        [
            ("view_name", "host"),
            ("site", context["site"]),
            ("host", context["host_name"]),
        ],
        filename="view.py",
    )


def create_service_view_url(context: Mapping[str, str]) -> str:
    return makeuri_contextless(
        request,
        [
            ("view_name", "service"),
            ("site", context["site"]),
            ("host", context["host_name"]),
            ("service", context["service_description"]),
        ],
        filename="view.py",
    )


def purge_metric_unit_for_js(unit: Unit) -> dict[str, object]:
    return {
        "bounds": {},
        "unit": _formatter_for_js(
            user_specific_unit_from_unit_format(
                unit_to_unit_format(unit),
                get_temperature_unit(user, active_config.default_temperature_unit),
            ).formatter
        ),
    }


def _scalar_bounds_for_js(performance_data: PerformanceData) -> Mapping[str, float]:
    bounds: dict[str, float] = {}
    if performance_data.warning is not None:
        bounds["warn"] = performance_data.warning
    if performance_data.critical is not None:
        bounds["crit"] = performance_data.critical
    if performance_data.minimum is not None:
        bounds["min"] = performance_data.minimum
    if performance_data.maximum is not None:
        bounds["max"] = performance_data.maximum
    return bounds


def purge_evaluated_metric_for_js(metric: EvaluatedMetric) -> dict[str, object]:
    return {
        "bounds": _scalar_bounds_for_js(metric.performance_data),
        "unit": _formatter_for_js(metric.formatter),
    }


def _purge_unit_spec_for_js(
    unit_spec: ConvertibleUnitSpecification,
    temperature_unit: TemperatureUnit,
) -> dict[str, object]:
    return {"unit": _formatter_for_js(user_specific_unit(unit_spec, temperature_unit).formatter)}


def _formatter_for_js(formatter: NotationFormatter) -> dict[str, object]:
    return {
        "formatter_type": formatter.js_formatter_name,
        "symbol": formatter.symbol,
        "precision_type": formatter.precision.type,
        "precision_digits": formatter.precision.digits,
        "stepping": "binary" if isinstance(formatter, IECFormatter) else None,
    }


def make_mk_missing_data_error(reason: str | None = None) -> MKMissingDataError:
    """Standardized missing data error for the dashboard."""
    message = _("No data was found with the current parameters of this widget.")
    return MKMissingDataError(f"{reason}" if reason else message)
