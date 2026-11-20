#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.png_renderer import drawings_to_json, PngDrawing, pngs_from_json, RenderingFailure

from ._drawing import png_drawing
from ._input import PngGraph, PngTexts


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


def _drawing_or_failure(
    graph: PngGraph, texts: PngTexts, temperature_unit: TemperatureUnit
) -> PngDrawing | RenderingFailure:
    try:
        return png_drawing(graph, texts, temperature_unit)
    except Exception as exc:
        return RenderingFailure.from_exception(exc)


def _all_failed(drawings: Sequence[PngDrawing], message: str) -> Sequence[RenderingFailure]:
    return [RenderingFailure(message)] * len(drawings)


def _rendered(
    drawings: Sequence[PngDrawing], command: Sequence[str], timeout: _Timeout
) -> Sequence[bytes | RenderingFailure]:
    if not drawings:
        return []
    seconds = timeout.for_graphs(len(drawings))
    try:
        rendering = subprocess.run(
            [*command],
            input=drawings_to_json(drawings).encode(),
            capture_output=True,
            check=False,
            timeout=seconds,
        )
    except subprocess.TimeoutExpired:
        return _all_failed(
            drawings,
            f"{' '.join(command)} did not render {len(drawings)} graphs within {seconds} seconds",
        )
    results = [] if rendering.returncode else pngs_from_json(rendering.stdout.decode())
    if len(drawings) > 1:
        return [
            *results[: len(drawings)],
            *(_rendered([drawing], command, timeout)[0] for drawing in drawings[len(results) :]),
        ]
    missing = RenderingFailure(
        f"{' '.join(command)} failed: {rendering.stderr.decode(errors='replace')}"
        if rendering.returncode
        else f"{' '.join(command)} answered no image for this graph"
    )
    return results[:1] or [missing]


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
    drawings = [_drawing_or_failure(graph, texts, temperature_unit) for graph in graphs]
    rendered = iter(
        _rendered(
            [drawing for drawing in drawings if isinstance(drawing, PngDrawing)], command, timeout
        )
    )
    return [next(rendered) if isinstance(drawing, PngDrawing) else drawing for drawing in drawings]
