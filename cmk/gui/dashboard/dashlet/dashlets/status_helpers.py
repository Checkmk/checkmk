#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from livestatus import LivestatusResponse

from cmk.gui import sites, visuals
from cmk.gui.exceptions import MKMissingDataError
from cmk.gui.graphing._legacy import UnitInfo
from cmk.gui.graphing._metrics import MetricSpec
from cmk.gui.graphing._translated_metrics import TranslatedMetric
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.type_defs import ColumnName, VisualContext
from cmk.gui.utils.urls import makeuri_contextless

from cmk.ccc.exceptions import MKGeneralException, MKTimeout


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

    query = (
        f"GET {table}\n"
        "Columns: %(cols)s\n"
        "%(filter)s"
        % {
            "cols": " ".join(columns),
            "filter": filter_headers,
        }
    )

    with sites.only_sites(only_sites), sites.prepend_site():
        try:
            rows = sites.live().query(query)
        except MKTimeout:
            raise
        except Exception:
            raise MKGeneralException(_("The query returned no data."))

    return ["site"] + list(columns), rows


def create_host_view_url(context):
    return makeuri_contextless(
        request,
        [
            ("view_name", "host"),
            ("site", context["site"]),
            ("host", context["host_name"]),
        ],
        filename="view.py",
    )


def create_service_view_url(context):
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
    return {"bounds": {}} | _purge_unit_info_for_js(metric_spec.unit_info)


def purge_translated_metric_for_js(translated_metric: TranslatedMetric) -> dict[str, object]:
    return {"bounds": translated_metric.scalar} | _purge_unit_info_for_js(
        translated_metric.unit_info
    )


def _purge_unit_info_for_js(unit_info: UnitInfo) -> dict[str, object]:
    return {
        "unit": {
            "js_render": unit_info.js_render,
            "stepping": unit_info.stepping,
        }
    }


def make_mk_missing_data_error() -> MKMissingDataError:
    return MKMissingDataError(_("No data was found with the current parameters of this dashlet."))
