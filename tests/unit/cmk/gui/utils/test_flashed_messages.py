#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from werkzeug.test import create_environ
from testlib.utils import DummyApplication

from cmk.gui.utils.flashed_messages import flash, get_flashed_messages
from cmk.gui.userdb import on_access, on_succeeded_login
from cmk.gui.globals import session, AppContext, RequestContext
import cmk.gui.login as login
import cmk.gui.htmllib as htmllib
import cmk.gui.http as http


def test_flash(with_user):
    user_id = with_user[0]

    environ = create_environ()
    # Execute the first request flash some message
    with AppContext(DummyApplication(environ, None)), \
            RequestContext(htmllib.html(http.Request(environ))) as request, \
            login.UserContext(user_id):
        session_id = on_succeeded_login(user_id)  # Create and activate session
        assert request.session is not None

        flash("abc")
        assert session.session_info.flashes == ["abc"]

    # Now create the second request to get the previously flashed message
    with AppContext(DummyApplication(environ, None)), \
            RequestContext(htmllib.html(http.Request(environ))), \
            login.UserContext(user_id):
        on_access(user_id, session_id)
        assert request.session is not None
        assert session.session_info.flashes == ["abc"]

        # Get the flashed messages removes the messages from the session
        # and subsequent calls to get_flashed_messages return the messages
        # over and over.
        assert get_flashed_messages() == ["abc"]
        assert get_flashed_messages() == ["abc"]
        assert session.session_info.flashes == []

    # Now create the third request that should not have access to the flashed messages since the
    # second one consumed them.
    with AppContext(DummyApplication(environ, None)), \
            RequestContext(htmllib.html(http.Request(environ))), \
            login.UserContext(user_id):
        on_access(user_id, session_id)
        assert request.session is not None
        assert session.session_info.flashes == []
        assert get_flashed_messages() == []
