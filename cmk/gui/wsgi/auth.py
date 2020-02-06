#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import functools
import time

from typing import Optional  # pylint: disable=unused-import

from connexion import problem  # type: ignore[import]

from cmk.utils.type_defs import UserId  # pylint: disable=unused-import
from cmk.utils.encoding import ensure_unicode

from cmk.gui.config import clear_user_login, set_user_by_id
from cmk.gui.exceptions import MKException, MKAuthException, MKUserError
from cmk.gui.login import verify_automation_secret, set_auth_type

from cmk.gui.wsgi.types import RFC7662  # pylint: disable=unused-import

MK_STATUS = {
    MKUserError: 404,
    MKAuthException: 401,
}


def bearer_auth(token):
    # type: (str) ->  Optional[RFC7662]
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

    if verify_automation_secret(UserId(ensure_unicode(user_id)), secret):
        # Auth with automation secret succeeded - mark transid as unneeded in this case
        return _subject(user_id)

    return None


def _subject(user_id):
    # type: (str) -> RFC7662
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
    @functools.wraps(func)
    def wrapper(*args, **kw):
        user_id = kw.get('user')
        token_info = kw.get('token_info')

        try:
            with verify_user(user_id, token_info):
                return func(*args, **kw)
        except MKException as exc:
            return problem(
                status=MK_STATUS.get(type(exc), 500),
                title=str(exc),
                detail="",
            )

    return wrapper
