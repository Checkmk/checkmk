#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Collection
from dataclasses import asdict
from typing import override, TypedDict

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import (
    PageMenu,
)
from cmk.gui.type_defs import PermissionName
from cmk.gui.utils.urls import makeuri
from cmk.gui.wato.pages.password_store import ModePasswords
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.shared_typing.mode_oauth2_connection import (
    AuthorityUrls,
    MsGraphApi,
    MsGraphApiUrls,
    Oauth2ConnectionConfig,
    Oauth2Urls,
)


class OAuthConnection(TypedDict):
    access_token: str
    refresh_token: str


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeRedirectOAuth2Connection)
    mode_registry.register(ModeCreateOAuth2Connection)


def get_oauth2_connection_config(connection: MsGraphApi | None = None) -> Oauth2ConnectionConfig:
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
        ),
        connection=connection,
    )


class ModeCreateOAuth2Connection(WatoMode[None]):
    @classmethod
    @override
    def name(cls) -> str:
        return "create_oauth2_connection"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts"]

    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode[None]] | None:
        return ModePasswords

    @override
    def title(self) -> str:
        return _("Add OAuth2 connection")

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(dropdowns=[], breadcrumb=breadcrumb)

    @override
    def page(self, config: Config) -> None:
        html.vue_component(
            "cmk-mode-create-oauth2-connection",
            data=asdict(get_oauth2_connection_config()),
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
        return ["hosts"]

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(dropdowns=[], breadcrumb=breadcrumb)

    @override
    def page(self, config: Config) -> None:
        html.vue_component(
            "cmk-mode-redirect-oauth2-connection",
            data={"code": request.get_ascii_input("code")},
        )
