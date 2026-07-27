#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared support for the graphing (IGU) tests (CMK-35973).

Skip reasons for the skeletons, and RRD injection for the tests that need a graph whose
values they chose rather than whatever a check happened to measure.

A skip reason names a skeleton's dependency, which also sets the enablement order (grep a
constant to find every skeleton blocked on the same dependency):

- ``SKIP_PENDING_GRAPH_BACKEND`` - integration/composition tests needing only the backend
  (discovery/data REST + ``<cmk-graph>`` embedding); enablable first.
- ``SKIP_PENDING_GRAPH_ENGINE`` - GUI E2E tests needing the engine to render on a surface.

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
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from cmk.graphing_engine import Graph
from cmk.gui.graphing._engine_serialization import ensure_type, graph_codec
from cmk.rrd import RRD_DEFAULT_CONFIG, RRD_HEARTBEAT
from cmk.utils.misc import pnp_cleanup
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

SKIP_PENDING_GRAPH_BACKEND: Final = (
    "CMK-35973 skeleton: pending the graph backend (discovery/data REST + "
    "<cmk-graph> embedding); enable once the backend lands."
)
SKIP_PENDING_GRAPH_ENGINE: Final = (
    "CMK-35973 skeleton: pending the new graph engine rendering on this surface."
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
# Samples per oscillation for the 'oscillating' shape. Below the smallest consolidating
# archive's pdp_per_row (5 in the core's geometry), so every consolidated bucket spans a full
# period and its MIN/AVERAGE/MAX come out far apart.
_OSCILLATION_PERIOD: Final = 4


class GraphDataShape(StrEnum):
    """The controlled data shapes a graph test fixture can request."""

    VARYING = "varying"
    GAPS = "gaps"
    # Oscillates fast enough that MIN, AVERAGE and MAX of a consolidated window differ by
    # nearly the full amplitude, instead of the hair's breadth a slow curve yields.
    OSCILLATING = "oscillating"


def service_rrd_path(host_name: str, service_description: str) -> str:
    """RRD path relative to ``OMD_ROOT`` the core reads for a service's metrics.

    Applies the core's `pnp_cleanup` quoting to both path elements
    (e.g. "CPU load" -> "CPU_load.rrd").
    """
    return f"var/check_mk/rrd/{pnp_cleanup(host_name)}/{pnp_cleanup(service_description)}.rrd"


def _info_rel_path(rrd_rel_path: str) -> str:
    return rrd_rel_path.removesuffix(".rrd") + ".info"


def read_rrd_metric_names(site: Site, host_name: str, service_description: str) -> Sequence[str]:
    """The metric names the core recorded for a service, in data-source order.

    Read them off the existing ``.info`` sidecar and hand them back to `inject_rrd`, so an
    injected RRD keeps the data-source order the core assigned.
    """
    info = site.read_file(_info_rel_path(service_rrd_path(host_name, service_description)))
    for line in info.splitlines():
        if line.startswith("METRICS "):
            return line.removeprefix("METRICS ").split(";")
    raise AssertionError(f"No METRICS line in the .info of {host_name}/{service_description}")


@dataclass(frozen=True)
class InjectedRrd:
    """An RRD file created on the site for a graph test."""

    rel_path: str
    info_rel_path: str
    shape: GraphDataShape
    step: int
    start: int
    count: int
    metric_names: Sequence[str]


def _period(shape: GraphDataShape, count: int) -> int:
    """Samples per oscillation: one slow curve over the whole window, or a fast one."""
    return _OSCILLATION_PERIOD if shape is GraphDataShape.OSCILLATING else max(count, 1)


def _value(index: int, period: int, ds_index: int) -> float:
    """A smoothly varying, always-positive sample value in this data source's band."""
    return ds_index * _BAND_WIDTH + 50.0 + 40.0 * math.sin(2.0 * math.pi * index / period)


def _is_gap(index: int, count: int, shape: GraphDataShape) -> bool:
    """For the 'gaps' shape, drop a contiguous block in the middle third."""
    return shape is GraphDataShape.GAPS and count // 3 <= index < 2 * count // 3


def _samples(
    shape: GraphDataShape, *, step: int, start: int, count: int, data_sources: int
) -> Sequence[str]:
    """The ``<timestamp>:<value>:...`` arguments of an rrdtool update, gaps left out."""
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
    """Write the data shape to a service's RRD at the path the core reads.

    Writes `service_rrd_path` and its ``.info`` sidecar; the service must be monitored (see
    the module docstring). ``metric_names`` becomes the sidecar's ``METRICS`` line and fixes
    the data-source order, so it has to list what the service reports. ``start`` defaults to
    now (the test host's clock) minus the window length so data lands in default relative
    views; pass an explicit ``start`` (e.g. `DST_FALL_BACK_BERLIN_UTC`, or a few days back to
    reach a consolidated archive) for a historical window.
    """
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
        graphs.extend(graph_codec().deserialize_graphs(json.loads(internal)))
    return graphs
