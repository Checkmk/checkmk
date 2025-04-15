#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass, field
from typing import Literal, NewType

FormSpecId = NewType("FormSpecId", str)


@dataclass(frozen=True, kw_only=True)
class Widget: ...


@dataclass(frozen=True, kw_only=True)
class Text(Widget):
    widget_type: str = field(default="text", init=False)
    text: str = ""
    tooltip: str | None = None


@dataclass(frozen=True, kw_only=True)
class NoteText(Widget):
    widget_type: str = field(default="note_text", init=False)
    text: str = ""


@dataclass(frozen=True, kw_only=True)
class Dialog(Widget):
    widget_type: str = field(default="dialog", init=False)
    text: str = ""


@dataclass(frozen=True, kw_only=True)
class ListOfWidgets(Widget):
    widget_type: str = field(default="list_of_widgets", init=False)
    items: list[Widget] = field(default_factory=list)
    list_type: None | Literal["bullet", "ordered", "check"] = None


@dataclass(frozen=True, kw_only=True)
class FormSpecWrapper(Widget):
    id: FormSpecId
    form_spec: object
    widget_type: str = field(default="form_spec", init=False)


@dataclass(frozen=True, kw_only=True)
class FormSpecRecap(Widget):
    id: FormSpecId
    widget_type: str = field(default="form_spec_recap", init=False)
    form_spec: object


@dataclass(frozen=True, kw_only=True)
class Collapsible(Widget):
    widget_type: str = field(default="collapsible", init=False)
    title: str
    items: list[Widget] = field(default_factory=list)
    help_text: str | None = None
