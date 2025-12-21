#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from dataclasses import asdict, dataclass

from cmk.gui.config import Config
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, Response
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.site_config import has_distributed_setup_remote_sites, is_distributed_setup_remote_site
from cmk.gui.utils.product_telemetry_popup_cookie import (
    product_telemetry_popup_timestamp_cookie,
    set_user_product_telemetry_popup_cookie,
)
from cmk.gui.utils.urls import makeuri
from cmk.product_telemetry.config import load_telemetry_config
from cmk.shared_typing.product_telemetry import ProductTelemetryConfig


@dataclass
class ProductTelemetryConfigTyped(ProductTelemetryConfig): ...


__telemetry_popup_enabled = True


def disable_telemetry_popup() -> None:
    global __telemetry_popup_enabled
    __telemetry_popup_enabled = False


def render_product_telemetry_popup(
    active_config: Config, user: LoggedInUser, request: Request, response: Response
) -> None:
    # Show product telemetry popup if user is admin and the site is a central site (in case of distributed setup) and has not decided about telemetry
    # We show the popup only after 30 days have passed since the first login. After 30 days, we keep showing the popup
    # on every login until the user makes a decision.

    is_not_distributed_setup = not has_distributed_setup_remote_sites(
        active_config.sites
    ) and not is_distributed_setup_remote_site(active_config.sites)
    is_central_site_in_distributed_setup = has_distributed_setup_remote_sites(
        active_config.sites
    ) and not is_distributed_setup_remote_site(active_config.sites)

    if not __telemetry_popup_enabled:
        return

    if "admin" in user.role_ids:
        if is_not_distributed_setup or is_central_site_in_distributed_setup:
            telemetry_choice = load_telemetry_config(logger).state == "not_decided"

            if telemetry_choice:
                popup_timestamp_cookie = product_telemetry_popup_timestamp_cookie(request)

                if popup_timestamp_cookie is None:
                    set_user_product_telemetry_popup_cookie(request, response)
                else:
                    # Check if 30 days (2592000 seconds) have passed since first login
                    THIRTY_DAYS_IN_SECONDS = 2592000
                    current_timestamp = datetime.datetime.now().timestamp()
                    time_difference = current_timestamp - popup_timestamp_cookie

                    if time_difference >= THIRTY_DAYS_IN_SECONDS:
                        _show_product_telemetry_popup(request)
                        set_user_product_telemetry_popup_cookie(request, response)


def _show_product_telemetry_popup(request: Request) -> None:
    html.vue_component(
        "cmk-product-telemetry",
        data=asdict(
            ProductTelemetryConfigTyped(
                global_settings_link=makeuri(
                    request,
                    addvars=[("mode", "edit_configvar"), ("varname", "product_telemetry")],
                    filename="wato.py",
                ),
            )
        ),
    )
