#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from livestatus import SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.gui.dashboard.page_show_dashboard import shareable_contact_groups, shareable_sites
from cmk.gui.groups import GroupSpecs
from tests.testlib.unit.gui.openapi_monitoring import site_configurations

_CONTACT_GROUPS: GroupSpecs = {
    "own": {"alias": "Own group"},
    "foreign": {"alias": "Foreign group"},
}


def _sites(alias: str) -> SiteConfigurations:
    config = site_configurations(["NO_SITE"])[SiteId("NO_SITE")]
    return SiteConfigurations({SiteId("NO_SITE"): {**config, "alias": alias}})


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


def test_shareable_sites_without_publish_permission_are_empty() -> None:
    assert shareable_sites(_sites("Local site NO_SITE"), may_share=False) == []


def test_shareable_sites_with_publish_permission_are_titled_by_alias() -> None:
    assert shareable_sites(_sites("Local site NO_SITE"), may_share=True) == [
        {"name": "NO_SITE", "title": "Local site NO_SITE"}
    ]


def test_shareable_sites_without_alias_are_titled_by_name() -> None:
    assert shareable_sites(_sites(""), may_share=True) == [{"name": "NO_SITE", "title": "NO_SITE"}]
