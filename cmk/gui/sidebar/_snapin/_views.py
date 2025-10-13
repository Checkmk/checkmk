#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


import pprint
from collections.abc import Callable

from cmk.ccc.user import UserId
from cmk.gui import pagetypes
from cmk.gui.config import active_config, Config
from cmk.gui.dashboard import get_permitted_dashboards
from cmk.gui.hooks import request_memoize
from cmk.gui.http import response
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.main_menu import MainMenuRegistry
from cmk.gui.nodevis.topology import ParentChildTopologyPage
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import (
    MainMenu,
    MainMenuTopic,
    Visual,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.store import get_permitted_views

from ._base import SidebarSnapin
from ._helpers import footnotelinks, make_main_menu, show_main_menu
from ._registry import SnapinRegistry


def register(
    page_registry: PageRegistry,
    snapin_registry: SnapinRegistry,
    main_menu_registry: MainMenuRegistry,
    view_menu_topics: Callable[[], list[MainMenuTopic]],
) -> None:
    snapin_registry.register(Views)
    page_registry.register(PageEndpoint("export_views", ajax_export_views))

    main_menu_registry.register(
        MainMenu(
            name="monitoring",
            title=_l("Monitor"),
            icon="main_monitoring",
            sort_index=5,
            topics=view_menu_topics,
            hint=_("Press Ctrl + K to trigger search"),
        )
    )


class Views(SidebarSnapin):
    @staticmethod
    def type_name():
        return "views"

    @classmethod
    def title(cls):
        return _("Views")

    @classmethod
    def description(cls):
        return _("Links to global views and dashboards")

    def show(self, config: Config) -> None:
        show_main_menu(
            treename="views",
            menu=make_main_menu(
                view_menu_items(
                    user_permissions := UserPermissions.from_config(config, permission_registry)
                ),
                user_permissions,
            ),
        )

        links = []
        if user.may("general.edit_views"):
            if config.debug:
                links.append((_("Export"), "export_views.py"))
            links.append((_("Edit"), "edit_views.py"))
            footnotelinks(links)


def ajax_export_views(config: Config) -> None:
    for view in get_permitted_views().values():
        view["owner"] = UserId.builtin()
        view["public"] = True
    response.set_data(pprint.pformat(get_permitted_views()))


@request_memoize()
def default_view_menu_topics() -> list[MainMenuTopic]:
    return make_main_menu(
        view_menu_items(
            user_permissions := UserPermissions.from_config(active_config, permission_registry)
        ),
        user_permissions,
    )


def view_menu_items(user_permissions: UserPermissions) -> list[tuple[str, tuple[str, Visual]]]:
    # The page types that are implementing the PageRenderer API should also be
    # part of the menu. Bring them into a visual like structure to make it easy to
    # integrate them.
    page_type_items: list[tuple[str, tuple[str, Visual]]] = []
    for page_type in pagetypes.all_page_types().values():
        if not issubclass(page_type, pagetypes.PageRenderer):
            continue

        for page in page_type.load(user_permissions).pages(user_permissions):
            if page._show_in_sidebar():
                visual = page.to_visual()
                visual["hidden"] = False  # Is currently not configurable for pagetypes
                visual["icon"] = None  # Is currently not configurable for pagetypes
                visual["main_menu_search_terms"] = []  # Is currently not configurable for pagetypes

                page_type_items.append((page_type.type_name(), (page.name(), visual)))

    network_topology_visual_spec = ParentChildTopologyPage.visual_spec()
    pages_to_show = [(network_topology_visual_spec["name"], network_topology_visual_spec)]

    visuals_to_show: list[tuple[str, tuple[str, Visual]]] = [
        ("views", (k, v)) for k, v in get_permitted_views().items()
    ]
    visuals_to_show += [("dashboards", (k, v)) for k, v in get_permitted_dashboards().items()]
    visuals_to_show += [("pages", e) for e in pages_to_show]
    visuals_to_show += page_type_items

    return visuals_to_show
