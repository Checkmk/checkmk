#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import flask

from cmk.gui.watolib import git


def test_add_message_commit_separation(flask_app: flask.Flask) -> None:
    prev = git._git_messages()
    assert not prev

    with flask_app.test_request_context("/NO_SITE/check_mk/login.py"):
        flask_app.preprocess_request()

        assert not git._git_messages()
        git.add_message("dingdong")
        assert git._git_messages() == ["dingdong"]

        flask_app.process_response(flask.Response())

    assert not git._git_messages()
    assert id(git._git_messages()) != id(prev)
