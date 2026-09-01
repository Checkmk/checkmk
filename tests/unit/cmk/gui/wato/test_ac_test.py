#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path
from typing import override

import pytest

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import __version__
from cmk.gui.config import Config
from cmk.gui.permissions import Permission, PermissionSection
from cmk.gui.role_types import BuiltInUserRole, CustomUserRole
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.wato._ac_tests import (
    ACTestAutomationUserSecret,
    ACTestBakeryAPI,
    ACTestGenericCheckHelperUsage,
    ACTestHaSIAPI,
    ACTestPasswordStoreAPI,
    ACTestSpecialAgentsAPI,
)
from cmk.gui.watolib.analyze_configuration import (
    ABCACTestPluginAPIs,
    ACResultState,
    ACSingleResult,
    local_plugin_roots,
    MAX_SCANNED_FILE_SIZE,
)
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.utils.paths import local_lib_dir, local_web_dir


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


def _write_plugin_file(plugin_root: Path, rel_path: str, content: str) -> Path:
    path = plugin_root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# Every API is checked by its own test, so a plug-in folder is scanned once per API.
_OUTDATED_API_TESTS: Sequence[type[ABCACTestPluginAPIs]] = (
    ACTestSpecialAgentsAPI,
    ACTestPasswordStoreAPI,
    ACTestHaSIAPI,
    ACTestBakeryAPI,
)


def _results(test: type[ABCACTestPluginAPIs], plugin_root: Path) -> Sequence[ACSingleResult]:
    return test().make_outdated_plugin_api_results(SiteId("NO_SITE"), [plugin_root])


def _reported(plugin_root: Path) -> Sequence[ACSingleResult]:
    """The findings of all outdated API tests, without the 'nothing found' results"""
    return [
        result
        for test in _OUTDATED_API_TESTS
        for result in _results(test, plugin_root)
        if result.state is not ACResultState.OK
    ]


@pytest.mark.parametrize("test", _OUTDATED_API_TESTS, ids=lambda t: t.__name__)
def test_outdated_plugin_apis_without_plugins(
    test: type[ABCACTestPluginAPIs], tmp_path: Path
) -> None:
    assert _results(test, tmp_path) == [
        ACSingleResult(
            state=ACResultState.OK,
            text="No plug-ins using an outdated API",
            site_id=SiteId("NO_SITE"),
        )
    ]


@pytest.mark.parametrize(
    "test, rel_path, content, expected_api",
    [
        pytest.param(
            ACTestSpecialAgentsAPI,
            # Special agents are executables, ie. they usually have no suffix at all.
            "foo/libexec/agent_foo",
            "#!/usr/bin/env python3\nfrom cmk.special_agents.v0_unstable import agent_common\n",
            "cmk.special_agents",
            id="special-agent-without-suffix",
        ),
        pytest.param(
            ACTestPasswordStoreAPI,
            "foo/lib/util.py",
            "import cmk.utils.password_store.hack\n",
            "cmk.utils.password_store",
            id="password-store-submodule",
        ),
        pytest.param(
            ACTestPasswordStoreAPI,
            # A module is commonly imported from its parent package.
            "foo/lib/util.py",
            "from cmk.utils import password_store\n",
            "cmk.utils.password_store",
            id="password-store-from-parent-package",
        ),
        pytest.param(
            ACTestBakeryAPI,
            "foo/bakery/bakery_foo.py",
            "from cmk.bakery.v1 import Plugin\n",
            "cmk.bakery.v1",
            id="bakery-v1",
        ),
        pytest.param(
            ACTestBakeryAPI,
            "bakery_foo.py",
            "from cmk.base.cee.plugins.bakery.bakery_api.v1 import register\n",
            "cmk.base.cee.plugins.bakery.bakery_api",
            id="legacy-bakery-api-cee",
        ),
        pytest.param(
            ACTestBakeryAPI,
            "bakery_foo.py",
            "from cmk.base.plugins.bakery.bakery_api.v1 import register\n",
            "cmk.base.plugins.bakery.bakery_api",
            id="legacy-bakery-api",
        ),
        pytest.param(
            # Bakery plug-ins in the legacy folder import the API relatively.
            ACTestBakeryAPI,
            "bakery_foo.py",
            "from .bakery_api.v1 import FileGenerator, register\n",
            ".bakery_api",
            id="legacy-bakery-api-relative",
        ),
        pytest.param(
            ACTestBakeryAPI,
            "bakery_foo.py",
            "from . import bakery_api\n",
            ".bakery_api",
            id="legacy-bakery-api-relative-package",
        ),
        pytest.param(
            ACTestBakeryAPI,
            "bakery_foo.py",
            "from cmk.base.cee.plugins.bakery import bakery_api\n",
            "cmk.base.cee.plugins.bakery.bakery_api",
            id="legacy-bakery-api-from-parent-package",
        ),
    ],
)
def test_outdated_plugin_apis_reports_outdated_import(
    test: type[ABCACTestPluginAPIs],
    tmp_path: Path,
    rel_path: str,
    content: str,
    expected_api: str,
) -> None:
    path = _write_plugin_file(tmp_path, rel_path, content)

    results = _results(test, tmp_path)

    # Only the detection is under test here, the state depends on the API's timeline.
    assert [r.path for r in results] == [path]
    assert expected_api in results[0].text


@pytest.mark.parametrize(
    "test, content, expected_api",
    [
        pytest.param(
            ACTestSpecialAgentsAPI,
            "import cmk.special_agents.v0_unstable\n",
            "cmk.special_agents",
            id="fallback-import-module",
        ),
        pytest.param(
            ACTestPasswordStoreAPI,
            "from cmk.utils.password_store import extract\n",
            "cmk.utils.password_store",
            id="fallback-from-module-import",
        ),
        pytest.param(
            ACTestPasswordStoreAPI,
            # A module is commonly imported from its parent package.
            "from cmk.utils import password_store\n",
            "cmk.utils.password_store",
            id="fallback-from-parent-package",
        ),
        pytest.param(
            ACTestPasswordStoreAPI,
            "import cmk.utils.password_store, os\n",
            "cmk.utils.password_store",
            id="fallback-import-several-modules",
        ),
    ],
)
def test_outdated_plugin_apis_falls_back_to_textual_search(
    test: type[ABCACTestPluginAPIs],
    tmp_path: Path,
    content: str,
    expected_api: str,
) -> None:
    """Plug-in folders may contain files which are no valid Python"""
    unparseable = '#!/bin/bash\nif [ -z "$1" ]; then\n    ' + content + "fi\n"
    path = _write_plugin_file(tmp_path, "foo/libexec/agent_foo", unparseable)

    results = _results(test, tmp_path)

    # Only the detection is under test here, the state depends on the API's timeline.
    assert [r.path for r in results] == [path]
    assert expected_api in results[0].text


def test_outdated_plugin_apis_reports_outdated_content(tmp_path: Path) -> None:
    """HW/SW inventory display hints are detected by their content, not by an import"""
    path = _write_plugin_file(
        tmp_path,
        "plugins/views/inv_foo.py",
        'inventory_displayhints.update({".hardware.foo:": {"title": _("Foo")}})\n',
    )

    results = _results(ACTestHaSIAPI, tmp_path)

    # Only the detection is under test here, the state depends on the API's timeline.
    assert [r.path for r in results] == [path]
    assert "inventory_displayhints.update" in results[0].text


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(
            "from cmk.server_side_programs.v1 import Storage\n"
            "from cmk.password_store.v1 import Secret\n"
            "from cmk.bakery.v2 import Plugin\n",
            id="migrated-to-new-apis",
        ),
        pytest.param("# from cmk.special_agents.v0_unstable import agent_common\n", id="comment"),
        pytest.param('"""Replaces import cmk.utils.password_store."""\n', id="docstring"),
        pytest.param("import cmk.special_agents_extra\n", id="shared-prefix"),
        pytest.param("from cmk.utils import paths\n", id="other-module-of-parent-package"),
        pytest.param(
            "#!/bin/bash\n# from cmk.utils import password_store\n", id="comment-unparseable"
        ),
        pytest.param("from cmk.bakery.v11 import Plugin\n", id="shared-prefix-from-import"),
    ],
)
def test_outdated_plugin_apis_ignores(tmp_path: Path, content: str) -> None:
    _write_plugin_file(tmp_path, "foo/libexec/agent_foo", content)

    assert not _reported(tmp_path)


@pytest.mark.parametrize(
    "rel_path",
    [
        # A stale byte code file next to a migrated plug-in still carries the old
        # module name in its constant pool.
        pytest.param("foo/util.pyc", id="ignored-suffix"),
        pytest.param("foo/__pycache__/util.cpython-313.pyc", id="pycache-folder"),
        pytest.param("foo/.git/util.py", id="dot-folder"),
    ],
)
def test_outdated_plugin_apis_skips_compiled_and_hidden_files(
    tmp_path: Path, rel_path: str
) -> None:
    outdated_import = "import cmk.special_agents\n"
    # Control: the very same content is reported from a plug-in file.
    control = _write_plugin_file(tmp_path, "foo/libexec/agent_foo", outdated_import)
    assert [r.path for r in _reported(tmp_path)] == [control]

    control.unlink()
    _write_plugin_file(tmp_path, rel_path, outdated_import)

    assert not _reported(tmp_path)


@pytest.mark.parametrize("test", _OUTDATED_API_TESTS, ids=lambda t: t.__name__)
def test_outdated_plugin_apis_without_plugin_folder(
    test: type[ABCACTestPluginAPIs], tmp_path: Path
) -> None:
    """Most of the searched folders do not exist on a site without local plug-ins"""
    assert _results(test, tmp_path / "does-not-exist") == [
        ACSingleResult(
            state=ACResultState.OK,
            text="No plug-ins using an outdated API",
            site_id=SiteId("NO_SITE"),
        )
    ]


def test_outdated_plugin_apis_skips_files_which_are_not_utf_8(tmp_path: Path) -> None:
    outdated_import = b" import cmk.special_agents "
    (tmp_path / "foo").mkdir()
    readable = tmp_path / "foo" / "agent_readable"
    readable.write_bytes(outdated_import)
    # Control: the very same content is reported as long as it can be decoded.
    assert [r.path for r in _reported(tmp_path)] == [readable]

    readable.unlink()
    (tmp_path / "foo" / "agent_foo.bin").write_bytes(b"\xff\xfe" + outdated_import + b"\x00")

    assert not _reported(tmp_path)


def test_outdated_plugin_apis_skips_files_which_are_too_big(tmp_path: Path) -> None:
    """Plug-in folders may contain payload which is far too big to be a plug-in"""
    outdated_import = "import cmk.special_agents\n"
    # Control: the very same content is reported as long as the file is small enough.
    path = _write_plugin_file(tmp_path, "foo/libexec/agent_foo", outdated_import)
    assert [r.path for r in _reported(tmp_path)] == [path]

    padding = "# padding\n" * (MAX_SCANNED_FILE_SIZE // 10)
    _write_plugin_file(tmp_path, "foo/libexec/agent_foo", outdated_import + padding)

    assert not _reported(tmp_path)


def test_outdated_plugin_apis_are_reported_by_the_test_of_their_own_api(tmp_path: Path) -> None:
    """A plug-in may use more than one outdated API, each reported by its own test"""
    path = _write_plugin_file(
        tmp_path,
        "foo/libexec/agent_foo",
        "import cmk.special_agents.v0_unstable\nfrom cmk.utils import password_store\n",
    )

    special_agents = _results(ACTestSpecialAgentsAPI, tmp_path)
    password_store = _results(ACTestPasswordStoreAPI, tmp_path)
    hasi = _results(ACTestHaSIAPI, tmp_path)

    assert [r.path for r in special_agents] == [path]
    assert "cmk.special_agents" in special_agents[0].text
    assert [r.path for r in password_store] == [path]
    assert "cmk.utils.password_store" in password_store[0].text
    # The APIs this plug-in does not use are not reported by their tests.
    assert hasi == [
        ACSingleResult(
            state=ACResultState.OK,
            text="No plug-ins using an outdated API",
            site_id=SiteId("NO_SITE"),
        )
    ]


class _OutdatedAPITest(ABCACTestPluginAPIs):
    """An outdated API with a timeline the test controls"""

    def __init__(self, deprecated_version: str, removed_version: str) -> None:
        self._deprecated_version = deprecated_version
        self._removed_version = removed_version

    @property
    @override
    def api_name(self) -> str:
        return "Some API 'cmk.some_api'"

    @property
    @override
    def successor(self) -> str:
        return "cmk.some_api.v2"

    @property
    @override
    def deprecated_version(self) -> str:
        return self._deprecated_version

    @property
    @override
    def removed_version(self) -> str:
        return self._removed_version

    @property
    @override
    def import_paths(self) -> tuple[str, ...]:
        return ("cmk.some_api.v1",)

    @property
    @override
    def content_patterns(self) -> tuple[str, ...]:
        return ()


# The timeline is evaluated against the running version, so the cases which must not
# sit on a boundary use versions far in the past resp. far in the future.
_LONG_AGO = "1.0.0"
_FAR_AHEAD = "99.0.0"


@pytest.mark.parametrize(
    "deprecated_version, removed_version, expected_state, expected_text",
    [
        pytest.param(
            _FAR_AHEAD,
            "99.1.0",
            ACResultState.OK,
            f"will be deprecated in Checkmk {_FAR_AHEAD}",
            id="before",
        ),
        pytest.param(
            _LONG_AGO,
            _FAR_AHEAD,
            ACResultState.WARN,
            f"will be removed in Checkmk {_FAR_AHEAD}",
            id="deprecated",
        ),
        pytest.param(
            _LONG_AGO,
            "2.0.0",
            ACResultState.CRIT,
            "removed in Checkmk 2.0.0",
            id="removed",
        ),
        # The deprecation and the removal are reported from their version on, so the
        # running version itself must already escalate.
        pytest.param(
            __version__,
            _FAR_AHEAD,
            ACResultState.WARN,
            f"will be removed in Checkmk {_FAR_AHEAD}",
            id="deprecated-in-the-running-version",
        ),
        pytest.param(
            _LONG_AGO,
            __version__,
            ACResultState.CRIT,
            f"removed in Checkmk {__version__}",
            id="removed-in-the-running-version",
        ),
    ],
)
def test_outdated_plugin_apis_follow_the_timeline(
    tmp_path: Path,
    deprecated_version: str,
    removed_version: str,
    expected_state: ACResultState,
    expected_text: str,
) -> None:
    _write_plugin_file(tmp_path, "foo/lib/util.py", "import cmk.some_api.v1\n")

    results = _OutdatedAPITest(
        deprecated_version, removed_version
    ).make_outdated_plugin_api_results(SiteId("NO_SITE"), [tmp_path])

    assert [r.state for r in results] == [expected_state]
    assert expected_text in results[0].text
    assert "cmk.some_api.v2" in results[0].text


@pytest.mark.parametrize("test", _OUTDATED_API_TESTS, ids=lambda t: t.__name__)
def test_outdated_plugin_apis_help_renders(test: type[ABCACTestPluginAPIs]) -> None:
    instance = test()

    assert instance.api_name in instance.title()
    for expected in (
        instance.api_name,
        instance.successor,
        instance.deprecated_version,
        instance.removed_version,
    ):
        assert expected in instance.help()


def test_local_plugin_roots_contain_legacy_views_folder() -> None:
    """The HW/SW inventory display hints only live in the legacy views folder"""
    assert local_web_dir / "plugins" / "views" in list(local_plugin_roots())


def test_local_plugin_roots_contain_legacy_bakery_folder() -> None:
    """Bakery plug-ins importing the API relatively only live in the legacy folder"""
    assert local_lib_dir / "python3/cmk/base/cee/plugins/bakery" in list(local_plugin_roots())


def test_outdated_plugin_apis_reports_one_result_per_api(tmp_path: Path) -> None:
    """A plug-in may reference the same outdated API via several import paths"""
    path = _write_plugin_file(
        tmp_path,
        "bakery_foo.py",
        "from cmk.base.plugins.bakery.bakery_api.v1 import register\n"
        "from .bakery_api.v1 import FileGenerator\n",
    )

    results = _results(ACTestBakeryAPI, tmp_path)

    # Only the detection is under test here, the state follows the timeline.
    assert [r.path for r in results] == [path]
    assert ".bakery_api, cmk.base.plugins.bakery.bakery_api" in results[0].text
