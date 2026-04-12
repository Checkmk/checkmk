#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import active_config
from cmk.gui.htmllib.html import html
from cmk.gui.http import Response, response
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.theme.current_theme import theme


def page_dashboard_token_invalid() -> Response:
    def _render_main_logo() -> None:
        html.open_div(class_="cmk_main_logo")
        html.open_a(href="https://checkmk.com", class_="logo_link")
        html.img(
            src=theme.detect_icon_path(
                icon_name="login_logo" if theme.has_custom_logo("login_logo") else "checkmk_logo",
                prefix="",
            ),
            id_="logo",
        )
        html.close_a()
        html.close_div()

    def _render_not_available_image() -> None:
        html.open_div(id_="error_image_container")
        html.img(
            src=theme.detect_icon_path(
                icon_name="site_unreachable",
                prefix="",
            ),
            id_="unavailable_icon",
        )
        html.close_div()  # error_image_container

    def _render_message_text_container() -> None:
        html.open_div(class_="message_text_container")
        html.h1(_("Dashboard not available"))
        html.open_div()
        html.p(_("This shared link is not valid."))
        html.p(_("Contact the dashboard owner if you need access."))
        html.close_div()
        html.close_div()  # message_text_container

    html.body_start(
        title=_("Token invalid"),
        main_javascript="side",
        lang=user.language,
        inject_js_profiling_code=active_config.inject_js_profiling_code,
        load_frontend_vue=active_config.load_frontend_vue,
        custom_style_sheet=active_config.custom_style_sheet,
        screenshotmode=active_config.screenshotmode,
        inline_help_as_text=user.inline_help_as_text,
    )
    html.begin_page_content(enable_scrollbar=False)

    html.open_div(id_="cmk_shared_dashboard_error_page")
    _render_main_logo()

    html.open_div(class_="error_message_container")
    _render_not_available_image()
    _render_message_text_container()
    html.close_div()  # error_message_container

    html.close_div()  # cmk_shared_dashboard_error_page
    html.footer()

    return response
