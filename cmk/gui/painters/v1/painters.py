# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Callable, Sequence

from cmk.gui.i18n import _l
from cmk.gui.painters.v1.helpers import (
    get_perfdata_nth_value,
    get_single_int_column,
    get_single_str_column,
    is_stale,
    render_str_with_staleness,
    StrWithStaleness,
)
from cmk.gui.painters.v1.painter_lib import (
    experimental_painter_registry,
    Formatters,
    Painter,
    PainterConfiguration,
)
from cmk.gui.type_defs import Rows
from cmk.gui.view_utils import CellSpec

experimental_painter_registry.register(
    Painter[str](
        "alias",
        get_single_str_column,
        Formatters[str](html=lambda painter_data, painter_configuration: ("", painter_data)),
        _l("Host alias"),
        _l("Alias"),
        columns=["host_alias"],
    )
)


def _get_number_of_services_formatter(
    css_id: str,
) -> Callable[[int, PainterConfiguration], CellSpec]:
    def number_of_services(painter_data: int, config: PainterConfiguration) -> CellSpec:
        if painter_data > 0:
            return f"count svcstate state{css_id}", str(painter_data)
        return "count svcstate", "0"

    return number_of_services


for state, state_type, short_title, title in [
    ("0", "ok", _l("Ok"), _l("Number of service in state OK")),
    ("1", "warn", _l("Warn"), _l("Number of service in state WARN")),
    ("2", "crit", _l("Crit"), _l("Number of service in state CRIT")),
    ("3", "unknown", _l("Un"), _l("Number of service in state UNKNOWN")),
    ("p", "pending", _l("Pe"), _l("Number of service in state Pending")),
]:
    experimental_painter_registry.register(
        Painter[int](
            f"num_services_{state_type}",
            get_single_int_column,
            Formatters[int](html=_get_number_of_services_formatter(state)),
            title,
            short_title,
            title_classes=["right"],
            columns=[f"host_num_services_{state_type}"],
        )
    )


def _get_perfdata_with_staleness_callable(
    value_number: int,
) -> Callable[[Rows, PainterConfiguration], Sequence[StrWithStaleness]]:
    def str_with_staleness(rows: Rows, config: PainterConfiguration) -> Sequence[StrWithStaleness]:
        return [
            StrWithStaleness(
                get_perfdata_nth_value(row, value_number),
                is_stale(row),
            )
            for row in rows
        ]

    return str_with_staleness


for i in range(1, 11):
    experimental_painter_registry.register(
        Painter[StrWithStaleness](
            f"svc_perf_val{i:02}",
            _get_perfdata_with_staleness_callable(i - 1),
            Formatters[StrWithStaleness](html=render_str_with_staleness),
            _l("Service performance data - value number %2d") % i,
            _l("Val. %d") % i,
            columns=["service_perf_data", "service_staleness", "host_staleness"],
        )
    )
