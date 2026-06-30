#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from werkzeug.datastructures import ETags

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.logged_in import (
    LoggedInNobody,
    LoggedInRemoteSite,
    LoggedInSuperUser,
    LoggedInUser,
    UserDefaultConfig,
)
from cmk.gui.openapi.framework import ApiContext, APIVersion
from cmk.gui.utils.roles import UserPermissions


def _api_context(user: LoggedInUser) -> ApiContext:
    return ApiContext.new(
        config=Config(),
        version=APIVersion.UNSTABLE,
        etag_if_match=ETags(),
        host_url="http://localhost/",
        user=user,
        token=None,
    )


def test_user_is_the_authenticated_user(request_context: None) -> None:
    """ApiContext.user must be the user the request actually authenticated as,
    not a user rebuilt from the (possibly None) user id (CMK-35778)."""
    user = LoggedInUser(
        UserId("cmkadmin"),
        UserPermissions({}, {}, {}, []),
        defaults=UserDefaultConfig(users={}, default_language="en", default_show_mode="default"),
    )
    assert _api_context(user).user is user


def test_super_user_is_preserved(request_context: None) -> None:
    """The site-internal secret (InternalToken, e.g. the DCD daemon) authenticates
    as a super user with no user id. ApiContext.user must keep the super user so
    the folder/host write-permission checks accept it."""
    context = _api_context(LoggedInSuperUser())

    assert isinstance(context.user, LoggedInSuperUser)
    assert context.user.id is None
    assert context.user.may("wato.all_folders")


@pytest.mark.parametrize(
    "pseudo_user",
    [LoggedInRemoteSite(site_name="remote"), LoggedInNobody()],
)
def test_other_user_id_less_users_are_not_promoted_to_super_user(
    pseudo_user: LoggedInUser, request_context: None
) -> None:
    """Other identities also have no user id but must NOT be treated as a super
    user - that is exactly the bug of rebuilding the user from a None user id."""
    context = _api_context(pseudo_user)

    assert context.user is pseudo_user
    assert context.user.id is None
    assert not context.user.may("wato.all_folders")
