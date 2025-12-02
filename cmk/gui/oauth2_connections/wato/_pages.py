#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict
from typing import override

import requests

from cmk.ccc.site import omd_site
from cmk.gui.oauth2_connections.watolib.store import OAuth2Connection, save_oauth2_connection
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.watolib.passwords import load_passwords, save_password
from cmk.shared_typing.mode_oauth2_connection import MsGraphApi
from cmk.utils.global_ident_type import GlobalIdent, PROGRAM_ID_OAUTH
from cmk.utils.password_store import Password


def register(page_registry: PageRegistry) -> None:
    page_registry.register(
        PageEndpoint(
            "ajax_request_and_save_ms_graph_access_token", PageRequestAndSaveMsGraphAccessToken()
        )
    )


class PageRequestAndSaveMsGraphAccessToken(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        data = MsGraphApi(**ctx.request.get_json())
        if not (ident := data.id):
            return {"status": "error", "message": f"ID missing in request data: {data}"}

        if not (title := data.title):
            return {"status": "error", "message": f"Title missing in request data: {data}"}

        if not (client_id := data.client_id):
            return {"status": "error", "message": f"Client ID missing in request data: {data}"}

        if not (client_secret := data.client_secret):
            return {"status": "error", "message": f"Client secret missing in request data: {data}"}

        if not (tenant_id := data.tenant_id):
            return {"status": "error", "message": f"Tenant ID missing in request data: {data}"}

        post_data = asdict(data) | {
            "scope": ".default offline_access",
            "grant_type": "authorization_code",
        }
        try:
            match data.authority:
                case "china":
                    res = requests.post(
                        url=f"https://login.chinacloudapi.cn/{data.tenant_id}/oauth2/v2.0/token",
                        data=post_data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=10,
                    )
                case "global_":
                    res = requests.post(
                        url=f"https://login.microsoftonline.com/{data.tenant_id}/oauth2/v2.0/token",
                        data=post_data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=10,
                    )
                case _:
                    return {"status": "error", "message": "Invalid authority"}

        except requests.exceptions.Timeout as timeout_exc:
            return {"status": "error", "message": f"Timeout error: {timeout_exc}"}
        except requests.exceptions.ConnectionError as connection_exc:
            return {"status": "error", "message": f"Connection error: {connection_exc}"}
        except Exception as e:
            return {"status": "error", "message": f"Unhandled error: {e}"}

        try:
            res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            return {"status": "error", "message": f"HTTP error: {e}, {res.text}"}

        try:
            response_json = res.json()
        except ValueError:
            return {
                "status": "error",
                "message": f"Answer contains no valid JSON format: {res.text}",
            }

        if (access_token := response_json.get("access_token")) is None or (
            refresh_token := response_json.get("refresh_token")
        ) is None:
            return {"status": "error", "message": f"Access or refresh token missing: {res.text}"}

        self._save_token_to_passwordstore(
            ident,
            title,
            access_token,
            refresh_token,
            client_secret,
        )

        self._save_reference_to_config_file(
            ident,
            title,
            client_id,
            tenant_id,
        )

        return {"status": "success"}

    def _save_token_to_passwordstore(
        self,
        ident: str,
        description: str,
        client_secret: str,
        access_token: str,
        refresh_token: str,
    ) -> None:
        # TODO Think site_id should be in data above
        site_id = omd_site()
        password_entries = load_passwords()
        for title, entry, password in [
            ("Client secret", "client_secret", client_secret),
            ("Access token", "access_token", access_token),
            ("Refresh token", "refresh_token", refresh_token),
        ]:
            password_ident = f"{ident}_{entry}"
            save_password(
                ident=password_ident,
                details=Password(
                    title=title,
                    comment=description,
                    docu_url="",
                    password=password,
                    owned_by=None,
                    shared_with=[],
                    locked_by=GlobalIdent(
                        site_id=site_id,
                        program_id=PROGRAM_ID_OAUTH,
                        instance_id=ident,
                    ),
                ),
                new_password=password_ident not in password_entries,
                user_id=None,
                pprint_value=True,
                use_git=True,
            )

    def _save_reference_to_config_file(
        self,
        ident: str,
        title: str,
        client_id: str,
        tenant_id: str,
    ) -> None:
        save_oauth2_connection(
            ident=ident,
            details=OAuth2Connection(
                title=title,
                access_token_reference=f"{ident}_access_token",
                client_id=client_id,
                client_secret_reference=f"{ident}_client_secret",
                refresh_token_reference=f"{ident}_refresh_token",
                tenant_id=tenant_id,
            ),
            pprint_value=True,
        )
