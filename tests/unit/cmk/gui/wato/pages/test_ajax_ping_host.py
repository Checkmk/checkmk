#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.wato.pages.hosts import PageAjaxPingHost


@pytest.mark.xfail(strict=True, raises=KeyError, reason="crash group 4931")
@pytest.mark.usefixtures("request_context")
def test_ping_via_an_unknown_site_reports_an_error() -> None:
    request.set_var("site_id", "gone")
    request.set_var("ip_or_dns_name", "localhost")
    config = Config()

    result = PageAjaxPingHost().page(
        PageContext(
            config=config,
            request=request,
            transactions=transactions,
            session=session,
            user_permissions=UserPermissions.from_config(config, all_permissions()),
        )
    )

    assert isinstance(result, dict)
    assert result["status_code"] == 99
    assert "gone" in result["message"]
