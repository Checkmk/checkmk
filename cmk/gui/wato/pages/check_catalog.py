#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Display information about the Checkmk check plug-ins

The maxium depth of the catalog paths is 3. The top level is being rendered
like the Setup main menu. The second and third level are being rendered like
the global settings.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping, Sequence
from typing import overload, TypedDict, Union

from cmk.utils import man_pages
from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import (
    get_search_expression,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
    search_form,
)
from cmk.gui.table import table_element
from cmk.gui.type_defs import PermissionName
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.valuespec import ID
from cmk.gui.watolib.check_mk_automations import get_check_information
from cmk.gui.watolib.main_menu import MenuItem
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.gui.watolib.rulespecs import rulespec_registry

from cmk.discover_plugins import discover_families, PluginGroup

from ._tile_menu import TileMenuRenderer


class CatalogEntry(TypedDict):
    name: str
    agents: Sequence[str]
    title: str


# NOTE: We can't use the '|' operator because of the recursion.
CatalogTree = dict[str, Union["CatalogTree", Sequence[CatalogEntry]]]


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeCheckPlugins)
    mode_registry.register(ModeCheckPluginSearch)
    mode_registry.register(ModeCheckPluginTopic)
    mode_registry.register(ModeCheckManPage)


class ModeCheckPlugins(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "check_plugins"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["check_plugins"]

    def _from_vars(self) -> None:
        self._manpages = _get_check_catalog(discover_families(raise_errors=False), only_path=())
        self._titles = man_pages.CATALOG_TITLES

    def title(self) -> str:
        return _("Catalog of check plug-ins")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = super().page_menu(breadcrumb)
        menu.inpage_search = PageMenuSearch(target_mode="check_plugin_search")
        return menu

    def page(self) -> None:
        html.help(
            _(
                "This catalog of check plug-ins gives you a complete listing of all plug-ins "
                "that are shipped with your Checkmk installation. It also allows you to "
                "access the rule sets for configuring the parameters of the checks and to "
                "manually create services in case you cannot or do not want to rely on the "
                "automatic service discovery."
            )
        )

        menu = TileMenuRenderer()
        for topic, _has_second_level, title, helptext in _man_page_catalog_topics():
            menu.add_item(
                MenuItem(
                    mode_or_url=makeuri(
                        request,
                        [("mode", "check_plugin_topic"), ("topic", topic)],
                    ),
                    title=title,
                    icon="plugins_" + topic,
                    permission=None,
                    description=helptext,
                )
            )
        menu.show()


class ModeCheckPluginSearch(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "check_plugin_search"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["check_plugins"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeCheckPlugins

    def _from_vars(self) -> None:
        self._search = get_search_expression()
        self._manpages = _get_check_catalog(discover_families(raise_errors=False), only_path=())
        self._titles = man_pages.CATALOG_TITLES

    def title(self) -> str:
        return "{}: {}".format(_("Check plug-ins matching"), self._search)

    def page(self) -> None:
        search_form(title="%s: " % _("Search for check plug-ins"), mode="check_plugin_search")

        for path, manpages in self._get_manpages_after_search():
            _render_manpage_list(self._titles, manpages, path, self._titles.get(path, path))

    def _get_manpages_after_search(self) -> list[tuple[str, list[CatalogEntry]]]:
        collection: dict[str, list[CatalogEntry]] = {}
        handled_check_names: set[str] = set()

        def entry_part_matches(entry: CatalogEntry, value: str) -> bool:
            return self._search is not None and self._search in value.lower()

        def get_matched_entry(entry: CatalogEntry) -> CatalogEntry | None:
            return (
                entry
                if isinstance(entry, dict)
                and (
                    entry_part_matches(entry, entry.get("name", ""))
                    or entry_part_matches(entry, entry.get("title", ""))
                )
                else None
            )

        def check_entries(key: str, entries: CatalogTree | Sequence[CatalogEntry]) -> None:
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


class ModeCheckPluginTopic(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "check_plugin_topic"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["check_plugins"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeCheckPlugins

    # pylint does not understand this overloading
    @overload
    @classmethod
    def mode_url(cls, *, topic: str) -> str: ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str: ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def breadcrumb(self) -> Breadcrumb:
        """Add each individual level of the catalog topics as single breadcrumb item"""
        parent_cls = self.parent_mode()
        assert parent_cls is not None
        breadcrumb = _add_breadcrumb_topic_items(
            parent_cls().breadcrumb(), self._titles, self._path
        )
        breadcrumb.append(self._breadcrumb_item())
        return breadcrumb

    def _breadcrumb_url(self) -> str:
        """Ensure the URL is computed correctly when linking from man pages to the topic"""
        return self.mode_url(topic=self._topic)

    def _from_vars(self) -> None:
        self._topic = request.get_ascii_input_mandatory("topic", "")
        if not re.match("^[a-zA-Z0-9_./]+$", self._topic):
            raise MKUserError("topic", _("Invalid topic"))

        self._path: tuple[str, ...] = tuple(self._topic.split("/"))  # e.g. [ "hw", "network" ]

        for comp in self._path:
            ID().validate_value(comp, "")  # Beware against code injection!

        self._manpages = _get_check_catalog(discover_families(raise_errors=False), self._path)
        self._titles = man_pages.CATALOG_TITLES

        self._has_second_level = None
        for t, has_second_level, title, _helptext in _man_page_catalog_topics():
            if t == self._path[0]:
                self._has_second_level = has_second_level
                self._topic_title = title
                break

        if len(self._path) == 2:
            self._topic_title = self._titles.get(self._path[1], self._path[1])

    def title(self) -> str:
        if self._topic == "unsorted":
            return "unsorted"
        return self._topic_title

    def page(self) -> None:
        if isinstance(self._manpages, list):
            _render_manpage_list(self._titles, self._manpages, self._path[-1], self._topic_title)
            return

        if len(self._path) == 1 and self._has_second_level:
            # For some topics we render a second level in the same optic as the first level
            menu = TileMenuRenderer()
            for path_comp, subnode in self._manpages.items():
                url = makeuri(request, [("topic", f"{self._path[0]}/{path_comp}")])
                title = self._titles.get(path_comp, path_comp)
                helptext = self._get_check_plugin_stats(subnode)

                menu.add_item(
                    MenuItem(
                        mode_or_url=url,
                        title=title,
                        icon="check_plugins",
                        permission=None,
                        description=helptext,
                    )
                )
            menu.show()

        else:
            # For the others we directly display the tables
            entries = []
            for path_comp, subnode in self._manpages.items():
                title = self._titles.get(path_comp, path_comp)
                entries.append((title, subnode, path_comp))

            for title, subnode, path_comp in sorted(entries, key=lambda x: x[0].lower()):
                assert isinstance(subnode, list)
                _render_manpage_list(self._titles, subnode, path_comp, title)

    def _get_check_plugin_stats(self, subnode: CatalogTree | Sequence[CatalogEntry]) -> str:
        if isinstance(subnode, list):
            num_cats = 1
            num_plugins = len(subnode)
        elif isinstance(subnode, dict):
            num_cats = len(subnode)
            num_plugins = 0
            for subcat in subnode.values():
                num_plugins += len(subcat)
        else:
            raise ValueError("Invalid subnode type")

        text = ""
        if num_cats > 1:
            text += "%d %s<br>" % (num_cats, _("sub categories"))
        text += "%d %s" % (num_plugins, _("check plug-ins"))
        return text


def _add_breadcrumb_topic_items(
    breadcrumb: Breadcrumb, titles: Mapping[str, str], path: tuple[str, ...]
) -> Breadcrumb:
    for num_elements in range(1, len(path)):
        elements = path[:num_elements]
        breadcrumb.append(
            BreadcrumbItem(
                title=titles.get(elements[-1], elements[-1]),
                url=makeuri_contextless(
                    request,
                    [("mode", "check_plugin_topic"), ("topic", "/".join(elements))],
                ),
            )
        )
    return breadcrumb


def _render_manpage_list(
    titles: Mapping[str, str], manpage_list: Sequence[CatalogEntry], path_comp: str, heading: str
) -> None:
    def translate(t: str) -> str:
        return titles.get(t, t)

    html.h3(heading)
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
            table.cell(
                _("Type of Check"), HTMLWriter.render_a(entry["title"], href=url), css=["title"]
            )
            table.cell(_("Plug-in name"), HTMLWriter.render_tt(entry["name"]), css=["name"])
            table.cell(
                _("Agents"), ", ".join(map(translate, sorted(entry["agents"]))), css=["agents"]
            )


def _man_page_catalog_topics() -> list[tuple[str, bool, str, str]]:
    # topic, has_second_level, title, description
    return [
        (
            "hw",
            True,
            _("Appliances, other dedicated hardware"),
            _("Switches, load balancers, storage, UPSes, environmental sensors, etc. "),
        ),
        (
            "os",
            True,
            _("Operating systems"),
            _("Plug-ins for operating systems, things like memory, CPU, file systems, etc."),
        ),
        (
            "app",
            False,
            _("Applications"),
            _("Monitoring of applications such as processes, services or databases"),
        ),
        (
            "cloud",
            False,
            _("Cloud Based Environments"),
            _("Monitoring of cloud environments like Microsoft Azure"),
        ),
        (
            "containerization",
            False,
            _("Containerization"),
            _("Monitoring of container and container orchestration software"),
        ),
        (
            "agentless",
            False,
            _("Networking checks without agent"),
            _("Plug-ins that directly check networking protocols like HTTP or IMAP"),
        ),
        (
            "generic",
            False,
            _("Generic check plug-ins"),
            _("Plug-ins for local agent extensions or communication with the agent in general"),
        ),
        (
            "virtual",
            False,
            _("Virtualization"),
            _("Monitoring of classic virtual environment like ESX, Nutanix and HyperV"),
        ),
    ]


def _get_check_catalog(
    plugin_families: Mapping[str, Sequence[str]],
    only_path: tuple[str, ...],
) -> CatalogTree:
    def path_prefix_matches(p: tuple[str, ...]) -> bool:
        return p[: len(only_path)] == only_path

    tree: CatalogTree = {}

    for path, entries in man_pages.load_man_page_catalog(
        plugin_families, PluginGroup.CHECKMAN.value
    ).items():
        if not path_prefix_matches(path):
            continue
        subtree: CatalogTree = tree
        for component in path[:-1]:
            next_level = subtree.setdefault(component, {})
            assert isinstance(next_level, dict)
            subtree = next_level

        subtree[path[-1]] = [
            CatalogEntry(
                {
                    "name": e.name,
                    "agents": e.agents,
                    "title": e.title,
                }
            )
            for e in entries
        ]

    for p in only_path:
        try:
            if not isinstance(next_level := tree[p], dict):
                break
            tree = next_level
        except KeyError:
            break

    return tree


class ModeCheckManPage(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "check_manpage"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["check_plugins"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeCheckPluginTopic

    def breadcrumb(self) -> Breadcrumb:
        # To be able to calculate the breadcrumb with ModeCheckPluginTopic as parent, we need to
        # ensure that the topic is available.
        with request.stashed_vars():
            request.set_var("topic", "/".join(self._manpage.catalog))
            return super().breadcrumb()

    @staticmethod
    def _get_full_ruleset_name(ruleset_name: str | None) -> str | None:
        if ruleset_name is None:
            return None

        check_group_param = RuleGroup.CheckgroupParameters(ruleset_name)
        if check_group_param in rulespec_registry:
            return check_group_param

        static_check = RuleGroup.StaticChecks(ruleset_name)
        if static_check in rulespec_registry:
            return static_check

        return None

    def _from_vars(self) -> None:
        self._check_plugin_name = request.get_ascii_input_mandatory("check_type", "")

        check_builtins = ["check-mk", "check-mk-inventory"]
        if (
            not re.match("^[a-zA-Z0-9_.]+$", self._check_plugin_name)
            and self._check_plugin_name not in check_builtins
        ):
            raise MKUserError("check_type", _("Invalid check type"))

        man_page_paths = man_pages.make_man_page_path_map(
            discover_families(raise_errors=False), PluginGroup.CHECKMAN.value
        )

        try:
            man_page_path = man_page_paths[self._check_plugin_name]
        except KeyError:
            raise MKUserError(None, _("There is no manpage for this check."))

        self._manpage = man_pages.parse_man_page(self._check_plugin_name, man_page_path)
        self._check_default_parameters: object = None

        checks = get_check_information(debug=active_config.debug).plugin_infos
        if (check_info := checks.get(self._check_plugin_name)) is not None:
            self._check_type = "check_mk"
            self._service_description = check_info["service_description"]
            ruleset_name = check_info.get("check_ruleset_name")
            self._ruleset: str | None = self._get_full_ruleset_name(ruleset_name)
            self._check_default_parameters = check_info.get("check_default_parameters")

        elif self._check_plugin_name in check_builtins:
            self._check_type = "check_mk"
            self._service_description = (
                "Check_MK" if self._check_plugin_name == "check-mk" else "Check_MK Discovery"
            )
            self._ruleset = None
        elif self._check_plugin_name.startswith("check_"):  # Assume active check
            self._check_type = "active"
            self._service_description = "Active check"  # unused
            self._ruleset = RuleGroup.ActiveChecks(self._check_plugin_name[6:])
        else:
            raise MKUserError(
                None,
                _("Could not detect type of manpage: %s. Maybe the check is missing ")
                % self._check_plugin_name,
            )

    def title(self) -> str:
        return self._manpage.title

    # TODO
    # We could simply detect on how many hosts and services this plug-in
    # is currently in use (Livestatus query) and display this information
    # together with a link for searching. Then we can remove the dumb context
    # button, that will always be shown - even if the plug-in is not in use.
    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        if self._check_plugin_name.startswith("check_"):
            command = "check_mk_active-" + self._check_plugin_name[6:]
        else:
            command = "check_mk-" + self._check_plugin_name
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

    def page(self) -> None:
        html.open_table(class_=["data", "headerleft"])

        html.open_tr()
        html.th(_("Title"))
        html.open_td()
        html.b(self._manpage.title)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.th(_("Name of plug-in"))
        html.open_td()
        html.tt(self._check_plugin_name)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.th(_("Description"))
        html.td(self._manpage_text(self._manpage.description))
        html.close_tr()

        if self._check_type == "check_mk":
            html.open_tr()
            html.th(_("Service name"))
            html.td(HTML.without_escaping(self._service_description.replace("%s", "&#9744;")))
            html.close_tr()

            if discovery := self._manpage.discovery:
                html.open_tr()
                html.th(_("Discovery"))
                html.td(self._manpage_text(discovery))
                html.close_tr()

            if self._manpage.cluster:
                html.open_tr()
                html.th(_("Cluster behaviour"))
                html.td(self._manpage_text(self._manpage.cluster))
                html.close_tr()

        if self._ruleset:
            self._show_ruleset(self._ruleset)
            self._show_defaults(self._ruleset, self._check_default_parameters)

        html.close_table()

    def _manpage_text(self, text: str) -> str:
        html_code = re.sub("{(.*?)}", "<tt>\\1</tt>", text)
        html_code = re.sub("\n\n+", "<p>", html_code)
        return html_code

    def _show_ruleset(self, varname: str) -> None:
        if varname not in rulespec_registry:
            return

        rulespec = rulespec_registry[varname]
        url = makeuri_contextless(request, [("mode", "edit_ruleset"), ("varname", varname)])
        html.open_tr()
        html.th(_("Parameter rule set"))
        html.open_td()
        html.icon_button(url, _("Edit parameter rule set for this check type"), "check_parameters")
        html.a(rulespec.title, url)
        html.close_td()
        html.close_tr()
        html.open_tr()
        html.th(_("Example for parameters"))
        html.open_td()
        vs = rulespec.valuespec
        vs.render_input("dummy", vs.default_value())
        html.close_td()
        html.close_tr()

    def _show_defaults(self, varname: str, params: object) -> None:
        if not params or varname not in rulespec_registry:
            return

        rulespec = rulespec_registry[varname]
        try:
            rulespec.valuespec.validate_datatype(params, "")
            rulespec.valuespec.validate_value(params, "")
            paramtext = rulespec.valuespec.value_to_html(params)
        except Exception:
            # This should not happen, we have tests for that.
            # If it does happen, do not fail here.
            return

        html.open_tr()
        html.th(_("Default parameters"))
        html.open_td()
        html.write_html(HTML.with_escaping(paramtext))
        html.close_td()
        html.close_tr()
