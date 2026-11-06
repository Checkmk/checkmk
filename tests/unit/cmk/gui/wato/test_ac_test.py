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
    ACTestApacheForwardedHeaders,
    ACTestAutomationUserSecret,
    ACTestBrokenGUIExtension,
    ACTestDeprecatedGUIExtensions,
    ACTestDeprecatedLegacyGUIExtensions,
    ACTestDeprecatedPNPTemplates,
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


def _omd_root(tmp_path: Path, forwarded_headers: str) -> Path:
    site_conf = tmp_path / "etc" / "omd" / "site.conf"
    site_conf.parent.mkdir(parents=True)
    site_conf.write_text(f"CONFIG_APACHE_FORWARDED_HEADERS='{forwarded_headers}'\n")
    return tmp_path


def test_apache_forwarded_headers_auto_ok(tmp_path: Path) -> None:
    """Default mode, no manual leftover config anywhere -> OK"""
    results = list(
        ACTestApacheForwardedHeaders(
            omd_root=_omd_root(tmp_path, "auto"), search_dirs=[tmp_path / "apache2"]
        ).execute(SiteId("NO_SITE"), Config())
    )

    assert [r.state for r in results] == [ACResultState.OK]
    assert "automatically" in results[0].text


def test_apache_forwarded_headers_auto_leftover_warns(tmp_path: Path) -> None:
    """Default mode, but a manual RequestHeader is still configured -> WARN"""
    apache_dir = tmp_path / "apache2" / "conf-enabled"
    apache_dir.mkdir(parents=True)
    leftover = apache_dir / "proxy.conf"
    leftover.write_text('RequestHeader set X-Forwarded-Proto "https"\n')

    results = list(
        ACTestApacheForwardedHeaders(
            omd_root=_omd_root(tmp_path, "auto"), search_dirs=[tmp_path / "apache2"]
        ).execute(SiteId("NO_SITE"), Config())
    )

    assert [r.state for r in results] == [ACResultState.WARN]
    assert str(leftover) in results[0].text


def test_apache_forwarded_headers_manual_with_config_ok(tmp_path: Path) -> None:
    """Opted out, and a manual RequestHeader is indeed configured -> OK"""
    apache_dir = tmp_path / "apache2"
    apache_dir.mkdir()
    (apache_dir / "proxy.conf").write_text('RequestHeader set X-Forwarded-Proto "https"\n')

    results = list(
        ACTestApacheForwardedHeaders(
            omd_root=_omd_root(tmp_path, "manual"), search_dirs=[apache_dir]
        ).execute(SiteId("NO_SITE"), Config())
    )

    assert [r.state for r in results] == [ACResultState.OK]
    assert "manually" in results[0].text


def test_apache_forwarded_headers_manual_without_config_warns(tmp_path: Path) -> None:
    """Opted out, but no matching manual configuration was found -> WARN"""
    results = list(
        ACTestApacheForwardedHeaders(
            omd_root=_omd_root(tmp_path, "manual"), search_dirs=[tmp_path / "apache2"]
        ).execute(SiteId("NO_SITE"), Config())
    )

    assert [r.state for r in results] == [ACResultState.WARN]
    assert "intentional" in results[0].text


def _write(root: Path, rel_path: str) -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def _gui_plugins_finding(tmp_path: Path, rel_path: str) -> ACSingleResult:
    _write(tmp_path / "local/lib/python3/cmk/gui/plugins", rel_path)
    [result] = ACTestDeprecatedGUIExtensions(
        tmp_path / "local/lib/python3/cmk/gui/plugins"
    ).execute(SiteId("NO_SITE"), Config())
    return result


def _legacy_gui_plugins_finding(tmp_path: Path, rel_path: str) -> ACSingleResult:
    _write(tmp_path / "local/share/check_mk/web", rel_path)
    [result] = ACTestDeprecatedLegacyGUIExtensions(tmp_path / "local/share/check_mk/web").execute(
        SiteId("NO_SITE"), Config()
    )
    return result


def test_gui_plugins_without_plugins(tmp_path: Path) -> None:
    [result] = ACTestDeprecatedGUIExtensions(
        tmp_path / "local/lib/python3/cmk/gui/plugins"
    ).execute(SiteId("NO_SITE"), Config())
    assert result.state is ACResultState.OK


def test_gui_plugin_in_loaded_package_warns(tmp_path: Path) -> None:
    result = _gui_plugins_finding(tmp_path, "views/my_view.py")
    assert (result.state, result.text) == (
        ACResultState.WARN,
        (
            f"'{tmp_path / 'local/lib/python3/cmk/gui/plugins/views/my_view.py'}'"
            " may break with any update of Checkmk."
            " Checkmk loads plug-ins from this folder through internal interfaces, which are"
            " not supported for plug-ins."
        ),
    )


def test_gui_plugin_in_nested_loaded_package_warns(tmp_path: Path) -> None:
    result = _gui_plugins_finding(tmp_path, "views/icons/my_icon.py")
    assert result.state is ACResultState.WARN


def test_gui_plugin_in_metrics_package_names_the_graphing_api(tmp_path: Path) -> None:
    result = _gui_plugins_finding(tmp_path, "metrics/my_metrics.py")
    assert (result.state, result.text) == (
        ACResultState.CRIT,
        (
            f"'{tmp_path / 'local/lib/python3/cmk/gui/plugins/metrics/my_metrics.py'}'"
            " has no effect in Checkmk. Checkmk no"
            " longer reads graphs, metrics and perf-o-meters from this folder. Re-implement it"
            " with the supported API cmk.graphing.v1."
        ),
    )


def test_gui_plugin_in_package_not_loaded_has_no_effect(tmp_path: Path) -> None:
    result = _gui_plugins_finding(tmp_path, "config/my_config.py")
    assert (result.state, result.text) == (
        ACResultState.CRIT,
        (
            f"'{tmp_path / 'local/lib/python3/cmk/gui/plugins/config/my_config.py'}'"
            " has no effect in Checkmk. Checkmk does"
            " not load plug-ins from this folder."
        ),
    )


def test_gui_plugins_ignore_files_other_than_python(tmp_path: Path) -> None:
    result = _gui_plugins_finding(tmp_path, "views/README")
    assert result.state is ACResultState.OK


@pytest.mark.parametrize("folder", ["metrics", "perfometer", "metrics/sub"])
def test_legacy_gui_plugin_in_graphing_folder_names_the_graphing_api(
    tmp_path: Path, folder: str
) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, f"plugins/{folder}/my_metrics.py")
    assert (result.state, result.text) == (
        ACResultState.CRIT,
        (
            f"'{tmp_path / 'local/share/check_mk/web/plugins' / folder / 'my_metrics.py'}'"
            " has no effect in Checkmk."
            " Checkmk no longer reads graphs, metrics and perf-o-meters from this folder."
            " Re-implement it with the supported API cmk.graphing.v1."
        ),
    )


def test_legacy_gui_plugin_nested_in_loaded_folder_has_no_effect(tmp_path: Path) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, "plugins/views/sub/my_view.py")
    assert result.state is ACResultState.CRIT


def test_legacy_gui_plugin_outside_plugins_folder_has_no_effect(tmp_path: Path) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, "htdocs/my_page.py")
    assert result.state is ACResultState.CRIT


@pytest.mark.parametrize("package", ["dashboard", "sidebar", "visuals", "wato"])
def test_gui_plugin_in_each_loaded_package_warns(tmp_path: Path, package: str) -> None:
    result = _gui_plugins_finding(tmp_path, f"{package}/my_plugin.py")
    assert result.state is ACResultState.WARN


def test_gui_plugin_finding_names_its_file(tmp_path: Path) -> None:
    result = _gui_plugins_finding(tmp_path, "views/my_view.py")
    assert result.path == tmp_path / "local/lib/python3/cmk/gui/plugins/views/my_view.py"


def test_gui_plugin_findings_are_sorted_by_their_file(tmp_path: Path) -> None:
    _write(tmp_path / "local/lib/python3/cmk/gui/plugins", "views/b_view.py")
    _write(tmp_path / "local/lib/python3/cmk/gui/plugins", "views/a_view.py")
    assert [
        result.path
        for result in ACTestDeprecatedGUIExtensions(
            tmp_path / "local/lib/python3/cmk/gui/plugins"
        ).execute(SiteId("NO_SITE"), Config())
    ] == [
        tmp_path / "local/lib/python3/cmk/gui/plugins/views/a_view.py",
        tmp_path / "local/lib/python3/cmk/gui/plugins/views/b_view.py",
    ]


def test_gui_plugin_outside_a_package_has_no_effect(tmp_path: Path) -> None:
    result = _gui_plugins_finding(tmp_path, "my_plugin.py")
    assert result.state is ACResultState.CRIT


def test_gui_plugin_nested_in_package_not_loaded_has_no_effect(tmp_path: Path) -> None:
    result = _gui_plugins_finding(tmp_path, "config/sub/my_config.py")
    assert result.state is ACResultState.CRIT


def test_legacy_gui_plugins_without_plugins(tmp_path: Path) -> None:
    [result] = ACTestDeprecatedLegacyGUIExtensions(tmp_path / "local/share/check_mk/web").execute(
        SiteId("NO_SITE"), Config()
    )
    assert result.state is ACResultState.OK


def test_legacy_gui_plugins_ignore_files_other_than_python(tmp_path: Path) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, "plugins/views/README")
    assert result.state is ACResultState.OK


@pytest.mark.parametrize(
    "folder", ["config", "dashboard", "icons", "pages", "sidebar", "visuals", "wato"]
)
def test_legacy_gui_plugin_in_each_loaded_folder_warns(tmp_path: Path, folder: str) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, f"plugins/{folder}/my_plugin.py")
    assert result.state is ACResultState.WARN


def test_legacy_gui_plugin_in_loaded_folder_is_reported_with_its_reason(tmp_path: Path) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, "plugins/views/my_view.py")
    assert (result.text, result.path) == (
        (
            f"'{tmp_path / 'local/share/check_mk/web/plugins/views/my_view.py'}'"
            " may break with any update of Checkmk."
            " Checkmk loads plug-ins from this folder through internal interfaces, which are"
            " not supported for plug-ins."
        ),
        tmp_path / "local/share/check_mk/web/plugins/views/my_view.py",
    )


def test_legacy_gui_plugin_without_effect_is_reported_with_its_reason(tmp_path: Path) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, "plugins/my_folder/my_view.py")
    assert result.text == (
        f"'{tmp_path / 'local/share/check_mk/web/plugins/my_folder/my_view.py'}'"
        " has no effect in Checkmk. Checkmk does"
        " not load plug-ins from this folder."
    )


def test_legacy_gui_plugin_directly_in_plugins_folder_has_no_effect(tmp_path: Path) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, "plugins/my_view.py")
    assert result.state is ACResultState.CRIT


def test_gui_plugins_help_names_its_folder(tmp_path: Path) -> None:
    assert f"'{tmp_path / 'plugins'}'" in ACTestDeprecatedGUIExtensions(tmp_path / "plugins").help()


def test_legacy_gui_plugins_help_names_its_folder(tmp_path: Path) -> None:
    assert (
        f"'{tmp_path / 'web/plugins'}'"
        in ACTestDeprecatedLegacyGUIExtensions(tmp_path / "web").help()
    )


_LOCAL_ROOT = Path("/omd/sites/NO_SITE/local")


def _broken_gui_extension_finding(path: Path, local_root: Path = _LOCAL_ROOT) -> ACSingleResult:
    def failed_plugins() -> Sequence[tuple[Path, str, str, BaseException]]:
        return [(path, "views", "my_view", NameError("name 'x' is not defined"))]

    [result] = ACTestBrokenGUIExtension(failed_plugins, local_root).execute(
        SiteId("NO_SITE"), Config()
    )
    return result


def test_broken_legacy_gui_plugin_is_named_by_its_file() -> None:
    path = Path("/omd/sites/NO_SITE/local/share/check_mk/web/plugins/views/my_view.py")
    result = _broken_gui_extension_finding(path)
    assert (result.state, result.text, result.path) == (
        ACResultState.CRIT,
        (
            "'local/share/check_mk/web/plugins/views/my_view.py' has no effect in Checkmk."
            " Checkmk fails to load it: name 'x' is not defined. The log file"
            " 'var/log/web.log' shows the details."
        ),
        path,
    )


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(
            Path("/omd/sites/NO_SITE/local/lib/python3/cmk/gui/plugins/views/my_view.py"),
            id="gui-plugin",
        ),
        pytest.param(
            Path(
                "/omd/sites/NO_SITE/local/lib/python3/cmk_addons/plugins/my_family/rulesets/my_rule.py"
            ),
            id="rule-spec-of-an-extension-package",
        ),
    ],
)
def test_broken_local_file_is_named_by_its_file(path: Path) -> None:
    assert _broken_gui_extension_finding(path).path == path


def test_broken_gui_extension_error_ending_with_a_period(tmp_path: Path) -> None:
    def failed_plugins() -> Sequence[tuple[Path, str, str, BaseException]]:
        return [(Path("a.py"), "views", "a_view", NameError("Some error."))]

    [result] = ACTestBrokenGUIExtension(failed_plugins, tmp_path).execute(
        SiteId("NO_SITE"), Config()
    )
    assert result.text == (
        "'views/a_view' has no effect in Checkmk. Checkmk fails to load it: Some error. The log"
        " file 'var/log/web.log' shows the details."
    )


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(
            Path("/omd/sites/NO_SITE/lib/python3/cmk/gui/rule_specs/legacy_converter.py"),
            id="traceback-frame",
        ),
        pytest.param(
            Path("/omd/sites/NO_SITE/share/check_mk/web/plugins/views/my_view.py"),
            id="shipped-legacy-plugin",
        ),
    ],
)
def test_broken_gui_extension_without_its_file_is_named_by_the_plugin(path: Path) -> None:
    result = _broken_gui_extension_finding(path)
    assert (result.state, result.text, result.path) == (
        ACResultState.CRIT,
        (
            "'views/my_view' has no effect in Checkmk. Checkmk fails to load it: name 'x' is"
            " not defined. The log file 'var/log/web.log' shows the details."
        ),
        None,
    )


_RULE_SET_MODULE_PATH = Path("cmk_addons/plugins/my_family/rulesets/my_rule.py")


def test_broken_module_of_a_local_file_is_named_by_its_file(tmp_path: Path) -> None:
    _write(tmp_path / "lib/python3", str(_RULE_SET_MODULE_PATH))
    assert (
        _broken_gui_extension_finding(_RULE_SET_MODULE_PATH, tmp_path).path
        == tmp_path / "lib/python3" / _RULE_SET_MODULE_PATH
    )


def test_broken_module_without_a_local_file_is_named_by_the_plugin(tmp_path: Path) -> None:
    result = _broken_gui_extension_finding(_RULE_SET_MODULE_PATH, tmp_path)
    assert (result.text, result.path) == (
        (
            "'views/my_view' has no effect in Checkmk. Checkmk fails to load it: name 'x' is"
            " not defined. The log file 'var/log/web.log' shows the details."
        ),
        None,
    )


def test_without_broken_gui_extensions() -> None:
    [result] = ACTestBrokenGUIExtension(list).execute(SiteId("NO_SITE"), Config())
    assert result.state is ACResultState.OK


def test_every_broken_gui_extension_is_reported(tmp_path: Path) -> None:
    def failed_plugins() -> Sequence[tuple[Path, str, str, BaseException]]:
        return [
            (Path("a.py"), "views", "a_view", NameError("a")),
            (Path("b.py"), "sidebar", "b_snapin", NameError("b")),
        ]

    assert [
        result.text
        for result in ACTestBrokenGUIExtension(failed_plugins, tmp_path).execute(
            SiteId("NO_SITE"), Config()
        )
    ] == [
        (
            "'views/a_view' has no effect in Checkmk. Checkmk fails to load it: a. The log file"
            " 'var/log/web.log' shows the details."
        ),
        (
            "'sidebar/b_snapin' has no effect in Checkmk. Checkmk fails to load it: b. The log"
            " file 'var/log/web.log' shows the details."
        ),
    ]


_PNP_TEMPLATES_DIR = "local/share/check_mk/pnp-templates"


def test_pnp_template_has_no_effect(tmp_path: Path) -> None:
    _write(tmp_path / _PNP_TEMPLATES_DIR, "check_mk-my_check.php")
    [result] = ACTestDeprecatedPNPTemplates(tmp_path / _PNP_TEMPLATES_DIR).execute(
        SiteId("NO_SITE"), Config()
    )
    assert (result.state, result.text, result.path) == (
        ACResultState.CRIT,
        (
            f"'{tmp_path}/local/share/check_mk/pnp-templates/check_mk-my_check.php' has no"
            " effect in Checkmk. Checkmk no longer reads PNP templates. Re-implement it with"
            " the supported API cmk.graphing.v1."
        ),
        tmp_path / "local/share/check_mk/pnp-templates/check_mk-my_check.php",
    )


def test_pnp_templates_are_reported_in_order_including_subfolders(tmp_path: Path) -> None:
    for rel_path in ("check_mk-b.php", "foo/check_mk-c.php", "check_mk-a.php"):
        _write(tmp_path / _PNP_TEMPLATES_DIR, rel_path)
    results = ACTestDeprecatedPNPTemplates(tmp_path / _PNP_TEMPLATES_DIR).execute(
        SiteId("NO_SITE"), Config()
    )
    assert [result.path for result in results] == [
        tmp_path / "local/share/check_mk/pnp-templates/check_mk-a.php",
        tmp_path / "local/share/check_mk/pnp-templates/check_mk-b.php",
        tmp_path / "local/share/check_mk/pnp-templates/foo/check_mk-c.php",
    ]


def test_without_pnp_templates(tmp_path: Path) -> None:
    [result] = ACTestDeprecatedPNPTemplates(tmp_path / _PNP_TEMPLATES_DIR).execute(
        SiteId("NO_SITE"), Config()
    )
    assert result.state is ACResultState.OK
