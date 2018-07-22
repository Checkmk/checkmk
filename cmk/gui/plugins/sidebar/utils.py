#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

"""Module to hold shared code for module internals and the plugins"""

import abc
import traceback
import json

import cmk.gui.plugin_registry
import cmk.gui.pages
import cmk.gui.config as config
from cmk.gui.i18n import _, _u
from cmk.gui.globals import html

# Constants to be used in snapins
snapin_width = 230

sidebar_snapins = {}
search_plugins  = []

# TODO: Transform methods to class methods
class SidebarSnapin(object):
    __metaclass__ = abc.ABCMeta

    @classmethod
    @abc.abstractmethod
    def title(cls):
        raise NotImplementedError()


    @classmethod
    @abc.abstractmethod
    def description(cls):
        raise NotImplementedError()


    @abc.abstractmethod
    def show(self):
        raise NotImplementedError()


    @classmethod
    def refresh_regularly(cls):
        return False


    @classmethod
    def refresh_on_restart(cls):
        return False


    @classmethod
    def allowed_roles(cls):
        return [ "admin", "user", "guest" ]


    def styles(self):
        return None


    def page_handlers(self):
        return {}


class SnapinRegistry(cmk.gui.plugin_registry.ClassRegistry):
    """The management object for all available plugins."""
    def plugin_base_class(self):
        return SidebarSnapin


    def _register(self, snapin_class):
        snapin_id = snapin_class.type_name()
        self._entries[snapin_id] = snapin_class

        config.declare_permission("sidesnap.%s" % snapin_id,
            snapin_class.title(),
            snapin_class.description(),
            snapin_class.allowed_roles())

        for path, page_func in snapin_class().page_handlers().items():
            cmk.gui.pages.register_page_handler(path, page_func)


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


def render_link(text, url, target="main", onclick = None):
    # Convert relative links into absolute links. We have three kinds
    # of possible links and we change only [3]
    # [1] protocol://hostname/url/link.py
    # [2] /absolute/link.py
    # [3] relative.py
    if not (":" in url[:10]) and not url.startswith("javascript") and url[0] != '/':
        url = config.url_prefix() + "check_mk/" + url
    return html.render_a(text, href=url, class_="link", target=target or '',\
                         onfocus = "if (this.blur) this.blur();",\
                         onclick = onclick or None)


def link(text, url, target="main", onclick = None):
    return html.write(render_link(text, url, target=target, onclick=onclick))


def simplelink(text, url, target="main"):
    link(text, url, target)
    html.br()


def bulletlink(text, url, target="main", onclick = None):
    html.open_li(class_="sidebar")
    link(text, url, target, onclick)
    html.close_li()


def iconlink(text, url, icon):
    html.open_a(class_=["iconlink", "link"], target="main", href=url)
    html.icon(icon=icon, help=None, cssclass="inline")
    html.write(text)
    html.close_a()
    html.br()


def write_snapin_exception(e):
    html.open_div(class_=["snapinexception"])
    html.h2(_('Error'))
    html.p(e)
    html.div(traceback.format_exc().replace('\n', '<br>'), style="display:none;")
    html.close_div()


def heading(text):
    html.write("<h3>%s</h3>\n" % html.attrencode(text))


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
    html.a(text, class_="link", target="main", href="%snagios/cgi-bin/%s" % (config.url_prefix(), target))
    html.close_li()


def snapin_site_choice(ident, choices):
    sites = config.user.load_file("sidebar_sites", {})
    site  = sites.get(ident, "")
    if site == "":
        only_sites = None
    else:
        only_sites = [site]

    site_choices = config.get_event_console_site_choices()
    if len(site_choices) <= 1:
        return None

    site_choices = [ ("", _("All sites")), ] + site_choices
    onchange = "set_snapin_site(event, %s, this)" % json.dumps(ident)
    html.dropdown("site", site_choices, deflt=site, onchange=onchange)

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

    s = [ (_u(visual.get("topic") or _("Other")), _u(visual.get("title")), name, 'painters' in visual)
          for name, visual
          in permitted_visuals
          if not visual["hidden"] and not visual.get("mobile")]

    s.sort()

    result = []
    for topic in default_order:
        result.append((topic, s))

    rest = list(set([ t for (t, _t, _v, _i) in s if t not in default_order ]))
    rest.sort()
    for topic in rest:
        if topic:
            result.append((topic, s))

    return result
