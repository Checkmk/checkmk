#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import time
from typing import Optional

from cmk.utils.type_defs import UserId

from cmk.gui import userdb
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.login import set_auth_type, verify_automation_secret
from cmk.gui.utils.logged_in import UserContext
from cmk.gui.wsgi.type_defs import AuthType, RFC7662


def automation_auth(user_id: UserId, secret: str) -> Optional[RFC7662]:
    if verify_automation_secret(user_id, secret):
        return rfc7662_subject(user_id, "automation")

    return None


def gui_user_auth(user_id: UserId, secret: str) -> Optional[RFC7662]:
    try:
        if userdb.check_credentials(user_id, secret):
            return rfc7662_subject(user_id, "cookie")
    except MKUserError:
        # This is the case of "Automation user rejected". We don't care about that in the REST API
        # because every type of user is allowed in.
        return None

    return None


def rfc7662_subject(user_id: UserId, auth_type: AuthType) -> RFC7662:
    """Create a RFC7662 compatible user representation

    Args:
        user_id:
            The user's user_id

        auth_type:
            One of automation, cookie, web_server, http_header

    Returns:
        The filled out dictionary.
    """
    return {"sub": user_id, "iat": int(time.time()), "active": True, "scope": auth_type}


@contextlib.contextmanager
def set_user_context(user_id: UserId, token_info: RFC7662):
    if user_id and token_info and user_id == token_info.get("sub"):
        with UserContext(user_id):
            set_auth_type(token_info["scope"])
            yield
    else:
        raise MKAuthException("Unauthorized by verify_user")
