#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from cmk.gui.graphing._autocompleter import metrics_of_query
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


def _metric_ids_of_query(rows: Sequence[Mapping[str, object]]) -> set[str | None]:
    return {
        metric_id
        for metric_id, _title in metrics_of_query(
            {}, {}, (), _FakeLivestatusQuery(rows), debug=False
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
