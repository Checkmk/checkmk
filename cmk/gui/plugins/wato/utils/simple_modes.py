#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""These modes implement a complete set of modes for managing a set of standard objects

Together with WatoSimpleConfigFile() as store class this implements

a) A list mode where all objects are shown. All objects can be deleted here.
   New objects can be created from here.
b) A edit mode which can be used to create and edit an object.
"""

import abc
import copy
from typing import Any, Generic, List, Mapping, Optional, Type, TypeVar, Union

from livestatus import SiteId

import cmk.gui.forms as forms
import cmk.gui.watolib as watolib
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.plugins.wato.utils.base_modes import mode_url, redirect, WatoMode
from cmk.gui.table import Table, table_element
from cmk.gui.type_defs import ActionResult
from cmk.gui.utils import unique_default_name_suggestion
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_link, makeuri_contextless
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    DictionaryEntry,
    DocumentationURL,
    DualListChoice,
    FixedValue,
    ID,
    RuleComment,
    SetupSiteChoice,
    TextInput,
)
from cmk.gui.watolib.simple_config_file import WatoSimpleConfigFile

_T = TypeVar("_T", bound=Mapping[str, Any])


class SimpleModeType(Generic[_T], abc.ABC):
    @abc.abstractmethod
    def type_name(self) -> str:
        """A GUI globally unique identifier (in singular form) for the managed type of object"""
        raise NotImplementedError()

    @abc.abstractmethod
    def name_singular(self):
        """Name of the object used. This is used in user visible messages, buttons and titles."""
        raise NotImplementedError()

    @abc.abstractmethod
    def is_site_specific(self) -> bool:
        """Whether or not an object of this type is site specific
        It has a mandatory "site" attribute in case it is.
        """
        raise NotImplementedError()

    def site_valuespec(self) -> Union[DualListChoice, SetupSiteChoice]:
        return SetupSiteChoice()

    @abc.abstractmethod
    def can_be_disabled(self) -> bool:
        """Whether or not an object of this type can be disabled

        If True the user can set an attribute named "disabled" for each object.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def affected_config_domains(self) -> List[Type[watolib.ABCConfigDomain]]:
        """List of config domains that are affected by changes to objects of this type"""
        raise NotImplementedError()

    def mode_ident(self) -> str:
        """A GUI wide unique identifier which is used to create the WATO mode identifiers"""
        return self.type_name()

    def list_mode_name(self) -> str:
        """The mode name of the WATO list mode of this object type"""
        return "%ss" % self.mode_ident()

    def edit_mode_name(self) -> str:
        """The mode name of the WATO edit mode of this object type"""
        return "edit_%s" % self.mode_ident()

    def affected_sites(self, entry: _T) -> Optional[List[SiteId]]:
        """Sites that are affected by changes to objects of this type

        Returns either a list of sites affected by a change or None.

        The entry argument is the data object that is currently being handled. In case
        the objects of this site are site specific it can be used to decide which sites
        are affected by a change to this object."""
        if self.is_site_specific():
            if isinstance(entry["site"], list):
                return entry["site"]
            return [entry["site"]]
        return None


class _SimpleWatoModeBase(Generic[_T], WatoMode, abc.ABC):
    """Base for specific WATO modes of different types

    This is essentially a base class for the SimpleListMode/SimpleEditMode
    classes. It should not be used directly by specific mode classes.
    """

    def __init__(self, mode_type: SimpleModeType[_T], store: WatoSimpleConfigFile[_T]) -> None:
        self._mode_type = mode_type
        self._store = store

        # WatoMode() implicitly calls self._from_vars() which may require self._store
        # to be set before it is executed. Therefore we execute the super constructor
        # here.
        # TODO: Make the _from_vars() mechanism more explicit
        super().__init__()

    def _add_change(
        self,
        *,
        action: str,
        text: str,
        affected_sites: Optional[List[SiteId]],
    ) -> None:
        """Add a WATO change entry for this object type modifications"""
        watolib.add_change(
            "%s-%s" % (action, self._mode_type.type_name()),
            text,
            domains=self._mode_type.affected_config_domains(),
            sites=affected_sites,
        )


class SimpleListMode(_SimpleWatoModeBase[_T]):
    """Base class for list modes"""

    @abc.abstractmethod
    def _table_title(self) -> str:
        """The user visible title shown on top of the list table"""
        raise NotImplementedError()

    @abc.abstractmethod
    def _show_entry_cells(self, table: Table, ident: str, entry: _T) -> None:
        """Shows the HTML code for the cells of an object row"""
        raise NotImplementedError()

    def _handle_custom_action(self, action: str) -> ActionResult:
        """Gives the mode the option to implement custom actions

        This function is called when the action phase is triggered. The action name is given
        with the _action HTTP variable. It is handed over as first argument to this function.

        NOTE: The implementation needs to invalidate the transaction ID on it's own.

        The "delete" action is automatically handled by the SimpleListMode implementation.
        """
        raise MKUserError("_action", _("The action '%s' is not implemented") % action)

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name=self._mode_type.type_name(),
                    title=self._mode_type.name_singular().title(),
                    topics=[
                        PageMenuTopic(
                            title=self._mode_type.name_singular().title(),
                            entries=[
                                PageMenuEntry(
                                    title=self._new_button_label(),
                                    icon_name="new",
                                    item=make_simple_link(
                                        makeuri_contextless(
                                            request,
                                            [("mode", self._mode_type.edit_mode_name())],
                                        )
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )

    def _new_button_label(self) -> str:
        return _("Add %s") % self._mode_type.name_singular()

    def action(self) -> ActionResult:
        if not transactions.transaction_valid():
            return None

        action_var = request.get_str_input("_action")
        if action_var is None:
            return None

        if action_var != "delete":
            return self._handle_custom_action(action_var)

        if not transactions.check_transaction():
            return redirect(mode_url(self._mode_type.list_mode_name()))

        entries = self._store.load_for_modification()

        ident = request.get_ascii_input("_delete")
        if ident not in entries:
            raise MKUserError(
                "_delete", _("This %s does not exist.") % self._mode_type.name_singular()
            )

        if ident not in self._store.filter_editable_entries(entries):
            raise MKUserError(
                "_delete",
                _("You are not allowed to delete this %s.") % self._mode_type.name_singular(),
            )

        self._validate_deletion(ident, entries[ident])

        entry = entries.pop(ident)
        self._add_change(
            action="delete",
            text=_("Removed the %s '%s'") % (self._mode_type.name_singular(), ident),
            affected_sites=self._mode_type.affected_sites(entry),
        )
        self._store.save(entries)

        flash(_("The %s has been deleted.") % self._mode_type.name_singular())
        return redirect(mode_url(self._mode_type.list_mode_name()))

    def _validate_deletion(self, ident: str, entry: _T) -> None:
        """Override this to implement custom validations"""

    def _delete_confirm_message(self) -> str:
        return _("Do you really want to delete this %s?") % self._mode_type.name_singular()

    def page(self) -> None:
        self._show_table(self._store.filter_editable_entries(self._store.load_for_reading()))

    def _show_table(self, entries: dict[str, _T]) -> None:
        with table_element(self._mode_type.type_name(), self._table_title()) as table:
            for ident, entry in sorted(entries.items(), key=lambda e: e[1]["title"]):
                table.row()
                self._show_row(table, ident, entry)

    def _show_row(self, table: Table, ident: str, entry: _T) -> None:
        self._show_action_cell(table, ident)
        self._show_entry_cells(table, ident, entry)

    def _show_action_cell(self, table: Table, ident: str) -> None:
        table.cell(_("Actions"), css="buttons")

        edit_url = makeuri_contextless(
            request,
            [
                ("mode", self._mode_type.edit_mode_name()),
                ("ident", ident),
            ],
        )
        html.icon_button(edit_url, _("Edit this %s") % self._mode_type.name_singular(), "edit")

        clone_url = makeuri_contextless(
            request,
            [
                ("mode", self._mode_type.edit_mode_name()),
                ("clone", ident),
            ],
        )
        html.icon_button(clone_url, _("Clone this %s") % self._mode_type.name_singular(), "clone")

        delete_url = make_confirm_link(
            url=watolib.make_action_link(
                [
                    ("mode", self._mode_type.list_mode_name()),
                    ("_action", "delete"),
                    ("_delete", ident),
                ]
            ),
            message=self._delete_confirm_message(),
        )
        html.icon_button(
            delete_url, _("Delete this %s") % self._mode_type.name_singular(), "delete"
        )


class SimpleEditMode(_SimpleWatoModeBase, abc.ABC):
    """Base class for edit modes"""

    @abc.abstractmethod
    def _vs_individual_elements(self) -> list[DictionaryEntry]:
        raise NotImplementedError()

    def _from_vars(self) -> None:
        ident = request.get_ascii_input("ident")
        if ident is not None:
            try:
                entry = self._store.filter_editable_entries(self._store.load_for_reading())[ident]
            except KeyError:
                raise MKUserError(
                    "ident", _("This %s does not exist.") % self._mode_type.name_singular()
                )

            self._new = False
            self._ident: Optional[str] = ident
            self._entry = entry
            return

        clone = request.get_ascii_input("clone")
        if clone is not None:
            try:
                entry = self._store.filter_editable_entries(self._store.load_for_reading())[clone]
            except KeyError:
                raise MKUserError(
                    "clone", _("This %s does not exist.") % self._mode_type.name_singular()
                )

            self._new = True
            self._ident = None
            self._entry = copy.deepcopy(entry)
            return

        self._new = True
        self._ident = None
        self._entry = {}

    def title(self) -> str:
        if self._new:
            return _("New %s") % self._mode_type.name_singular()
        return _("Edit %s: %s") % (self._mode_type.name_singular(), self._entry["title"])

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Actions"), breadcrumb, form_name="edit", button_name="_save"
        )

    def valuespec(self) -> Dictionary:
        general_elements = self._vs_mandatory_elements()
        general_keys = [k for k, _v in general_elements]

        individual_elements = self._vs_individual_elements()
        individual_keys = [k for k, _v in individual_elements]

        return Dictionary(
            title=self._mode_type.name_singular().title(),
            elements=general_elements + individual_elements,
            optional_keys=self._vs_optional_keys(),
            show_more_keys=["docu_url"],
            headers=[
                (_("General Properties"), general_keys),
                (_("%s Properties") % self._mode_type.name_singular().title(), individual_keys),
            ],
            render="form",
        )

    def _vs_mandatory_elements(self) -> list[DictionaryEntry]:
        ident_attr: List = []
        if self._new:
            ident_attr = [
                (
                    "ident",
                    ID(
                        title=_("Unique ID"),
                        help=_(
                            "The ID must be a unique text. It will be used as an internal key "
                            "when objects refer to this object."
                        ),
                        default_value=self._default_id,
                        allow_empty=False,
                        size=80,
                    ),
                ),
            ]
        else:
            ident_attr = [
                (
                    "ident",
                    FixedValue(
                        value=self._ident,
                        title=_("Unique ID"),
                    ),
                ),
            ]

        if self._mode_type.is_site_specific():
            site_attr = [
                ("site", self._mode_type.site_valuespec()),
            ]
        else:
            site_attr = []

        if self._mode_type.can_be_disabled():
            disable_attr = [
                (
                    "disabled",
                    Checkbox(
                        title=_("Activation"),
                        help=_("Disabled %s are kept in the configuration but are not active.")
                        % self._mode_type.name_singular(),
                        label=_("do not activate this %s") % self._mode_type.name_singular(),
                    ),
                ),
            ]
        else:
            disable_attr = []

        elements = (
            ident_attr
            + [
                (
                    "title",
                    TextInput(
                        title=_("Title"),
                        help=_("The title of the %s. It will be used as display name.")
                        % (self._mode_type.name_singular()),
                        allow_empty=False,
                        size=80,
                    ),
                ),
                ("comment", RuleComment()),
                ("docu_url", DocumentationURL()),
            ]
            + disable_attr
            + site_attr
        )

        return elements

    def _default_id(self) -> str:
        return unique_default_name_suggestion(
            self._mode_type.name_singular(),
            self._store.load_for_reading().keys(),
        )

    def _vs_optional_keys(self) -> list[str]:
        return []

    def action(self) -> ActionResult:
        if not transactions.transaction_valid():
            return redirect(mode_url(self._mode_type.list_mode_name()))

        vs = self.valuespec()

        config = vs.from_html_vars("_edit")
        vs.validate_value(config, "_edit")

        if "ident" in config:
            self._ident = config.pop("ident")
        assert self._ident is not None
        self._entry = config

        entries = self._store.load_for_modification()

        if self._new and self._ident in entries:
            raise MKUserError("ident", _("This ID is already in use. Please choose another one."))

        if not self._new and self._ident not in self._store.filter_editable_entries(entries):
            raise MKUserError(
                "ident", _("You are not allowed to edit this %s.") % self._mode_type.name_singular()
            )

        if self._new:
            entries[self._ident] = self._entry
            self._add_change(
                action="add",
                text=_("Added the %s '%s'") % (self._mode_type.name_singular(), self._ident),
                affected_sites=self._mode_type.affected_sites(self._entry),
            )
        else:
            current_sites = self._mode_type.affected_sites(self._entry)
            previous_sites = self._mode_type.affected_sites(entries[self._ident])

            affected_sites = (
                None
                if current_sites is None or previous_sites is None
                else sorted({*previous_sites, *current_sites})
            )

            entries[self._ident] = self._entry

            self._add_change(
                action="edit",
                text=_("Edited the %s '%s'") % (self._mode_type.name_singular(), self._ident),
                affected_sites=affected_sites,
            )

        self._save(entries)

        return redirect(mode_url(self._mode_type.list_mode_name()))

    def _save(self, entries: dict[str, _T]) -> None:
        self._store.save(entries)

    def page(self) -> None:
        html.begin_form("edit", method="POST")
        html.prevent_password_auto_completion()

        vs = self.valuespec()

        vs.render_input("_edit", self._entry)
        vs.set_focus("_edit")
        forms.end()

        html.hidden_fields()
        html.end_form()
