#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Generator
from contextlib import contextmanager

from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.shared_typing.loading_transition import LoadingTransition as LoadingTransition


@contextmanager
def loading_transition(template: LoadingTransition, delay_ms: int = 1000) -> Generator[None]:
    with output_funnel.plugged():
        yield
        html.span(
            HTML(output_funnel.drain(), False),
            onclick=f"cmk.utils.makeLoadingTransition('{template.value}', {delay_ms});",
        )


def with_loading_transition(
    content: HTML,
    template: LoadingTransition | None,
    delay_ms: int = 1000,
) -> HTML:
    template_value = "null" if template is None else f"'{template.value}'"
    return HTMLWriter.render_span(
        content,
        onclick=f"cmk.utils.makeLoadingTransition({template_value}, {delay_ms});",
    )
