#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Add a visual to other visuals (dashboard, report)"""

from pydantic import BaseModel

import cmk.utils.version as cmk_version

from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import (
    make_javascript_link,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuLink,
    PageMenuTopic,
)
from cmk.gui.pagetypes import page_menu_add_to_topics
from cmk.gui.plugins.visuals.utils import visual_type_registry
from cmk.gui.type_defs import VisualContext
from cmk.gui.utils.csrf_token import check_csrf_token


def ajax_popup_add() -> None:
    # name is unused at the moment in this, hand over as empty name
    page_menu_dropdown = page_menu_dropdown_add_to_visual(
        add_type=request.get_ascii_input_mandatory("add_type"), name=""
    )[0]

    html.open_ul()

    for topic in page_menu_dropdown.topics:
        html.open_li()
        html.span(topic.title)
        html.close_li()

        for entry in topic.entries:
            html.open_li()

            if not isinstance(entry.item, PageMenuLink):
                html.write_text(f"Unhandled entry type '{type(entry.item)}': {entry.name}")
                continue

            html.open_a(
                href=entry.item.link.url,
                onclick=entry.item.link.onclick,
                target=entry.item.link.target,
            )
            html.icon(entry.icon_name or "trans")
            html.write_text(entry.title)
            html.close_a()
            html.close_li()

    html.close_ul()


def page_menu_dropdown_add_to_visual(add_type: str, name: str) -> list[PageMenuDropdown]:
    """Create the dropdown menu for adding a visual to other visuals / pagetypes

    Please not that this data structure is not only used for rendering the dropdown
    in the page menu. There is also the case of graphs which open a popup menu to
    show these entries.
    """

    visual_topics = []

    for visual_type_class in visual_type_registry.values():
        visual_type = visual_type_class()

        entries = list(visual_type.page_menu_add_to_entries(add_type))
        if not entries:
            continue

        visual_topics.append(
            PageMenuTopic(
                title=_("Add to %s") % visual_type.title,
                entries=entries,
            )
        )

    if add_type == "pnpgraph" and cmk_version.edition() is not cmk_version.Edition.CRE:
        visual_topics.append(
            PageMenuTopic(
                title=_("Export"),
                entries=[
                    PageMenuEntry(
                        title=_("Export as JSON"),
                        icon_name="download",
                        item=make_javascript_link("cmk.popup_menu.graph_export('graph_export')"),
                    ),
                    PageMenuEntry(
                        title=_("Export as PNG"),
                        icon_name="download",
                        item=make_javascript_link("cmk.popup_menu.graph_export('graph_image')"),
                    ),
                ],
            )
        )

    return [
        PageMenuDropdown(
            name="add_to",
            title=_("Add to"),
            topics=page_menu_add_to_topics(add_type) + visual_topics,
            popup_data=[
                add_type,
                _encode_page_context(g.get("page_context", {})),
                {
                    "name": name,
                },
            ],
        )
    ]


def set_page_context(page_context: VisualContext) -> None:
    g.page_context = page_context


# TODO: VisualContext can't be part of the types, VisualContext has neither
# None nor str on the values. Thus unhelpfully set to Dict
def _encode_page_context(page_context: dict) -> dict:
    return {k: "" if v is None else v for k, v in page_context.items()}


class CreateInfoModel(BaseModel):
    params: dict
    context: VisualContext | None


def ajax_add_visual() -> None:
    check_csrf_token()
    visual_type_name = request.get_str_input_mandatory("visual_type")  # dashboards / views / ...
    try:
        visual_type = visual_type_registry[visual_type_name]()
    except KeyError:
        raise MKUserError("visual_type", _("Invalid visual type"))

    visual_name = request.get_str_input_mandatory("visual_name")  # add to this visual

    # type of the visual to add (e.g. view)
    element_type = request.get_str_input_mandatory("type")

    create_info = request.get_model_mandatory(CreateInfoModel, "create_info")

    visual_type.add_visual_handler(
        visual_name,
        element_type,
        create_info.context,
        create_info.params,
    )
