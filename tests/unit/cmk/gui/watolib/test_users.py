#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Generator

import pytest

from cmk.ccc.site import SiteId

from cmk.utils.user import UserId

from cmk.gui import userdb
from cmk.gui.type_defs import UserObject, UserSpec
from cmk.gui.watolib.paths import wato_var_dir
from cmk.gui.watolib.site_changes import SiteChanges
from cmk.gui.watolib.users import default_sites, delete_users, edit_users

USER1_ID = UserId("user1")
USER2_ID = UserId("user2")

SITE1 = SiteId("1")
SITE2 = SiteId("2")
SITE3 = SiteId("3")

ALL_SITES = [SITE1, SITE2, SITE3]


def _reset_site_changes(sites: list[SiteId]) -> None:
    for site_id in sites:
        changes_mk = wato_var_dir() / f"replication_changes_{site_id}.mk"
        if changes_mk.exists():
            changes_mk.unlink()
        changes_mk.touch()


@pytest.fixture(name="sites")
def setup_site_changes() -> Generator[list[SiteId], None, None]:
    _reset_site_changes(ALL_SITES)
    yield ALL_SITES


def _changed_sites(sites: list[SiteId]) -> list[SiteId]:
    changed_sites = []
    for site_id in sites:
        if SiteChanges(site_id).read():
            changed_sites.append(site_id)
    return changed_sites


@pytest.mark.parametrize(
    "changed_users, expected_changed_sites",
    [
        pytest.param(
            {
                USER1_ID: {
                    "attributes": UserSpec({"alias": "user1", "locked": False}),
                    "is_new_user": True,
                }
            },
            [],
            id="no sites => all sites change",
        ),
        pytest.param(
            {
                USER1_ID: {
                    "attributes": UserSpec(
                        {
                            "alias": "user1",
                            "locked": False,
                            "authorized_sites": [SITE1],
                        }
                    ),
                    "is_new_user": True,
                }
            },
            [SITE1],
            id="single site change",
        ),
        pytest.param(
            {
                USER1_ID: {
                    "attributes": UserSpec(
                        {
                            "alias": "user1",
                            "locked": False,
                        }
                    ),
                    "is_new_user": True,
                },
                USER2_ID: {
                    "attributes": UserSpec(
                        {
                            "alias": "user2",
                            "locked": False,
                            "authorized_sites": [SITE1],
                        }
                    ),
                    "is_new_user": True,
                },
            },
            [],
            id="all sites change because of one user",
        ),
    ],
)
@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_only_affected_sites_require_activation_when_adding_users(
    sites: list[SiteId], changed_users: UserObject, expected_changed_sites: list[SiteId]
) -> None:
    edit_users(changed_users, default_sites)
    all_users = userdb.load_users()
    assert all(user_id in all_users for user_id in changed_users)
    assert expected_changed_sites == _changed_sites(sites)


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_only_affected_sites_require_activation_when_changing_user(sites: list[SiteId]) -> None:
    # GIVEN one user added on site1
    edit_users(
        {
            USER1_ID: {
                "attributes": UserSpec(
                    {"alias": "user1", "locked": False, "authorized_sites": [SITE1]}
                ),
                "is_new_user": True,
            }
        },
        default_sites,
    )
    _reset_site_changes(ALL_SITES)

    # WHEN "moving" this user to site2
    edit_users(
        {
            USER1_ID: {
                "attributes": UserSpec(
                    {"alias": "user1", "locked": False, "authorized_sites": [SITE2]}
                ),
                "is_new_user": False,
            }
        },
        default_sites,
    )

    # THEN both site1 and site2 should require activation
    assert [SITE1, SITE2] == _changed_sites(sites)


@pytest.mark.parametrize(
    "users_to_delete, expected_changed_sites",
    [
        pytest.param(
            [USER1_ID],
            [],
            id="global user",
        ),
        pytest.param(
            [USER2_ID],
            [SITE2],
            id="single user on single site",
        ),
        pytest.param(
            [USER1_ID, USER2_ID],
            [],
            id="two users, one global",
        ),
    ],
)
@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_only_affected_sites_require_activation_when_deleting_users(
    sites: list[SiteId], users_to_delete: list[UserId], expected_changed_sites: list[SiteId]
) -> None:
    # GIVEN "global" user1 and user2 on site2
    edit_users(
        {
            USER1_ID: {
                "attributes": UserSpec({"alias": "user1", "locked": False}),
                "is_new_user": True,
            },
            USER2_ID: {
                "attributes": UserSpec(
                    {"alias": "user2", "locked": False, "authorized_sites": [SITE2]}
                ),
                "is_new_user": True,
            },
        },
        default_sites,
    )
    _reset_site_changes(ALL_SITES)

    # WHEN
    delete_users(users_to_delete, default_sites)

    # THEN
    all_users = userdb.load_users()
    assert not any(user_id in all_users for user_id in users_to_delete)
    assert expected_changed_sites == _changed_sites(sites)
