#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import time

from six import ensure_str

from cmk.utils.type_defs import UserId

from cmk.gui.config import clear_user_login, set_user_by_id
from cmk.gui.exceptions import MKAuthException
from cmk.gui.login import verify_automation_secret, set_auth_type

from cmk.gui.wsgi.type_defs import RFC7662


def bearer_auth(auth_header: str) -> RFC7662:
    try:
        _, token = auth_header.split("Bearer", 1)
    except ValueError:
        raise MKAuthException(None, "Not a valid Bearer token.")

    try:
        user_id, secret = token.strip().split(' ', 1)
    except ValueError:
        raise MKAuthException("No user/password combination in Bearer token.")

    if not secret:
        raise MKAuthException("Empty password not allowed.")

    if not user_id:
        raise MKAuthException("Empty user not allowed.")

    if "/" in user_id:
        raise MKAuthException("No slashes / allowed in username.")

    if not verify_automation_secret(UserId(ensure_str(user_id)), secret):
        raise MKAuthException("Not authenticated.")

    # Auth with automation secret succeeded - mark transid as unneeded in this case
    return rfc7662_subject(user_id, 'automation')


def rfc7662_subject(user_id: str, auth_type: str) -> RFC7662:
    return {'sub': user_id, 'iat': int(time.time()), 'active': True, 'scope': auth_type}


@contextlib.contextmanager
def verify_user(user_id, token_info):
    if user_id and token_info and user_id == token_info.get('sub'):
        set_user_by_id(user_id)
        set_auth_type("automation")
        yield
        clear_user_login()
    else:
        raise MKAuthException("Unauthorized by verify_user")
