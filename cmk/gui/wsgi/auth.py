#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import time
from typing import Optional

from connexion import problem  # type: ignore[import]
from six import ensure_str

from cmk.utils.type_defs import UserId

from cmk.gui.config import clear_user_login, set_user_by_id
from cmk.gui.exceptions import MKException, MKAuthException, MKUserError
from cmk.gui.login import verify_automation_secret, set_auth_type

from cmk.gui.wsgi.wrappers import ParameterDict
from cmk.gui.wsgi.type_defs import RFC7662

MK_STATUS = {
    MKUserError: 400,
    MKAuthException: 401,
}


def bearer_auth(token: str) -> Optional[RFC7662]:
    try:
        user_id, secret = token.split(' ', 1)
    except ValueError:
        return None

    if not secret:
        return None

    if not user_id:
        return None

    if "/" in user_id:
        return None

    if verify_automation_secret(UserId(ensure_str(user_id)), secret):
        # Auth with automation secret succeeded - mark transid as unneeded in this case
        return _subject(user_id)

    return None


def _subject(user_id: str) -> RFC7662:
    # noinspection PyTypeChecker
    return {'sub': user_id, 'iat': int(time.time()), 'active': True}


@contextlib.contextmanager
def verify_user(user_id, token_info):
    if user_id and token_info and user_id == token_info.get('sub'):
        set_user_by_id(user_id)
        set_auth_type("automation")
        yield
        clear_user_login()
    else:
        raise MKAuthException("Unauthorized by verify_user")


def with_user(func):
    # NOTE: Don't use @functools.wraps here, as under Python3 connexion will only ever check the
    # signature of the wrapped function (which has no keyword arguments) and only gives us the
    # context if the wrapped function accepts keyword arguments (which it does not).
    def wrapper(*args, **kw):
        user_id = kw.get('user')
        token_info = kw.get('token_info')

        try:
            with verify_user(user_id, token_info):
                parameters = ParameterDict(kw)
                return func(parameters)
        except MKException as exc:
            return problem(
                status=MK_STATUS.get(type(exc), 500),
                title=str(exc),
                detail="An exception occurred.",
            )

    return wrapper
