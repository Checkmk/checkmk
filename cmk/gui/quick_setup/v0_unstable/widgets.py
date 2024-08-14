#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass, field
from typing import Literal, NewType

FormSpecId = NewType("FormSpecId", str)


@dataclass
class Widget: ...


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
    id: FormSpecId
    form_spec: object
    widget_type: str = field(default="form_spec")
    rendering_option: str | None = None


@dataclass
class FormSpecDictWrapper(FormSpecWrapper):
    rendering_option: Literal["table"] | None = None


@dataclass
class FormSpecRecap(Widget):
    id: FormSpecId
    widget_type: str = field(default="form_spec_recap", init=False)
    form_spec: object


@dataclass
class Collapsible(Widget):
    widget_type: str = field(default="collapsible", init=False)
    title: str
    items: list[Widget] = field(default_factory=list)
