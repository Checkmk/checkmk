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
from typing import Optional, List, Type, Union, Tuple, Dict

from cmk.gui.table import table_element, Table
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.wato.utils.base_modes import WatoMode
from cmk.gui.plugins.wato.utils.html_elements import wato_confirm
from cmk.gui.watolib.simple_config_file import WatoSimpleConfigFile
from cmk.gui.valuespec import (
    ID,
    FixedValue,
    SiteChoice,
    Dictionary,
    TextUnicode,
    Checkbox,
    DocumentationURL,
    RuleComment,
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


class SimpleModeType(metaclass=abc.ABCMeta):
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

    def site_valuespec(self) -> SiteChoice:
        return SiteChoice()

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

    def affected_sites(self, entry: dict) -> Optional[List[str]]:
        """Sites that are affected by changes to objects of this type

        Returns either a list of sites affected by a change or None.

        The entry argument is the data object that is currently being handled. In case
        the objects of this site are site specific it can be used to decide which sites
        are affected by a change to this object."""
        if self.is_site_specific():
            return [entry["site"]]
        return None


class SimpleWatoModeBase(WatoMode, metaclass=abc.ABCMeta):
    """Base for specific WATO modes of different types

    This is essentially a base class for the SimpleListMode/SimpleEditMode
    classes. It should not be used directly by specific mode classes.
    """
    def __init__(self, mode_type: SimpleModeType, store: WatoSimpleConfigFile) -> None:
        self._mode_type = mode_type
        self._store = store

        # WatoMode() implicitly calls self._from_vars() which may require self._store
        # to be set before it is executed. Therefore we execute the super constructor
        # here.
        # TODO: Make the _from_vars() mechanism more explicit
        super(SimpleWatoModeBase, self).__init__()

    def _add_change(self, action: str, entry: Dict, text: str) -> None:
        """Add a WATO change entry for this object type modifications"""
        watolib.add_change("%s-%s" % (action, self._mode_type.type_name()),
                           text,
                           domains=self._mode_type.affected_config_domains(),
                           sites=self._mode_type.affected_sites(entry))


class SimpleListMode(SimpleWatoModeBase):
    """Base class for list modes"""
    @abc.abstractmethod
    def _table_title(self) -> str:
        """The user visible title shown on top of the list table"""
        raise NotImplementedError()

    @abc.abstractmethod
    def _show_entry_cells(self, table: Table, ident: str, entry: dict) -> None:
        """Shows the HTML code for the cells of an object row"""
        raise NotImplementedError()

    def _handle_custom_action(self, action: str) -> Union[None, bool, Tuple[Optional[str], str]]:
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
                                        html.makeuri_contextless([
                                            ("mode", self._mode_type.edit_mode_name())
                                        ])),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def _new_button_label(self) -> str:
        return _("Add %s") % self._mode_type.name_singular()

    def action(self):
        if not html.transaction_valid():
            return

        action_var = html.request.get_str_input("_action")
        if action_var is None:
            return

        if action_var != "delete":
            return self._handle_custom_action(action_var)

        confirm = wato_confirm(_("Confirm deletion"), self._delete_confirm_message())
        if confirm is False:
            return False
        if not confirm:
            return
        html.check_transaction()  # invalidate transid

        entries = self._store.load_for_modification()

        ident = html.request.get_ascii_input("_delete")
        if ident not in entries:
            raise MKUserError("_delete",
                              _("This %s does not exist.") % self._mode_type.name_singular())

        if ident not in self._store.filter_editable_entries(entries):
            raise MKUserError(
                "_delete",
                _("You are not allowed to delete this %s.") % self._mode_type.name_singular())

        self._validate_deletion(ident, entries[ident])

        entry = entries.pop(ident)
        self._add_change("delete", entry,
                         _("Removed the %s '%s'") % (self._mode_type.name_singular(), ident))
        self._store.save(entries)

        return None, _("The %s has been deleted.") % self._mode_type.name_singular()

    def _validate_deletion(self, ident, entry):
        """Override this to implement custom validations"""

    def _delete_confirm_message(self):
        return _("Do you really want to delete this %s?") % self._mode_type.name_singular()

    def page(self):
        self._show_table(self._store.filter_editable_entries(self._store.load_for_reading()))

    def _show_table(self, entries):
        with table_element(self._mode_type.type_name(), self._table_title()) as table:
            for ident, entry in sorted(entries.items(), key=lambda e: e[1]["title"]):
                table.row()
                self._show_row(table, ident, entry)

    def _show_row(self, table, ident, entry):
        self._show_action_cell(table, ident)
        self._show_entry_cells(table, ident, entry)

    def _show_action_cell(self, table, ident):
        table.cell(_("Actions"), css="buttons")

        edit_url = html.makeuri_contextless([
            ("mode", self._mode_type.edit_mode_name()),
            ("ident", ident),
        ])
        html.icon_button(edit_url, _("Edit this %s") % self._mode_type.name_singular(), "edit")

        clone_url = html.makeuri_contextless([
            ("mode", self._mode_type.edit_mode_name()),
            ("clone", ident),
        ])
        html.icon_button(clone_url, _("Clone this %s") % self._mode_type.name_singular(), "clone")

        delete_url = watolib.make_action_link([
            ("mode", self._mode_type.list_mode_name()),
            ("_action", "delete"),
            ("_delete", ident),
        ])
        html.icon_button(delete_url,
                         _("Delete this %s") % self._mode_type.name_singular(), "delete")


class SimpleEditMode(SimpleWatoModeBase, metaclass=abc.ABCMeta):
    """Base class for edit modes"""
    @abc.abstractmethod
    def _vs_individual_elements(self):
        # type () -> list
        raise NotImplementedError()

    def _from_vars(self):
        ident = html.request.get_ascii_input("ident")
        if ident is not None:
            try:
                entry = self._store.filter_editable_entries(self._store.load_for_reading())[ident]
            except KeyError:
                raise MKUserError("ident",
                                  _("This %s does not exist.") % self._mode_type.name_singular())

            self._new = False
            self._ident: Optional[str] = ident
            self._entry = entry
            return

        clone = html.request.get_ascii_input("clone")
        if clone is not None:
            try:
                entry = self._store.filter_editable_entries(self._store.load_for_reading())[clone]
            except KeyError:
                raise MKUserError("clone",
                                  _("This %s does not exist.") % self._mode_type.name_singular())

            self._new = True
            self._ident = None
            self._entry = copy.deepcopy(entry)
            return

        self._new = True
        self._ident = None
        self._entry = {}

    def title(self):
        if self._new:
            return _("New %s") % self._mode_type.name_singular()
        return _("Edit %s: %s") % (self._mode_type.name_singular(), self._entry["title"])

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(breadcrumb, form_name="edit", button_name="save")

    def valuespec(self):
        general_elements = self._vs_mandatory_elements()
        general_keys = [k for k, _v in general_elements]

        individual_elements = self._vs_individual_elements()
        individual_keys = [k for k, _v in individual_elements]

        return Dictionary(
            title=self._mode_type.name_singular().title(),
            elements=general_elements + individual_elements,
            optional_keys=self._vs_optional_keys(),
            headers=[
                (_("General Properties"), general_keys),
                (_("%s Properties") % self._mode_type.name_singular().title(), individual_keys),
            ],
            render="form",
        )

    def _vs_mandatory_elements(self):
        if self._new:
            ident_attr = [
                ("ident",
                 ID(
                     title=_("Unique ID"),
                     help=_("The ID must be a unique text. It will be used as an internal key "
                            "when objects refer to this object."),
                     allow_empty=False,
                     size=12,
                 )),
            ]
        else:
            ident_attr = [
                ("ident", FixedValue(
                    self._ident,
                    title=_("Unique ID"),
                )),
            ]

        if self._mode_type.is_site_specific():
            site_attr = [
                ("site", self._mode_type.site_valuespec()),
            ]
        else:
            site_attr = []

        if self._mode_type.can_be_disabled():
            disable_attr = [
                ("disabled",
                 Checkbox(
                     title=_("Activation"),
                     help=_("Disabled %s are kept in the configuration but are not active.") %
                     self._mode_type.name_singular(),
                     label=_("do not activate this %s") % self._mode_type.name_singular(),
                 )),
            ]
        else:
            disable_attr = []

        elements = ident_attr + [
            ("title",
             TextUnicode(
                 title=_("Title"),
                 help=_("The title of the %s. It will be used as display name.") %
                 (self._mode_type.name_singular()),
                 allow_empty=False,
                 size=80,
             )),
            ("comment", RuleComment()),
            ("docu_url", DocumentationURL()),
        ] + disable_attr + site_attr

        return elements

    def _vs_optional_keys(self):
        return []

    def action(self):
        if not html.transaction_valid():
            return self._mode_type.list_mode_name()

        vs = self.valuespec()

        config = vs.from_html_vars("_edit")
        vs.validate_value(config, "_edit")

        if "ident" in config:
            self._ident = config.pop("ident")
        self._entry = config

        entries = self._store.load_for_modification()

        if self._new and self._ident in entries:
            raise MKUserError("ident", _("This ID is already in use. Please choose another one."))

        if not self._new and self._ident not in self._store.filter_editable_entries(entries):
            raise MKUserError(
                "ident",
                _("You are not allowed to edit this %s.") % self._mode_type.name_singular())

        entries[self._ident] = self._entry

        if self._new:
            self._add_change(
                "add", self._entry,
                _("Added the %s '%s'") % (self._mode_type.name_singular(), self._ident))
        else:
            self._add_change(
                "edit", self._entry,
                _("Edited the %s '%s'") % (self._mode_type.name_singular(), self._ident))

        self._save(entries)

        return self._mode_type.list_mode_name()

    def _save(self, entries):
        self._store.save(entries)

    def page(self):
        html.begin_form("edit", method="POST")
        html.prevent_password_auto_completion()

        vs = self.valuespec()

        vs.render_input("_edit", self._entry)
        vs.set_focus("_edit")
        forms.end()

        html.hidden_fields()
        html.end_form()
