#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from flask import session

from cmk.utils.exceptions import MKGeneralException

from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInNobody


def check_csrf_token(token: str | None = None) -> None:
    # We have to assert the attributes, due to importing flask.session because of
    # circular imports.
    assert hasattr(session, "user")  # mypy
    if isinstance(session.user, LoggedInNobody):
        return

    csrf_token = token or request.get_str_input("csrf_token")
    if csrf_token is None:
        csrf_token = request.get_request().get("csrf_token")

    if csrf_token is None:
        raise MKGeneralException(_("No CSRF token received"))

    assert hasattr(session, "session_info")  # mypy
    if csrf_token != session.session_info.csrf_token:
        raise MKGeneralException(
            _("Invalid CSRF token (%r) for Session (%r)")
            % (csrf_token, session.session_info.session_id)
        )
