#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path

import pytest

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.permissions import Permission, PermissionSection
from cmk.gui.role_types import BuiltInUserRole, CustomUserRole
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.wato._ac_tests import (
    ACTestAutomationUserSecret,
    ACTestGenericCheckHelperUsage,
    ACTestShadowedWebFiles,
)
from cmk.gui.watolib.analyze_configuration import (
    ACResultState,
    ACSingleResult,
    compute_deprecation_result,
)
from cmk.livestatus_client.testing import MockLiveStatusConnection


def test_local_connection_mocked(
    mock_livestatus: MockLiveStatusConnection, request_context: None
) -> None:
    live = mock_livestatus
    live.set_sites(["NO_SITE"])
    live.expect_query(
        [
            "GET status",
            "Columns: helper_usage_generic average_latency_generic",
            "ColumnHeaders: off",
        ]
    )
    with live(expect_status_query=False):
        gen = ACTestGenericCheckHelperUsage().execute(SiteId("NO_SITE"), Config())
        list(gen)


@pytest.mark.parametrize(
    "version, result",
    [
        pytest.param(
            "1.2.6",
            ACSingleResult(
                state=ACResultState.CRIT,
                text="Entity uses an API (API) which was removed in Checkmk 1.2.5 (file: /path/to/file).",
                site_id=SiteId("site_id"),
                path=Path("/path/to/file"),
            ),
            id="was_removed",
        ),
        pytest.param(
            "1.2.5",
            ACSingleResult(
                state=ACResultState.CRIT,
                text="Entity uses an API (API) which was marked as deprecated in Checkmk 1.2.3 and is removed in Checkmk 1.2.5 (file: /path/to/file).",
                site_id=SiteId("site_id"),
                path=Path("/path/to/file"),
            ),
            id="removed",
        ),
        pytest.param(
            "1.2.4",
            ACSingleResult(
                state=ACResultState.WARN,
                text="Entity uses an API (API) which was marked as deprecated in Checkmk 1.2.3 and will be removed in Checkmk 1.2.5 (file: /path/to/file).",
                site_id=SiteId("site_id"),
                path=Path("/path/to/file"),
            ),
            id="was_deprecated",
        ),
        pytest.param(
            "1.2.3",
            ACSingleResult(
                state=ACResultState.WARN,
                text="Entity uses an API (API) which is marked as deprecated in Checkmk 1.2.3 and will be removed in Checkmk 1.2.5 (file: /path/to/file).",
                site_id=SiteId("site_id"),
                path=Path("/path/to/file"),
            ),
            id="deprecated",
        ),
        pytest.param(
            "1.2.2",
            ACSingleResult(
                state=ACResultState.OK,
                text="",
                site_id=SiteId("site_id"),
                path=Path("/path/to/file"),
            ),
            id="ok",
        ),
    ],
)
def test_compute_deprecation_result(version: str, result: ACSingleResult) -> None:
    assert (
        compute_deprecation_result(
            version=version,
            deprecated_version="1.2.3",
            removed_version="1.2.5",
            title_entity="Entity",
            title_api="API",
            site_id=SiteId("site_id"),
            path=Path("/path/to/file"),
        )
        == result
    )


def _userpermission_mock() -> UserPermissions:
    def _make_permission(name: str) -> Permission:
        return Permission(
            section=PermissionSection(name="unittest", title="Unit Test Permissions"),
            name=name,
            title=f"title:{name}",
            description=f"description:{name}",
            defaults=[],
        )

    roles: dict[str, BuiltInUserRole | CustomUserRole] = {
        "admin": BuiltInUserRole(
            alias="Administrator",
            permissions={
                "unittest.foo": True,
                "unittest.bar": True,
                "wato.manage_mkps": True,
            },
            builtin=True,
        ),
        "custom_role": CustomUserRole(
            alias="Custom role",
            basedon="admin",
            permissions={"wato.manage_mkps": False},
            builtin=False,
        ),
    }
    permissions = {
        x: _make_permission(x)
        for x in (
            "unittest.foo",
            "unittest.bar",
            "wato.manage_mkps",
        )
    }
    return UserPermissions(
        roles=roles,
        permissions=permissions,
        user_roles={
            UserId("user1"): ["admin"],
            UserId("automation"): ["admin"],
        },
        default_user_profile_roles=["guest"],
    )


def test_automation_user_secret_flagging() -> None:
    user_permissions = _userpermission_mock()

    assert not ACTestAutomationUserSecret.get_flagged_users(user_permissions, {})
    # I guess you did not expect wato.users here :-) Me neither...
    # It comes from the UserPermissions class, follow up: CMK-31241
    assert ACTestAutomationUserSecret().get_flagged_users(
        user_permissions,
        {
            UserId("user1"): {"roles": ["admin"]},
            UserId("automation"): {"roles": ["admin"], "store_automation_secret": True},
        },
    ) == {
        UserId("automation"): ["wato.manage_mkps", "wato.users"],
    }


def _touch(root: Path, rel_path: str) -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def _shadowed_web_files_results(tmp_path: Path) -> Sequence[ACSingleResult]:
    return list(
        ACTestShadowedWebFiles(tmp_path / "local", tmp_path / "shipped").execute(
            SiteId("NO_SITE"), Config()
        )
    )


def test_shadowed_web_files_reports_local_copies_of_shipped_files(tmp_path: Path) -> None:
    _touch(tmp_path / "shipped", "themes/facelift/theme.css")
    _touch(tmp_path / "local", "themes/facelift/theme.css")

    [result] = _shadowed_web_files_results(tmp_path)

    assert result.state is ACResultState.WARN
    assert "themes/facelift/theme.css" in result.text


def test_shadowed_web_files_runs_as_part_of_analyze_configuration(tmp_path: Path) -> None:
    _touch(tmp_path / "shipped", "themes/facelift/theme.css")
    _touch(tmp_path / "local", "themes/facelift/theme.css")
    ac_test = ACTestShadowedWebFiles(tmp_path / "local", tmp_path / "shipped")

    assert ac_test.is_relevant()
    assert [r.state for r in ac_test.run(SiteId("NO_SITE"), Config())] == [ACResultState.WARN]


def test_shadowed_web_files_ignores_files_that_shadow_nothing(tmp_path: Path) -> None:
    _touch(tmp_path / "shipped", "themes/facelift/theme.css")
    _touch(tmp_path / "local", "themes/my_theme/theme.css")

    [result] = _shadowed_web_files_results(tmp_path)

    assert result.state is ACResultState.OK


def test_shadowed_web_files_ignores_files_other_than_style_sheets_and_scripts(
    tmp_path: Path,
) -> None:
    _touch(tmp_path / "shipped", "images/icon_checkmk_logo.svg")
    _touch(tmp_path / "local", "images/icon_checkmk_logo.svg")

    [result] = _shadowed_web_files_results(tmp_path)

    assert result.state is ACResultState.OK


def test_shadowed_web_files_without_local_dir(tmp_path: Path) -> None:
    _touch(tmp_path / "shipped", "themes/facelift/theme.css")

    [result] = _shadowed_web_files_results(tmp_path)

    assert result.state is ACResultState.OK


def test_shadowed_web_files_lists_only_the_first_files(tmp_path: Path) -> None:
    for idx in range(12):
        _touch(tmp_path / "shipped", f"js/script_{idx:02}.js")
        _touch(tmp_path / "local", f"js/script_{idx:02}.js")

    [result] = _shadowed_web_files_results(tmp_path)

    assert "js/script_09.js" in result.text
    assert "js/script_10.js" not in result.text
    assert "and 2 more" in result.text
