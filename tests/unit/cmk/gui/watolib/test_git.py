#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.utils.script_helpers import application_and_request_context
from cmk.gui.watolib import git


def test_add_message_commit_separation() -> None:
    with application_and_request_context():
        assert git._git_messages() == []
        git.add_message("dingdong")
        assert git._git_messages() == ["dingdong"]

    with application_and_request_context():
        assert git._git_messages() == []
        git.add_message("xyz")
        assert git._git_messages() == ["xyz"]
