#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import asdict
from typing import override

import requests

from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.shared_typing.mode_oauth2_connection import MsGraphApi


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
        post_data = asdict(data) | {
            "scope": ".default offline_access",
            "grant_type": "authorization_code",
        }
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

        if res.status_code != 200:
            return {"status": "error", "message": res.json()["error_description"]}

        # TODO: save oauth object
        return {"status": "success"}
