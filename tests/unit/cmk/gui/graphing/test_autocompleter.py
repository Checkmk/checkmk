#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import pytest

from cmk.ccc.site import SiteId
from cmk.graphing.v1 import metrics as metrics_v1
from cmk.graphing.v1 import Title
from cmk.gui.graphing._autocompleter import (
    _metric_choices,
    _metrics_autocompleter,
    metrics_of_query,
)
from cmk.gui.type_defs import VisualContext


@dataclass(frozen=True)
class _FakeLivestatusQuery:
    rows: Sequence[Mapping[str, object]]

    def __call__(
        self,
        table: Literal["host", "service"],  # noqa: ARG002
        context: VisualContext,  # noqa: ARG002
        columns: list[str],
    ) -> Sequence[Mapping[str, object]]:
        return [
            {"site": row["site"], **{column: row[column] for column in columns}}
            for row in self.rows
        ]


@dataclass(frozen=True)
class _FakeLivestatusQueryBare:
    rows_by_sites: Mapping[str, Sequence[Mapping[str, object]]]

    def __call__(
        self,
        table: Literal["host", "service"],  # noqa: ARG002
        context: VisualContext,
        columns: list[str],
    ) -> Sequence[Mapping[str, object]]:
        rows = self.rows_by_sites.get(context.get("sites", {}).get("sites", ""), [])
        return [
            {"site": row["site"], **{column: row[column] for column in columns}} for row in rows
        ]


def _service_row(
    *,
    site: str = "site1",
    host_name: str = "host1",
    service_perf_data: str = "",
    service_metrics: Sequence[str] = (),
    host_perf_data: str = "",
    host_metrics: Sequence[str] = (),
) -> Mapping[str, object]:
    return {
        "site": site,
        "host_name": host_name,
        "service_check_command": "check_mk-cpu",
        "service_perf_data": service_perf_data,
        "service_metrics": list(service_metrics),
        "host_check_command": "check-mk-ping",
        "host_perf_data": host_perf_data,
        "host_metrics": list(host_metrics),
    }


def _metric(name: str, title: Title) -> metrics_v1.Metric:
    return metrics_v1.Metric(
        name=name,
        title=title,
        unit=metrics_v1.Unit(metrics_v1.DecimalNotation("")),
        color=metrics_v1.Color.BLUE,
    )


_REGISTERED_METRICS = {"mem_used": _metric("mem_used", Title("Memory used"))}


def _metric_ids_of_query(rows: Sequence[Mapping[str, object]]) -> set[str | None]:
    return {
        metric_id
        for metric_id, _title in metrics_of_query(
            {}, {}, (), _FakeLivestatusQuery(rows), debug=False
        )
    }


def _metric_ids_of_choices(params: Mapping[str, object]) -> set[str | None]:
    return {
        metric_id
        for metric_id, _title in _metric_choices(
            params,
            _REGISTERED_METRICS,
            (),
            _FakeLivestatusQueryBare(
                {
                    "": [_service_row(service_perf_data="util=5;;;;")],
                    "site1|site2": [_service_row(service_perf_data="load1=1;;;;")],
                }
            ),
            lambda: [SiteId("site1"), SiteId("site2")],
            debug=False,
        )
    }


def test_metrics_of_query_offers_service_perf_data_metrics() -> None:
    assert _metric_ids_of_query(
        [
            _service_row(service_perf_data="util=5;;;; load1=1;;;;"),
            _service_row(service_perf_data="mem_used=3;;;;"),
        ]
    ) == {"util", "load1", "mem_used"}


def test_metrics_of_query_offers_rrd_only_metrics() -> None:
    assert _metric_ids_of_query([_service_row(service_metrics=["util"])]) == {"util"}


def test_metrics_of_query_offers_metrics_of_every_host_of_the_matched_services() -> None:
    assert _metric_ids_of_query(
        [
            _service_row(host_name="host1", host_perf_data="rta=0.1;;;; pl=0;;;;"),
            _service_row(host_name="host2", host_metrics=["response_time"]),
        ]
    ) == {"rta", "pl", "response_time"}


def test_metrics_of_query_offers_service_metrics_of_every_host() -> None:
    assert _metric_ids_of_query(
        [
            _service_row(host_name="host1", service_perf_data="util=5;;;;"),
            _service_row(host_name="host2", service_metrics=["mem_used"]),
            _service_row(host_name="host3", service_perf_data="load1=1;;;;"),
        ]
    ) == {"util", "mem_used", "load1"}


def test_metrics_of_query_offers_the_host_metrics_once_per_host() -> None:
    assert [
        metric_id
        for metric_id, _title in metrics_of_query(
            {},
            {},
            (),
            _FakeLivestatusQuery(
                [
                    _service_row(host_name="host1", host_perf_data="rta=0.1;;;;"),
                    _service_row(host_name="host1", host_perf_data="rta=0.1;;;;"),
                ]
            ),
            debug=False,
        )
    ] == ["rta"]


def test_metrics_of_query_tells_equally_named_hosts_of_different_sites_apart() -> None:
    assert _metric_ids_of_query(
        [
            _service_row(site="site1", host_name="host1", host_perf_data="rta=0.1;;;;"),
            _service_row(site="site2", host_name="host1", host_metrics=["response_time"]),
        ]
    ) == {"rta", "response_time"}


def test_metric_choices_without_context_offers_registered_metrics() -> None:
    assert _metric_ids_of_choices({"show_independent_of_context": True}) == {"mem_used"}


def test_metric_choices_with_filters_queries_the_matching_objects() -> None:
    assert _metric_ids_of_choices(
        {"show_independent_of_context": True, "context": {"host": {"host": "host1"}}}
    ) == {"util"}


def test_metric_choices_without_context_offers_registered_metrics_on_request() -> None:
    assert _metric_ids_of_choices(
        {"show_independent_of_context": True, "metrics_without_context": "registered"}
    ) == {"mem_used"}


def test_metric_choices_rejects_unknown_metrics_without_context() -> None:
    with pytest.raises(ValueError):
        _metric_ids_of_choices(
            {"show_independent_of_context": True, "metrics_without_context": "all"}
        )


def test_metric_choices_without_context_offers_monitored_metrics_of_all_sites() -> None:
    assert _metric_ids_of_choices(
        {"show_independent_of_context": True, "metrics_without_context": "monitored"}
    ) == {"load1"}


def test_metric_choices_with_filters_ignores_the_metrics_without_context() -> None:
    assert _metric_ids_of_choices(
        {
            "show_independent_of_context": True,
            "metrics_without_context": "monitored",
            "context": {"host": {"host": "host1"}},
        }
    ) == {"util"}


def _autocompleted_metric_ids(
    value: str, registered_metrics: Mapping[str, metrics_v1.Metric]
) -> list[str | None]:
    return [
        metric_id
        for metric_id, _title in _metrics_autocompleter(
            value,
            {"show_independent_of_context": True},
            registered_metrics,
            (),
            _FakeLivestatusQueryBare({}),
            list,
            debug=False,
        )
    ]


def test_metrics_autocompleter_offers_the_metrics_matching_the_typed_text() -> None:
    assert _autocompleted_metric_ids(
        "memory",
        {
            "mem_used": _metric("mem_used", Title("Memory used")),
            "util": _metric("util", Title("CPU load")),
        },
    ) == ["mem_used"]


def test_metrics_autocompleter_sorts_the_metrics_by_title() -> None:
    assert _autocompleted_metric_ids(
        "",
        {
            "mem_used": _metric("mem_used", Title("Memory used")),
            "util": _metric("util", Title("CPU load")),
        },
    ) == ["util", "mem_used"]
