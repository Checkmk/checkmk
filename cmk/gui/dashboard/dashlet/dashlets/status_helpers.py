#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from livestatus import LivestatusResponse

from cmk.utils.exceptions import MKGeneralException, MKTimeout

from cmk.gui import sites, visuals
from cmk.gui.exceptions import MKMissingDataError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.type_defs import ColumnName, VisualContext
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
    filter_headers, only_sites = visuals.get_filter_headers(table, infos, context)

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


def purge_metric_for_js(metric):
    return {
        "bounds": metric.get("scalar", {}),
        "unit": {k: v for k, v in metric["unit"].items() if k in ["js_render", "stepping"]},
    }


def make_mk_missing_data_error() -> MKMissingDataError:
    return MKMissingDataError(_("No data was found with the current parameters of this dashlet."))
