#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import abc
from typing import Dict, Iterator

import cmk.utils.paths

import cmk.gui.watolib as watolib
import cmk.gui.userdb as userdb
import cmk.gui.escaping as escaping
from cmk.gui.table import table_element
import cmk.gui.forms as forms
from cmk.gui.htmllib import HTML
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    Dictionary,
    CascadingDropdown,
    ListChoice,
    ListOfStrings,
    ListOf,
    TextAscii,
)
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    make_simple_link,
    make_simple_form_page_menu,
)

from cmk.gui.groups import (
    load_host_group_information,
    load_service_group_information,
)
from cmk.gui.watolib.groups import (
    load_contact_group_information,
    GroupType,
)

from cmk.gui.plugins.wato import ActionResult
from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
    wato_confirm,
)


class ModeGroups(WatoMode, metaclass=abc.ABCMeta):
    @abc.abstractproperty
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
        super(ModeGroups, self).__init__()
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
        )

    def action(self) -> ActionResult:
        if html.request.var('_delete'):
            delname = html.request.get_ascii_input_mandatory("_delete")
            usages = watolib.find_usages_of_group(delname, self.type_name)

            if usages:
                message = "<b>%s</b><br>%s:<ul>" % \
                            (_("You cannot delete this %s group.") % self.type_name,
                             _("It is still in use by"))
                for title, link in usages:
                    message += '<li><a href="%s">%s</a></li>\n' % (link, title)
                message += "</ul>"
                raise MKUserError(None, message)

            confirm_txt = _('Do you really want to delete the %s group "%s"?') % (self.type_name,
                                                                                  delname)

            c = wato_confirm(_("Confirm deletion of group \"%s\"") % delname, confirm_txt)
            if c:
                watolib.delete_group(delname, self.type_name)
                self._groups = self._load_groups()
            elif c is False:
                return ""

        return None

    def _page_no_groups(self) -> None:
        html.div(_("No groups are defined yet."), class_="info")

    def _collect_additional_data(self):
        pass

    def _show_row_cells(self, table, name, group):
        table.cell(_("Actions"), css="buttons")
        edit_url = watolib.folder_preserving_link([("mode", "edit_%s_group" % self.type_name),
                                                   ("edit", name)])
        delete_url = html.makeactionuri([("_delete", name)])
        clone_url = watolib.folder_preserving_link([("mode", "edit_%s_group" % self.type_name),
                                                    ("clone", name)])
        html.icon_button(edit_url, _("Properties"), "edit")
        html.icon_button(clone_url, _("Create a copy of this group"), "clone")
        html.icon_button(delete_url, _("Delete"), "delete")

        table.cell(_("Name"), escaping.escape_attribute(name))
        table.cell(_("Alias"), escaping.escape_attribute(group['alias']))

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
    @abc.abstractproperty
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
        self._name = html.request.get_ascii_input("edit")  # missing -> new group
        self._new = self._name is None

        if self._new:
            clone_group = html.request.get_ascii_input("clone")
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
        if not html.check_transaction():
            return "%s_groups" % self.type_name

        alias = html.request.get_unicode_input_mandatory("alias").strip()
        self.group = {"alias": alias}

        self._determine_additional_group_data()

        if self._new:
            self._name = html.request.get_ascii_input_mandatory("name").strip()
            watolib.add_group(self._name, self.type_name, self.group)
        else:
            watolib.edit_group(self._name, self.type_name, self.group)

        return "%s_groups" % self.type_name

    def _show_extra_page_elements(self):
        pass

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(breadcrumb, form_name="group", button_name="save")

    def page(self) -> None:
        html.begin_form("group")
        forms.header(_("Properties"))
        forms.section(_("Name"), simple=not self._new)
        html.help(
            _("The name of the group is used as an internal key. It cannot be "
              "changed later. It is also visible in the status GUI."))
        if self._new:
            html.text_input("name")
            html.set_focus("name")
        else:
            html.write_text(self._name)
            html.set_focus("alias")

        forms.section(_("Alias"))
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
        super(ModeContactgroups, self)._show_row_cells(table, name, group)
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
        super(ModeEditContactgroup, self)._determine_additional_group_data()

        permitted_inventory_paths = self._vs_inventory_paths().from_html_vars('inventory_paths')
        self._vs_inventory_paths().validate_value(permitted_inventory_paths, 'inventory_paths')
        if permitted_inventory_paths:
            self.group['inventory_paths'] = permitted_inventory_paths

        permitted_maps = self._vs_nagvis_maps().from_html_vars('nagvis_maps')
        self._vs_nagvis_maps().validate_value(permitted_maps, 'nagvis_maps')
        if permitted_maps:
            self.group["nagvis_maps"] = permitted_maps

    def _show_extra_page_elements(self):
        super(ModeEditContactgroup, self)._show_extra_page_elements()

        forms.header(_("Permissions"))
        forms.section(_("Permitted HW/SW inventory paths"))
        self._vs_inventory_paths().render_input('inventory_paths',
                                                self.group.get('inventory_paths'))

        if self._get_nagvis_maps():
            forms.section(_("Access to NagVis Maps"))
            html.help(_("Configure access permissions to NagVis maps."))
            self._vs_nagvis_maps().render_input('nagvis_maps', self.group.get('nagvis_maps', []))

    def _vs_inventory_paths(self):
        return CascadingDropdown(
            choices=[
                ("allow_all", _("Allowed to see the whole tree")),
                ("forbid_all", _("Forbid to see the whole tree")),
                ("paths", _("Allowed to see the following entries"),
                 ListOf(
                     Dictionary(
                         elements=[("path", TextAscii(
                             title=_("Path"),
                             size=60,
                             allow_empty=False,
                         )),
                                   ("attributes",
                                    ListOfStrings(
                                        orientation="horizontal",
                                        title=_("Attributes"),
                                        size=15,
                                        allow_empty=True,
                                    ))],
                         optional_keys=["attributes"],
                     ),
                     allow_empty=False,
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
