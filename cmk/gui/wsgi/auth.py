#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
import contextlib
import functools
import time

from typing import Optional  # pylint: disable=unused-import

from connexion import problem  # type: ignore

from cmk.gui.config import clear_user_login
from cmk.gui.exceptions import MKException, MKAuthException, MKUserError
from cmk.gui.globals import html
from cmk.gui.login import verify_automation_secret, set_auth_type, login

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

    if verify_automation_secret(user_id, secret):
        # Auth with automation secret succeeded - mark transid as unneeded in this case
        return _subject(user_id)

    return None


def _subject(user_id):
    # type: (str) -> RFC7662
    # noinspection PyTypeChecker
    return {'sub': user_id, 'iat': int(time.time()), 'active': True}


@contextlib.contextmanager
def verify_user(user, token_info):
    if user and token_info and user == token_info.get('sub'):
        login(user)
        set_auth_type("automation")
        yield
        html.finalize()
        clear_user_login()
    else:
        raise MKAuthException("Unauthorized")


def with_user(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        user = kw.get('user')
        token_info = kw.get('token_info')

        try:
            with verify_user(user, token_info):
                return func(*args, **kw)
        except MKException as exc:
            return problem(
                status=MK_STATUS.get(type(exc), 500),
                title=str(exc),
                detail="",
            )

    return wrapper
