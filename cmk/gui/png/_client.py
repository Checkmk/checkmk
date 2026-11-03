#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from collections.abc import Sequence
from typing import Final

from cmk.gui.utils.temperature_unit import TemperatureUnit

from ._wire import PngGraph, pngs_from_json, PngTexts, RenderingFailure, request_to_json

_COMMAND: Final = ("cmk-render-png-graphs",)
# The process spends a few seconds importing matplotlib and well under one per graph. The limits
# leave a loaded site ample room, but release the request or report job that waits for it when
# the renderer hangs.
_TIMEOUT_BASE_SECONDS: Final = 60
_TIMEOUT_PER_GRAPH_SECONDS: Final = 5


def render_pngs(
    graphs: Sequence[PngGraph],
    texts: PngTexts,
    temperature_unit: TemperatureUnit,
    *,
    command: Sequence[str] = _COMMAND,
) -> Sequence[bytes | RenderingFailure]:
    """One result per graph, in the order of the graphs. A graph that fails to render yields a
    RenderingFailure, so that the other graphs still get their images."""
    timeout = _TIMEOUT_BASE_SECONDS + _TIMEOUT_PER_GRAPH_SECONDS * len(graphs)
    try:
        rendering = subprocess.run(
            [*command],
            input=request_to_json(graphs, texts, temperature_unit).encode(),
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(
            f"{' '.join(command)} did not render {len(graphs)} graphs within {timeout} seconds"
        ) from e
    if rendering.returncode:
        raise RuntimeError(
            f"{' '.join(command)} failed: {rendering.stderr.decode(errors='replace')}"
        )
    return pngs_from_json(rendering.stdout.decode())
