#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.dashboard.page_show_dashboard import shareable_contact_groups
from cmk.gui.groups import GroupSpecs

_CONTACT_GROUPS: GroupSpecs = {
    "own": {"alias": "Own group"},
    "foreign": {"alias": "Foreign group"},
}


def test_shareable_contact_groups_without_publish_permission_are_empty() -> None:
    groups = shareable_contact_groups(
        _CONTACT_GROUPS, ["own"], may_share_with_own=False, may_share_with_foreign=False
    )

    assert groups == []


def test_shareable_contact_groups_with_own_permission_are_the_users_groups() -> None:
    groups = shareable_contact_groups(
        _CONTACT_GROUPS, ["own"], may_share_with_own=True, may_share_with_foreign=False
    )

    assert groups == [{"name": "own", "title": "Own group"}]


def test_shareable_contact_groups_with_foreign_permission_are_all_groups() -> None:
    groups = shareable_contact_groups(
        _CONTACT_GROUPS, ["own"], may_share_with_own=False, may_share_with_foreign=True
    )

    assert groups == [
        {"name": "own", "title": "Own group"},
        {"name": "foreign", "title": "Foreign group"},
    ]


def test_shareable_contact_groups_without_alias_are_titled_by_name() -> None:
    groups = shareable_contact_groups(
        {"own": {}}, ["own"], may_share_with_own=True, may_share_with_foreign=False
    )

    assert groups == [{"name": "own", "title": "own"}]
