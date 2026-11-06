#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path

import pytest

from livestatus import SiteId

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.gui.wato._ac_tests import (
    _compute_deprecation_result,
    ACTestBrokenGUIExtension,
    ACTestDeprecatedGUIExtensions,
    ACTestDeprecatedLegacyGUIExtensions,
    ACTestDeprecatedPNPTemplates,
    ACTestGenericCheckHelperUsage,
)
from cmk.gui.watolib.analyze_configuration import ACResultState, ACSingleResult


def test_local_connection_mocked(
    mock_livestatus: MockLiveStatusConnection, request_context: None
) -> None:
    live = mock_livestatus
    live.set_sites(["local"])
    live.expect_query(
        [
            "GET status",
            "Columns: helper_usage_generic average_latency_generic",
            "ColumnHeaders: off",
        ]
    )
    with live(expect_status_query=False):
        gen = ACTestGenericCheckHelperUsage().execute()
        list(gen)


@pytest.mark.parametrize(
    "version, result",
    [
        pytest.param(
            "1.2.6",
            ACSingleResult(
                state=ACResultState.CRIT,
                text="Entity uses an API (API) which was removed in Checkmk 1.2.5 (File: /path/to/file).",
                site_id=SiteId("site_id"),
                path=Path("/path/to/file"),
            ),
            id="was_removed",
        ),
        pytest.param(
            "1.2.5",
            ACSingleResult(
                state=ACResultState.CRIT,
                text="Entity uses an API (API) which was marked as deprecated in Checkmk 1.2.3 and is removed in Checkmk 1.2.5 (File: /path/to/file).",
                site_id=SiteId("site_id"),
                path=Path("/path/to/file"),
            ),
            id="removed",
        ),
        pytest.param(
            "1.2.4",
            ACSingleResult(
                state=ACResultState.WARN,
                text="Entity uses an API (API) which was marked as deprecated in Checkmk 1.2.3 and will be removed in Checkmk 1.2.5 (File: /path/to/file).",
                site_id=SiteId("site_id"),
                path=Path("/path/to/file"),
            ),
            id="was_deprecated",
        ),
        pytest.param(
            "1.2.3",
            ACSingleResult(
                state=ACResultState.WARN,
                text="Entity uses an API (API) which is marked as deprecated in Checkmk 1.2.3 and will be removed in Checkmk 1.2.5 (File: /path/to/file).",
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
def test__compute_deprecation_result(version: str, result: ACSingleResult) -> None:
    assert (
        _compute_deprecation_result(
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


_GUI_PLUGINS_DIR = "local/lib/check_mk/gui/plugins"

_WEB_DIR = "local/share/check_mk/web"

_SHIPPED_GUI_DIR = "lib/check_mk/gui"


def _write(root: Path, rel_path: str) -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def _gui_module_dirs(tmp_path: Path) -> Sequence[Path]:
    return [tmp_path / _SHIPPED_GUI_DIR, (tmp_path / _GUI_PLUGINS_DIR).parent]


def _gui_plugins_test(tmp_path: Path) -> ACTestDeprecatedGUIExtensions:
    return ACTestDeprecatedGUIExtensions(tmp_path / _GUI_PLUGINS_DIR, _gui_module_dirs(tmp_path))


def _gui_plugins_finding(tmp_path: Path, rel_path: str) -> ACSingleResult:
    _write(tmp_path / _GUI_PLUGINS_DIR, rel_path)
    [result] = _gui_plugins_test(tmp_path).execute()
    return result


def _legacy_gui_plugins_finding(tmp_path: Path, rel_path: str) -> ACSingleResult:
    _write(tmp_path / _WEB_DIR, rel_path)
    [result] = ACTestDeprecatedLegacyGUIExtensions(
        tmp_path / _WEB_DIR, _gui_module_dirs(tmp_path)
    ).execute()
    return result


def test_gui_plugins_without_plugins(tmp_path: Path) -> None:
    [result] = _gui_plugins_test(tmp_path).execute()
    assert result.state is ACResultState.OK


def test_gui_plugin_in_loaded_package_warns(tmp_path: Path) -> None:
    _write(tmp_path / _SHIPPED_GUI_DIR, "views/__init__.py")
    result = _gui_plugins_finding(tmp_path, "views/my_view.py")
    assert (result.state, result.text) == (
        ACResultState.WARN,
        (
            f"'{tmp_path / _GUI_PLUGINS_DIR / 'views/my_view.py'}'"
            " may break with any update of Checkmk."
            " Checkmk loads plug-ins from this folder through internal interfaces, which are"
            " not supported for plug-ins."
        ),
    )


def test_gui_plugin_in_nested_loaded_package_warns(tmp_path: Path) -> None:
    _write(tmp_path / _SHIPPED_GUI_DIR, "views/__init__.py")
    result = _gui_plugins_finding(tmp_path, "views/icons/my_icon.py")
    assert result.state is ACResultState.WARN


@pytest.mark.parametrize(
    "gui_module",
    [
        pytest.param(f"{_SHIPPED_GUI_DIR}/inventory/__init__.py", id="package"),
        pytest.param(f"{_SHIPPED_GUI_DIR}/inventory.py", id="module"),
        pytest.param(f"{_SHIPPED_GUI_DIR}/cee/inventory/__init__.py", id="commercial-package"),
        pytest.param("local/lib/check_mk/gui/inventory.py", id="local-module"),
    ],
)
def test_gui_plugin_in_package_named_like_a_gui_module_warns(
    tmp_path: Path, gui_module: str
) -> None:
    _write(tmp_path, gui_module)
    result = _gui_plugins_finding(tmp_path, "inventory/my_plugin.py")
    assert result.text.endswith(
        "Checkmk loads plug-ins from this folder through internal interfaces, which are"
        " not supported for plug-ins."
    )


def test_gui_plugin_in_metrics_package_is_deprecated_for_the_graphing_api(
    tmp_path: Path,
) -> None:
    result = _gui_plugins_finding(tmp_path, "metrics/my_metrics.py")
    assert (result.state, result.text) == (
        ACResultState.WARN,
        (
            f"'{tmp_path / _GUI_PLUGINS_DIR / 'metrics/my_metrics.py'}'"
            " may break with any update of Checkmk."
            " Checkmk reads graphs, metrics and perf-o-meters from this folder through internal"
            " interfaces, which are not supported for plug-ins. Checkmk 2.5.0 no longer reads"
            " them. Re-implement it with the supported API cmk.graphing.v1."
        ),
    )


def test_gui_plugin_in_package_not_loaded_has_no_effect(tmp_path: Path) -> None:
    result = _gui_plugins_finding(tmp_path, "my_package/my_plugin.py")
    assert (result.state, result.text) == (
        ACResultState.CRIT,
        (
            f"'{tmp_path / _GUI_PLUGINS_DIR / 'my_package/my_plugin.py'}'"
            " has no effect in Checkmk. Checkmk does not load plug-ins from this folder."
        ),
    )


def test_gui_plugin_nested_in_package_not_loaded_has_no_effect(tmp_path: Path) -> None:
    result = _gui_plugins_finding(tmp_path, "my_package/sub/my_plugin.py")
    assert result.state is ACResultState.CRIT


def test_gui_plugin_outside_a_package_has_no_effect(tmp_path: Path) -> None:
    result = _gui_plugins_finding(tmp_path, "my_plugin.py")
    assert result.state is ACResultState.CRIT


def test_gui_plugins_ignore_files_other_than_python(tmp_path: Path) -> None:
    result = _gui_plugins_finding(tmp_path, "views/README")
    assert result.state is ACResultState.OK


def test_gui_plugin_finding_names_its_file(tmp_path: Path) -> None:
    result = _gui_plugins_finding(tmp_path, "views/my_view.py")
    assert result.path == tmp_path / _GUI_PLUGINS_DIR / "views/my_view.py"


def test_gui_plugin_findings_are_sorted_by_their_file(tmp_path: Path) -> None:
    _write(tmp_path / _GUI_PLUGINS_DIR, "views/b_view.py")
    _write(tmp_path / _GUI_PLUGINS_DIR, "views/a_view.py")
    assert [result.path for result in _gui_plugins_test(tmp_path).execute()] == [
        tmp_path / _GUI_PLUGINS_DIR / "views/a_view.py",
        tmp_path / _GUI_PLUGINS_DIR / "views/b_view.py",
    ]


def test_gui_plugins_help_names_its_folder(tmp_path: Path) -> None:
    assert f"'{tmp_path / 'plugins'}'" in ACTestDeprecatedGUIExtensions(tmp_path / "plugins").help()


def test_legacy_gui_plugins_help_names_its_folder(tmp_path: Path) -> None:
    assert (
        f"'{tmp_path / 'web/plugins'}'"
        in ACTestDeprecatedLegacyGUIExtensions(tmp_path / "web").help()
    )


def test_legacy_gui_plugins_without_plugins(tmp_path: Path) -> None:
    [result] = ACTestDeprecatedLegacyGUIExtensions(
        tmp_path / _WEB_DIR, _gui_module_dirs(tmp_path)
    ).execute()
    assert result.state is ACResultState.OK


@pytest.mark.parametrize(
    "folder", ["config", "dashboard", "icons", "pages", "sidebar", "visuals", "wato"]
)
def test_legacy_gui_plugin_in_each_loaded_folder_warns(tmp_path: Path, folder: str) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, f"plugins/{folder}/my_plugin.py")
    assert result.text.endswith(
        "Checkmk loads plug-ins from this folder through internal interfaces, which are"
        " not supported for plug-ins."
    )


def test_legacy_gui_plugin_in_loaded_folder_is_reported_with_its_reason(tmp_path: Path) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, "plugins/views/my_view.py")
    assert (result.state, result.text, result.path) == (
        ACResultState.WARN,
        (
            f"'{tmp_path / _WEB_DIR / 'plugins/views/my_view.py'}'"
            " may break with any update of Checkmk."
            " Checkmk loads plug-ins from this folder through internal interfaces, which are"
            " not supported for plug-ins."
        ),
        tmp_path / _WEB_DIR / "plugins/views/my_view.py",
    )


@pytest.mark.parametrize(
    "folder, gui_module",
    [
        ("reporting", "cee/reporting/__init__.py"),
        ("sla", "cee/sla/__init__.py"),
        ("userdb", "userdb/__init__.py"),
        ("watolib", "watolib/__init__.py"),
    ],
)
def test_legacy_gui_plugin_in_deprecated_folder_is_deprecated(
    tmp_path: Path, folder: str, gui_module: str
) -> None:
    _write(tmp_path / _SHIPPED_GUI_DIR, gui_module)
    result = _legacy_gui_plugins_finding(tmp_path, f"plugins/{folder}/my_plugin.py")
    assert (result.state, result.text) == (
        ACResultState.WARN,
        (
            f"'{tmp_path / _WEB_DIR / 'plugins' / folder / 'my_plugin.py'}'"
            " may break with any update of Checkmk."
            " Checkmk loads plug-ins from this folder through internal interfaces, which are"
            " not supported for plug-ins. Checkmk 2.5.0 no longer loads them."
        ),
    )


@pytest.mark.parametrize("folder", ["reporting", "sla"])
def test_legacy_gui_plugin_of_a_commercial_module_has_no_effect_without_it(
    tmp_path: Path, folder: str
) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, f"plugins/{folder}/my_plugin.py")
    assert result.state is ACResultState.CRIT


@pytest.mark.parametrize("folder", ["metrics", "perfometer", "metrics/sub"])
def test_legacy_gui_plugin_in_graphing_folder_names_the_graphing_api(
    tmp_path: Path, folder: str
) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, f"plugins/{folder}/my_metrics.py")
    assert (result.state, result.text) == (
        ACResultState.CRIT,
        (
            f"'{tmp_path / _WEB_DIR / 'plugins' / folder / 'my_metrics.py'}'"
            " has no effect in Checkmk."
            " Checkmk no longer reads graphs, metrics and perf-o-meters from this folder."
            " Re-implement it with the supported API cmk.graphing.v1."
        ),
    )


def test_legacy_gui_plugin_without_effect_is_reported_with_its_reason(tmp_path: Path) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, "plugins/my_folder/my_view.py")
    assert (result.state, result.text) == (
        ACResultState.CRIT,
        (
            f"'{tmp_path / _WEB_DIR / 'plugins/my_folder/my_view.py'}'"
            " has no effect in Checkmk. Checkmk does not load plug-ins from this folder."
        ),
    )


def test_legacy_gui_plugin_nested_in_loaded_folder_has_no_effect(tmp_path: Path) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, "plugins/views/sub/my_view.py")
    assert result.state is ACResultState.CRIT


def test_legacy_gui_plugin_directly_in_plugins_folder_has_no_effect(tmp_path: Path) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, "plugins/my_view.py")
    assert result.state is ACResultState.CRIT


def test_legacy_gui_plugin_outside_plugins_folder_has_no_effect(tmp_path: Path) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, "htdocs/my_page.py")
    assert result.state is ACResultState.CRIT


def test_legacy_gui_plugins_ignore_files_other_than_python(tmp_path: Path) -> None:
    result = _legacy_gui_plugins_finding(tmp_path, "plugins/views/README")
    assert result.state is ACResultState.OK


_LOCAL_ROOT = Path("/omd/sites/NO_SITE/local")


def _broken_gui_extension_finding(path: Path) -> ACSingleResult:
    def failed_plugins() -> Sequence[tuple[Path, str, str, BaseException]]:
        return [(path, "views", "my_view", NameError("name 'x' is not defined"))]

    [result] = ACTestBrokenGUIExtension(failed_plugins, _LOCAL_ROOT).execute()
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
            Path("/omd/sites/NO_SITE/local/lib/check_mk/gui/plugins/views/my_view.py"),
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


def test_broken_gui_extension_error_ending_with_a_period() -> None:
    def failed_plugins() -> Sequence[tuple[Path, str, str, BaseException]]:
        return [(Path("a.py"), "views", "a_view", NameError("Some error."))]

    [result] = ACTestBrokenGUIExtension(failed_plugins, _LOCAL_ROOT).execute()
    assert result.text == (
        "'views/a_view' has no effect in Checkmk. Checkmk fails to load it: Some error. The log"
        " file 'var/log/web.log' shows the details."
    )


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(
            Path("/omd/sites/NO_SITE/lib/python3/cmk/gui/utils/rule_specs/legacy_converter.py"),
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


def test_without_broken_gui_extensions() -> None:
    [result] = ACTestBrokenGUIExtension(list).execute()
    assert result.state is ACResultState.OK


def test_every_broken_gui_extension_is_reported() -> None:
    def failed_plugins() -> Sequence[tuple[Path, str, str, BaseException]]:
        return [
            (Path("a.py"), "views", "a_view", NameError("a")),
            (Path("b.py"), "sidebar", "b_snapin", NameError("b")),
        ]

    assert [
        result.text for result in ACTestBrokenGUIExtension(failed_plugins, _LOCAL_ROOT).execute()
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
    [result] = ACTestDeprecatedPNPTemplates(tmp_path / _PNP_TEMPLATES_DIR).execute()
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
    results = ACTestDeprecatedPNPTemplates(tmp_path / _PNP_TEMPLATES_DIR).execute()
    assert [result.path for result in results] == [
        tmp_path / "local/share/check_mk/pnp-templates/check_mk-a.php",
        tmp_path / "local/share/check_mk/pnp-templates/check_mk-b.php",
        tmp_path / "local/share/check_mk/pnp-templates/foo/check_mk-c.php",
    ]


def test_without_pnp_templates(tmp_path: Path) -> None:
    [result] = ACTestDeprecatedPNPTemplates(tmp_path / _PNP_TEMPLATES_DIR).execute()
    assert result.state is ACResultState.OK
