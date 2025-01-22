#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import cast

from flask import current_app

from cmk.gui import http, i18n
from cmk.gui.config import active_config
from cmk.gui.ctx_stack import set_global_var
from cmk.gui.display_options import DisplayOptions
from cmk.gui.htmllib.html import HTMLGenerator
from cmk.gui.http import request
from cmk.gui.theme import make_theme
from cmk.gui.utils.logging_filters import PrependURLFilter
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.output_funnel import OutputFunnel
from cmk.gui.utils.timeout_manager import TimeoutManager
from cmk.gui.utils.user_errors import UserErrors
from cmk.gui.wsgi.applications.checkmk import get_mime_type_from_output_format, get_output_format


def set_global_vars() -> None:
    # These variables will only be retained for the duration of the request.
    # *Flask* will clear them after the request finished.

    # Be aware that the order, in which these initialized is intentional.
    set_global_var("endpoint", None)
    set_global_var("translation", None)

    output_format = get_output_format(request.args.get("output_format", default="html", type=str))
    set_global_var("output_format", output_format)

    response = cast(http.Response, current_app.make_response(""))
    response.mimetype = get_mime_type_from_output_format(output_format)

    # The oder within this block is irrelevant.
    theme = make_theme(validate_choices=current_app.debug and not current_app.testing)
    theme.from_config(active_config.ui_theme)
    set_global_var("theme", theme)

    output_funnel = OutputFunnel(response)
    set_global_var("output_funnel", output_funnel)

    set_global_var("display_options", DisplayOptions())
    set_global_var("response", response)
    set_global_var("timeout_manager", TimeoutManager())
    set_global_var("url_filter", PrependURLFilter())
    set_global_var("user_errors", UserErrors())
    set_global_var(
        "html",
        HTMLGenerator(
            request,
            output_funnel=output_funnel,
            output_format=output_format,
            mobile=is_mobile(request, response),
        ),
    )

    lang_code = request.args.get("lang", default=active_config.default_language, type=str)
    i18n.localize(lang_code)  # sets g.translation
