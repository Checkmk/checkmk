#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.unit.gui.gui_session_endpoints import (
    internal_token_header,
    make_session_cookie,
    SessionCookieFactory,
)


@pytest.fixture(name="internal_token")
def fixture_internal_token() -> dict[str, str]:
    return internal_token_header()


@pytest.fixture(name="make_session_cookie")
def fixture_make_session_cookie() -> SessionCookieFactory:
    return make_session_cookie
