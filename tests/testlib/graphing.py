#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared support for the graphing (IGU) tests.

Skip reasons for the skeletons, and RRD injection for the tests that need a graph whose
values they chose rather than whatever a check happened to measure.

A skip reason names a skeleton's dependency, which also sets the enablement order (grep a
constant to find every skeleton blocked on the same dependency):

- ``SKIP_PENDING_GRAPH_BACKEND`` - integration tests needing the ``<cmk-graph>`` embedding;
  enablable first.
- ``SKIP_PENDING_GRAPH_ENGINE`` - GUI E2E tests pending the accessibility behaviour they assert.
- ``SKIP_PENDING_ENGINE_CUSTOM_GRAPH_DESIGNER`` - cases written against the former custom
  graph designer, blocked on the new designer growing the flows they drive.

`injected_ping_rrds` is the cheapest way to get one: a no-agent host has exactly one service
with an RRD (PING), and the core holds its RRDs open, so it takes every host it needs in one go
and pays the site stop/start once. It writes the CMC's ``cmc_single`` layout, so callers have to
skip the community edition, which stores per-metric files under pnp4nagios instead.

RRD files are written with the site's own ``rrdtool`` (as `tests.integration.core.test_rrd_files`
reads one), in the core's ``cmc_single`` layout: data sources numbered ``1``, ``2``, … plus a
``.info`` sidecar mapping those numbers to metric names. Pass the metric names the service
actually reports, in the order its existing ``.info`` lists them, and both files are rewritten
consistently.

Visibility caveat: the engine reads RRD via the livestatus ``rrddata:`` column, so only the
RRD of a *monitored* service surfaces - inject into the real path of an already-discovered
service (`service_rrd_path`).

The geometry is the core's own (`cmk.rrd.RRD_DEFAULT_CONFIG`): AVERAGE, MIN and MAX at
``pdp_per_row`` 1, 5, 30 and 360. At the default 60s step the ``pdp_per_row=1`` archive covers
48h, so a window older than that is served from a coarser archive and the three consolidation
functions diverge.
"""

import json
import logging
import math
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from cmk.graphing_engine import Graph
from cmk.gui.graphing._engine_codec import community_graph_codec, ensure_type
from cmk.rrd import RRD_DEFAULT_CONFIG, RRD_HEARTBEAT
from cmk.utils.misc import pnp_cleanup
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

SKIP_PENDING_GRAPH_BACKEND: Final = (
    "CMK-35973 skeleton: pending the graph backend (discovery/data REST + "
    "<cmk-graph> embedding); enable once the backend lands."
)
SKIP_PENDING_GRAPH_ENGINE: Final = (
    "CMK-35973 skeleton: the engine now renders on every surface, so these are pending the "
    "accessibility behaviour they assert rather than the engine itself."
)
SKIP_PENDING_ENGINE_CUSTOM_GRAPH_DESIGNER: Final = (
    "CMK-38108 skeleton: 'custom_graph.py' now serves the Vue designer, but these cases "
    "drive the former designer's form POST and legend DOM. Port them once the new designer "
    "covers the metric backend source flow they need."
)

# Default RRD geometry: one sample per minute over roughly a day.
_DEFAULT_STEP_SECONDS: Final = 60
_DEFAULT_SAMPLE_COUNT: Final = 1440

# The window the finest archive of `RRD_DEFAULT_CONFIG` covers at `_DEFAULT_STEP_SECONDS`
# (2880 rows x 60s). Query further back than this to be served a consolidated archive.
FINEST_ARCHIVE_SECONDS: Final = 2880 * _DEFAULT_STEP_SECONDS

# Europe/Berlin DST transition instants. Pass as inject_rrd(start=...) with the
# user timezone set to a DST zone; the test selects the historical window so the
# rendered axis crosses the transition.
#
# Fall-back is the relevant one for the "no duplicate X-axis labels" regression
# (Werk #14830): clocks go back, so local 02:00-02:59 occurs *twice* and a naive
# axis would emit the same label twice. Spring-forward merely *skips* the hour
# (no duplicate), so it does not exercise that regression.
DST_FALL_BACK_BERLIN_UTC: Final = 1729990800  # 2024-10-27 01:00 UTC; local 03:00->02:00
DST_SPRING_FORWARD_BERLIN_UTC: Final = 1711846800  # 2024-03-31 01:00 UTC; local 02:00->03:00

# One sample per rrdtool update argument, so a whole window would blow up a single command
# line - push them in bounded batches instead.
_UPDATE_BATCH: Final = 1000
# Each data source occupies its own band of values, so a series read back through a graph can
# be attributed to the metric it came from.
_BAND_WIDTH: Final = 100.0
_BAND_CENTRE: Final = 50.0
_BAND_AMPLITUDE: Final = 40.0
# Samples per oscillation for the 'oscillating' shape. Below the smallest consolidating
# archive's pdp_per_row (5 in the core's geometry), so every consolidated bucket spans a full
# period and its MIN/AVERAGE/MAX come out far apart.
_OSCILLATION_PERIOD: Final = 4


class GraphDataShape(StrEnum):
    VARYING = "varying"
    GAPS = "gaps"
    # Oscillates fast enough that MIN, AVERAGE and MAX of a consolidated window differ by
    # nearly the full amplitude, instead of the hair's breadth a slow curve yields.
    OSCILLATING = "oscillating"


def service_rrd_path(host_name: str, service_description: str) -> str:
    return f"var/check_mk/rrd/{pnp_cleanup(host_name)}/{pnp_cleanup(service_description)}.rrd"


def _info_rel_path(rrd_rel_path: str) -> str:
    return rrd_rel_path.removesuffix(".rrd") + ".info"


def read_rrd_metric_names(site: Site, host_name: str, service_description: str) -> Sequence[str]:
    info = site.read_file(_info_rel_path(service_rrd_path(host_name, service_description)))
    for line in info.splitlines():
        if line.startswith("METRICS "):
            return line.removeprefix("METRICS ").split(";")
    raise AssertionError(f"No METRICS line in the .info of {host_name}/{service_description}")


@dataclass(frozen=True)
class InjectedRrd:
    rel_path: str
    info_rel_path: str
    shape: GraphDataShape
    step: int
    start: int
    count: int
    metric_names: Sequence[str]

    def band_of(self, metric_name: str) -> tuple[float, float]:
        """The closed interval this file's samples of `metric_name` stay within."""
        offset = self.metric_names.index(metric_name) * _BAND_WIDTH
        return offset + _BAND_CENTRE - _BAND_AMPLITUDE, offset + _BAND_CENTRE + _BAND_AMPLITUDE


def _period(shape: GraphDataShape, count: int) -> int:
    return _OSCILLATION_PERIOD if shape is GraphDataShape.OSCILLATING else max(count, 1)


def _value(index: int, period: int, ds_index: int) -> float:
    return (
        ds_index * _BAND_WIDTH
        + _BAND_CENTRE
        + _BAND_AMPLITUDE * math.sin(2.0 * math.pi * index / period)
    )


def _is_gap(index: int, count: int, shape: GraphDataShape) -> bool:
    return shape is GraphDataShape.GAPS and count // 3 <= index < 2 * count // 3


def _samples(
    shape: GraphDataShape, *, step: int, start: int, count: int, data_sources: int
) -> Sequence[str]:
    period = _period(shape, count)
    return [
        f"{start + index * step}:"
        + ":".join(f"{_value(index, period, ds_index):f}" for ds_index in range(data_sources))
        for index in range(count)
        if not _is_gap(index, count, shape)
    ]


def inject_rrd(
    site: Site,
    shape: GraphDataShape,
    *,
    host_name: str,
    service_description: str,
    metric_names: Sequence[str],
    step: int = _DEFAULT_STEP_SECONDS,
    start: int | None = None,
    count: int = _DEFAULT_SAMPLE_COUNT,
) -> InjectedRrd:
    if start is None:
        start = int(time.time()) - count * step
    rel_path = service_rrd_path(host_name, service_description)
    logger.info("Injecting RRD '%s' with shape '%s'", rel_path, shape.value)
    rrd_path = site.path(rel_path).as_posix()
    site.makedirs(site.path(rel_path).parent)
    # Idempotent: re-seeding an existing service RRD is the documented workflow, so drop any
    # prior file rather than relying on rrdtool create's overwrite behaviour.
    site.delete_file(rel_path)
    data_sources = [str(number) for number in range(1, len(metric_names) + 1)]
    site.check_output(
        [
            "rrdtool",
            "create",
            rrd_path,
            "--start",
            str(start - step),
            "--step",
            str(step),
            *(f"DS:{name}:GAUGE:{RRD_HEARTBEAT}:U:U" for name in data_sources),
            *RRD_DEFAULT_CONFIG,
        ]
    )
    template = ":".join(data_sources)
    samples = _samples(shape, step=step, start=start, count=count, data_sources=len(data_sources))
    for offset in range(0, len(samples), _UPDATE_BATCH):
        site.check_output(
            ["rrdtool", "update", rrd_path, "-t", template]
            + list(samples[offset : offset + _UPDATE_BATCH])
        )
    # The core keeps the metric names out of the RRD (rrdtool limits DS names to 19
    # alphanumeric chars) and in this sidecar instead; without a matching one the engine
    # cannot map a DS back to its metric.
    site.write_file(
        _info_rel_path(rel_path),
        f"HOST {host_name}\nSERVICE {service_description}\nMETRICS {';'.join(metric_names)}\n",
    )
    return InjectedRrd(
        rel_path=rel_path,
        info_rel_path=_info_rel_path(rel_path),
        shape=shape,
        step=step,
        start=start,
        count=count,
        metric_names=tuple(metric_names),
    )


def discovered_graphs(discovered: Mapping[str, object]) -> Sequence[Graph]:
    graphs: list[Graph] = []
    for definition in ensure_type(discovered["graphs"], list):
        internal = ensure_type(ensure_type(definition, dict)["internal"], str)
        graphs.extend(community_graph_codec().deserialize_graphs(json.loads(internal)))
    return graphs


PING_SERVICE: Final = "PING"

_DAY: Final = 86400
# Inject a window that ends well before "now", so every query the tests make lands outside the
# finest RRD archive (48h at the core's geometry) and is served consolidated.
_WINDOW_START_DAYS_AGO: Final = 9
_WINDOW_DAYS: Final = 6


@dataclass(frozen=True, kw_only=True)
class InjectedPingRrd:
    host_name: str
    rrd: InjectedRrd

    @property
    def gap_start(self) -> int:
        return self.rrd.start + (self.rrd.count // 3) * self.rrd.step

    def window(self, *, offset_seconds: int, length_seconds: int) -> dict[str, int]:
        start = self.rrd.start + offset_seconds
        return {"start": start, "end": start + length_seconds, "step": 300}


@contextmanager
def injected_ping_rrds(
    site: Site, shapes: Mapping[str, GraphDataShape]
) -> Iterator[dict[str, InjectedPingRrd]]:
    host_names = list(shapes)
    try:
        for host_name in host_names:
            site.openapi.hosts.create(
                hostname=host_name,
                attributes={
                    "tag_address_family": "ip-v4-only",
                    "ipaddress": "127.0.0.1",
                    "tag_agent": "no-agent",
                },
            )
        site.activate_changes_and_wait_for_core_reload(allow_foreign_changes=True)
        for host_name in host_names:
            # The first check is what makes the core create the RRD and its .info sidecar, whose
            # data-source order the injected file has to keep.
            site.wait_until_service_has_been_checked(host_name, PING_SERVICE)

        metric_names = {
            host_name: read_rrd_metric_names(site, host_name, PING_SERVICE)
            for host_name in host_names
        }
        start = int(time.time()) - _WINDOW_START_DAYS_AGO * _DAY
        count = _WINDOW_DAYS * _DAY // _DEFAULT_STEP_SECONDS
        site.stop()
        try:
            injected = {
                host_name: InjectedPingRrd(
                    host_name=host_name,
                    rrd=inject_rrd(
                        site,
                        shape,
                        host_name=host_name,
                        service_description=PING_SERVICE,
                        metric_names=metric_names[host_name],
                        start=start,
                        count=count,
                    ),
                )
                for host_name, shape in shapes.items()
            }
        finally:
            site.start()
        yield injected
    finally:
        site.openapi.hosts.bulk_delete(host_names)
        site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)


def ping_graph_internal(site: Site, host_name: str) -> Mapping[str, object]:
    discovered = site.openapi.graph.discover_template_graphs(host_name, PING_SERVICE)
    assert discovered["graphs"], (
        f"No graph discovered for {host_name}/{PING_SERVICE}: {discovered['no_data_message']}"
    )
    internal: Mapping[str, object] = json.loads(discovered["graphs"][0]["internal"])
    return internal


def data_points_of_every_metric(response: Mapping[str, object]) -> Sequence[Sequence[float | None]]:
    metrics = response["metrics"]
    assert isinstance(metrics, list) and metrics, f"No series in the graph data: {response}"
    return [metric["data_points"] for metric in metrics]
