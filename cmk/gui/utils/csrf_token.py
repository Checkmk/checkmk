#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional

from cmk.utils.exceptions import MKGeneralException

from cmk.gui.globals import html, request, session
from cmk.gui.i18n import _


def check_csrf_token(token: Optional[str] = None) -> None:
    # session is LocalProxy, only on access it is None, so we cannot test on 'is None'
    if not hasattr(session, "session_info"):
        return

    csrf_token = token or request.get_str_input("csrf_token")
    if csrf_token is None:
        csrf_token = html.get_request().get("csrf_token")

    if csrf_token is None:
        raise MKGeneralException(_("No CSRF token received"))
    if csrf_token != session.session_info.csrf_token:
        raise MKGeneralException(
            _("Invalid CSRF token (%r) for Session (%r)") %
            (csrf_token, session.session_info.session_id))
