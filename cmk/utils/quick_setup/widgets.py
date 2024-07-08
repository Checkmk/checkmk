#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass, field


@dataclass
class Widget:
    widget_type: str


@dataclass
class Text(Widget):
    widget_type: str = "text"
    text: str = field(default="text", init=False)


@dataclass
class NoteText(Widget):
    widget_type: str = field(default="note_text", init=False)
    text: str = ""


@dataclass
class List(Widget):
    widget_type: str = field(default="list", init=False)
    items: list[str] = field(default_factory=list)
    ordered: bool = False


@dataclass
class FormSpecWrapper(Widget):
    id: str
    widget_type: str = field(default="form_spec", init=False)
    form_spec: object | None = None
