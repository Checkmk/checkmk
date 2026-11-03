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


@pytest.mark.usefixtures("request_context")
def test_user_is_the_authenticated_user() -> None:
    """ApiContext.user must be the user the request actually authenticated as,
    not a user rebuilt from the (possibly None) user id (CMK-35778)."""
    user = LoggedInUser(
        UserId("cmkadmin"),
        UserPermissions({}, {}, {}, []),
        defaults=UserDefaultConfig(users={}, default_language="en", default_show_mode="default"),
    )
    assert _api_context(user).user is user


@pytest.mark.usefixtures("request_context")
def test_super_user_is_preserved() -> None:
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
@pytest.mark.usefixtures("request_context")
def test_other_user_id_less_users_are_not_promoted_to_super_user(pseudo_user: LoggedInUser) -> None:
    """Other identities also have no user id but must NOT be treated as a super
    user - that is exactly the bug of rebuilding the user from a None user id."""
    context = _api_context(pseudo_user)

    assert context.user is pseudo_user
    assert context.user.id is None
    assert not context.user.may("wato.all_folders")


def _build_value(api_context: ApiContext) -> tuple[str, ApiContext]:
    return ("value", api_context)


def _build_other_value(api_context: ApiContext) -> tuple[str, ApiContext]:
    return ("other", api_context)


def test_a_request_shares_one_value_per_build_function() -> None:
    context = _api_context(LoggedInNobody())

    assert context.shared(_build_value) is context.shared(_build_value)


def test_a_shared_value_is_built_from_the_api_context_of_the_request() -> None:
    context = _api_context(LoggedInNobody())

    assert context.shared(_build_value)[1] is context


def test_each_build_function_gets_its_own_shared_value() -> None:
    context = _api_context(LoggedInNobody())

    assert context.shared(_build_value) != context.shared(_build_other_value)


def test_requests_do_not_share_values() -> None:
    first = _api_context(LoggedInNobody())
    second = _api_context(LoggedInNobody())

    assert first.shared(_build_value) is not second.shared(_build_value)
