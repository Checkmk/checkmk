#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict, dataclass
from typing import Dict, Optional, Union

from cmk.gui.type_defs import HTTPVariables
from cmk.gui.utils.urls import urlencode_vars


@dataclass
class PopupMethod:
    """Base class for the different methods to open popups in Checkmk."""

    type: str

    def asdict(self) -> Dict[str, Union[str, Optional[str]]]:
        """Dictionary representation used to pass information to JS code."""
        return {k: v for k, v in asdict(self).items() if not k.startswith("_")}

    @property
    def content(self) -> str:
        """String representation of the HTML content of the popup."""
        return ""


@dataclass(init=False)
class MethodAjax(PopupMethod):
    endpoint: Optional[str]
    url_vars: Optional[str]

    def __init__(self, endpoint: str, url_vars: Optional[HTTPVariables]) -> None:
        super().__init__(type="ajax")
        self.endpoint = endpoint if endpoint else None
        self.url_vars = urlencode_vars(url_vars) if url_vars else None


@dataclass(init=False)
class MethodInline(PopupMethod):
    _content: str  # used only for server side rendering

    def __init__(self, content: str) -> None:
        super().__init__(type="inline")
        self._content: str = content

    @property
    def content(self) -> str:
        return self._content


@dataclass(init=False)
class MethodColorpicker(PopupMethod):
    varprefix: Optional[str]
    value: Optional[str]

    def __init__(self, varprefix: str, value: str) -> None:
        super().__init__(type="colorpicker")
        self.varprefix = varprefix
        self.value = value
