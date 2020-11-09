#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Display information about the Checkmk check plugins

The maxium depth of the catalog paths is 3. The top level is being rendered
like the WATO main menu. The second and third level are being rendered like
the global settings.
"""

import re
from typing import Set, List, Dict, Any, Tuple, Optional, Type, overload

from six import ensure_str

import cmk.utils.man_pages as man_pages
from cmk.utils.man_pages import ManPageCatalogPath
from cmk.utils.type_defs import CheckPluginNameStr

import cmk.gui.watolib as watolib
from cmk.gui.table import table_element
from cmk.gui.htmllib import HTML
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html, request
from cmk.gui.watolib.rulespecs import rulespec_registry
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    PageMenuSearch,
    make_simple_link,
)

from cmk.gui.valuespec import (
    ID,)

from cmk.gui.plugins.wato.utils.main_menu import (
    MainMenu,
    MenuItem,
)

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
    search_form,
    get_search_expression,
)

from cmk.gui.utils.urls import makeuri, makeuri_contextless


@mode_registry.register
class ModeCheckPlugins(WatoMode):
    @classmethod
    def name(cls):
        return "check_plugins"

    @classmethod
    def permissions(cls):
        return []

    def _from_vars(self):
        self._manpages = _get_check_catalog(only_path=())
        self._titles = man_pages.man_page_catalog_titles()

    def title(self):
        return _("Catalog of check plugins")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = super().page_menu(breadcrumb)
        menu.inpage_search = PageMenuSearch(target_mode="check_plugin_search",
                                            placeholder=_("Search"))
        return menu

    def page(self):
        html.help(
            _("This catalog of check plugins gives you a complete listing of all plugins "
              "that are shipped with your Check_MK installation. It also allows you to "
              "access the rule sets for configuring the parameters of the checks and to "
              "manually create services in case you cannot or do not want to rely on the "
              "automatic service discovery."))

        menu = MainMenu()
        for topic, _has_second_level, title, helptext in _man_page_catalog_topics():
            menu.add_item(
                MenuItem(mode_or_url=makeuri(
                    request,
                    [("mode", "check_plugin_topic"), ("topic", topic)],
                ),
                         title=title,
                         icon="plugins_" + topic,
                         permission=None,
                         description=helptext))
        menu.show()


@mode_registry.register
class ModeCheckPluginSearch(WatoMode):
    @classmethod
    def name(cls):
        return "check_plugin_search"

    @classmethod
    def permissions(cls):
        return []

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeCheckPlugins

    def _from_vars(self):
        self._search = get_search_expression()
        self._manpages = _get_check_catalog(only_path=())
        self._titles = man_pages.man_page_catalog_titles()

    def title(self):
        return "%s: %s" % (_("Check plugins matching"), self._search)

    def page(self):
        search_form(title="%s: " % _("Search for check plugins"), mode="check_plugin_search")

        for path, manpages in self._get_manpages_after_search():
            _render_manpage_list(self._titles, manpages, path, self._titles.get(path, path))

    def _get_manpages_after_search(self):
        collection: Dict[ManPageCatalogPath, List[Dict]] = {}
        handled_check_names: Set[CheckPluginNameStr] = set()

        # searches in {"name" : "asd", "title" : "das", ...}
        def get_matched_entry(entry):
            if isinstance(entry, dict):
                name = ensure_str(entry.get("name", ""))
                title = ensure_str(entry.get("title", ""))
                if self._search in name.lower() or self._search in title.lower():
                    return entry

            return None

        def check_entries(key, entries):
            if isinstance(entries, list):
                these_matches = []
                for entry in entries:
                    match = get_matched_entry(entry)
                    if match:
                        these_matches.append(match)

                if these_matches:
                    collection.setdefault(key, [])
                    # avoid duplicates due to the fact that a man page can have more than
                    # one places in the global tree of man pages.
                    for match in these_matches:
                        name = match.get("name")
                        if name and name in handled_check_names:
                            continue  # avoid duplicate
                        collection[key].append(match)
                        if name:
                            handled_check_names.add(name)

            elif isinstance(entries, dict):
                for k, subentries in entries.items():
                    check_entries(k, subentries)

        for key, entries in self._manpages.items():
            check_entries(key, entries)

        return list(collection.items())


@mode_registry.register
class ModeCheckPluginTopic(WatoMode):
    @classmethod
    def name(cls):
        return "check_plugin_topic"

    @classmethod
    def permissions(cls):
        return []

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeCheckPlugins

    # pylint does not understand this overloading
    @overload
    @classmethod
    def mode_url(cls, *, topic: str) -> str:  # pylint: disable=arguments-differ
        ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def breadcrumb(self) -> Breadcrumb:
        """Add each individual level of the catalog topics as single breadcrumb item"""
        parent_cls = self.parent_mode()
        assert parent_cls is not None
        breadcrumb = _add_breadcrumb_topic_items(parent_cls().breadcrumb(), self._titles,
                                                 self._path)
        breadcrumb.append(self._breadcrumb_item())
        return breadcrumb

    def _breadcrumb_url(self) -> str:
        """Ensure the URL is computed correctly when linking from man pages to the topic"""
        return self.mode_url(topic=self._topic)

    def _from_vars(self):
        self._topic = html.request.get_ascii_input_mandatory("topic", "")
        if not re.match("^[a-zA-Z0-9_./]+$", self._topic):
            raise MKUserError("topic", _("Invalid topic"))

        self._path: Tuple[str, ...] = tuple(self._topic.split("/"))  # e.g. [ "hw", "network" ]

        for comp in self._path:
            ID().validate_value(comp, None)  # Beware against code injection!

        self._manpages = _get_check_catalog(self._path)
        self._titles = man_pages.man_page_catalog_titles()

        self._has_second_level = None
        for t, has_second_level, title, _helptext in _man_page_catalog_topics():
            if t == self._path[0]:
                self._has_second_level = has_second_level
                self._topic_title = title
                break

        if len(self._path) == 2:
            self._topic_title = self._titles.get(self._path[1], self._path[1])

    def title(self):
        return self._topic_title

    def page(self):
        if isinstance(self._manpages, list):
            _render_manpage_list(self._titles, self._manpages, self._path[-1], self._topic_title)
            return

        if len(self._path) == 1 and self._has_second_level:
            # For some topics we render a second level in the same optic as the first level
            menu = MainMenu()
            for path_comp, subnode in self._manpages.items():
                url = makeuri(request, [("topic", "%s/%s" % (self._path[0], path_comp))])
                title = self._titles.get(path_comp, path_comp)
                helptext = self._get_check_plugin_stats(subnode)

                menu.add_item(
                    MenuItem(
                        mode_or_url=url,
                        title=title,
                        icon="check_plugins",
                        permission=None,
                        description=helptext,
                    ))
            menu.show()

        else:
            # For the others we directly display the tables
            entries = []
            for path_comp, subnode in self._manpages.items():
                title = self._titles.get(path_comp, path_comp)
                entries.append((title, subnode, path_comp))

            for title, subnode, path_comp in sorted(entries, key=lambda x: x[0].lower()):
                _render_manpage_list(self._titles, subnode, path_comp, title)

    def _get_check_plugin_stats(self, subnode):
        if isinstance(subnode, list):
            num_cats = 1
            num_plugins = len(subnode)
        else:
            num_cats = len(subnode)
            num_plugins = 0
            for subcat in subnode.values():
                num_plugins += len(subcat)

        text = u""
        if num_cats > 1:
            text += "%d %s<br>" % (num_cats, _("sub categories"))
        text += "%d %s" % (num_plugins, _("check plugins"))
        return text


def _add_breadcrumb_topic_items(breadcrumb, titles, path):
    for num_elements in range(1, len(path)):
        elements = path[:num_elements]
        breadcrumb.append(
            BreadcrumbItem(
                title=titles.get(elements[-1], elements[-1]),
                url=makeuri_contextless(
                    request,
                    [("mode", "check_plugin_topic"), ("topic", "/".join(elements))],
                ),
            ))
    return breadcrumb


def _render_manpage_list(titles, manpage_list, path_comp, heading):
    def translate(t):
        return titles.get(t, t)

    html.h2(heading)
    with table_element(searchable=False, sortable=False, css="check_catalog") as table:
        for entry in sorted(manpage_list, key=lambda x: x["title"]):
            if not isinstance(entry, dict):
                continue
            table.row()
            url = makeuri(
                request,
                [
                    ("mode", "check_manpage"),
                    ("check_type", entry["name"]),
                    ("back", makeuri(request, [])),
                ],
            )
            table.cell(_("Type of Check"),
                       "<a href='%s'>%s</a>" % (url, entry["title"]),
                       css="title")
            table.cell(_("Plugin Name"), "<tt>%s</tt>" % entry["name"], css="name")
            table.cell(_("Agents"),
                       ", ".join(map(translate, sorted(entry["agents"]))),
                       css="agents")


def _man_page_catalog_topics():
    # topic, has_second_level, title, description
    return [
        ("hw", True, _("Appliances, other dedicated hardware"),
         _("Switches, load balancers, storage, UPSes, "
           "environmental sensors, etc. ")),
        ("os", True, _("Operating systems"),
         _("Plugins for operating systems, things "
           "like memory, CPU, filesystems, etc.")),
        ("app", False, _("Applications"),
         _("Monitoring of applications such as "
           "processes, services or databases")),
        ("cloud", False, _("Cloud Based Environments"),
         _("Monitoring of cloud environments like Microsoft Azure")),
        ("containerization", False, _("Containerization"),
         _("Monitoring of container and container orchestration software")),
        ("agentless", False, _("Networking checks without agent"),
         _("Plugins that directly check networking "
           "protocols like HTTP or IMAP")),
        ("generic", False, _("Generic check plugins"),
         _("Plugins for local agent extensions or "
           "communication with the agent in general")),
    ]


def _get_check_catalog(only_path):
    def path_prefix_matches(p, op):
        if op and not p:
            return False
        if not op:
            return True
        return p[0] == op[0] and path_prefix_matches(p[1:], op[1:])

    def strip_manpage_entry(entry):
        return {k: v for k, v in entry.items() if k in ["name", "agents", "title"]}

    tree: Dict[str, Any] = {}

    for path, entries in man_pages.load_man_page_catalog().items():
        if not path_prefix_matches(path, only_path):
            continue
        subtree = tree
        for component in path[:-1]:
            subtree = subtree.setdefault(component, {})
        subtree[path[-1]] = list(map(strip_manpage_entry, entries))

    for p in only_path:
        try:
            tree = tree[p]
        except KeyError:
            pass

    return tree


@mode_registry.register
class ModeCheckManPage(WatoMode):
    @classmethod
    def name(cls):
        return "check_manpage"

    @classmethod
    def permissions(cls):
        return []

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeCheckPluginTopic

    def breadcrumb(self) -> Breadcrumb:
        # To be able to calculate the breadcrumb with ModeCheckPluginTopic as parent, we need to
        # ensure that the topic is available.
        with html.stashed_vars():
            html.request.set_var("topic", self._manpage["header"]["catalog"])
            return super().breadcrumb()

    def _from_vars(self):
        self._check_type = html.request.get_ascii_input_mandatory("check_type", "")

        builtin_check_types = ['check-mk', "check-mk-inventory"]
        if not re.match("^[a-zA-Z0-9_.]+$", self._check_type) and \
                self._check_type not in builtin_check_types:
            raise MKUserError("check_type", _("Invalid check type"))

        manpage = man_pages.load_man_page(self._check_type)
        if manpage is None:
            raise MKUserError(None, _("There is no manpage for this check."))
        self._manpage = manpage

        checks = watolib.check_mk_local_automation("get-check-information")
        if self._check_type in checks:
            self._manpage = {
                "type": "check_mk",
                **checks[self._check_type],
                **self._manpage,
            }
        elif self._check_type.startswith("check_"):  # Assume active check
            self._manpage = {
                "type": "active",
                **self._manpage,
            }
        elif self._check_type in builtin_check_types:
            self._manpage = {
                "type": "check_mk",
                "service_description": "Check_MK%s" %
                                       ("" if self._check_type == "check-mk" else " Discovery"),
                **self._manpage,
            }

    def title(self):
        return self._manpage["header"]["title"]

    # TODO
    # We could simply detect on how many hosts and services this plugin
    # is currently in use (Livestatus query) and display this information
    # together with a link for searching. Then we can remove the dumb context
    # button, that will always be shown - even if the plugin is not in use.
    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        if self._check_type.startswith("check_"):
            command = "check_mk_active-" + self._check_type[6:]
        else:
            command = "check_mk-" + self._check_type
        url = makeuri_contextless(
            request,
            [("view_name", "searchsvc"), ("check_command", command), ("filled_in", "filter")],
            filename="view.py",
        )

        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Monitoring"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Show services using this check"),
                                    icon_name="status",
                                    item=make_simple_link(url),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def page(self):
        html.open_table(class_=["data", "headerleft"])

        html.open_tr()
        html.th(_("Title"))
        html.open_td()
        html.b(self._manpage["header"]["title"])
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.th(_("Name of plugin"))
        html.open_td()
        html.tt(self._check_type)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.th(_("Description"))
        html.td(self._manpage_text(self._manpage["header"]["description"]))
        html.close_tr()

        if self._manpage["type"] == "check_mk":
            html.open_tr()
            html.th(_("Service name"))
            html.td(HTML(self._manpage["service_description"].replace("%s", "&#9744;")))
            html.close_tr()

            check_ruleset_name = self._manpage.get("check_ruleset_name")
            if check_ruleset_name is not None:
                self._show_ruleset("checkgroup_parameters:%s" % check_ruleset_name)

        else:
            self._show_ruleset("active_checks:%s" % self._check_type[6:])

        html.close_table()

    def _manpage_text(self, text):
        html_code = text.replace("<br>", "\n")
        html_code = re.sub("{(.*?)}", "<tt>\\1</tt>", html_code)
        html_code = re.sub("\n\n+", "<p>", html_code)
        return html_code

    def _show_ruleset(self, varname):
        if varname not in rulespec_registry:
            return

        rulespec = rulespec_registry[varname]
        url = makeuri_contextless(request, [("mode", "edit_ruleset"), ("varname", varname)])
        param_ruleset = html.render_a(rulespec.title, url)
        html.open_tr()
        html.th(_("Parameter rule set"))
        html.open_td()
        html.icon_button(url, _("Edit parameter rule set for this check type"), "check_parameters")
        html.write(param_ruleset)
        html.close_td()
        html.close_tr()
        html.open_tr()
        html.th(_("Example for Parameters"))
        html.open_td()
        vs = rulespec.valuespec
        vs.render_input("dummy", vs.default_value())
        html.close_td()
        html.close_tr()
