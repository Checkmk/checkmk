#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The Checkmk page menus of the map list and the image library.

The actions open what the SPA owns (a dialog, a file picker), so they do not
link anywhere: they dispatch :data:`PAGE_MENU_EVENT` with the action as its
detail, and the SPA handles it, like the monitoring pages' export menu. The
list's layout is a page parameter instead, so the menu can offer the other one.
"""

from typing import Final, Literal

from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_main_menu_breadcrumb
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import (
    make_javascript_link,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuLink,
    PageMenuTopic,
)
from cmk.maps.gui._settings import MapListView
from cmk.web.utils.icons import IconNames, StaticIcon

PAGE_MENU_EVENT: Final = "cmk-maps-page-menu"
MAPS_HOME_URL: Final = "maps.py"

IMAGES_URL: Final = f"{MAPS_HOME_URL}?mode=icons"

type PageMenuAction = Literal["create", "import", "upload"]


def maps_breadcrumb() -> Breadcrumb:
    # Maps has no Setup tile; its pages hang under Customize → Maps.
    breadcrumb = make_main_menu_breadcrumb(main_menu_registry.menu_customize())
    breadcrumb.append(BreadcrumbItem(title=_("Maps"), url=MAPS_HOME_URL, id="maps"))
    return breadcrumb


def images_breadcrumb() -> Breadcrumb:
    breadcrumb = maps_breadcrumb()
    breadcrumb.append(BreadcrumbItem(title=_("Images"), url=IMAGES_URL, id="maps_images"))
    return breadcrumb


def images_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    return PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="images",
                title=_("Images"),
                topics=[
                    PageMenuTopic(
                        title=_("Images"),
                        entries=[
                            PageMenuEntry(
                                title=_("Upload image"),
                                icon_name=StaticIcon(IconNames.upload),
                                item=_dispatch("upload"),
                                name="maps_upload_image",
                                is_shortcut=True,
                                is_suggested=True,
                            )
                        ],
                    )
                ],
            )
        ],
        breadcrumb=breadcrumb,
    )


def map_list_page_menu(
    acting_user: LoggedInUser, breadcrumb: Breadcrumb, *, settings_url: str, layout: MapListView
) -> PageMenu:
    menu = PageMenu(
        dropdowns=[_maps_dropdown(acting_user, settings_url)],
        breadcrumb=breadcrumb,
    )
    menu["display"].topics.append(PageMenuTopic(title=_("Maps"), entries=[_layout_entry(layout)]))
    return menu


def _layout_entry(shown: MapListView) -> PageMenuEntry:
    # Only the layout not shown, as the availability offers its timeline.
    other: MapListView
    if shown == "table":
        other, title, icon = "cards", _("Show as cards"), IconNames.dashboard_grid
    else:
        other, title, icon = "table", _("Show as table"), IconNames.view
    return PageMenuEntry(
        title=title,
        icon_name=StaticIcon(icon),
        item=_switch_layout(other),
        name=f"maps_show_{other}",
        is_shortcut=True,
        is_suggested=True,
    )


def _switch_layout(layout: MapListView) -> PageMenuLink:
    # Built from the URL at the time of the click, which also holds the search
    # and scope the list has written into it since the page was rendered.
    return make_javascript_link(f"location.href = cmk.utils.makeuri({{layout: '{layout}'}})")


def _maps_dropdown(acting_user: LoggedInUser, settings_url: str) -> PageMenuDropdown:
    topics = []
    if acting_user.may("general.edit_map"):
        topics.append(
            PageMenuTopic(
                title=_("Maps"),
                entries=[
                    PageMenuEntry(
                        title=_("Add map"),
                        icon_name=StaticIcon(IconNames.new),
                        item=_dispatch("create"),
                        name="maps_create",
                        is_shortcut=True,
                        is_suggested=True,
                    ),
                    PageMenuEntry(
                        title=_("Import map"),
                        icon_name=StaticIcon(IconNames.upload),
                        item=_dispatch("import"),
                        name="maps_import",
                    ),
                ],
            )
        )
    if acting_user.may("maps.configure"):
        topics.append(
            PageMenuTopic(
                title=_("Setup"),
                entries=[
                    PageMenuEntry(
                        title=_("Images"),
                        icon_name=StaticIcon(IconNames.icons),
                        item=make_simple_link(IMAGES_URL),
                        name="maps_images",
                    ),
                    PageMenuEntry(
                        title=_("Maps settings"),
                        icon_name=StaticIcon(IconNames.configuration),
                        item=make_simple_link(settings_url),
                        name="maps_settings",
                    ),
                ],
            )
        )
    return PageMenuDropdown(name="maps", title=_("Maps"), topics=topics)


def _dispatch(action: PageMenuAction) -> PageMenuLink:
    return make_javascript_link(
        f"document.dispatchEvent(new CustomEvent('{PAGE_MENU_EVENT}', {{detail: '{action}'}}))"
    )
