#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import copy
from collections.abc import Collection

from cmk.utils.password_store import Password

from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.quick_setup.html import (
    quick_setup_duplication_warning,
    quick_setup_locked_warning,
    quick_setup_render_link,
    quick_setup_source_cell,
)
from cmk.gui.table import Table
from cmk.gui.type_defs import PermissionName
from cmk.gui.valuespec import (
    Alternative,
    DictionaryEntry,
    DropdownChoice,
    DualListChoice,
    FixedValue,
    ValueSpec,
)
from cmk.gui.valuespec import Password as PasswordValuespec
from cmk.gui.wato.pages._simple_modes import (
    convert_dict_elements_vs2fs,
    SimpleEditMode,
    SimpleListMode,
    SimpleModeType,
)
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.gui.watolib.configuration_bundle_store import is_locked_by_quick_setup
from cmk.gui.watolib.groups_io import load_contact_group_information
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.gui.watolib.password_store import PasswordStore
from cmk.gui.watolib.passwords import sorted_contact_group_choices

from cmk.rulesets.v1.form_specs import DictElement


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModePasswords)
    mode_registry.register(ModeEditPassword)


class PasswordStoreModeType(SimpleModeType[Password]):
    def type_name(self) -> str:
        return "password"

    def name_singular(self) -> str:
        return _("password")

    def is_site_specific(self) -> bool:
        return False

    def can_be_disabled(self) -> bool:
        return False

    def affected_config_domains(self) -> list[ABCConfigDomain]:
        return [ConfigDomainCore()]


class ModePasswords(SimpleListMode[Password]):
    @classmethod
    def name(cls) -> str:
        return "passwords"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["passwords"]

    def __init__(self) -> None:
        super().__init__(
            mode_type=PasswordStoreModeType(),
            store=PasswordStore(),
        )
        self._contact_groups = load_contact_group_information()

    def title(self) -> str:
        return _("Passwords")

    def _table_title(self) -> str:
        return _("Passwords")

    def _validate_deletion(self, ident: str, entry: Password, *, debug: bool) -> None:
        if is_locked_by_quick_setup(entry.get("locked_by")):
            raise MKUserError(
                "_delete",
                _("Cannot delete %s because it is managed by quick setup.")
                % self._mode_type.name_singular(),
            )

    def _delete_confirm_message(self) -> str:
        return " ".join(
            [
                _(
                    "<b>Beware:</b> The password may be used in checks. If you "
                    "delete the password, the checks won't be able to "
                    "authenticate with this password anymore."
                ),
                super()._delete_confirm_message(),
            ]
        )

    def _show_delete_action(self, nr: int, ident: str, entry: Password) -> None:
        if is_locked_by_quick_setup(entry.get("locked_by")):
            html.icon_button(
                url="",
                title=_("%s can only be deleted via quick setup")
                % self._mode_type.name_singular().title(),
                icon="delete",
                class_=["disabled"],
            )

        else:
            super()._show_delete_action(nr, ident, entry)

    def page(self) -> None:
        html.p(
            _(
                "This password management module stores the passwords you use in your checks and "
                "special agents in a central place. Please note that this password store is no "
                "kind of password safe. Your passwords will not be encrypted."
            )
        )
        html.p(
            _(
                "All the passwords you store in your monitoring configuration, "
                "including this password store, are needed in plain text to contact remote systems "
                "for monitoring. So all those passwords have to be stored readable by the monitoring."
            )
        )
        super().page()

    def _show_entry_cells(self, table: Table, ident: str, entry: Password) -> None:
        table.cell(_("ID"), ident)
        table.cell(_("Title"), entry["title"])
        table.cell(_("Editable by"))
        if entry["owned_by"] is None:
            html.write_text_permissive(
                _('Administrators (having the permission "Write access to all passwords")')
            )
        else:
            html.write_text_permissive(self._contact_group_alias(entry["owned_by"]))
        table.cell(_("Shared with"))
        if not entry["shared_with"]:
            html.write_text_permissive(_("Not shared"))
        else:
            html.write_text_permissive(
                ", ".join([self._contact_group_alias(g) for g in entry["shared_with"]])
            )

        quick_setup_source_cell(table, entry.get("locked_by"))

    def _contact_group_alias(self, name: str) -> str:
        return self._contact_groups.get(name, {"alias": name})["alias"]


class ModeEditPassword(SimpleEditMode[Password]):
    @classmethod
    def name(cls) -> str:
        return "edit_password"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["passwords"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModePasswords

    def __init__(self) -> None:
        self._clone_source: Password | None = None
        super().__init__(
            mode_type=PasswordStoreModeType(),
            store=PasswordStore(),
        )

    def _clone_entry(self, entry: Password) -> Password:
        self._clone_source = entry
        clone = copy.deepcopy(entry)
        # remove the lock when cloning
        clone.pop("locked_by", None)
        return clone

    def _vs_mandatory_elements(self) -> list[DictionaryEntry]:
        elements = super()._vs_mandatory_elements()
        locked_by = None if self._new else self._entry.get("locked_by")
        if is_locked_by_quick_setup(locked_by, check_reference_exists=False):
            elements.append(
                (
                    "source",
                    FixedValue(
                        value=locked_by["instance_id"],
                        title=_("Source"),
                        totext=quick_setup_render_link(locked_by),
                    ),
                )
            )

        return elements

    def _mandatory_elements(self) -> dict[str, DictElement]:
        return convert_dict_elements_vs2fs(self._vs_mandatory_elements())

    def _vs_individual_elements(self) -> list[DictionaryEntry]:
        if user.may("wato.edit_all_passwords"):
            admin_element: list[ValueSpec] = [
                FixedValue(
                    value=None,
                    title=_("Administrators"),
                    totext=_(
                        'Administrators (having the permission "Write access to all passwords")'
                    ),
                )
            ]
        else:
            admin_element = []

        elements: list[DictionaryEntry] = [
            (
                "password",
                PasswordValuespec(
                    title=_("Password"),
                    allow_empty=False,
                    size=32,
                ),
            ),
            (
                "owned_by",
                Alternative(
                    title=_("Editable by"),
                    help=_(
                        "Each password is owned by a group of users which are able to edit, "
                        "delete and use existing passwords."
                    ),
                    elements=admin_element
                    + [
                        DropdownChoice(
                            title=_("Members of the contact group:"),
                            choices=lambda: sorted_contact_group_choices(only_own=True),
                            invalid_choice="complain",
                            empty_text=_(
                                "You need to be member of at least one contact group to be able to "
                                "create a password."
                            ),
                            invalid_choice_title=_("Group not existant or not member"),
                            invalid_choice_error=_(
                                "The choosen group is either not existant "
                                "anymore or you are not a member of this "
                                "group. Please choose another one."
                            ),
                        ),
                    ],
                ),
            ),
            (
                "shared_with",
                DualListChoice(
                    title=_("Share with"),
                    help=_(
                        "By default only the members of the owner contact group are permitted "
                        "to use a a configured password. It is possible to share a password with "
                        "other groups of users to make them able to use a password in checks."
                    ),
                    choices=sorted_contact_group_choices,
                    autoheight=False,
                    size=43,
                ),
            ),
        ]

        return elements

    def _page_form_quick_setup_warning(self) -> None:
        locked_by = None if self._new else self._entry.get("locked_by")
        if (
            is_locked_by_quick_setup(locked_by)
            and request.get_ascii_input("mode") != "edit_configuration_bundle"
        ):
            quick_setup_locked_warning(locked_by, self._mode_type.name_singular())

        elif self._clone_source and (locked_by := self._clone_source.get("locked_by")):
            quick_setup_duplication_warning(locked_by, self._mode_type.name_singular())
