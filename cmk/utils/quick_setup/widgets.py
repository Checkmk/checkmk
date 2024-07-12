#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Widget:
    widget_type: str


@dataclass
class Text(Widget):
    widget_type: str = "text"
    text: str = ""
    tooltip: str | None = None


@dataclass
class NoteText(Widget):
    widget_type: str = field(default="note_text", init=False)
    text: str = ""


@dataclass
class ListOfWidgets(Widget):
    widget_type: str = field(default="list_of_widgets", init=False)
    items: list[Widget] = field(default_factory=list)
    list_type: None | Literal["bullet", "ordered", "check"] = None


@dataclass
class FormSpecWrapper(Widget):
    id: str
    widget_type: str = field(default="form_spec", init=False)
    form_spec: object | None = None


@dataclass
class Collapsible(Widget):
    widget_type: str = field(default="collapsible", init=False)
    title: str
    items: list[Widget] = field(default_factory=list)
