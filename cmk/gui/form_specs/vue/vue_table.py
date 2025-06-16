#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import traceback
import uuid
from dataclasses import dataclass
from typing import Any, TypedDict

from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.theme.current_theme import theme
from cmk.gui.utils.html import HTML


class VueCell(TypedDict):
    content: str
    html_content: str
    attributes: dict[str, Any]
    css: list[str]


def create_vue_cell(content=None, html_content=None):
    return VueCell(content=content, html_content=html_content, attributes={}, css=[])


class VueRow(TypedDict):
    columns: list[str]
    attributes: dict[str, Any]
    css: list[str]


def create_vue_row() -> VueRow:
    return VueRow(columns=[], attributes={}, css=[])


class VueTable(TypedDict):
    rows: list[VueRow]


def create_vue_table(rows: list[VueRow]) -> VueTable:
    return VueTable(rows=rows)


def create_vue_table_config(table: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "some_table",
        "component": table,
    }


class VueIconButton(TypedDict):
    type: str
    url: str
    title: str
    icon: str


def create_icon_button(url, title, icon):
    return VueIconButton(type="icon", url=url, title=title, icon=icon)


class VueButtons(TypedDict):
    entries: list[VueRow]
    type: str


def create_buttons(entries):
    return VueButtons(entries=entries, type="buttons")


class VueCheckbox(TypedDict):
    type: str


def create_checkbox():
    return VueCheckbox(type="checkbox")


class VueHref(TypedDict):
    type: str
    link: str
    alias: str


def create_href(link, alias):
    return VueHref(type="href", link=link, alias=alias)


class VueList(TypedDict):
    type: str
    elements: list[str]


def create_list(elements):
    return VueList(type="list", elements=elements)


def build_text(content: str | HTML) -> dict[str, Any]:
    return {
        "type": "text",
        "content": str(content),
    }


def build_html(content: str | HTML) -> dict[str, Any]:
    return {
        "type": "html_",
        "html_content": str(content),
    }


def build_table_cell(
    content: list[dict[str, Any]] | None = None,
    attributes: dict[str, Any] | None = None,
    classes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "cell",
        "content": content or [],
        "attributes": attributes or {},
        "classes": classes or [],
    }


def build_row(
    key: str | None = None,
    columns: list[dict[str, Any]] | None = None,
    attributes: dict[str, Any] | None = None,
    classes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "key": key or uuid.uuid4(),
        "type": "row",
        "columns": columns or [],
        "attributes": attributes or {},
        "classes": classes or [],
    }


def build_header_field(field_id: str, name: str, sortable: bool) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "name": name,
        "sortable": sortable,
    }


def build_table(
    rows: list[dict[str, Any]],
    headers: list[str],
    attributes: dict[str, Any] | None = None,
    classes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "table",
        "rows": rows,
        "headers": headers,
        "attributes": attributes or {},
        "classes": classes or [],
    }


def build_checkbox() -> dict[str, Any]:
    return {
        "type": "checkbox",
    }


def build_icon_button(url: str, title: str, icon: str) -> dict[str, Any]:
    icon_settings = detect_icon_settings(icon, title)
    return {
        "type": "button",
        "url": url,
        "title": icon_settings.title,
        "icon": icon_settings.src,
    }


def build_href(url: str, alias: str) -> dict[str, Any]:
    return {
        "type": "href",
        "url": url,
        "alias": alias,
    }


@dataclass(kw_only=True)
class IconSettings:
    src: str
    title: str
    classes: list[str]


def detect_icon_settings(icon: str | dict[str, str], title: str = "") -> IconSettings:
    classes = []
    icon_name = icon["icon"] if isinstance(icon, dict) else icon
    if icon_name is None:
        icon_name = "empty"
    src = icon_name if "/" in icon_name else theme.detect_icon_path(icon_name, prefix="icon_")
    if src.endswith(".png"):
        classes = ["png"]
    if src.endswith("/icon_missing.svg") and title:
        title += " (%s)" % _("icon not found")

    return IconSettings(src=src, title=title, classes=classes)


def render_vue_table(table: dict[str, Any]) -> None:
    try:
        table_config = create_vue_table_config(table)
        # logger.warning(pprint.pformat(table_config))
        use_d3_table = False
        if html.request.has_var("table_mode"):
            use_d3_table = html.request.var("table_mode") == "d3"
        html.vue_component(
            component_name="cmk-d3-table" if use_d3_table else "cmk-vue-table", data=table_config
        )
    except Exception:
        # Debug only. This block will vanish
        logger.warning("".join(traceback.format_exc()))
