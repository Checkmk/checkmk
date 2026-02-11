#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

import requests

from cmk.gui import userdb
from cmk.gui.form_specs import (
    get_visitor,
    parse_and_validate_frontend_data,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.form_specs.visitors._utils import option_id
from cmk.gui.logged_in import user
from cmk.gui.oauth2_connections.wato._modes import get_oauth2_connection_form_spec
from cmk.gui.oauth2_connections.watolib.store import extract_password_store_entry
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult


def register(page_registry: PageRegistry) -> None:
    page_registry.register(
        PageEndpoint("ajax_request_ms_graph_access_token", PageRequestAndSaveMsGraphAccessToken())
    )


class PageRequestAndSaveMsGraphAccessToken(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        result = ctx.request.get_json()
        form_spec = get_oauth2_connection_form_spec()
        visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))
        editable_by: tuple[str, str | None]
        if user.may("wato.edit_all_passwords"):
            editable_by = ("administrators", None)
        else:
            assert user.id
            editable_by = ("contact_group", option_id(userdb.contactgroups_of_user(user.id)[0]))
        data = parse_and_validate_frontend_data(
            form_spec,
            RawFrontendData(
                value=result["data"]
                | {
                    "title": "dummy",
                    "editable_by": editable_by,
                    "shared_with": [],
                }
            ),
        )
        assert isinstance(data, dict)
        if not (client_secret_raw := data.get("client_secret")):
            return {"status": "error", "message": f"Client secret missing in request data: {data}"}

        if not (tenant_id := data.get("tenant_id")):
            return {"status": "error", "message": f"Tenant ID missing in request data: {data}"}

        if not (authority := data.get("authority")):
            return {"status": "error", "message": f"Authority missing in request data: {data}"}

        client_secret = extract_password_store_entry(client_secret_raw)
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
            return {"status": "error", "message": f"{e}", "error_data": res.json()}

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

        return {
            "status": "success",
            "data": visitor.to_vue(
                RawDiskData(
                    value=data
                    | {
                        "access_token": (
                            "cmk_postprocessed",
                            "explicit_password",
                            ("", access_token),
                        ),
                        "refresh_token": (
                            "cmk_postprocessed",
                            "explicit_password",
                            ("", refresh_token),
                        ),
                    }
                )
            )[1],
        }
