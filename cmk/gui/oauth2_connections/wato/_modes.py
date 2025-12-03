#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Collection, Mapping
from dataclasses import asdict
from typing import override

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
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
from cmk.gui.oauth2_connections.watolib.store import OAuth2Connection, OAuth2ConnectionsConfigFile
from cmk.gui.page_menu import (
    PageMenu,
)
from cmk.gui.table import Table
from cmk.gui.type_defs import PermissionName
from cmk.gui.utils.urls import makeuri
from cmk.gui.wato import SimpleEditMode, SimpleListMode, SimpleModeType
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Password,
    String,
)
from cmk.shared_typing.mode_oauth2_connection import (
    AuthorityUrls,
    MsGraphApiUrls,
    Oauth2ConnectionConfig,
    Oauth2Urls,
)


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeRedirectOAuth2Connection)
    mode_registry.register(ModeCreateOAuth2Connection)
    mode_registry.register(ModeOAuth2Connections)


def get_oauth_2_connection_form_spec() -> Dictionary:
    return TwoColumnDictionary(
        title=Title("Define OAuth parameters"),
        elements={
            "title": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Title"),
                    help_text=Help("A descriptive name for this OAuth2 connection."),
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
                ),
            ),
            "client_id": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Client ID"),
                    help_text=Help(
                        "The Client ID (Application ID) of your registered application."
                    ),
                ),
            ),
            "client_secret": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Client secret"),
                    help_text=Help("The Client secret of your registered application."),
                ),
            ),
        },
    )


def get_oauth2_connection_config() -> Oauth2ConnectionConfig:
    return Oauth2ConnectionConfig(
        urls=Oauth2Urls(
            redirect=makeuri(request, [("mode", "redirect_oauth2_connection")]),
            ms_graph_api=MsGraphApiUrls(
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


class ModeOAuth2Connections(SimpleListMode[OAuth2Connection]):
    @classmethod
    def name(cls) -> str:
        return "oauth2_connections"

    def _table_title(self) -> str:
        return _("OAuth2 connections")

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts"]  # TODO: add correct permissions

    def __init__(self) -> None:
        super().__init__(
            mode_type=OAuth2ModeType(),
            store=OAuth2ConnectionsConfigFile(),
        )

    def title(self) -> str:
        return _("OAuth2 connections")

    def page(self, config: Config) -> None:
        super().page(config)

    def _show_entry_cells(self, table: Table, ident: str, entry: OAuth2Connection) -> None:
        table.cell(_("ID"), ident)
        table.cell(_("Title"), entry["title"])


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
        return ["hosts"]  # TODO: add correct permissions

    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode[None]] | None:
        return ModeOAuth2Connections

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(dropdowns=[], breadcrumb=breadcrumb)

    @override
    def page(self, config: Config, form_name: str = "edit") -> None:
        if self._clone:
            html.vue_component(
                "cmk-mode-create-oauth2-connection",
                data={
                    "config": asdict(get_oauth2_connection_config()),
                    "form_spec": asdict(
                        serialize_data_for_frontend(
                            form_spec=get_oauth_2_connection_form_spec(),
                            value=RawDiskData(
                                value={
                                    "title": self._entry["title"] + " (Clone)",
                                    "authority": self._entry["authority"],
                                    "tenant_id": self._entry["tenant_id"],
                                    "client_id": self._entry["client_id"],
                                    "client_secret": (
                                        "cmk_postprocessed",
                                        "stored_password",
                                        (self._entry["client_secret_reference"], ""),
                                    ),
                                }
                            ),
                            field_id=form_name,
                            do_validate=False,
                        )
                    ),
                    "authority_mapping": get_authority_mapping(),
                },
            )
            return

        if self._new:
            html.vue_component(
                "cmk-mode-create-oauth2-connection",
                data={
                    "config": asdict(get_oauth2_connection_config()),
                    "form_spec": asdict(
                        serialize_data_for_frontend(
                            form_spec=get_oauth_2_connection_form_spec(),
                            field_id=form_name,
                            do_validate=False,
                        )
                    ),
                    "authority_mapping": get_authority_mapping(),
                },
            )
            return

        html.vue_component(
            "cmk-mode-create-oauth2-connection",
            data={
                "config": asdict(get_oauth2_connection_config()),
                "form_spec": asdict(
                    serialize_data_for_frontend(
                        form_spec=get_oauth_2_connection_form_spec(),
                        value=RawDiskData(
                            value={
                                "title": self._entry["title"],
                                "authority": self._entry["authority"],
                                "tenant_id": self._entry["tenant_id"],
                                "client_id": self._entry["client_id"],
                                "client_secret": (
                                    "cmk_postprocessed",
                                    "stored_password",
                                    (self._entry["client_secret_reference"], ""),
                                ),
                            }
                        ),
                        field_id=form_name,
                        do_validate=False,
                    )
                ),
                "ident": self._ident,
                "authority_mapping": get_authority_mapping(),
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
        return ["hosts"]  # TODO: add correct permissions

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(dropdowns=[], breadcrumb=breadcrumb)

    @override
    def page(self, config: Config) -> None:
        html.vue_component(
            "cmk-mode-redirect-oauth2-connection",
            data={"code": request.get_ascii_input("code")},
        )
