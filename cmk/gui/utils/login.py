#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.userdb import SAMLUserConnectionConfig
from cmk.gui.userdb.type_defs import RelayState
from cmk.gui.utils.escaping import escape_text
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.utils.user_errors import user_errors


def show_saml2_login(
    saml_connections: list[SAMLUserConnectionConfig],
    saml2_user_error: str | None,
    origtarget: str,
) -> str | None:
    saml_css_class: list[str] = ["hot"]
    for connection in saml_connections:
        relay_state = RelayState(target_url=origtarget, connection_id=connection["id"])
        html.open_div(id_="saml_button")
        html.buttonlink(
            href=makeuri_contextless(
                request, [("RelayState", str(relay_state))], filename="saml_sso.py"
            ),
            text=f"{_('Login with')} {connection['name']}",
            obj_id="_saml2_login_button",
            class_=saml_css_class,
        )
        saml_css_class = []
        html.close_div()
        if (
            saml2_user_error := escape_text(
                request.get_str_input("_saml2_user_error"), escape_links=True
            )
        ) and request.get_str_input("_connection_id") == connection["id"]:
            user_errors.add(
                MKUserError(
                    varname=None,
                    message=saml2_user_error
                    + str(HTMLWriter.render_p(_("Please contact your administrator."))),
                )
            )
            show_user_errors(id_="login_error_saml2")

    if saml_connections:
        html.open_h2(class_=["login_separator"])
        html.span(_("or"))
        html.close_h2()

    return saml2_user_error


def show_user_errors(id_: str) -> None:
    html.open_div(id_=id_)
    html.show_user_errors()
    html.close_div()
