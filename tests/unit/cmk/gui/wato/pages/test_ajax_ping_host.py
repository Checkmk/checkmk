#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.gui.session import session
from cmk.gui.wato.pages.hosts import PageAjaxPingHost


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_ping_via_an_unknown_site_reports_an_error() -> None:
    request.set_var("_csrf_token", str(session.session_info.csrf_token))
    request.set_var("site_id", "gone")
    request.set_var("ip_or_dns_name", "localhost")
    config = Config()

    result = PageAjaxPingHost().page(PageContext(config=config, request=request))

    assert isinstance(result, dict)
    assert result["status_code"] == 99
    assert "gone" in result["message"]
