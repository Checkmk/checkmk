#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=cmk-module-layer-violation

import datetime
import logging

from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, Response
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.site_config import has_wato_slave_sites, is_wato_slave_site
from cmk.gui.utils.html import HTML
from cmk.gui.utils.product_usage_analytics_popup_cookie import (
    product_usage_analytics_popup_timestamp_cookie,
    set_user_product_usage_analytics_popup_cookie,
)
from cmk.gui.utils.urls import makeuri

from cmk.product_usage.config import load_config

__popup_enabled = True


def disable_product_usage_analytics_popup() -> None:
    global __popup_enabled  # noqa: PLW0603
    __popup_enabled = False


def render_product_usage_analytics_popup(
    user: LoggedInUser, request: Request, response: Response
) -> None:
    # Show product usage analytics popup if user is admin and the site is a central site (in case of distributed setup) and has not decided about product usage analytics
    # We show the popup only after 30 days have passed since the first login. After 30 days, we keep showing the popup
    # on every login until the user makes a decision.

    is_not_distributed_setup = not has_wato_slave_sites() and not is_wato_slave_site()
    is_central_site_in_distributed_setup = has_wato_slave_sites() and not is_wato_slave_site()

    if not __popup_enabled:
        return

    if "admin" in user.role_ids:
        if is_not_distributed_setup or is_central_site_in_distributed_setup:
            analytics_choice = load_config(logging.getLogger()).state == "not_decided"

            if analytics_choice:
                popup_timestamp_cookie = product_usage_analytics_popup_timestamp_cookie(request)

                if popup_timestamp_cookie is None:
                    set_user_product_usage_analytics_popup_cookie(request, response)
                else:
                    # Check if 30 days (2592000 seconds) have passed since first login
                    THIRTY_DAYS_IN_SECONDS = 2592000
                    current_timestamp = datetime.datetime.now().timestamp()
                    time_difference = current_timestamp - popup_timestamp_cookie

                    if time_difference >= THIRTY_DAYS_IN_SECONDS:
                        _show_product_usage_analytics_popup(request)
                        set_user_product_usage_analytics_popup_cookie(request, response)


def _show_product_usage_analytics_popup(request: Request) -> None:
    settings_url = makeuri(
        request,
        addvars=[("mode", "edit_configvar"), ("varname", "product_usage_analytics")],
        filename="wato.py",
    )

    title = _("Help us improve Checkmk with product usage analytics")

    html.open_div(class_="modal_overlay", id_="product_usage_analytics_popup_overlay")
    html.open_div(class_="container")
    html.h2(title)

    html.open_div(class_="content")
    html.p(
        html.render_b(_("We want to understand how you use Checkmk. "))
        + _(
            "Product usage analytics allows us to make data-driven decisions and focus development on what parts of Checkmk you regularly use. "
            "The data you share will help us prioritize the features that matter most to you."
        )
    )

    html.h3(_("What data are we collecting?"))

    html.open_ul()
    html.li(
        html.render_b(_("We collect: "))
        + HTML(
            _(
                "data about the general usage of features and configuration options (e.g., counts of hosts, folders, plug-ins, MKPs, and services)."
            )
        )
    )
    html.li(
        html.render_b(_("We do NOT collect: "))
        + HTML(
            _(
                "any data about users or their behavior (e.g., PII) or possibly sensitive identifiers about your environment (e.g., hostnames, file paths, service names)."
            )
        )
    )
    html.close_ul()

    html.p(
        html.render_b(_("Important: "))
        + _(
            "The names of custom check plug-ins (either developed internally or installed as an MKP from the Checkmk Exchange) will be collected as part of the product usage data. "
            "If you use MKPs, we recommend you inspect the data carefully via the data download option to verify the content before opting in, to ensure no sensitive data is included. "
            "Do not enable product usage analytics if you do not wish to share this information."
        )
    )

    html.p(
        html.render_b(_("Product usage analytics is turned off by default. "))
        + _(
            "We believe in only receiving data you explicitly choose to share. You can enable sharing analytics data any time from global settings. "
            "If you do not wish to be reminded, please manage your preferences in global settings."
        )
    )
    html.close_div()

    html.open_div(class_="footer")
    html.input(
        name="product_usage_analytics_ask_later",
        type_="button",
        value=_("Remind me again in 30 days"),
        onclick="document.getElementById('product_usage_analytics_popup_overlay').remove();",
        class_="button",
    )
    html.a(
        _("Manage in global settings"),
        href=settings_url,
        class_=["button", "hot"],
        target="main",
        onclick="document.getElementById('product_usage_analytics_popup_overlay').remove();",
    )
    html.close_div()
    html.close_div()
    html.close_div()

    html.final_javascript("""
        setTimeout(function() {
            var popup = document.getElementById('product_usage_analytics_popup_overlay');
            if (popup) {
                popup.style.display = 'block';
            }
        }, 100);
    """)
