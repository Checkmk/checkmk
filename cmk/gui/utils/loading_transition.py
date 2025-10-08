#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Generator
from contextlib import contextmanager

from cmk.gui.htmllib.html import html
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel


@contextmanager
def loading_transition(template: str = "default", delay_ms: int = 0) -> Generator[None]:
    with output_funnel.plugged():
        yield
        html.span(
            HTML(output_funnel.drain(), False),
            onclick=f"cmk.utils.createSkeleton('{template}', {delay_ms});",
        )
