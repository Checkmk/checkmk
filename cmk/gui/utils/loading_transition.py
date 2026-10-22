#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Generator
from contextlib import contextmanager

from cmk.gui.htmllib.generator import ClickAction, HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.utils.output_funnel import output_funnel
from cmk.shared_typing.loading_transition import LoadingTransition as LoadingTransition
from cmk.web.utils.html import HTML


@contextmanager
def loading_transition(
    template: LoadingTransition,
    delay_ms: int = 1000,
    title: str | None = None,
) -> Generator[None]:
    with output_funnel.plugged():
        yield
        html.span(
            HTML(output_funnel.drain(), False),
            **loading_transition_click_action(template, delay_ms, title).data_attributes(),
        )


def with_loading_transition(
    content: HTML,
    template: LoadingTransition | None,
    delay_ms: int = 1000,
    title: str | None = None,
) -> HTML:
    return HTMLWriter.render_span(
        content,
        **loading_transition_click_action(template, delay_ms, title).data_attributes(),
    )


def loading_transition_click_action(
    template: LoadingTransition | None,
    delay_ms: int = 1000,
    title: str | None = None,
) -> ClickAction:
    """Shows the loading transition while the clicked link inside the element is followed"""
    return ClickAction(
        action="loading_transition",
        arguments={
            "template": "" if template is None else template.value,
            "delay_ms": str(delay_ms),
            **({"title": title} if title else {}),
        },
    )


def loading_transition_onclick(
    template: LoadingTransition | None,
    delay_ms: int = 1000,
    title: str | None = None,
) -> str:
    template_value = "null" if template is None else f"'{template.value}'"
    title_value = json.dumps(title) if title else "undefined"
    return f"cmk.utils.makeLoadingTransition({template_value}, {delay_ms}, {title_value}, event);"
