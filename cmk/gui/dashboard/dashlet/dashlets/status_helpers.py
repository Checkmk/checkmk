#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping
from typing import assert_never

from livestatus import LivestatusResponse

from cmk.ccc.exceptions import MKGeneralException, MKTimeout
from cmk.gui import sites, visuals
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKMissingDataError
from cmk.gui.graphing import (
    ConvertibleUnitSpecification,
    get_temperature_unit,
    MetricSpec,
    TranslatedMetric,
    user_specific_unit,
    UserSpecificUnit,
)
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import ColumnName, VisualContext
from cmk.gui.unit_formatter import AutoPrecision, IECFormatter, StrictPrecision
from cmk.gui.utils.temperate_unit import TemperatureUnit
from cmk.gui.utils.urls import makeuri_contextless


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


def purge_metric_spec_for_js(metric_spec: MetricSpec) -> dict[str, object]:
    return {"bounds": {}} | _purge_unit_spec_for_js(
        metric_spec.unit_spec,
        temperature_unit=get_temperature_unit(user, active_config.default_temperature_unit),
    )


def purge_translated_metric_for_js(translated_metric: TranslatedMetric) -> dict[str, object]:
    return {"bounds": translated_metric.scalar} | _purge_unit_spec_for_js(
        translated_metric.unit_spec,
        temperature_unit=get_temperature_unit(user, active_config.default_temperature_unit),
    )


def _purge_unit_spec_for_js(
    unit_spec: ConvertibleUnitSpecification,
    temperature_unit: TemperatureUnit,
) -> dict[str, object]:
    return {
        "unit": _transform_user_specific_unit_for_js(
            user_specific_unit(unit_spec, temperature_unit)
        )
    }


def _transform_user_specific_unit_for_js(
    unit_for_current_user: UserSpecificUnit,
) -> dict[str, object]:
    match unit_for_current_user.formatter.precision:
        case AutoPrecision():
            js_precision = "AutoPrecision"
        case StrictPrecision():
            js_precision = "StrictPrecision"
        case _:
            assert_never(unit_for_current_user.formatter)
    return {
        "js_render": f"""v => new cmk.number_format.{unit_for_current_user.formatter.js_formatter_name}(
    "{unit_for_current_user.formatter.symbol}",
    new cmk.number_format.{js_precision}({unit_for_current_user.formatter.precision.digits}),
).render(v)""",
        "stepping": "binary" if isinstance(unit_for_current_user.formatter, IECFormatter) else None,
    }


def make_mk_missing_data_error(reason: str | None = None) -> MKMissingDataError:
    """Standardized missing data error for the dashboard."""
    message = _("No data was found with the current parameters of this widget.")
    return MKMissingDataError(f"{reason}" if reason else message)
