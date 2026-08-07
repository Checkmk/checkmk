#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable


class AiExplain:
    """Entry point for the cloud edition's "Explain with AI" feature.

    The service slide-in offers the explanation, but the feature itself ships in
    the cloud edition only. The cloud registration supplies the two callables
    below; every other edition keeps the no-op default and renders no button.
    """

    def __init__(self) -> None:
        self._is_enabled: Callable[[], bool] = lambda: False
        self._render_listener: Callable[[], None] = lambda: None

    def register(
        self,
        is_enabled: Callable[[], bool],
        render_listener: Callable[[], None],
    ) -> None:
        self._is_enabled = is_enabled
        self._render_listener = render_listener

    def is_enabled(self) -> bool:
        return self._is_enabled()

    def render_listener(self) -> None:
        if self._is_enabled():
            self._render_listener()


ai_explain = AiExplain()
