#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for module internals and the plugins"""

import json
import traceback
from collections.abc import Sequence

from cmk.ccc.site import SiteId, url_prefix

from cmk.gui import pagetypes
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import get_main_menu_items_prefixed_by_segment
from cmk.gui.sites import filter_available_site_choices
from cmk.gui.type_defs import Choices, Icon, MainMenuItem, MainMenuTopic, Visual
from cmk.gui.utils.html import HTML
from cmk.gui.visuals import visual_title

# Constants to be used in snap-ins
snapin_width = 240


def render_link(
    text: str | HTML, url: str, target: str = "main", onclick: str | None = None
) -> HTML:
    # Convert relative links into absolute links. We have three kinds
    # of possible links and we change only [3]
    # [1] protocol://hostname/url/link.py
    # [2] /absolute/link.py
    # [3] relative.py
    if ":" not in url[:10] and not url.startswith("javascript") and url[0] != "/":
        url = url_prefix() + "check_mk/" + url
    return HTMLWriter.render_a(
        text,
        href=url,
        class_="link",
        target=target or "",
        onfocus="if (this.blur) this.blur();",
        onclick=onclick or None,
    )


def link(text: str | HTML, url: str, target: str = "main", onclick: str | None = None) -> None:
    html.write_html(render_link(text, url, target=target, onclick=onclick))


def bulletlink(text: str, url: str, target: str = "main", onclick: str | None = None) -> None:
    html.open_li(class_="sidebar")
    link(text, url, target, onclick)
    html.close_li()


def iconlink(text: str, url: str, icon: Icon) -> None:
    html.open_a(class_=["iconlink", "link"], target="main", href=url)
    html.icon(icon, cssclass="inline")
    html.write_text_permissive(text)
    html.close_a()
    html.br()


def write_snapin_exception(e: Exception) -> None:
    html.open_div(class_=["snapinexception"])
    html.h2(_("Error"))
    html.p(str(e))
    html.div(traceback.format_exc().replace("\n", "<br>"), style="display:none;")
    html.close_div()


def heading(text: str) -> None:
    html.h3(text)


# TODO: Better change to context manager?
def begin_footnote_links() -> None:
    html.open_div(class_="footnotelink")


def end_footnote_links() -> None:
    html.close_div()


def footnotelinks(links: list[tuple[str, str]]) -> None:
    begin_footnote_links()
    for text, target in links:
        link(text, target)
    end_footnote_links()


def snapin_site_choice(ident: str, choices: list[tuple[SiteId, str]]) -> list[SiteId] | None:
    sites = user.load_file("sidebar_sites", {})
    available_site_choices = filter_available_site_choices(choices)
    site = sites.get(ident, "")
    if site == "":
        only_sites = None
    else:
        only_sites = [site]

    if len(available_site_choices) <= 1:
        return None

    dropdown_choices: Choices = [
        ("", _("All sites")),
    ]
    dropdown_choices += available_site_choices

    onchange = "cmk.sidebar.set_snapin_site(event, %s, this)" % json.dumps(ident)
    html.dropdown("site", dropdown_choices, deflt=site, onchange=onchange)

    return only_sites


def make_main_menu(
    visuals: Sequence[tuple[str, tuple[str, Visual]]],
) -> list[MainMenuTopic]:
    topics = {p.name(): p for p in pagetypes.PagetypeTopics.load().permitted_instances_sorted()}

    by_topic: dict[pagetypes.PagetypeTopics, MainMenuTopic] = {}

    for visual_type_name, (name, visual) in visuals:
        if visual["hidden"] or visual.get("mobile"):
            continue  # Skip views not inteded to be shown in the menus

        topic_id = visual["topic"]
        try:
            topic = topics[topic_id]
        except KeyError:
            if "other" not in topics:
                raise MKUserError(
                    None,
                    _(
                        "No permission for fallback topic 'Other'. Please contact your administrator."
                    ),
                )
            topic = topics["other"]

        url = _visual_url(visual_type_name, name)

        main_menu_topic = by_topic.setdefault(
            topic,
            MainMenuTopic(
                name=topic.name(),
                title=topic.title(),
                max_entries=topic.max_entries(),
                entries=[],
                icon=topic.icon_name(),
                hide=topic.hide(),
            ),
        )
        main_menu_topic.entries.append(
            MainMenuItem(
                name=name,
                title=visual_title(
                    visual_type_name, visual, visual["context"], skip_title_context=True
                ),
                url=url,
                sort_index=visual["sort_index"],
                is_show_more=visual["is_show_more"],
                icon=visual["icon"],
                main_menu_search_terms=visual["main_menu_search_terms"],
            )
        )

    # Sort the entries of all topics
    for main_menu in by_topic.values():
        main_menu.entries.sort(key=lambda i: (i.sort_index, i.title))

    # Return the sorted topics
    return [
        v
        for k, v in sorted(by_topic.items(), key=lambda e: (e[0].sort_index(), e[0].title()))
        if not v.hide
    ]


def _visual_url(visual_type_name: str, name: str) -> str:
    if visual_type_name == "views":
        return "view.py?view_name=%s" % name

    if visual_type_name == "dashboards":
        return "dashboard.py?name=%s" % name

    # Note: This is no real visual type like the others here. This is just a hack to make top level
    # pages work with this function.
    if visual_type_name == "pages":
        return name if name.endswith(".py") else "%s.py" % name

    if visual_type_name == "reports":
        return "report.py?name=%s" % name

    # Handle page types
    if visual_type_name in ["custom_graph", "graph_collection", "forecast_graph"]:
        return f"{visual_type_name}.py?name={name}"

    raise NotImplementedError("Unknown visual type: %s" % visual_type_name)


def show_main_menu(treename: str, menu: list[MainMenuTopic], show_item_icons: bool = False) -> None:
    for topic in menu:
        _show_topic(treename, topic, show_item_icons)


def _show_topic(treename: str, topic: MainMenuTopic, show_item_icons: bool) -> None:
    if not topic.entries:
        return

    with foldable_container(
        treename=treename,
        id_=topic.name,
        isopen=False,
        title=topic.title,
        indent=True,
    ):
        for item in get_main_menu_items_prefixed_by_segment(topic):
            if show_item_icons:
                html.open_li(class_=["sidebar"] + (["show_more_mode"] if item.is_show_more else []))
                iconlink(item.title, item.url, item.icon or "icon_missing")
                html.close_li()
            else:
                bulletlink(
                    item.title,
                    item.url,
                    onclick="return cmk.sidebar.wato_views_clicked(this)",
                )
