#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import os
from typing import Dict, Iterator

import cmk.utils.paths

import cmk.gui.forms as forms
import cmk.gui.userdb as userdb
import cmk.gui.watolib as watolib
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html, request, transactions
from cmk.gui.groups import load_host_group_information, load_service_group_information
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.inventory import vs_element_inventory_visible_raw_path, vs_inventory_path_or_keys_help
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.plugins.wato import (
    ActionResult,
    make_confirm_link,
    mode_registry,
    mode_url,
    redirect,
    WatoMode,
)
from cmk.gui.table import table_element
from cmk.gui.utils.urls import makeactionuri
from cmk.gui.valuespec import CascadingDropdown, Dictionary, ListChoice, ListOf, ListOfStrings
from cmk.gui.watolib.groups import GroupType, load_contact_group_information


class ModeGroups(WatoMode, metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def type_name(self) -> GroupType:
        raise NotImplementedError()

    @abc.abstractmethod
    def _load_groups(self) -> Dict:
        raise NotImplementedError()

    @abc.abstractmethod
    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        raise NotImplementedError()

    @abc.abstractmethod
    def _rules_url(self) -> str:
        raise NotImplementedError()

    def __init__(self) -> None:
        super().__init__()
        self._groups = self._load_groups()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="groups",
                    title=self.title(),
                    topics=[
                        PageMenuTopic(
                            title=_("Add"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add group"),
                                    icon_name="new",
                                    item=make_simple_link(
                                        watolib.folder_preserving_link([
                                            ("mode", "edit_%s_group" % self.type_name)
                                        ])),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("Assign to group"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Rules"),
                                    icon_name="rulesets",
                                    item=make_simple_link(self._rules_url()),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(self._page_menu_entries_related()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(mode_url("%s_groups" % self.type_name))

        if request.var('_delete'):
            delname = request.get_ascii_input_mandatory("_delete")
            usages = watolib.find_usages_of_group(delname, self.type_name)

            if usages:
                message = "<b>%s</b><br>%s:<ul>" % \
                            (_("You cannot delete this %s group.") % self.type_name,
                             _("It is still in use by"))
                for title, link in usages:
                    message += '<li><a href="%s">%s</a></li>\n' % (link, title)
                message += "</ul>"
                raise MKUserError(None, message)

            watolib.delete_group(delname, self.type_name)
            self._groups = self._load_groups()

        return redirect(mode_url("%s_groups" % self.type_name))

    def _page_no_groups(self) -> None:
        html.div(_("No groups are defined yet."), class_="info")

    def _collect_additional_data(self):
        pass

    def _show_row_cells(self, table, name, group):
        table.cell(_("Actions"), css="buttons")
        edit_url = watolib.folder_preserving_link([("mode", "edit_%s_group" % self.type_name),
                                                   ("edit", name)])
        delete_url = make_confirm_link(
            url=makeactionuri(request, transactions, [("_delete", name)]),
            message=_('Do you really want to delete the %s group "%s"?') % (self.type_name, name))
        clone_url = watolib.folder_preserving_link([("mode", "edit_%s_group" % self.type_name),
                                                    ("clone", name)])
        html.icon_button(edit_url, _("Properties"), "edit")
        html.icon_button(clone_url, _("Create a copy of this group"), "clone")
        html.icon_button(delete_url, _("Delete"), "delete")

        table.cell(_("Name"), name)
        table.cell(_("Alias"), group['alias'])

    def page(self) -> None:
        if not self._groups:
            self._page_no_groups()
            return

        self._collect_additional_data()

        with table_element(self.type_name + "groups") as table:
            for name, group in sorted(self._groups.items(), key=lambda x: x[1]['alias']):
                table.row()
                self._show_row_cells(table, name, group)


class ABCModeEditGroup(WatoMode, metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def type_name(self) -> GroupType:
        raise NotImplementedError()

    @abc.abstractmethod
    def _load_groups(self) -> Dict:
        raise NotImplementedError()

    def __init__(self):
        self._name = None
        self._new = False
        self.group = {}
        self._groups = self._load_groups()

        super().__init__()

    def _from_vars(self) -> None:
        self._name = request.get_ascii_input("edit")  # missing -> new group
        self._new = self._name is None

        if self._new:
            clone_group = request.get_ascii_input("clone")
            if clone_group:
                self._name = clone_group

                self.group = self._get_group(self._name)
            else:
                self.group = {}
        else:
            self.group = self._get_group(self._name)

        self.group.setdefault("alias", self._name)

    def _get_group(self, group_name):
        try:
            return self._groups[self._name]
        except KeyError:
            raise MKUserError(None, _("This group does not exist."))

    def _determine_additional_group_data(self) -> None:
        pass

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(mode_url("%s_groups" % self.type_name))

        alias = request.get_unicode_input_mandatory("alias").strip()
        self.group = {"alias": alias}

        self._determine_additional_group_data()

        if self._new:
            self._name = request.get_ascii_input_mandatory("name").strip()
            watolib.add_group(self._name, self.type_name, self.group)
        else:
            watolib.edit_group(self._name, self.type_name, self.group)

        return redirect(mode_url("%s_groups" % self.type_name))

    def _show_extra_page_elements(self):
        pass

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(_("Group"),
                                          breadcrumb,
                                          form_name="group",
                                          button_name="save")

    def page(self) -> None:
        html.begin_form("group")
        forms.header(_("Properties"))
        forms.section(_("Name"), simple=not self._new, is_required=True)
        html.help(
            _("The name of the group is used as an internal key. It cannot be "
              "changed later. It is also visible in the status GUI."))
        if self._new:
            html.text_input("name")
            html.set_focus("name")
        else:
            html.write_text(self._name)
            html.set_focus("alias")

        forms.section(_("Alias"), is_required=True)
        html.help(_("An alias or description of this group."))
        html.text_input("alias", self.group["alias"])

        self._show_extra_page_elements()

        forms.end()
        html.hidden_fields()
        html.end_form()


@mode_registry.register
class ModeHostgroups(ModeGroups):
    @property
    def type_name(self):
        return "host"

    @classmethod
    def name(cls):
        return "host_groups"

    @classmethod
    def permissions(cls):
        return ["groups"]

    def _load_groups(self):
        return load_host_group_information()

    def title(self):
        return _("Host groups")

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Service groups"),
            icon_name="servicegroups",
            item=make_simple_link(watolib.folder_preserving_link([("mode", "service_groups")])),
        )

    def _rules_url(self) -> str:
        return watolib.folder_preserving_link([("mode", "edit_ruleset"),
                                               ("varname", "host_groups")])


@mode_registry.register
class ModeServicegroups(ModeGroups):
    @property
    def type_name(self):
        return "service"

    @classmethod
    def name(cls):
        return "service_groups"

    @classmethod
    def permissions(cls):
        return ["groups"]

    def _load_groups(self):
        return load_service_group_information()

    def title(self):
        return _("Service groups")

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Host groups"),
            icon_name="hostgroups",
            item=make_simple_link(watolib.folder_preserving_link([("mode", "host_groups")])),
        )

    def _rules_url(self) -> str:
        return watolib.folder_preserving_link([("mode", "edit_ruleset"),
                                               ("varname", "service_groups")])


@mode_registry.register
class ModeContactgroups(ModeGroups):
    @property
    def type_name(self):
        return "contact"

    @classmethod
    def name(cls):
        return "contact_groups"

    @classmethod
    def permissions(cls):
        return ["users"]

    def _load_groups(self):
        return load_contact_group_information()

    def title(self):
        self._members = {}
        return _("Contact groups")

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Users"),
            icon_name="users",
            item=make_simple_link(watolib.folder_preserving_link([("mode", "users")])),
        )

    def _rules_url(self) -> str:
        return watolib.folder_preserving_link([("mode", "rule_search"), ("filled_in", "search"),
                                               ("search", "contactgroups")])

    def _collect_additional_data(self):
        users = userdb.load_users()
        self._members = {}
        for userid, user in users.items():
            cgs = user.get("contactgroups", [])
            for cg in cgs:
                self._members.setdefault(cg, []).append((userid, user.get('alias', userid)))

    def _show_row_cells(self, table, name, group):
        super()._show_row_cells(table, name, group)
        table.cell(_("Members"))
        html.write_html(
            HTML(", ").join([
                html.render_a(alias,
                              href=watolib.folder_preserving_link([("mode", "edit_user"),
                                                                   ("edit", userid)]))
                for userid, alias in self._members.get(name, [])
            ]))


@mode_registry.register
class ModeEditServicegroup(ABCModeEditGroup):
    @property
    def type_name(self):
        return "service"

    @classmethod
    def name(cls):
        return "edit_service_group"

    @classmethod
    def parent_mode(cls):
        return ModeServicegroups

    @classmethod
    def permissions(cls):
        return ["groups"]

    def _load_groups(self):
        return load_service_group_information()

    def title(self):
        if self._new:
            return _("Add service group")
        return _("Edit service group")


@mode_registry.register
class ModeEditHostgroup(ABCModeEditGroup):
    @property
    def type_name(self):
        return "host"

    @classmethod
    def name(cls):
        return "edit_host_group"

    @classmethod
    def parent_mode(cls):
        return ModeHostgroups

    @classmethod
    def permissions(cls):
        return ["groups"]

    def _load_groups(self):
        return load_host_group_information()

    def title(self):
        if self._new:
            return _("Add host group")
        return _("Edit host group")


@mode_registry.register
class ModeEditContactgroup(ABCModeEditGroup):
    @property
    def type_name(self):
        return "contact"

    @classmethod
    def name(cls):
        return "edit_contact_group"

    @classmethod
    def parent_mode(cls):
        return ModeContactgroups

    @classmethod
    def permissions(cls):
        return ["users"]

    def _load_groups(self):
        return load_contact_group_information()

    def title(self):
        if self._new:
            return _("Add contact group")
        return _("Edit contact group")

    def _determine_additional_group_data(self):
        super()._determine_additional_group_data()

        permitted_inventory_paths = self._vs_inventory_paths_and_keys().from_html_vars(
            'inventory_paths')
        self._vs_inventory_paths_and_keys().validate_value(permitted_inventory_paths,
                                                           'inventory_paths')
        if permitted_inventory_paths:
            self.group['inventory_paths'] = permitted_inventory_paths

        permitted_maps = self._vs_nagvis_maps().from_html_vars('nagvis_maps')
        self._vs_nagvis_maps().validate_value(permitted_maps, 'nagvis_maps')
        if permitted_maps:
            self.group["nagvis_maps"] = permitted_maps

    def _show_extra_page_elements(self):
        super()._show_extra_page_elements()

        forms.header(_("Permissions"))
        forms.section(_("Permitted HW/SW inventory paths"))
        self._vs_inventory_paths_and_keys().render_input('inventory_paths',
                                                         self.group.get('inventory_paths'))

        if self._get_nagvis_maps():
            forms.section(_("Access to NagVis Maps"))
            html.help(_("Configure access permissions to NagVis maps."))
            self._vs_nagvis_maps().render_input('nagvis_maps', self.group.get('nagvis_maps', []))

    def _vs_inventory_paths_and_keys(self):
        def vs_choices(title):
            return CascadingDropdown(
                title=title,
                choices=[
                    ("nothing", _("Restrict all")),
                    ("choices", _("Restrict the following keys"),
                     ListOfStrings(
                         orientation="horizontal",
                         size=15,
                         allow_empty=True,
                     )),
                ],
                default_value="nothing",
            )

        return CascadingDropdown(
            choices=[
                ("allow_all", _("Allowed to see the whole tree")),
                ("forbid_all", _("Forbid to see the whole tree")),
                ("paths", _("Allowed to see parts of the tree"),
                 ListOf(
                     Dictionary(
                         elements=[
                             vs_element_inventory_visible_raw_path(),
                             ("attributes", vs_choices(_("Restrict single values"))),
                             ("columns", vs_choices(_("Restrict table columns"))),
                             ("nodes", vs_choices(_("Restrict subcategories"))),
                         ],
                         optional_keys=["attributes", "columns", "nodes"],
                     ),
                     help=vs_inventory_path_or_keys_help() +
                     _("<br>If single values, table columns or subcategories are not"
                       " restricted, then all entries are added respectively."),
                 )),
            ],
            default_value="allow_all",
        )

    def _vs_nagvis_maps(self):
        return ListChoice(
            title=_('NagVis Maps'),
            choices=self._get_nagvis_maps,
            toggle_all=True,
        )

    def _get_nagvis_maps(self):
        # Find all NagVis maps in the local installation to register permissions
        # for each map. When no maps can be found skip this problem silently.
        # This only works in OMD environments.
        maps = []
        nagvis_maps_path = cmk.utils.paths.omd_root + '/etc/nagvis/maps'
        for f in os.listdir(nagvis_maps_path):
            if f[0] != '.' and f.endswith('.cfg'):
                maps.append((f[:-4], f[:-4]))
        return sorted(maps)
