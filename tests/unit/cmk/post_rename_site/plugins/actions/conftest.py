#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.cmk.web_test_app import WebTestAppForCMK

from cmk.gui import http


@pytest.fixture(autouse=True)
def post_rename_request_context(  # pylint: disable=redefined-outer-name
    wsgi_app: WebTestAppForCMK,
    gui_cleanup_after_test: None,
    admin_auth_request: http.Request,
) -> None:
    """This fixture registers a global htmllib.html() instance just like the regular GUI"""
    wsgi_app.get(admin_auth_request)
