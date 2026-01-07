#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""These modes implement a complete set of modes for managing a set of standard objects

Together with WatoSimpleConfigFile() as store class this implements

a) A list mode where all objects are shown. All objects can be deleted here.
   New objects can be created from here.
b) A edit mode which can be used to create and edit an object.
"""

# mypy: disable-error-code="type-arg"

import abc
import copy
import json
from collections.abc import Mapping
from typing import Any, cast

import cmk.gui.watolib.changes as _changes
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.default_name import unique_default_name_suggestion
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs import (
    DEFAULT_VALUE,
    IncomingData,
    parse_data_from_field_id,
    RawDiskData,
    RawFrontendData,
    render_form_spec,
)
from cmk.gui.form_specs.generators.dict_to_catalog import Dict2CatalogConverter, Headers
from cmk.gui.form_specs.generators.setup_site_choice import create_setup_site_choice
from cmk.gui.form_specs.unstable import (
    Catalog,
    CommentTextArea,
    LegacyValueSpec,
    SingleChoiceExtended,
)
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
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
from cmk.gui.type_defs import ActionResult, IconNames, RenderMode, StaticIcon
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeuri_contextless
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    DictionaryEntry,
    DocumentationURL,
    DualListChoice,
    FixedValue,
    ID,
    RuleComment,
    TextInput,
    ValueSpec,
)
from cmk.gui.valuespec import SetupSiteChoice as VSSetupSiteChoice
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.hosts_and_folders import make_action_link
from cmk.gui.watolib.mode import mode_url, redirect, WatoMode
from cmk.gui.watolib.simple_config_file import WatoSimpleConfigFile
from cmk.rulesets.v1 import form_specs, Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    FieldSize,
    FormSpec,
    MultipleChoice,
    SingleChoice,
)
from cmk.rulesets.v1.form_specs import Dictionary as FormSpecDictionary
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.utils.urls import is_allowed_url

DoValidate = bool


class SimpleModeType[T: Mapping[str, Any]](abc.ABC):
    @abc.abstractmethod
    def type_name(self) -> str:
        """A GUI globally unique identifier (in singular form) for the managed type of object"""
        raise NotImplementedError()

    @abc.abstractmethod
    def name_singular(self) -> str:
        """Name of the object used. This is used in user visible messages, buttons and titles."""
        raise NotImplementedError()

    @abc.abstractmethod
    def is_site_specific(self) -> bool:
        """Whether or not an object of this type is site specific
        It has a mandatory "site" attribute in case it is.
        """
        raise NotImplementedError()

    def site_valuespec(self) -> DualListChoice | VSSetupSiteChoice:
        return VSSetupSiteChoice()

    def site_form_spec(
        self,
    ) -> SingleChoice | MultipleChoice | SingleChoiceExtended:
        return create_setup_site_choice()

    @abc.abstractmethod
    def can_be_disabled(self) -> bool:
        """Whether or not an object of this type can be disabled

        If True the user can set an attribute named "disabled" for each object.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def affected_config_domains(self) -> list[ABCConfigDomain]:
        """List of config domains that are affected by changes to objects of this type"""
        raise NotImplementedError()

    def mode_ident(self) -> str:
        """A GUI wide unique identifier which is used to create the Setup mode identifiers"""
        return self.type_name()

    def list_mode_name(self) -> str:
        """The mode name of the Setup list mode of this object type"""
        return "%ss" % self.mode_ident()

    def edit_mode_name(self) -> str:
        """The mode name of the Setup edit mode of this object type"""
        return "edit_%s" % self.mode_ident()

    def affected_sites(self, entry: T) -> list[SiteId] | None:
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


class _SimpleWatoModeBase[T: Mapping[str, Any]](WatoMode):
    """Base for specific Setup modes of different types

    This is essentially a base class for the SimpleListMode/SimpleEditMode
    classes. It should not be used directly by specific mode classes.
    """

    def __init__(self, mode_type: SimpleModeType[T], store: WatoSimpleConfigFile[T]) -> None:
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
        user_id: UserId | None,
        affected_sites: list[SiteId] | None,
        use_git: bool,
    ) -> None:
        """Add a Setup change entry for this object type modifications"""
        _changes.add_change(
            action_name=f"{action}-{self._mode_type.type_name()}",
            text=text,
            user_id=user_id,
            domains=self._mode_type.affected_config_domains(),
            sites=affected_sites,
            use_git=use_git,
        )


class SimpleListMode[T: Mapping[str, Any]](_SimpleWatoModeBase[T]):
    """Base class for list modes"""

    @abc.abstractmethod
    def _table_title(self) -> str:
        """The user visible title shown on top of the list table"""
        raise NotImplementedError()

    @abc.abstractmethod
    def _show_entry_cells(self, table: Table, ident: str, entry: T) -> None:
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

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
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
                                    icon_name=StaticIcon(IconNames.new),
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

    def action(self, config: Config) -> ActionResult:
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

        self._validate_deletion(ident, entries[ident], debug=config.debug)

        entry = entries.pop(ident)
        self._add_change(
            action="delete",
            text=_("Removed the %s '%s'") % (self._mode_type.name_singular(), ident),
            user_id=user.id,
            affected_sites=self._mode_type.affected_sites(entry),
            use_git=config.wato_use_git,
        )
        self._store.save(entries, pprint_value=config.wato_pprint_config)

        flash(_("The %s has been deleted.") % self._mode_type.name_singular())
        return redirect(mode_url(self._mode_type.list_mode_name()))

    def _validate_deletion(self, ident: str, entry: T, *, debug: bool) -> None:
        """Override this to implement custom validations"""

    def _delete_confirm_title(self, nr: int) -> str:
        return _("Delete %s #%d") % (self._mode_type.name_singular(), nr)

    def _delete_confirm_message(self) -> str:
        return ""

    def page(self, config: Config) -> None:
        self._show_table(self._store.filter_editable_entries(self._store.load_for_reading()))

    def _show_table(self, entries: dict[str, T]) -> None:
        with table_element(self._mode_type.type_name(), self._table_title()) as table:
            for nr, (ident, entry) in enumerate(
                sorted(entries.items(), key=lambda e: e[1]["title"])
            ):
                table.row()
                self._show_row(nr, table, ident, entry)

    def _show_row(self, nr: int, table: Table, ident: str, entry: T) -> None:
        table.cell("#", css=["narrow nowrap"])
        html.write_text_permissive(nr)

        self._show_action_cell(nr, table, ident, entry)
        self._show_entry_cells(table, ident, entry)

    def _show_action_cell(self, nr: int, table: Table, ident: str, entry: T) -> None:
        table.cell(_("Actions"), css=["buttons"])

        edit_url = makeuri_contextless(
            request,
            [
                ("mode", self._mode_type.edit_mode_name()),
                ("ident", ident),
            ],
        )
        html.icon_button(
            edit_url,
            _("Edit this %s") % self._mode_type.name_singular(),
            StaticIcon(IconNames.edit),
        )

        clone_url = makeuri_contextless(
            request,
            [
                ("mode", self._mode_type.edit_mode_name()),
                ("clone", ident),
            ],
        )
        html.icon_button(
            clone_url,
            _("Clone this %s") % self._mode_type.name_singular(),
            StaticIcon(IconNames.clone),
        )

        self._show_delete_action(nr, ident, entry)

    def _show_delete_action(self, nr: int, ident: str, entry: T) -> None:
        confirm_delete: str = _("ID: %s") % ident
        if delete_confirm_msg := self._delete_confirm_message():
            confirm_delete += "<br><br>" + delete_confirm_msg
        delete_url = make_confirm_delete_link(
            url=make_action_link(
                [
                    ("mode", self._mode_type.list_mode_name()),
                    ("_action", "delete"),
                    ("_delete", ident),
                ]
            ),
            title=self._delete_confirm_title(nr),
            suffix=entry["title"],
            message=confirm_delete,
        )
        html.icon_button(
            delete_url,
            _("Delete this %s") % self._mode_type.name_singular(),
            StaticIcon(IconNames.delete),
        )


class SimpleEditMode[T: Mapping[str, Any]](_SimpleWatoModeBase[T]):
    """Base class for edit modes"""

    def __init__(self, mode_type: SimpleModeType[T], store: WatoSimpleConfigFile[T]):
        self._ident: str | None = None
        self._clone: str | None = None
        self._new: bool = True
        super().__init__(mode_type, store)

    def _vs_individual_elements(self) -> list[DictionaryEntry]:
        raise NotImplementedError()

    def _fs_individual_elements(self) -> dict[str, DictElement]:
        raise NotImplementedError()

    def _individual_elements(self) -> dict[str, DictElement]:
        return self._fs_individual_elements()

    def _fs_mandatory_elements(self) -> dict[str, DictElement]:
        return self._fs_general_properties()

    def from_vars(self, ident_var: str) -> None:
        self._from_vars(ident_var)

    @property
    def entry(self) -> T:
        return self._entry

    def _from_vars(self, ident_var: str = "ident") -> None:
        ident = request.get_ascii_input(ident_var)
        if ident is not None:
            try:
                entry = self._store.filter_editable_entries(self._store.load_for_reading())[ident]
            except KeyError:
                raise MKUserError(
                    "ident", _("This %s does not exist.") % self._mode_type.name_singular()
                )

            self._new = False
            self._ident = ident
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

            self._clone = self._default_id()
            self._entry = self._clone_entry(entry)
            return

        self._entry = self._default_entry()

    def _clone_entry(self, entry: T) -> T:
        return copy.deepcopy(entry)

    def _default_entry(self) -> T:
        # This is only relevant when rendering with form specs
        return cast(T, {})

    def title(self) -> str:
        if self._new:
            return _("Add %s") % self._mode_type.name_singular()
        return _("Edit %s: %s") % (self._mode_type.name_singular(), self._entry["title"])

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Actions"), breadcrumb, form_name="edit", button_name="_save"
        )

    def _get_catalog_converter(
        self,
    ) -> Dict2CatalogConverter:
        general_elements = self._fs_mandatory_elements()
        general_keys = general_elements.keys()
        individual_elements = self._individual_elements()
        individual_keys = individual_elements.keys()
        headers: Headers = [
            (_("General properties"), list(general_keys)),
            (_("%s properties") % self._mode_type.name_singular().title(), list(individual_keys)),
        ]
        return Dict2CatalogConverter.build_from_dictionary(
            FormSpecDictionary(
                elements={**general_elements, **individual_elements},
                custom_validate=(self._validate_fs,),
            ),
            headers,
        )

    def _validate_fs(self, elements: Mapping[str, object]) -> None:
        pass

    def catalog(self) -> Catalog | None:
        # Note: We may skip the CatalogConverter and build the Catalog ourselves
        return self._get_catalog_converter().catalog

    def _validate_vs(self, entry: dict[str, Any], varprefix: str) -> None:
        pass

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
                (_("General properties"), general_keys),
                (_("%s properties") % self._mode_type.name_singular().title(), individual_keys),
            ],
            render="form",
            validate=self._validate_vs,
        )

    def _vs_mandatory_elements(self) -> list[DictionaryEntry]:
        if self._new:
            ident_attr: list[tuple[str, ValueSpec]] = [
                (
                    "ident",
                    ID(
                        title=_("Unique ID"),
                        help=_(
                            "The ID must be unique. It acts as internal key "
                            "when objects reference it."
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
                        title=_("Configuration activation"),
                        help=_(
                            "Selecting this option will disable the %s, but "
                            "it will remain in the configuration."
                        )
                        % self._mode_type.name_singular(),
                        label=_("Do not apply this configuration"),
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
                        help=_("Name your %s for easy recognition.")
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

    def _fs_general_properties(self) -> dict[str, form_specs.DictElement]:
        elements: dict[str, form_specs.DictElement[Any]] = {}
        if self._new:
            elements["ident"] = form_specs.DictElement(
                parameter_form=form_specs.String(
                    title=Title("Unique ID"),
                    help_text=Help(
                        "The ID must be unique. It acts as internal key when objects reference it."
                    ),
                    prefill=form_specs.DefaultValue(self._default_id()),
                    custom_validate=(form_specs.validators.LengthInRange(min_value=1),),
                    field_size=FieldSize.LARGE,
                ),
            )
        else:
            assert self._ident is not None
            elements["ident"] = form_specs.DictElement(
                required=True,
                parameter_form=form_specs.FixedValue(
                    title=Title("Unique ID"),
                    help_text=Help(
                        "The ID must be unique. It acts as internal key when objects reference it."
                    ),
                    value=self._ident,
                ),
            )

        if "locked_by" in self._entry:
            shown_info = ", ".join(f"{x}: {y}" for x, y in self._entry["locked_by"].items())
            elements["locked_by"] = form_specs.DictElement(
                required=True,
                parameter_form=form_specs.FixedValue(
                    title=Title("Locked by"),
                    value=shown_info,
                ),
            )

        elements["title"] = form_specs.DictElement(
            parameter_form=form_specs.String(
                title=Title("Title"),
                help_text=Help("Name your %s for easy recognition.")
                % self._mode_type.name_singular(),
                custom_validate=(form_specs.validators.LengthInRange(min_value=1),),
                field_size=FieldSize.LARGE,
            ),
        )
        elements["comment"] = form_specs.DictElement(
            parameter_form=CommentTextArea(
                title=Title("Comment"),
                help_text=Help(
                    "Optionally, add a comment to explain the purpose of this "
                    "object. The comment is only visible in this dialog and can help "
                    "other users to understand the intentions of the configured "
                    "attributes."
                ),
            ),
        )

        def _validate_documentation_url(value: str) -> None:
            if not is_allowed_url(value, cross_domain=True, schemes=["http", "https"]):
                raise ValidationError(
                    Message("Not a valid URL (Only http and https URLs are allowed)."),
                )

        elements["docu_url"] = form_specs.DictElement(
            parameter_form=form_specs.String(
                title=Title("Documentation URL"),
                help_text=Help(
                    "Optionally, add a URL linking to a documentation or any other "
                    "page. An icon links to the page and opens in a new tab when "
                    "clicked. You can use either global URLs (starting with "
                    "<tt>http://</tt>), absolute local URLs (starting with "
                    "<tt>/</tt>) or relative URLs (relative to "
                    "<tt>check_mk/</tt>)."
                ),  # % str(html.render_icon("url")),
                custom_validate=(_validate_documentation_url,),
                field_size=FieldSize.LARGE,
            ),
        )

        if self._mode_type.can_be_disabled():
            elements["disabled"] = form_specs.DictElement(
                parameter_form=form_specs.BooleanChoice(
                    title=Title("Configuration activation"),
                    help_text=Help(
                        "Selecting this option will disable the %s, but "
                        "it will remain in the configuration."
                    )
                    % self._mode_type.name_singular(),
                    label=Label("Do not apply this configuration"),
                ),
            )

        if self._mode_type.is_site_specific():
            elements["site"] = form_specs.DictElement(
                parameter_form=self._mode_type.site_form_spec()
            )

        return elements

    def _default_id(self) -> str:
        return unique_default_name_suggestion(
            self._mode_type.name_singular(),
            self._store.load_for_reading().keys(),
        )

    def _vs_optional_keys(self) -> list[str]:
        return []

    def _update_entry_from_vars(self) -> None:
        render_mode, form_spec = self._get_render_mode()
        match render_mode:
            case RenderMode.FRONTEND:
                assert form_spec is not None
                self._update_entry_from_vars_form_spec(form_spec)
            case RenderMode.BACKEND:
                self._update_entry_from_vars_valuespec()

    def _update_entry_from_vars_valuespec(self) -> None:
        vs = self.valuespec()

        config = vs.from_html_vars("_edit")
        vs.validate_value(config, "_edit")

        if "ident" in config:
            self._ident = config.pop("ident")
        assert self._ident is not None
        entries = self._store.load_for_modification()

        # Keep the "locked_by" attribute if it exists in the current entry
        if self._ident in entries and "locked_by" in entries[self._ident]:
            config = {**config, "locked_by": entries[self._ident]["locked_by"]}

        # No typing support from valuespecs here, so we need to cast
        self._entry = cast(T, config)

    def _update_entry_from_vars_form_spec(self, form_spec: FormSpec) -> None:
        config = parse_data_from_field_id(
            form_spec,
            self._vue_field_id(),
        )

        assert isinstance(config, dict)

        # The form spec was rendered via a Catalog form spec, which introduced needless topics
        # We need to convert the config back to a flat dictionary
        config = self._get_catalog_converter().convert_catalog_to_flat_config(config)

        if "ident" in config:
            ident = config.pop("ident")
            assert isinstance(ident, str | None)  # horrible typing of config...
            self._ident = ident
        assert self._ident is not None
        entries = self._store.load_for_modification()

        # Keep the "locked_by" attribute if it exists in the current entry
        if self._ident in entries and "locked_by" in entries[self._ident]:
            config = {**config, "locked_by": entries[self._ident]["locked_by"]}

        # No typing support from form specs here, so we need to cast
        self._entry = cast(T, config)

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        if not transactions.transaction_valid():
            return redirect(mode_url(self._mode_type.list_mode_name()))

        self._update_entry_from_vars()
        assert self._ident is not None

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
                user_id=user.id,
                affected_sites=self._mode_type.affected_sites(self._entry),
                use_git=config.wato_use_git,
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
                user_id=user.id,
                affected_sites=affected_sites,
                use_git=config.wato_use_git,
            )

        self._save(
            entries,
            pprint_value=config.wato_pprint_config,
            debug=config.debug,
            use_git=config.wato_use_git,
        )

        return redirect(mode_url(self._mode_type.list_mode_name()))

    def _save(
        self, entries: dict[str, T], *, pprint_value: bool, debug: bool, use_git: bool
    ) -> None:
        self._store.save(entries, pprint_value=pprint_value)

    def page(self, config: Config, form_name: str = "edit") -> None:
        with html.form_context(form_name, method="POST"):
            self._page_form_quick_setup_warning()

            html.prevent_password_auto_completion()

            self._page_form_render_entry()

            forms.end()
            html.hidden_fields()

    def _page_form_quick_setup_warning(self) -> None:
        pass

    def _get_render_mode(self) -> tuple[RenderMode, FormSpec | None]:
        # No longer depends on global switch, but on the global switch
        # but on existence of the fs_individual_elements implementation
        try:
            self._fs_individual_elements()
        except NotImplementedError:
            return RenderMode.BACKEND, None

        # Frontend rendering is done via the Catalog class. There is no valuespec fallback
        return RenderMode.FRONTEND, self.catalog()

    def _page_form_render_entry(self) -> None:
        render_mode, form_spec = self._get_render_mode()
        match render_mode:
            case RenderMode.BACKEND:
                self._page_form_render_entry_valuespec()

            case RenderMode.FRONTEND:
                assert form_spec is not None
                # This prevents sending the form when pressing enter in an input field
                html.form_has_submit_button = True
                self._page_form_render_entry_form_spec(form_spec)

    def _page_form_render_entry_valuespec(self) -> None:
        vs = self.valuespec()
        vs.render_input("_edit", dict(self._entry) if not self._new or self._clone else {})
        vs.set_focus("_edit")

    def _page_form_render_entry_form_spec(self, form_spec: FormSpec) -> None:
        value, do_validate = self._get_render_settings()
        render_form_spec(form_spec, self._vue_field_id(), value, do_validate)

    def _vue_field_id(self) -> str:
        return f"_edit_{self._mode_type.type_name()}"

    def _get_render_settings(self) -> tuple[IncomingData, DoValidate]:
        if request.has_var(self._vue_field_id()):
            # The form was submitted, always validate data
            return (
                RawFrontendData(json.loads(request.get_str_input_mandatory(self._vue_field_id()))),
                True,
            )

        if self._new and self._clone is None:
            # New form, no validation
            return DEFAULT_VALUE, False

        if self._clone is not None:
            self._ident = self._clone

        # Existing entry from disk
        catalog_converter = self._get_catalog_converter()

        # The ident is not part of the saved config
        # So, the entry is not longer a type T
        cloned_entry: Any = copy.deepcopy(self._entry)
        cloned_entry["ident"] = self._ident
        catalog_config = catalog_converter.convert_flat_to_catalog_config(cloned_entry)
        return RawDiskData(catalog_config), True


def convert_dict_elements_vs2fs(elements: list[DictionaryEntry]) -> dict[str, DictElement]:
    # Transitional helper function, can be removed once all SimpleEditMode pages are converted
    # Wraps legacy dictionary valuespec elements into form spec elements
    fs_elements: dict[str, form_specs.DictElement[Any]] = {}
    for key, element in elements:
        fs_elements[key] = DictElement(
            parameter_form=LegacyValueSpec.wrap(element),
        )
    return fs_elements
