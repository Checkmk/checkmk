#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.discover_plugins import PluginConflict, PluginLocation
from cmk.gui.exceptions import MKUserError
from cmk.mkp_tool import Manifest, PackageID, PackageName, PackageVersion
from cmk.update_config.internal import ConflictMode
from cmk.update_config.plugins.pre_actions.agent_based_plugins import (
    find_plugin_problems,
    PluginProblems,
    report_plugin_problems,
)

LOCAL_ROOT = Path("/omd/sites/heute/local")
SHIPPED_MODULE = "cmk.plugins.network.agent_based.openvpn_clients"
SHIPPED_FILE = Path("/omd/versions/default/lib/python3/cmk/plugins/network/agent_based/x.py")
OTHER_SHIPPED_MODULE = "cmk.plugins.collection.agent_based.openvpn_clients"
OTHER_SHIPPED_FILE = Path(
    "/omd/versions/default/lib/python3/cmk/plugins/collection/agent_based/y.py"
)
MKP_MODULE = "cmk_addons.plugins.openvpn_clients.agent_based.openvpn_clients"
MKP_FILE = LOCAL_ROOT / "lib/python3/cmk_addons/plugins/openvpn_clients/agent_based/x.py"
OTHER_MKP_MODULE = "cmk_addons.plugins.openvpn_clients.agent_based.openvpn_clients_v2"
OTHER_MKP_FILE = LOCAL_ROOT / "lib/python3/cmk_addons/plugins/openvpn_clients/agent_based/y.py"
LOCAL_MODULE = "cmk_addons.plugins.mine.agent_based.mine"
LOCAL_FILE = LOCAL_ROOT / "lib/python3/cmk_addons/plugins/mine/agent_based/mine.py"

OUTDATED_MKP_MODULE = "cmk_addons.plugins.openvpn_old.agent_based.openvpn_clients"
OUTDATED_MKP_FILE = LOCAL_ROOT / "lib/python3/cmk_addons/plugins/openvpn_old/agent_based/x.py"

MODULE_PATHS = {
    SHIPPED_MODULE: SHIPPED_FILE,
    OTHER_SHIPPED_MODULE: OTHER_SHIPPED_FILE,
    MKP_MODULE: MKP_FILE,
    OTHER_MKP_MODULE: OTHER_MKP_FILE,
    LOCAL_MODULE: LOCAL_FILE,
    OUTDATED_MKP_MODULE: OUTDATED_MKP_FILE,
}

MANIFEST = Manifest(
    title="OpenVPN Clients",
    name=PackageName("openvpn_clients"),
    description="",
    version=PackageVersion("1.0.0"),
    version_packaged="2.3.0p34",
    version_min_required="2.3.0b1",
    author="someone",
    download_url="",
    files={},
)
OUTDATED_MANIFEST = MANIFEST.model_copy(
    update={"name": PackageName("openvpn_old"), "version_usable_until": "2.0.0"}
)


def _plugins(
    conflicts: list[PluginConflict] | None = None,
    errors_by_module: dict[str, list[str]] | None = None,
) -> AgentBasedPlugins:
    return AgentBasedPlugins(
        agent_sections={},
        snmp_sections={},
        check_plugins={},
        inventory_plugins={},
        errors=(),
        conflicts=conflicts or [],
        errors_by_module=errors_by_module or {},
    )


def _conflict(used_module: str, ignored_module: str) -> PluginConflict:
    return PluginConflict(
        "openvpn_clients",
        used=PluginLocation(used_module, "agent_section_openvpn_clients"),
        ignored=PluginLocation(ignored_module, "agent_section_openvpn_clients"),
    )


def test_package_replacing_a_shipped_plugin_is_reported_for_the_package() -> None:
    problems = find_plugin_problems(
        _plugins(conflicts=[_conflict(MKP_MODULE, SHIPPED_MODULE)]),
        MODULE_PATHS.get,
        {MKP_FILE: MANIFEST},
        LOCAL_ROOT,
    )

    assert list(problems.by_package) == [MANIFEST.id]


def test_package_ignored_in_favor_of_a_shipped_plugin_is_reported_for_the_package() -> None:
    problems = find_plugin_problems(
        _plugins(conflicts=[_conflict(SHIPPED_MODULE, MKP_MODULE)]),
        MODULE_PATHS.get,
        {MKP_FILE: MANIFEST},
        LOCAL_ROOT,
    )

    assert list(problems.by_package) == [MANIFEST.id]


def test_conflict_among_shipped_plugins_is_reported_as_shipped() -> None:
    problems = find_plugin_problems(
        _plugins(conflicts=[_conflict(SHIPPED_MODULE, OTHER_SHIPPED_MODULE)]),
        MODULE_PATHS.get,
        {},
        LOCAL_ROOT,
    )

    assert (problems.by_package, problems.by_local, len(problems.shipped)) == ({}, {}, 1)


def test_conflict_within_one_package_is_reported_once() -> None:
    problems = find_plugin_problems(
        _plugins(conflicts=[_conflict(MKP_MODULE, OTHER_MKP_MODULE)]),
        MODULE_PATHS.get,
        {MKP_FILE: MANIFEST, OTHER_MKP_FILE: MANIFEST},
        LOCAL_ROOT,
    )

    assert {package_id: len(messages) for package_id, messages in problems.by_package.items()} == {
        MANIFEST.id: 1
    }


def test_conflict_between_a_package_and_a_local_file_is_reported_for_both() -> None:
    problems = find_plugin_problems(
        _plugins(conflicts=[_conflict(LOCAL_MODULE, MKP_MODULE)]),
        MODULE_PATHS.get,
        {MKP_FILE: MANIFEST},
        LOCAL_ROOT,
    )

    assert (list(problems.by_package), list(problems.by_local)) == (
        [MANIFEST.id],
        [f"local file {LOCAL_FILE}"],
    )


def test_error_of_a_package_names_the_file() -> None:
    problems = find_plugin_problems(
        _plugins(errors_by_module={MKP_MODULE: ["bad section"]}),
        MODULE_PATHS.get,
        {MKP_FILE: MANIFEST},
        LOCAL_ROOT,
    )

    assert problems.by_package == {MANIFEST.id: [f"bad section ({MKP_FILE})"]}


def test_errors_of_a_package_that_will_be_disabled_are_not_reported() -> None:
    problems = find_plugin_problems(
        _plugins(errors_by_module={OUTDATED_MKP_MODULE: ["bad section"]}),
        MODULE_PATHS.get,
        {OUTDATED_MKP_FILE: OUTDATED_MANIFEST},
        LOCAL_ROOT,
    )

    assert (problems.by_package, problems.outdated) == ({}, [OUTDATED_MANIFEST])


def test_problems_of_one_unpackaged_local_file_are_grouped() -> None:
    problems = find_plugin_problems(
        _plugins(
            conflicts=[_conflict(LOCAL_MODULE, SHIPPED_MODULE)],
            errors_by_module={LOCAL_MODULE: ["bad section"]},
        ),
        MODULE_PATHS.get,
        {},
        LOCAL_ROOT,
    )

    assert {culprit: len(messages) for culprit, messages in problems.by_local.items()} == {
        f"local file {LOCAL_FILE}": 2
    }


def test_problems_of_a_module_that_can_not_be_located_are_reported_as_local() -> None:
    problems = find_plugin_problems(
        _plugins(errors_by_module={"cmk_addons.plugins.gone.agent_based.gone": ["bad section"]}),
        MODULE_PATHS.get,
        {},
        LOCAL_ROOT,
    )

    assert (list(problems.by_local), problems.shipped) == (
        ["module cmk_addons.plugins.gone.agent_based.gone"],
        [],
    )


def test_conflict_with_a_package_that_will_be_disabled_is_not_reported() -> None:
    problems = find_plugin_problems(
        _plugins(conflicts=[_conflict(OUTDATED_MKP_MODULE, MKP_MODULE)]),
        MODULE_PATHS.get,
        {MKP_FILE: MANIFEST, OUTDATED_MKP_FILE: OUTDATED_MANIFEST},
        LOCAL_ROOT,
    )

    assert (problems.by_package, problems.outdated) == ({}, [OUTDATED_MANIFEST])


def _problems(
    by_package: dict[PackageID, list[str]] | None = None,
    by_local: dict[str, list[str]] | None = None,
    shipped: list[str] | None = None,
) -> PluginProblems:
    return PluginProblems(
        by_package=by_package or {},
        by_local=by_local or {},
        shipped=shipped or [],
        outdated=[],
    )


def test_problems_of_a_package_can_abort_the_update() -> None:
    with pytest.raises(MKUserError):
        report_plugin_problems(
            logging.getLogger(__name__),
            ConflictMode.ABORT,
            _problems(by_package={MANIFEST.id: ["bad section"]}),
        )


def test_force_continues_despite_problems_of_a_package() -> None:
    """The post-update step runs with FORCE: it must respect a "continue" of the pre-flight"""
    # Does not raise.
    report_plugin_problems(
        logging.getLogger(__name__),
        ConflictMode.FORCE,
        _problems(by_package={MANIFEST.id: ["bad section"]}),
    )


def test_problems_of_shipped_plugins_do_not_abort_the_update() -> None:
    # Does not raise, even though we would abort on any user fixable problem.
    report_plugin_problems(
        logging.getLogger(__name__),
        ConflictMode.ABORT,
        _problems(shipped=["bad section"]),
    )


def test_problems_of_an_unpackaged_local_file_can_abort_the_update() -> None:
    with pytest.raises(MKUserError):
        report_plugin_problems(
            logging.getLogger(__name__),
            ConflictMode.ABORT,
            _problems(by_local={f"local file {LOCAL_FILE}": ["bad section"]}),
        )
