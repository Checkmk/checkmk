#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import uuid
from collections.abc import Collection, Mapping
from dataclasses import asdict
from typing import override

from cmk.gui import userdb
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs import RawDiskData, serialize_data_for_frontend
from cmk.gui.form_specs.unstable import (
    MultipleChoiceExtended,
    MultipleChoiceExtendedLayout,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
    TwoColumnDictionary,
)
from cmk.gui.form_specs.unstable.multiple_choice import MultipleChoiceElementExtended
from cmk.gui.form_specs.visitors.single_choice import SingleChoiceVisitor
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.oauth2_connections.watolib.store import (
    delete_oauth2_connection,
    load_oauth2_connections,
    OAuth2ConnectionsConfigFile,
)
from cmk.gui.page_menu import (
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.table import Table
from cmk.gui.type_defs import ActionResult, IconNames, PermissionName, StaticIcon
from cmk.gui.user_sites import get_configured_site_choices
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.wato import SimpleEditMode, SimpleListMode, SimpleModeType
from cmk.gui.wato._group_selection import sorted_contact_group_choices
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.passwords import load_passwords, remove_password
from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    DictGroup,
    Dictionary,
    FixedValue,
    Password,
    String,
    validators,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.shared_typing.mode_oauth2_connection import (
    AuthorityUrls,
    MicrosoftEntraIdUrls,
    Oauth2ConnectionConfig,
    Oauth2Urls,
)
from cmk.utils.oauth2_connection import OAuth2Connection


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeRedirectOAuth2Connection)
    mode_registry.register(ModeCreateOAuth2Connection)
    mode_registry.register(ModeOAuth2Connections)
    mode_registry.register(ModeMicrosoftEntraIdConnections)
    mode_registry.register(ModeCreateMicrosoftEntraIdConnection)


def uuid4_validator(error_msg: Message | None = None) -> validators.MatchRegex:
    return validators.MatchRegex(
        regex="^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$",
        error_msg=error_msg,
    )


def _custom_validate_editable_by(value: tuple[str, object]) -> None:
    if user.may("wato.edit_all_passwords"):
        return

    assert user.id
    match value:
        case ("administrators", None):
            raise ValidationError(
                Message(
                    "Only users with the permission 'Write access to all passwords' can assign ownership to 'Administrators'."
                )
            )
        case ("contact_group", group_name):
            user_groups = userdb.contactgroups_of_user(user.id)
            if group_name not in user_groups:
                raise ValidationError(
                    Message("You can only assign ownership to contact groups you are a member of.")
                )
        case _:
            pass


def get_oauth2_connection_form_spec(ident: str | None = None) -> Dictionary:
    return TwoColumnDictionary(
        title=Title("Define OAuth parameters"),
        elements={
            "ident": DictElement(
                required=True,
                render_only=True,
                parameter_form=String(
                    title=Title("OAuth2 connection ID"),
                    help_text=Help("A unique identifier for this OAuth2 connection."),
                    prefill=DefaultValue(ident or str(uuid.uuid4())),
                    custom_validate=[
                        uuid4_validator(
                            error_msg=Message("OAuth2 connection ID must be a valid UUID.")
                        ),
                    ],
                ),
                group=DictGroup(title=Title("Hidden")),
            ),
            "title": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Title"),
                    help_text=Help("A descriptive name for this OAuth2 connection."),
                    custom_validate=[
                        validators.LengthInRange(
                            min_value=1, error_msg=Message("Title is required")
                        ),
                    ],
                ),
                group=DictGroup(title=Title("General properties")),
            ),
            "editable_by": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Editable by"),
                    prefill=DefaultValue("administrators"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="administrators",
                            title=Title("Administrators"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="contact_group",
                            title=Title("Members of the contact group"),
                            parameter_form=SingleChoiceExtended(
                                title=Title("Select contact group"),
                                help_text=Help(
                                    "Select the contact group that can edit this OAuth2 connection."
                                ),
                                elements=[
                                    SingleChoiceElementExtended(
                                        name=name,
                                        title=Title("%s") % title,
                                    )
                                    for name, title in sorted_contact_group_choices()
                                ],
                            ),
                        ),
                    ],
                    custom_validate=[_custom_validate_editable_by],
                ),
                group=DictGroup(title=Title("General properties")),
            ),
            "shared_with": DictElement(
                required=True,
                parameter_form=MultipleChoiceExtended(
                    title=Title("Share with"),
                    elements=[
                        MultipleChoiceElementExtended(
                            name=name,
                            title=Title("%s") % title,
                        )
                        for name, title in sorted_contact_group_choices()
                    ],
                    show_toggle_all=True,
                    layout=MultipleChoiceExtendedLayout.dual_list,
                ),
                group=DictGroup(title=Title("General properties")),
            ),
            "sites": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Sites"),
                    help_text=Help(
                        "Restrict this OAuth2 connection to specific sites or make it available on all sites."
                    ),
                    prefill=DefaultValue("all"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="all",
                            title=Title("All sites"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="restricted",
                            title=Title("Restricted to specific sites"),
                            parameter_form=MultipleChoiceExtended(
                                title=Title("Site restriction"),
                                help_text=Help(
                                    "Restrict this OAuth2 connection to specific sites."
                                ),
                                elements=[
                                    MultipleChoiceElementExtended(
                                        name=site_id,
                                        title=Title("%s") % name,
                                    )
                                    for site_id, name in get_configured_site_choices()
                                ],
                                show_toggle_all=True,
                                layout=MultipleChoiceExtendedLayout.dual_list,
                            ),
                        ),
                    ],
                ),
                group=DictGroup(title=Title("General properties")),
            ),
            "authority": DictElement(
                required=True,
                parameter_form=SingleChoiceExtended(
                    title=Title("Authority"),
                    help_text=Help("Select the authority for the OAuth2 connection."),
                    elements=[
                        SingleChoiceElementExtended(
                            name="global",
                            title=Title("Global"),
                        ),
                        SingleChoiceElementExtended(
                            name="china",
                            title=Title("China"),
                        ),
                    ],
                    prefill=DefaultValue("global"),
                ),
                group=DictGroup(title=Title("IDs")),
            ),
            "tenant_id": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Directory (Tenant) ID"),
                    help_text=Help(
                        "The Directory (Tenant) ID of your Microsoft Entra ID instance."
                    ),
                    custom_validate=[
                        validators.LengthInRange(
                            min_value=1, error_msg=Message("Tenant ID is required")
                        ),
                        uuid4_validator(error_msg=Message("Tenant ID must be a valid UUID.")),
                    ],
                ),
                group=DictGroup(title=Title("IDs")),
            ),
            "client_id": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Application (Client) ID"),
                    help_text=Help("The Application (Client) ID of your registered application."),
                    custom_validate=[
                        validators.LengthInRange(
                            min_value=1, error_msg=Message("Client ID is required")
                        ),
                        uuid4_validator(error_msg=Message("Client ID must be a valid UUID.")),
                    ],
                ),
                group=DictGroup(title=Title("IDs")),
            ),
            "client_secret": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Client secret"),
                    help_text=Help("The Client secret of your registered application."),
                    custom_validate=[
                        validators.LengthInRange(
                            min_value=1, error_msg=Message("Client secret is required")
                        ),
                    ],
                ),
                group=DictGroup(title=Title("Secret")),
            ),
            "access_token": DictElement(
                render_only=True,
                required=True,
                parameter_form=Password(
                    title=Title("Access token"),
                    help_text=Help("The access token for this OAuth2 connection."),
                    custom_validate=[
                        validators.LengthInRange(
                            min_value=1, error_msg=Message("Access token is required")
                        ),
                    ],
                ),
                group=DictGroup(title=Title("Hidden")),
            ),
            "refresh_token": DictElement(
                render_only=True,
                required=True,
                parameter_form=Password(
                    title=Title("Refresh token"),
                    help_text=Help("The refresh token for this OAuth2 connection."),
                    custom_validate=[
                        validators.LengthInRange(
                            min_value=1, error_msg=Message("Refresh token is required")
                        ),
                    ],
                ),
                group=DictGroup(title=Title("Hidden")),
            ),
        },
    )


def get_oauth2_connection_config() -> Oauth2ConnectionConfig:
    return Oauth2ConnectionConfig(
        urls=Oauth2Urls(
            redirect=makeuri(request, [("mode", "redirect_oauth2_connection")]),
            back=makeuri(request, [("mode", "oauth2_connections")]),
            microsoft_entra_id=MicrosoftEntraIdUrls(
                global_=AuthorityUrls(
                    base_url="https://login.microsoftonline.com/###tenant_id###/oauth2/v2.0"
                ),
                china=AuthorityUrls(
                    base_url="https://login.chinacloudapi.cn/###tenant_id###/oauth2/v2.0"
                ),
            ),
        )
    )


def get_authority_mapping() -> Mapping[str, str]:
    return {
        SingleChoiceVisitor.option_id("global"): "global_",
        SingleChoiceVisitor.option_id("china"): "china",
    }


class OAuth2ModeType(SimpleModeType[OAuth2Connection]):
    def type_name(self) -> str:
        return "oauth2_connection"

    def name_singular(self) -> str:
        return _("OAuth2 connection")

    def is_site_specific(self) -> bool:
        return False

    def can_be_disabled(self) -> bool:
        return False

    def affected_config_domains(self) -> list[ABCConfigDomain]:
        return [ConfigDomainCore()]


class MicrosoftEntraIdModeType(SimpleModeType[OAuth2Connection]):
    def type_name(self) -> str:
        return "microsoft_entra_id_connection"

    def name_singular(self) -> str:
        return _("Microsoft Entra ID connection")

    def is_site_specific(self) -> bool:
        return False

    def can_be_disabled(self) -> bool:
        return False

    def edit_mode_name(self) -> str:
        return "edit_microsoft_entra_id_connection"

    def affected_config_domains(self) -> list[ABCConfigDomain]:
        return [ConfigDomainCore()]


class ModeOAuth2Connections(SimpleListMode[OAuth2Connection]):
    @classmethod
    def name(cls) -> str:
        return "oauth2_connections"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["general.oauth2_connections", "passwords"]

    def _table_title(self) -> str:
        return self.title()

    @classmethod
    def _connector_type(cls) -> str | None:
        return None

    def __init__(self, mode_type: SimpleModeType[OAuth2Connection] | None = None) -> None:
        super().__init__(
            mode_type=mode_type or OAuth2ModeType(),
            store=OAuth2ConnectionsConfigFile(),
        )

    def title(self) -> str:
        return _("OAuth2 connections")

    def page(self, config: Config) -> None:
        self._show_table(
            self._filter_for_connector_type(
                self._store.filter_editable_entries(self._store.load_for_reading())
            )
        )

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name=self._mode_type.type_name(),
                    title=self._mode_type.name_singular(),
                    topics=[
                        PageMenuTopic(
                            title=self._mode_type.name_singular(),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add Microsoft Entra ID connection"),
                                    icon_name=StaticIcon(IconNames.new),
                                    item=make_simple_link(
                                        makeuri_contextless(
                                            request,
                                            [
                                                (
                                                    "mode",
                                                    "edit_microsoft_entra_id_connection",
                                                ),
                                            ],
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

    def _filter_for_connector_type(
        self, entries: dict[str, OAuth2Connection]
    ) -> dict[str, OAuth2Connection]:
        if self._connector_type() is None:
            return entries
        return {
            ident: entry
            for ident, entry in entries.items()
            if entry["connector_type"] == self._connector_type()
        }

    def _show_entry_cells(self, table: Table, ident: str, entry: OAuth2Connection) -> None:
        table.cell(_("Title"), entry["title"])
        if self._connector_type() is None:
            table.cell(_("Connector type"), entry["connector_type"])
        table.cell(_("ID"), ident)

    def _delete_confirm_message(self) -> str:
        return " ".join(
            [
                _(
                    "<b>Beware:</b> The OAuth2 connection may be used in checks. If you "
                    "delete the connection, the checks won't be able to "
                    "authenticate with this connection anymore."
                ),
                super()._delete_confirm_message(),
            ]
        )

    @override
    def action(self, config: Config) -> ActionResult:
        if not transactions.transaction_valid():
            return None

        action_var = request.get_str_input("_action")
        if action_var is None:
            return None

        if not transactions.check_transaction():
            return redirect(mode_url(self._mode_type.list_mode_name()))

        ident = request.get_ascii_input("_delete")
        entries = load_oauth2_connections()
        if ident not in entries:
            raise MKUserError(
                "_delete", _("This %s does not exist.") % self._mode_type.name_singular()
            )

        self._delete_passwords(entries[ident], config)
        delete_oauth2_connection(
            ident,
            user_id=user.id,
            pprint_value=config.wato_pprint_config,
            use_git=config.wato_use_git,
        )
        return redirect(mode_url(self._mode_type.list_mode_name()))

    def _delete_passwords(self, entry: OAuth2Connection, config: Config) -> None:
        remove_password(
            entry["client_secret"][2][0],
            user_id=user.id,
            pprint_value=config.wato_pprint_config,
            use_git=config.wato_use_git,
        )
        remove_password(
            entry["access_token"][2][0],
            user_id=user.id,
            pprint_value=config.wato_pprint_config,
            use_git=config.wato_use_git,
        )
        remove_password(
            entry["refresh_token"][2][0],
            user_id=user.id,
            pprint_value=config.wato_pprint_config,
            use_git=config.wato_use_git,
        )


class ModeMicrosoftEntraIdConnections(ModeOAuth2Connections):
    def __init__(self) -> None:
        super().__init__(mode_type=MicrosoftEntraIdModeType())

    @classmethod
    @override
    def name(cls) -> str:
        return "microsoft_entra_id_connections"

    @override
    def title(self) -> str:
        return _("Microsoft Entra ID connections")

    @classmethod
    @override
    def _connector_type(cls) -> str | None:
        return "microsoft_entra_id"


class ModeCreateOAuth2Connection(SimpleEditMode[OAuth2Connection]):
    @classmethod
    @override
    def name(cls) -> str:
        return "edit_oauth2_connection"

    def __init__(self, mode_type: SimpleModeType[OAuth2Connection] | None = None) -> None:
        super().__init__(
            mode_type=mode_type or OAuth2ModeType(),
            store=OAuth2ConnectionsConfigFile(),
        )

    @classmethod
    def _connector_type(cls) -> str | None:
        return None

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["general.oauth2_connections", "passwords"]

    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode[None]] | None:
        return ModeOAuth2Connections

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(dropdowns=[], breadcrumb=breadcrumb)

    def _check_connection_permissions(self, editable_by: str | None) -> None:
        if user.may("wato.edit_all_passwords"):
            return

        if editable_by is None:
            raise MKUserError(
                "",
                _("You don't have permission to edit this %s.") % self._mode_type.name_singular(),
            )
        assert user.id
        if editable_by not in userdb.contactgroups_of_user(user.id):
            raise MKUserError(
                "",
                _("You don't have permission to edit this %s.") % self._mode_type.name_singular(),
            )

    @override
    def page(self, config: Config, form_name: str = "edit") -> None:
        html.enable_help_toggle()
        assert user.id
        if len(userdb.contactgroups_of_user(user.id)) == 0 and not user.may(
            "wato.edit_all_passwords"
        ):
            raise MKUserError(
                "",
                _("You need to be a member of at least one contact group to create a %s.")
                % self._mode_type.name_singular(),
            )

        if self._new:
            html.vue_component(
                "cmk-mode-create-oauth2-connection",
                data={
                    "new": True,
                    "config": asdict(get_oauth2_connection_config()),
                    "form_spec": asdict(
                        serialize_data_for_frontend(
                            form_spec=get_oauth2_connection_form_spec(),
                            field_id=form_name,
                            do_validate=False,
                        )
                    ),
                    "authority_mapping": get_authority_mapping(),
                    "connector_type": self._connector_type(),
                },
            )
            return

        client_secret = load_passwords()[self._entry["client_secret"][2][0]]
        editable_by = client_secret["owned_by"]
        self._check_connection_permissions(editable_by)

        if self._clone:
            html.vue_component(
                "cmk-mode-create-oauth2-connection",
                data={
                    "new": True,
                    "config": asdict(get_oauth2_connection_config()),
                    "form_spec": asdict(
                        serialize_data_for_frontend(
                            form_spec=get_oauth2_connection_form_spec(),
                            value=RawDiskData(
                                {k: v for k, v in self._entry.items() if k != "connector_type"}
                                | {
                                    "editable_by": ("contact_group", editable_by)
                                    if editable_by
                                    else ("administrators", None),
                                    "shared_with": client_secret["shared_with"],
                                }
                            ),
                            field_id=form_name,
                            do_validate=False,
                        )
                    ),
                    "authority_mapping": get_authority_mapping(),
                    "connector_type": self._entry["connector_type"],
                },
            )
            return

        html.vue_component(
            "cmk-mode-create-oauth2-connection",
            data={
                "new": False,
                "config": asdict(get_oauth2_connection_config()),
                "form_spec": asdict(
                    serialize_data_for_frontend(
                        form_spec=get_oauth2_connection_form_spec(self._ident),
                        value=RawDiskData(
                            value={k: v for k, v in self._entry.items() if k != "connector_type"}
                            | {
                                "editable_by": ("contact_group", editable_by)
                                if editable_by
                                else ("administrators", None),
                                "shared_with": client_secret["shared_with"],
                            }
                        ),
                        field_id=form_name,
                        do_validate=False,
                    )
                ),
                "authority_mapping": get_authority_mapping(),
                "connector_type": self._entry["connector_type"],
            },
        )


class ModeCreateMicrosoftEntraIdConnection(ModeCreateOAuth2Connection):
    def __init__(self) -> None:
        super().__init__(mode_type=MicrosoftEntraIdModeType())

    @classmethod
    @override
    def name(cls) -> str:
        return "edit_microsoft_entra_id_connection"

    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode[None]] | None:
        return ModeMicrosoftEntraIdConnections

    @classmethod
    @override
    def _connector_type(cls) -> str | None:
        return "microsoft_entra_id"


class ModeRedirectOAuth2Connection(WatoMode[None]):
    @classmethod
    @override
    def name(cls) -> str:
        return "redirect_oauth2_connection"

    @override
    def title(self) -> str:
        return _("OAuth2 connection")

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["general.oauth2_connections", "passwords"]

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(dropdowns=[], breadcrumb=breadcrumb)

    @override
    def page(self, config: Config) -> None:
        html.vue_component(
            "cmk-mode-redirect-oauth2-connection",
            data={"code": request.get_ascii_input("code")},
        )
