#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import traceback

from cmk.gui.png._drawing import png_drawing
from cmk.gui.png._wire import PngGraph, PngTexts, request_from_json
from cmk.gui.utils.temperature_unit import TemperatureUnit

from ._image import render_pngs
from ._model import PngDrawing, RenderingFailure
from ._wire import pngs_to_json


def _drawing_or_failure(
    graph: PngGraph, texts: PngTexts, temperature_unit: TemperatureUnit
) -> PngDrawing | RenderingFailure:
    try:
        return png_drawing(graph, texts, temperature_unit)
    except Exception as exc:
        return RenderingFailure("".join(traceback.format_exception_only(exc)).strip())


def main() -> None:
    graphs, texts, temperature_unit = request_from_json(sys.stdin.read())
    drawings = [_drawing_or_failure(graph, texts, temperature_unit) for graph in graphs]
    rendered = iter(
        render_pngs([drawing for drawing in drawings if isinstance(drawing, PngDrawing)])
    )
    sys.stdout.write(
        pngs_to_json(
            [next(rendered) if isinstance(drawing, PngDrawing) else drawing for drawing in drawings]
        )
    )


if __name__ == "__main__":
    main()
