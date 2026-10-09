#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from werkzeug.test import create_environ

from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.logged_in import LoggedInNobody, LoggedInSuperUser
from cmk.gui.painter_options import PainterOptions


def test_painter_options_are_permitted_to_a_user_granted_them() -> None:
    options = PainterOptions(Config(), Request(create_environ()), LoggedInSuperUser())
    assert options.painter_options_permitted()


def test_painter_options_are_denied_to_a_user_without_the_permission() -> None:
    options = PainterOptions(Config(), Request(create_environ()), LoggedInNobody())
    assert not options.painter_options_permitted()


def test_resetting_painter_options_drops_them_from_the_request() -> None:
    request = Request(create_environ(query_string="_reset_painter_options=1&po_refresh=30"))
    options = PainterOptions(Config(), request, LoggedInSuperUser())
    options.update_from_url("allhosts", ["refresh"])
    assert not request.has_var("po_refresh")
