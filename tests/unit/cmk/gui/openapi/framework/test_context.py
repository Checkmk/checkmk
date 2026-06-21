#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from werkzeug.datastructures import ETags

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInSuperUser, LoggedInUser
from cmk.gui.openapi.framework import ApiContext, APIVersion


def _api_context(user_id: UserId | None) -> ApiContext:
    return ApiContext.new(
        config=Config(),
        version=APIVersion.UNSTABLE,
        etag_if_match=ETags(),
        host_url="http://localhost/",
        user_id=user_id,
        token=None,
    )


def test_logged_in_user_without_user_id_is_super_user(request_context: None) -> None:
    """Internal-token requests (e.g. the DCD daemon) carry no user id and are
    represented as a super user by the session. logged_in_user() must mirror
    that, otherwise permission checks fed with the acting user reject these
    callers (CMK-35778)."""
    acting_user = _api_context(user_id=None).logged_in_user()

    assert isinstance(acting_user, LoggedInSuperUser)
    # The site-internal user must pass the folder write-permission checks just
    # like the global "user" proxy did before acting_user was threaded through.
    assert acting_user.may("wato.all_folders")


def test_logged_in_user_with_user_id_is_not_super_user(request_context: None) -> None:
    acting_user = _api_context(user_id=UserId("cmkadmin")).logged_in_user()

    assert not isinstance(acting_user, LoggedInSuperUser)
    assert isinstance(acting_user, LoggedInUser)
    assert acting_user.id == UserId("cmkadmin")
