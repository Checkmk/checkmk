#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for module internals and the plugins"""

import abc
import traceback
import json
from typing import Optional, Text, Any, Dict, List, Tuple, Type
import six

import cmk.utils.plugin_registry

from cmk.gui.sites import SiteId  # pylint: disable=unused-import
import cmk.gui.pages
import cmk.gui.config as config
import cmk.gui.escaping as escaping
from cmk.gui.i18n import _, _u
from cmk.gui.globals import html
from cmk.gui.htmllib import Choices  # pylint: disable=unused-import
from cmk.gui.type_defs import RoleName, PermissionName  # pylint: disable=unused-import
from cmk.gui.permissions import (
    permission_section_registry,
    PermissionSection,
    declare_permission,
)

# TODO: Actually this is cmk.gui.sidebar.CustomSnapins, but we run into a hell
# of cycles and untyped dependencies. So for now this is just a reminder.
CustomSnapins = Any

# Constants to be used in snapins
snapin_width = 230

search_plugins = []  # type: List

PageHandlers = Dict[str, "cmk.gui.pages.PageHandlerFunc"]


@permission_section_registry.register
class PermissionSectionSidebarSnapins(PermissionSection):
    @property
    def name(self):
        # type: () -> str
        return "sidesnap"

    @property
    def title(self):
        # type: () -> Text
        return _("Sidebar snapins")

    @property
    def do_sort(self):
        # type: () -> bool
        return True


# TODO: Transform methods to class methods
class SidebarSnapin(six.with_metaclass(abc.ABCMeta, object)):
    """Abstract base class for all sidebar snapins"""
    @classmethod
    @abc.abstractmethod
    def type_name(cls):
        # type: () -> str
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def title(cls):
        # type: () -> Text
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def description(cls):
        # type: () -> Text
        raise NotImplementedError()

    @abc.abstractmethod
    def show(self):
        # type: () -> None
        raise NotImplementedError()

    @classmethod
    def refresh_regularly(cls):
        # type: () -> bool
        return False

    @classmethod
    def refresh_on_restart(cls):
        # type: () -> bool
        return False

    @classmethod
    def is_custom_snapin(cls):
        # type: () -> bool
        """Whether or not a snapin type is a customized snapin"""
        return False

    @classmethod
    def permission_name(cls):
        # type: () -> PermissionName
        return "sidesnap.%s" % cls.type_name()

    @classmethod
    def allowed_roles(cls):
        # type: () -> List[RoleName]
        return ["admin", "user", "guest"]

    def styles(self):
        # type: () -> Optional[str]
        return None

    def page_handlers(self):
        # type: () -> PageHandlers
        return {}


class CustomizableSidebarSnapin(six.with_metaclass(abc.ABCMeta, SidebarSnapin)):
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


# TODO: We should really use the InstanceRegistry here... :-/ Using the
# ClassRegistry obfuscates the code and makes typing a nightmare.
class SnapinRegistry(cmk.utils.plugin_registry.ClassRegistry):
    """The management object for all available plugins."""
    def plugin_base_class(self):
        return SidebarSnapin

    def plugin_name(self, plugin_class):
        return plugin_class.type_name()

    def registration_hook(self, plugin_class):
        # type: (Type[SidebarSnapin]) -> None
        declare_permission(
            "sidesnap.%s" % self.plugin_name(plugin_class),
            plugin_class.title(),
            plugin_class.description(),
            plugin_class.allowed_roles(),
        )

        for path, page_func in plugin_class().page_handlers().items():
            cmk.gui.pages.register_page_handler(path, page_func)

    def get_customizable_snapin_types(self):
        # type: () -> List[Tuple[str, CustomizableSidebarSnapin]]
        return [(snapin_type_id, snapin_type)
                for snapin_type_id, snapin_type in self.items()
                if (issubclass(snapin_type, CustomizableSidebarSnapin) and
                    not snapin_type.is_custom_snapin())]

    def register_custom_snapins(self, custom_snapins):
        # type: (List[CustomSnapins]) -> None
        """Extends the snapin registry with the ones configured in the site (for the current user)"""
        self._clear_custom_snapins()
        self._add_custom_snapins(custom_snapins)

    def _clear_custom_snapins(self):
        # type: () -> None
        for snapin_type_id, snapin_type in self.items():
            if snapin_type.is_custom_snapin():
                self.unregister(snapin_type_id)

    def _add_custom_snapins(self, custom_snapins):
        # type: (List[CustomSnapins]) -> None
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

            _it_is_really_used = CustomSnapin  # noqa: F841


snapin_registry = SnapinRegistry()

#.
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'
# TODO: Move these to a class


def render_link(text, url, target="main", onclick=None):
    # Convert relative links into absolute links. We have three kinds
    # of possible links and we change only [3]
    # [1] protocol://hostname/url/link.py
    # [2] /absolute/link.py
    # [3] relative.py
    if not (":" in url[:10]) and not url.startswith("javascript") and url[0] != '/':
        url = config.url_prefix() + "check_mk/" + url
    return html.render_a(text,
                         href=url,
                         class_="link",
                         target=target or '',
                         onfocus="if (this.blur) this.blur();",
                         onclick=onclick or None)


def link(text, url, target="main", onclick=None):
    return html.write(render_link(text, url, target=target, onclick=onclick))


def simplelink(text, url, target="main"):
    link(text, url, target)
    html.br()


def bulletlink(text, url, target="main", onclick=None):
    html.open_li(class_="sidebar")
    link(text, url, target, onclick)
    html.close_li()


def iconlink(text, url, icon):
    html.open_a(class_=["iconlink", "link"], target="main", href=url)
    html.icon(icon=icon, title=None, cssclass="inline")
    html.write_text(text)
    html.close_a()
    html.br()


def write_snapin_exception(e):
    html.open_div(class_=["snapinexception"])
    html.h2(_('Error'))
    html.p(e)
    html.div(traceback.format_exc().replace('\n', '<br>'), style="display:none;")
    html.close_div()


def heading(text):
    html.write("<h3>%s</h3>\n" % escaping.escape_attribute(text))


# TODO: Better change to context manager?
def begin_footnote_links():
    html.open_div(class_="footnotelink")


def end_footnote_links():
    html.close_div()


def footnotelinks(links):
    begin_footnote_links()
    for text, target in links:
        link(text, target)
    end_footnote_links()


def nagioscgilink(text, target):
    html.open_li(class_="sidebar")
    html.a(text,
           class_="link",
           target="main",
           href="%snagios/cgi-bin/%s" % (config.url_prefix(), target))
    html.close_li()


def snapin_site_choice(ident, choices):
    # type: (SiteId, List[Tuple[SiteId, Text]]) -> Optional[List[SiteId]]
    sites = config.user.load_file("sidebar_sites", {})
    site = sites.get(ident, "")
    if site == "":
        only_sites = None
    else:
        only_sites = [site]

    if len(choices) <= 1:
        return None

    dropdown_choices = [
        ("", _("All sites")),
    ]  # type: Choices
    dropdown_choices += choices

    onchange = "cmk.sidebar.set_snapin_site(event, %s, this)" % json.dumps(ident)
    html.dropdown("site", dropdown_choices, deflt=site, onchange=onchange)

    return only_sites


def visuals_by_topic(permitted_visuals, default_order=None):
    if default_order is None:
        default_order = [
            _("Overview"),
            _("Hosts"),
            _("Host Groups"),
            _("Services"),
            _("Service Groups"),
            _("Metrics"),
            _("Business Intelligence"),
            _("Problems"),
        ]

    s = sorted([(_u(visual.get("topic") or _("Other")), _u(visual.get("title")), name, 'painters'
                 in visual)
                for name, visual in permitted_visuals
                if not visual["hidden"] and not visual.get("mobile")])

    result = []
    for topic in default_order:
        result.append((topic, s))

    rest = sorted({t for (t, _t, _v, _i) in s if t not in default_order})
    for topic in rest:
        if topic:
            result.append((topic, s))

    return result
