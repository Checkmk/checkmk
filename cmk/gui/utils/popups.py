#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict, dataclass
from typing import Optional

from cmk.gui.type_defs import HTTPVariables
from cmk.gui.utils.url_encoder import URLEncoder


@dataclass
class PopupMethod:
    type: str

    def asdict(self):
        return asdict(self)


@dataclass(init=False)
class MethodAjax(PopupMethod):
    endpoint: Optional[str]
    url_vars: Optional[str]

    def __init__(self, endpoint: str, url_vars: Optional[HTTPVariables]):
        self.type = 'ajax'
        self.endpoint = endpoint if endpoint else None
        self.url_vars = URLEncoder().urlencode_vars(url_vars) if url_vars else None


@dataclass(init=False)
class MethodInline(PopupMethod):
    content: Optional[str]

    def __init__(self, content: str):
        self.type = 'inline'
        self.content = content if content else None


@dataclass(init=False)
class MethodColorpicker(PopupMethod):
    varprefix: Optional[str]
    value: Optional[str]

    def __init__(self, varprefix: str, value: str):
        self.type = 'colorpicker'
        self.varprefix = varprefix
        self.value = value
