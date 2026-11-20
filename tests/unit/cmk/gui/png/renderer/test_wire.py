#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.gui.png.renderer import pngs_from_json, RenderingFailure
from cmk.gui.png.renderer._wire import pngs_to_json


def test_images_and_failures_survive_the_trip_back_from_the_rendering_process() -> None:
    results: Sequence[bytes | RenderingFailure] = [
        b"\x89PNG first",
        RenderingFailure("ValueError: boom"),
        b"\x89PNG second",
    ]

    assert pngs_from_json(pngs_to_json(results)) == results
