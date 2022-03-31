#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for module internals and the plugins"""

import abc
import json
import traceback
from typing import Any, Dict, List, Optional, Tuple, Type, Union

import cmk.utils.plugin_registry
from cmk.utils.site import url_prefix

import cmk.gui.pages
import cmk.gui.pagetypes as pagetypes
from cmk.gui.globals import html
from cmk.gui.htmllib import foldable_container
from cmk.gui.i18n import _
from cmk.gui.permissions import declare_permission, permission_section_registry, PermissionSection
from cmk.gui.sites import filter_available_site_choices, SiteId
from cmk.gui.type_defs import (
    Choices,
    Icon,
    PermissionName,
    RoleName,
    TopicMenuItem,
    TopicMenuTopic,
    Visual,
)
from cmk.gui.utils.html import HTML
from cmk.gui.utils.logged_in import user
from cmk.gui.visuals import visual_title

# TODO: Actually this is cmk.gui.sidebar.CustomSnapins, but we run into a hell
# of cycles and untyped dependencies. So for now this is just a reminder.
CustomSnapins = Any

# Constants to be used in snapins
snapin_width = 240

search_plugins: List = []

PageHandlers = Dict[str, "cmk.gui.pages.PageHandlerFunc"]


@permission_section_registry.register
class PermissionSectionSidebarSnapins(PermissionSection):
    @property
    def name(self) -> str:
        return "sidesnap"

    @property
    def title(self) -> str:
        return _("Sidebar elements")

    @property
    def do_sort(self) -> bool:
        return True


# TODO: Transform methods to class methods
class SidebarSnapin(abc.ABC):
    """Abstract base class for all sidebar snapins"""

    @classmethod
    @abc.abstractmethod
    def type_name(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def title(cls) -> str:
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def description(cls) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def show(self) -> None:
        raise NotImplementedError()

    @classmethod
    def has_show_more_items(cls) -> bool:
        return False

    @classmethod
    def refresh_regularly(cls) -> bool:
        return False

    @classmethod
    def refresh_on_restart(cls) -> bool:
        return False

    @classmethod
    def is_custom_snapin(cls) -> bool:
        """Whether or not a snapin type is a customized snapin"""
        return False

    @classmethod
    def permission_name(cls) -> PermissionName:
        return "sidesnap.%s" % cls.type_name()

    @classmethod
    def allowed_roles(cls) -> List[RoleName]:
        return ["admin", "user", "guest"]

    @classmethod
    def may_see(cls) -> bool:
        return user.may(cls.permission_name())

    def styles(self) -> Optional[str]:
        return None

    def page_handlers(self) -> PageHandlers:
        return {}


class CustomizableSidebarSnapin(SidebarSnapin, abc.ABC):
    """Parent for all user configurable sidebar snapins

    Subclass this class in case you want to implement a sidebar snapin type that can
    be customized by the user"""

    @classmethod
    @abc.abstractmethod
    def vs_parameters(cls):
        """The Dictionary() elements to be used for configuring the parameters"""
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def parameters(cls):
        """Default set of parameters to be used for the uncustomized snapin"""
        raise NotImplementedError()


# TODO: We should really register instances instead of classes here... :-/ Using
# classes obfuscates the code and makes typing a nightmare.
class SnapinRegistry(cmk.utils.plugin_registry.Registry[Type[SidebarSnapin]]):
    """The management object for all available plugins."""

    def plugin_name(self, instance):
        return instance.type_name()

    def registration_hook(self, instance: Type[SidebarSnapin]) -> None:
        # Custom snapins have their own permissions "custom_snapin.*"
        if not instance.is_custom_snapin():
            declare_permission(
                "sidesnap.%s" % self.plugin_name(instance),
                instance.title(),
                instance.description(),
                instance.allowed_roles(),
            )

        for path, page_func in instance().page_handlers().items():
            cmk.gui.pages.register_page_handler(path, page_func)

    def get_customizable_snapin_types(self) -> List[Tuple[str, Type[CustomizableSidebarSnapin]]]:
        return [
            (snapin_type_id, snapin_type)
            for snapin_type_id, snapin_type in self.items()
            if (
                issubclass(snapin_type, CustomizableSidebarSnapin)
                and not snapin_type.is_custom_snapin()
            )
        ]

    def register_custom_snapins(self, custom_snapins: List[CustomSnapins]) -> None:
        """Extends the snapin registry with the ones configured in the site (for the current user)"""
        self._clear_custom_snapins()
        self._add_custom_snapins(custom_snapins)

    def _clear_custom_snapins(self) -> None:
        for snapin_type_id, snapin_type in list(self.items()):
            if snapin_type.is_custom_snapin():
                self.unregister(snapin_type_id)

    def _add_custom_snapins(self, custom_snapins: List[CustomSnapins]) -> None:
        for custom_snapin in custom_snapins:
            base_snapin_type_id = custom_snapin._["custom_snapin"][0]

            try:
                base_snapin_type = self[base_snapin_type_id]
            except KeyError:
                continue

            # TODO: This is just our assumption, can we enforce this via
            # typing? Probably not in the current state of affairs where things
            # which should be instances are classes... :-/
            if not issubclass(base_snapin_type, SidebarSnapin):
                raise ValueError("invalid snapin type %r" % base_snapin_type)

            if not issubclass(base_snapin_type, CustomizableSidebarSnapin):
                continue

            # TODO: The stuff below is completely untypeable... :-P * * *
            @self.register
            class CustomSnapin(base_snapin_type):  # type: ignore[valid-type,misc]
                _custom_snapin = custom_snapin

                @classmethod
                def is_custom_snapin(cls):
                    return True

                @classmethod
                def type_name(cls):
                    return cls._custom_snapin.name()

                @classmethod
                def title(cls):
                    return cls._custom_snapin.title()

                @classmethod
                def description(cls):
                    return cls._custom_snapin.description()

                @classmethod
                def parameters(cls):
                    return cls._custom_snapin._["custom_snapin"][1]

                @classmethod
                def permission_name(cls) -> PermissionName:
                    return "custom_snapin.%s" % cls.type_name()

                @classmethod
                def may_see(cls) -> bool:
                    return cls._custom_snapin.is_permitted()

            _it_is_really_used = CustomSnapin  # noqa: F841


snapin_registry = SnapinRegistry()

# .
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'
# TODO: Move these to a class


def render_link(
    text: Union[str, HTML], url: str, target: str = "main", onclick: Optional[str] = None
) -> HTML:
    # Convert relative links into absolute links. We have three kinds
    # of possible links and we change only [3]
    # [1] protocol://hostname/url/link.py
    # [2] /absolute/link.py
    # [3] relative.py
    if not (":" in url[:10]) and not url.startswith("javascript") and url[0] != "/":
        url = url_prefix() + "check_mk/" + url
    return html.render_a(
        text,
        href=url,
        class_="link",
        target=target or "",
        onfocus="if (this.blur) this.blur();",
        onclick=onclick or None,
    )


def link(
    text: Union[str, HTML], url: str, target: str = "main", onclick: Optional[str] = None
) -> None:
    html.write_html(render_link(text, url, target=target, onclick=onclick))


def bulletlink(text: str, url: str, target: str = "main", onclick: Optional[str] = None) -> None:
    html.open_li(class_="sidebar")
    link(text, url, target, onclick)
    html.close_li()


def iconlink(text: str, url: str, icon: Icon) -> None:
    html.open_a(class_=["iconlink", "link"], target="main", href=url)
    html.icon(icon, cssclass="inline")
    html.write_text(text)
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


def footnotelinks(links: List[Tuple[str, str]]) -> None:
    begin_footnote_links()
    for text, target in links:
        link(text, target)
    end_footnote_links()


def snapin_site_choice(ident: str, choices: List[Tuple[SiteId, str]]) -> Optional[List[SiteId]]:
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


def make_topic_menu(visuals: List[Tuple[str, Tuple[str, Visual]]]) -> List[TopicMenuTopic]:
    pagetypes.PagetypeTopics.load()
    topics = pagetypes.PagetypeTopics.get_permitted_instances()

    by_topic: Dict[pagetypes.PagetypeTopics, TopicMenuTopic] = {}

    for visual_type_name, (name, visual) in visuals:
        if visual["hidden"] or visual.get("mobile"):
            continue  # Skip views not inteded to be shown in the menus

        topic_id = visual["topic"]
        try:
            topic = topics[topic_id]
        except KeyError:
            topic = topics["other"]

        url = _visual_url(visual_type_name, name)

        topic = by_topic.setdefault(
            topic,
            TopicMenuTopic(
                name=topic.name(),
                title=topic.title(),
                max_entries=topic.max_entries(),
                items=[],
                icon=topic.icon_name(),
                hide=topic.hide(),
            ),
        )
        topic.items.append(
            TopicMenuItem(
                name=name,
                title=visual_title(
                    visual_type_name, visual, visual["context"], skip_title_context=True
                ),
                url=url,
                sort_index=visual["sort_index"],
                is_show_more=visual["is_show_more"],
                icon=visual["icon"],
            )
        )

    # Sort the items of all topics
    for topic in by_topic.values():
        topic.items.sort(key=lambda i: (i.sort_index, i.title))

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
        return "%s.py?name=%s" % (visual_type_name, name)

    raise NotImplementedError("Unknown visual type: %s" % visual_type_name)


def show_topic_menu(
    treename: str, menu: List[TopicMenuTopic], show_item_icons: bool = False
) -> None:
    for topic in menu:
        _show_topic(treename, topic, show_item_icons)


def _show_topic(treename: str, topic: TopicMenuTopic, show_item_icons: bool) -> None:
    if not topic.items:
        return

    with foldable_container(
        treename=treename,
        id_=topic.name,
        isopen=False,
        title=topic.title,
        indent=True,
        icon="foldable_sidebar",
    ):

        for item in topic.items:
            if show_item_icons:
                html.open_li(class_=["sidebar", "show_more_mode" if item.is_show_more else None])
                iconlink(item.title, item.url, item.icon or "icon_missing")
                html.close_li()
            else:
                bulletlink(
                    item.title, item.url, onclick="return cmk.sidebar.wato_views_clicked(this)"
                )
