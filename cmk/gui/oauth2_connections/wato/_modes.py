#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import uuid
from collections.abc import Collection, Mapping
from dataclasses import asdict
from typing import override

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs import RawDiskData, serialize_data_for_frontend
from cmk.gui.form_specs.unstable import (
    SingleChoiceElementExtended,
    SingleChoiceExtended,
    TwoColumnDictionary,
)
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
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.wato import SimpleEditMode, SimpleListMode, SimpleModeType
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.passwords import remove_password
from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Password,
    String,
    validators,
)
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


def uuid4_validator(error_msg: Message | None = None) -> validators.MatchRegex:
    return validators.MatchRegex(
        regex="^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-4[0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$",
        error_msg=error_msg,
    )


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
            ),
            "tenant_id": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Tenant ID"),
                    help_text=Help("The Tenant ID of your Azure AD instance."),
                    custom_validate=[
                        validators.LengthInRange(
                            min_value=1, error_msg=Message("Tenant ID is required")
                        ),
                        uuid4_validator(error_msg=Message("Tenant ID must be a valid UUID.")),
                    ],
                ),
            ),
            "client_id": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Client ID"),
                    help_text=Help(
                        "The Client ID (Application ID) of your registered application."
                    ),
                    custom_validate=[
                        validators.LengthInRange(
                            min_value=1, error_msg=Message("Client ID is required")
                        ),
                        uuid4_validator(error_msg=Message("Tenant ID must be a valid UUID.")),
                    ],
                ),
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
            ),
            "access_token": DictElement(
                render_only=True,
                required=True,
                parameter_form=Password(
                    title=Title("Access token"),
                    help_text=Help("The access token for this OAuth2 connection."),
                ),
            ),
            "refresh_token": DictElement(
                render_only=True,
                required=True,
                parameter_form=Password(
                    title=Title("Refresh token"),
                    help_text=Help("The refresh token for this OAuth2 connection."),
                ),
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
        return "microsoft_entra_id"

    def name_singular(self) -> str:
        return _("Microsoft Entra ID connection")

    def is_site_specific(self) -> bool:
        return False

    def can_be_disabled(self) -> bool:
        return False

    def edit_mode_name(self) -> str:
        return "edit_oauth2_connection"

    def affected_config_domains(self) -> list[ABCConfigDomain]:
        return [ConfigDomainCore()]


class ModeOAuth2Connections(SimpleListMode[OAuth2Connection]):
    @classmethod
    def name(cls) -> str:
        return "oauth2_connections"

    def _table_title(self) -> str:
        if self._connector_type == "microsoft_entra_id":
            return _("Microsoft Entra ID connections")
        return _("OAuth2 connections")

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["general.oauth2_connections", "passwords"]

    def __init__(self) -> None:
        self._connector_type = request.get_ascii_input("connector_type")
        mode_type: SimpleModeType[OAuth2Connection]
        match self._connector_type:
            case "microsoft_entra_id":
                mode_type = MicrosoftEntraIdModeType()
            case _:
                mode_type = OAuth2ModeType()

        super().__init__(
            mode_type=mode_type,
            store=OAuth2ConnectionsConfigFile(),
        )

    def title(self) -> str:
        if self._connector_type == "microsoft_entra_id":
            return _("Microsoft Entra ID connections")
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
                                                    self._mode_type.edit_mode_name(),
                                                ),
                                                (
                                                    "connector_type",
                                                    "microsoft_entra_id",
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
        if self._connector_type is None:
            return entries
        return {
            ident: entry
            for ident, entry in entries.items()
            if entry["connector_type"] == self._connector_type
        }

    def _show_entry_cells(self, table: Table, ident: str, entry: OAuth2Connection) -> None:
        table.cell(_("Title"), entry["title"])
        if self._connector_type is None:
            table.cell(_("Connector type"), entry["connector_type"])
        table.cell(_("ID"), ident)

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


class ModeCreateOAuth2Connection(SimpleEditMode[OAuth2Connection]):
    @classmethod
    @override
    def name(cls) -> str:
        return "edit_oauth2_connection"

    def __init__(self) -> None:
        super().__init__(
            mode_type=OAuth2ModeType(),
            store=OAuth2ConnectionsConfigFile(),
        )

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

    @override
    def page(self, config: Config, form_name: str = "edit") -> None:
        html.enable_help_toggle()
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
                                value={
                                    "title": self._entry["title"] + " (Clone)",
                                    "authority": self._entry["authority"],
                                    "tenant_id": self._entry["tenant_id"],
                                    "client_id": self._entry["client_id"],
                                    "client_secret": self.entry["client_secret"],
                                    "access_token": self._entry["access_token"],
                                    "refresh_token": self._entry["refresh_token"],
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
                    "connector_type": request.get_ascii_input_mandatory("connector_type"),
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
                            value={
                                "ident": self._ident,
                                "title": self._entry["title"],
                                "authority": self._entry["authority"],
                                "tenant_id": self._entry["tenant_id"],
                                "client_id": self._entry["client_id"],
                                "client_secret": self.entry["client_secret"],
                                "access_token": self._entry["access_token"],
                                "refresh_token": self._entry["refresh_token"],
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
