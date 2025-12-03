#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, override

import requests

from cmk.ccc.site import omd_site
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs import (
    parse_and_validate_frontend_data,
    RawFrontendData,
)
from cmk.gui.logged_in import user
from cmk.gui.oauth2_connections.wato._modes import get_oauth_2_connection_form_spec
from cmk.gui.oauth2_connections.watolib.store import (
    load_oauth2_connections,
    OAuth2Connection,
    save_oauth2_connection,
    update_oauth2_connection,
)
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.watolib.passwords import load_passwords, save_password
from cmk.utils.global_ident_type import GlobalIdent, PROGRAM_ID_OAUTH
from cmk.utils.password_store import Password


def register(page_registry: PageRegistry) -> None:
    page_registry.register(
        PageEndpoint(
            "ajax_request_and_save_ms_graph_access_token", PageRequestAndSaveMsGraphAccessToken()
        )
    )


def _parse_client_secret(
    value: tuple[
        Literal["cmk_postprocessed"],
        Literal["explicit_password", "stored_password"],
        tuple[str, str],
    ],
) -> str:
    match value:
        case ("cmk_postprocessed", "stored_password", (password_id, str())):
            password_entries = load_passwords()
            password_entry = password_entries[password_id]
            if not password_entry:
                raise MKUserError("client_secret", f"Password with ID '{password_id}' not found")
            return str(password_entry["password"])
        case ("cmk_postprocessed", "explicit_password", (_password_id, password)):
            return str(password)
        case _:
            raise MKUserError("client_secret", "Incorrect format for secret value")


class PageRequestAndSaveMsGraphAccessToken(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        result = ctx.request.get_json()
        data = parse_and_validate_frontend_data(
            get_oauth_2_connection_form_spec(), RawFrontendData(value=result["data"])
        )
        assert isinstance(data, dict)
        if not (ident := result.get("id")):
            return {"status": "error", "message": f"ID missing in request data: {data}"}

        if not (title := data.get("title")):
            return {"status": "error", "message": f"Title missing in request data: {data}"}

        if not (client_id := data.get("client_id")):
            return {"status": "error", "message": f"Client ID missing in request data: {data}"}

        if not (client_secret_raw := data.get("client_secret")):
            return {"status": "error", "message": f"Client secret missing in request data: {data}"}

        if not (tenant_id := data.get("tenant_id")):
            return {"status": "error", "message": f"Tenant ID missing in request data: {data}"}

        if not (authority := data.get("authority")):
            return {"status": "error", "message": f"Authority missing in request data: {data}"}

        client_secret = _parse_client_secret(client_secret_raw)
        post_data = data | {
            "scope": ".default offline_access",
            "grant_type": "authorization_code",
            "redirect_uri": result.get("redirect_uri"),
            "code": result.get("code"),
            "client_secret": client_secret,
        }
        try:
            match authority:
                case "china":
                    res = requests.post(
                        url=f"https://login.chinacloudapi.cn/{tenant_id}/oauth2/v2.0/token",
                        data=post_data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=10,
                    )
                case "global":
                    res = requests.post(
                        url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
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
            ident=ident,
            title=title,
            client_secret=client_secret,
            access_token=access_token,
            refresh_token=refresh_token,
            config=ctx.config,
        )

        self._save_reference_to_config_file(
            ident=ident,
            title=title,
            client_id=client_id,
            tenant_id=tenant_id,
            authority=authority,
            config=ctx.config,
        )

        return {"status": "success"}

    def _save_token_to_passwordstore(
        self,
        *,
        ident: str,
        title: str,
        client_secret: str,
        access_token: str,
        refresh_token: str,
        config: Config,
    ) -> None:
        # TODO Think site_id should be in data above
        site_id = omd_site()
        password_entries = load_passwords()
        for pw_title, entry, password in [
            ("Client secret", "client_secret", client_secret),
            ("Access token", "access_token", access_token),
            ("Refresh token", "refresh_token", refresh_token),
        ]:
            password_ident = f"{ident}_{entry}"
            save_password(
                ident=password_ident,
                details=Password(
                    title=pw_title,
                    comment=title,
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
                user_id=user.id,
                pprint_value=config.wato_pprint_config,
                use_git=config.wato_use_git,
            )

    def _save_reference_to_config_file(
        self,
        *,
        ident: str,
        title: str,
        client_id: str,
        tenant_id: str,
        authority: str,
        config: Config,
    ) -> None:
        details = OAuth2Connection(
            title=title,
            access_token_reference=f"{ident}_access_token",
            client_id=client_id,
            client_secret_reference=f"{ident}_client_secret",
            refresh_token_reference=f"{ident}_refresh_token",
            tenant_id=tenant_id,
            authority=authority,
        )
        if ident in load_oauth2_connections():
            update_oauth2_connection(
                ident=ident,
                details=details,
                user_id=user.id,
                pprint_value=config.wato_pprint_config,
                use_git=config.wato_use_git,
            )
            return
        save_oauth2_connection(
            ident=ident,
            details=details,
            user_id=user.id,
            pprint_value=config.wato_pprint_config,
            use_git=config.wato_use_git,
        )
