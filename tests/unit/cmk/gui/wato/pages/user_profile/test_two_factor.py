#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from bs4 import BeautifulSoup

from cmk.ccc.version import Edition
from cmk.crypto.password_hashing import PasswordHash
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.userdb.store import save_two_factor_credentials
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.wato.pages.user_profile.two_factor import UserTwoFactorOverview


@pytest.mark.usefixtures(
    "request_context", "with_user_login", "patch_theme", "stub_user_menu_quick_entries"
)
def test_overview_offers_invalidating_backup_codes_via_confirm_dialog(
    test_edition: Edition, config: Config
) -> None:
    assert user.id is not None
    save_two_factor_credentials(
        user.id,
        {
            "webauthn_credentials": {},
            "backup_codes": [
                PasswordHash("$2y$12$Dyu8ToMAk7lhiyuRUNUZbuCBo6KtK08H0rCqoWl6nZHWCoE9u0ys.")
            ],
            "totp_credentials": {},
        },
    )

    with output_funnel.plugged():
        UserTwoFactorOverview(test_edition).page(
            PageContext(
                config=config,
                request=request,
                transactions=transactions,
                session=session,
                user_permissions=UserPermissions.from_config(config, all_permissions()),
            )
        )
        rendered = "".join(output_funnel.drain())

    button = BeautifulSoup(rendered, "html.parser").find(
        "input", attrs={"name": "invalidate_codes"}
    )
    assert button is not None
    assert button.get("onclick") is None
    assert button["data-cmk_on_click"] == "confirm_link"
    assert "_delete_codes=" in json.loads(str(button["data-cmk_on_click_arguments"]))["url"]
