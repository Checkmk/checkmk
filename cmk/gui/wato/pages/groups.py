#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Collection, Iterator, Sequence

from cmk.ccc import version
from cmk.ccc.user import UserId
from cmk.ccc.version import edition_supports_nagvis

import cmk.utils.paths

from cmk.gui import forms, userdb
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.groups import GroupName, GroupSpec, GroupType
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
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
from cmk.gui.table import Table, table_element
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeactionuri, makeuri
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    ListChoice,
    ListChoiceChoice,
    ListOf,
    ListOfStrings,
)
from cmk.gui.watolib import groups
from cmk.gui.watolib.groups_io import (
    load_contact_group_information,
    load_host_group_information,
    load_service_group_information,
)
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeHostgroups)
    mode_registry.register(ModeServicegroups)
    mode_registry.register(ModeContactgroups)
    mode_registry.register(ModeEditServicegroup)
    mode_registry.register(ModeEditHostgroup)
    mode_registry.register(ModeEditContactgroup)


class ModeGroups(WatoMode, abc.ABC):
    @property
    @abc.abstractmethod
    def type_name(self) -> GroupType:
        raise NotImplementedError()

    @abc.abstractmethod
    def _load_groups(self) -> dict[GroupName, GroupSpec]:
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
                                        folder_preserving_link(
                                            [("mode", "edit_%s_group" % self.type_name)]
                                        )
                                    ),
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
            request.del_var("_transid")
            return redirect(makeuri(request=request, addvars=list(request.itervars())))

        if request.var("_delete"):
            delname = request.get_ascii_input_mandatory("_delete")
            usages = groups.find_usages_of_group(delname, self.type_name)

            if usages:
                message = "<b>{}</b><br>{}:<ul>".format(
                    _("You cannot delete this %s group.") % self.type_name,
                    _("It is still in use by"),
                )
                for title, link in usages:
                    message += f'<li><a href="{link}">{title}</a></li>\n'
                message += "</ul>"
                raise MKUserError(None, message)

            groups.delete_group(
                delname, self.type_name, pprint_value=active_config.wato_pprint_config
            )
            self._groups = self._load_groups()

        if request.var("mode") == "edit_host_group":
            return redirect(mode_url("%s_groups" % self.type_name))

        request.del_var("_transid")
        return redirect(makeuri(request=request, addvars=list(request.itervars())))

    def _page_no_groups(self) -> None:
        html.div(_("No groups are defined yet."), class_="info")

    def _collect_additional_data(self) -> None:
        pass

    def _show_row_cells(self, nr: int, table: Table, name: GroupName, group: GroupSpec) -> None:
        table.cell("#", css=["narrow nowrap"])
        html.write_text_permissive(nr)

        table.cell(_("Actions"), css=["buttons"])
        edit_url = folder_preserving_link(
            [("mode", "edit_%s_group" % self.type_name), ("edit", name)]
        )
        delete_url = make_confirm_delete_link(
            url=makeactionuri(request, transactions, [("_delete", name)]),
            title=_("Delete %s group #%d") % (self.type_name, nr),
            suffix=group["alias"],
            message=_("Name: %s") % name,
        )
        clone_url = folder_preserving_link(
            [("mode", "edit_%s_group" % self.type_name), ("clone", name)]
        )
        html.icon_button(edit_url, _("Properties"), "edit")
        html.icon_button(clone_url, _("Create a copy of this group"), "clone")
        html.icon_button(delete_url, _("Delete"), "delete")

        table.cell(_("Name"), name)
        table.cell(_("Alias"), group["alias"])

    def page(self) -> None:
        if not self._groups:
            self._page_no_groups()
            return

        self._collect_additional_data()

        with table_element(self.type_name + "groups") as table:
            for nr, (name, group) in enumerate(
                sorted(self._groups.items(), key=lambda x: x[1]["alias"])
            ):
                table.row()
                self._show_row_cells(nr, table, name, group)


class ABCModeEditGroup(WatoMode, abc.ABC):
    @property
    @abc.abstractmethod
    def type_name(self) -> GroupType:
        raise NotImplementedError()

    @abc.abstractmethod
    def _load_groups(self) -> dict[GroupName, GroupSpec]:
        raise NotImplementedError()

    def __init__(self) -> None:
        self._name: GroupName | None = None
        self._new = False
        self.group: GroupSpec = {}
        self._groups: dict[GroupName, GroupSpec] = self._load_groups()

        super().__init__()

    def _from_vars(self) -> None:
        edit_group = request.get_ascii_input("edit")  # missing -> new group
        self._name = GroupName(edit_group) if edit_group else None
        self._new = self._name is None

        if self._new:
            clone_group = request.get_ascii_input("clone")
            if clone_group:
                self._name = GroupName(clone_group)
                self.group = self._get_group(self._name)
            else:
                self.group = {}
        else:
            assert self._name is not None
            self.group = self._get_group(self._name)

        self.group.setdefault("alias", self._name)

    def _get_group(self, group_name: GroupName) -> GroupSpec:
        try:
            return self._groups[group_name]
        except KeyError:
            raise MKUserError(None, _("This group does not exist."))

    def _determine_additional_group_data(self) -> None:
        pass

    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return redirect(mode_url("%s_groups" % self.type_name))

        alias = request.get_str_input_mandatory("alias").strip()
        self.group = {"alias": alias}

        self._determine_additional_group_data()

        if self._new:
            self._name = request.get_ascii_input_mandatory("name").strip()
            groups.add_group(
                self._name,
                self.type_name,
                self.group,
                pprint_value=active_config.wato_pprint_config,
            )
        else:
            assert self._name is not None
            groups.edit_group(
                self._name,
                self.type_name,
                self.group,
                pprint_value=active_config.wato_pprint_config,
            )

        return redirect(mode_url("%s_groups" % self.type_name))

    def _show_extra_page_elements(self) -> None:
        pass

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Group"), breadcrumb, form_name="group", button_name="_save"
        )

    def page(self) -> None:
        with html.form_context("group", method="POST"):
            forms.header(_("Properties"))
            forms.section(_("Name"), simple=not self._new, is_required=True)
            html.help(
                _(
                    "The name of the group is used as an internal key. It cannot be "
                    "changed later. It is also visible in the status GUI."
                )
            )
            if self._new:
                html.text_input("name", size=50)
                html.set_focus("name")
            else:
                html.write_text_permissive(self._name)
                html.set_focus("alias")

            forms.section(_("Alias"), is_required=True)
            html.help(_("An alias or description of this group."))
            html.text_input("alias", self.group["alias"], size=50)

            self._show_extra_page_elements()

            forms.end()
            html.hidden_fields()


class ModeHostgroups(ModeGroups):
    @property
    def type_name(self) -> GroupType:
        return "host"

    @classmethod
    def name(cls) -> str:
        return "host_groups"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["groups"]

    def _load_groups(self) -> dict[GroupName, GroupSpec]:
        return load_host_group_information()

    def title(self) -> str:
        return _("Host groups")

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Service groups"),
            icon_name="servicegroups",
            item=make_simple_link(folder_preserving_link([("mode", "service_groups")])),
        )

    def _rules_url(self) -> str:
        return folder_preserving_link([("mode", "edit_ruleset"), ("varname", "host_groups")])


class ModeServicegroups(ModeGroups):
    @property
    def type_name(self) -> GroupType:
        return "service"

    @classmethod
    def name(cls) -> str:
        return "service_groups"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["groups"]

    def _load_groups(self) -> dict[GroupName, GroupSpec]:
        return load_service_group_information()

    def title(self) -> str:
        return _("Service groups")

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Host groups"),
            icon_name="hostgroups",
            item=make_simple_link(folder_preserving_link([("mode", "host_groups")])),
        )

    def _rules_url(self) -> str:
        return folder_preserving_link([("mode", "edit_ruleset"), ("varname", "service_groups")])


class ModeContactgroups(ModeGroups):
    @property
    def type_name(self) -> GroupType:
        return "contact"

    @classmethod
    def name(cls) -> str:
        return "contact_groups"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["users"]

    def _load_groups(self) -> dict[GroupName, GroupSpec]:
        return load_contact_group_information()

    def title(self) -> str:
        # TODO: Move to constructor (incl. _collect_additional_data)
        self._members: dict[GroupName, list[tuple[UserId, str]]] = {}
        return _("Contact groups")

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Users"),
            icon_name="users",
            item=make_simple_link(folder_preserving_link([("mode", "users")])),
        )

    def _rules_url(self) -> str:
        return folder_preserving_link(
            [("mode", "rule_search"), ("filled_in", "search"), ("search", "contactgroups")]
        )

    def _collect_additional_data(self) -> None:
        users = userdb.load_users()
        self._members = {}
        for userid, user in users.items():
            cgs = user.get("contactgroups", [])
            for cg in cgs:
                self._members.setdefault(cg, []).append((userid, user.get("alias", userid)))

    def _show_row_cells(self, nr: int, table: Table, name: GroupName, group: GroupSpec) -> None:
        super()._show_row_cells(nr, table, name, group)
        table.cell(_("Members"))
        html.write_html(
            HTML.without_escaping(", ").join(
                [
                    HTMLWriter.render_a(
                        alias,
                        href=folder_preserving_link([("mode", "edit_user"), ("edit", userid)]),
                    )
                    for userid, alias in self._members.get(name, [])
                ]
            )
        )


class ModeEditServicegroup(ABCModeEditGroup):
    @property
    def type_name(self) -> GroupType:
        return "service"

    @classmethod
    def name(cls) -> str:
        return "edit_service_group"

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeServicegroups

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["groups"]

    def _load_groups(self) -> dict[GroupName, GroupSpec]:
        return load_service_group_information()

    def title(self) -> str:
        if self._new:
            return _("Add service group")
        return _("Edit service group")


class ModeEditHostgroup(ABCModeEditGroup):
    @property
    def type_name(self) -> GroupType:
        return "host"

    @classmethod
    def name(cls) -> str:
        return "edit_host_group"

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeHostgroups

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["groups"]

    def _load_groups(self) -> dict[GroupName, GroupSpec]:
        return load_host_group_information()

    def title(self) -> str:
        if self._new:
            return _("Add host group")
        return _("Edit host group")


class ModeEditContactgroup(ABCModeEditGroup):
    @property
    def type_name(self) -> GroupType:
        return "contact"

    @classmethod
    def name(cls) -> str:
        return "edit_contact_group"

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeContactgroups

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["users"]

    def _load_groups(self) -> dict[GroupName, GroupSpec]:
        return load_contact_group_information()

    def title(self) -> str:
        if self._new:
            return _("Add contact group")
        return _("Edit contact group")

    def _determine_additional_group_data(self) -> None:
        super()._determine_additional_group_data()

        permitted_inventory_paths = self._vs_inventory_paths_and_keys().from_html_vars(
            "inventory_paths"
        )
        self._vs_inventory_paths_and_keys().validate_value(
            permitted_inventory_paths, "inventory_paths"
        )
        if permitted_inventory_paths:
            self.group["inventory_paths"] = permitted_inventory_paths

        if edition_supports_nagvis(version.edition(cmk.utils.paths.omd_root)):
            permitted_maps = self._vs_nagvis_maps().from_html_vars("nagvis_maps")
            self._vs_nagvis_maps().validate_value(permitted_maps, "nagvis_maps")
            if permitted_maps:
                self.group["nagvis_maps"] = permitted_maps

    def _show_extra_page_elements(self) -> None:
        super()._show_extra_page_elements()

        forms.header(_("Permissions"))
        forms.section(_("Permitted HW/SW Inventory paths"))
        self._vs_inventory_paths_and_keys().render_input(
            "inventory_paths", self.group.get("inventory_paths")
        )

        if (
            edition_supports_nagvis(version.edition(cmk.utils.paths.omd_root))
            and self._get_nagvis_maps()
        ):
            forms.section(_("Access to NagVis Maps"))
            html.help(_("Configure access permissions to NagVis maps."))
            self._vs_nagvis_maps().render_input("nagvis_maps", self.group.get("nagvis_maps", []))

    def _vs_inventory_paths_and_keys(self) -> CascadingDropdown:
        def vs_choices(title):
            return CascadingDropdown(
                title=title,
                choices=[
                    ("nothing", _("Restrict all")),
                    (
                        "choices",
                        _("Restrict the following keys"),
                        ListOfStrings(
                            orientation="horizontal",
                            size=15,
                            allow_empty=True,
                        ),
                    ),
                ],
                default_value="nothing",
            )

        return CascadingDropdown(
            choices=[
                ("allow_all", _("Allowed to see the whole tree")),
                ("forbid_all", _("Forbid to see the whole tree")),
                (
                    "paths",
                    _("Allowed to see parts of the tree"),
                    ListOf(
                        valuespec=Dictionary(
                            elements=[
                                vs_element_inventory_visible_raw_path(),
                                ("attributes", vs_choices(_("Restrict single values"))),
                                ("columns", vs_choices(_("Restrict table columns"))),
                                ("nodes", vs_choices(_("Restrict subcategories"))),
                            ],
                            optional_keys=["attributes", "columns", "nodes"],
                        ),
                        help=vs_inventory_path_or_keys_help()
                        + _(
                            "<br>If single values, table columns or subcategories are not"
                            " restricted, then all entries are added respectively."
                        ),
                    ),
                ),
            ],
            default_value="allow_all",
        )

    def _vs_nagvis_maps(self) -> ListChoice:
        return ListChoice(
            title=_("NagVis Maps"),
            choices=self._get_nagvis_maps,
            toggle_all=True,
        )

    def _get_nagvis_maps(self) -> Sequence[ListChoiceChoice]:
        # Find all NagVis maps in the local installation to register permissions
        # for each map. When no maps can be found skip this problem silently.
        # This only works in OMD environments.
        maps = []
        nagvis_maps_path = cmk.utils.paths.omd_root / "etc/nagvis/maps"
        for f in nagvis_maps_path.iterdir():
            if f.name[0] != "." and f.name.endswith(".cfg"):
                maps.append((f.name[:-4], f.name[:-4]))
        return sorted(maps)
