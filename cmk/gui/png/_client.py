#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from cmk.gui.png.renderer import RenderingFailure
from cmk.gui.utils.temperature_unit import TemperatureUnit

from ._wire import PngGraph, pngs_from_json, PngTexts, request_to_json


@dataclass(frozen=True)
class _Timeout:
    base_seconds: float
    per_graph_seconds: float

    def for_graphs(self, count: int) -> float:
        return self.base_seconds + self.per_graph_seconds * count


_COMMAND: Final = ("cmk-render-png-graphs",)
# The process spends a few seconds importing matplotlib and well under one per graph. The limits
# leave a loaded site ample room, but release the request or report job that waits for it when
# the renderer hangs.
_TIMEOUT: Final = _Timeout(base_seconds=60, per_graph_seconds=5)


def _all_failed(graphs: Sequence[PngGraph], message: str) -> Sequence[RenderingFailure]:
    return [RenderingFailure(message)] * len(graphs)


def render_pngs(
    graphs: Sequence[PngGraph],
    texts: PngTexts,
    temperature_unit: TemperatureUnit,
    *,
    command: Sequence[str] = _COMMAND,
    timeout: _Timeout = _TIMEOUT,
) -> Sequence[bytes | RenderingFailure]:
    """One result per graph, in the order of the graphs. A graph that fails to render yields a
    RenderingFailure, so that the other graphs still get their images."""
    if not graphs:
        return []
    seconds = timeout.for_graphs(len(graphs))
    try:
        rendering = subprocess.run(
            [*command],
            input=request_to_json(graphs, texts, temperature_unit).encode(),
            capture_output=True,
            check=False,
            timeout=seconds,
        )
    except subprocess.TimeoutExpired:
        return _all_failed(
            graphs,
            f"{' '.join(command)} did not render {len(graphs)} graphs within {seconds} seconds",
        )
    results = [] if rendering.returncode else pngs_from_json(rendering.stdout.decode())
    if len(graphs) > 1:
        return [
            *results[: len(graphs)],
            *(
                render_pngs([graph], texts, temperature_unit, command=command, timeout=timeout)[0]
                for graph in graphs[len(results) :]
            ),
        ]
    missing = RenderingFailure(
        f"{' '.join(command)} failed: {rendering.stderr.decode(errors='replace')}"
        if rendering.returncode
        else f"{' '.join(command)} answered no image for this graph"
    )
    return results[:1] or [missing]
