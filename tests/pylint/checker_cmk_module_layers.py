#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checker to prevent disallowed imports of modules"""

from contextlib import suppress
from pathlib import Path
from typing import NewType

from astroid.nodes import Import, ImportFrom  # type: ignore[import-untyped]
from pylint.checkers import BaseChecker
from pylint.checkers.utils import only_required_for_messages
from pylint.lint.pylinter import PyLinter

from tests.testlib.repo import repo_path

ModuleName = NewType("ModuleName", str)
ModulePath = NewType("ModulePath", str)  # TODO: use pathlib.Path
Component = NewType("Component", str)


def register(linter: PyLinter) -> None:
    linter.register_checker(CMKModuleLayerChecker(linter))


# https://www.python.org/dev/peps/pep-0616/
def removeprefix(text: str, prefix: Path) -> str:
    prefix_as_string = str(prefix) + "/"
    return text[len(prefix_as_string) :] if text.startswith(prefix_as_string) else text


def removesuffix(text: str, suffix: str) -> str:
    return text[: -len(suffix)] if suffix and text.endswith(suffix) else text


def get_absolute_importee(
    *,
    root_name: str,
    modname: str,
    level: int,
    is_package: bool,
) -> ModuleName:
    parent = root_name.rsplit(".", level - is_package)[0]
    return ModuleName(f"{parent}.{modname}")


def _is_package(node: ImportFrom) -> bool:
    parent = node.parent
    try:
        return bool(parent.package)
    except AttributeError:  # could be a try/except block, for instance.
        return _is_package(parent)


def _in_component(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return imported == ModuleName(component) or imported.startswith(component + ".")


def _is_allowed_import(imported: ModuleName) -> bool:
    """these are allowed to be imported from all over the place"""
    return any(
        (
            imported == "cmk",
            _in_component(imported=imported, component=Component("cmk.ccc")),
            _in_component(imported=imported, component=Component("cmk.crypto")),
            _in_component(imported=imported, component=Component("cmk.utils")),
            _in_component(imported=imported, component=Component("cmk.fields")),
            _in_component(imported=imported, component=Component("cmk.automations")),
            _in_component(imported=imported, component=Component("cmk.bi")),
            _in_component(imported=imported, component=Component("cmk.piggyback")),
            _in_component(imported=imported, component=Component("cmk.piggyback_hub")),
            _in_component(imported=imported, component=Component("cmk.plugins.mail")),
            _in_component(imported=imported, component=Component("cmk.plugins.collection")),
            _in_component(imported=imported, component=Component("cmk.discover_plugins")),
            _in_component(imported=imported, component=Component("cmk.agent_based")),
            _in_component(imported=imported, component=Component("cmk.rulesets")),
            _in_component(imported=imported, component=Component("cmk.shared_typing")),
            _in_component(imported=imported, component=Component("cmk.server_side_calls")),
            _in_component(imported=imported, component=Component("cmk.werks")),
            _in_component(imported=imported, component=Component("cmk.messaging")),
            _in_component(imported=imported, component=Component("cmk.mkp_tool")),
            _in_component(imported=imported, component=Component("cmk.graphing")),
            _in_component(imported=imported, component=Component("cmk.trace")),
            _in_component(imported=imported, component=Component("cmk.events")),
            _in_component(imported=imported, component=Component("cmk.otel_collector")),
        )
    )


def _is_default_allowed_import(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return _is_allowed_import(imported) or _in_component(imported=imported, component=component)


def _is_allowed_for_special_agent_executable(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    if _in_component(imported=imported, component=Component("cmk.special_agents")):
        # still ok, but is on its way out.
        return True

    if _in_component(imported=imported, component=Component("cmk.plugins")):
        # allow all `cmk.plugins.<FAMILY>.special_agents`
        with suppress(IndexError):
            return imported.split(".")[3] == "special_agents"

    return False


def _allow_default_plus_checkers(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    """`cmk.checkengine` is the generic (library) part to the check engine."""
    return any(
        (
            _is_default_allowed_import(imported=imported, component=component),
            _in_component(imported=imported, component=Component("cmk.checkengine")),
        )
    )


def _allow_default_plus_fetchers_and_snmplib(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    """
    Allow import of `cmk.checkengine`, `cmk.fetchers` and `cmk.snmplib`.

    `cmk.fetchers` are concrete fetchers implementations to the check engine.
    The module shouldn't be required in too many places, always prefer the
    more abstract `cmk.checkengine` or refactor the code so that `cmk.checkengine` can
    be used instead.

    `cmk.snmplib` is part of the SNMP fetcher backend.  The same restrictions apply.

    """
    return any(
        (
            _is_default_allowed_import(imported=imported, component=component),
            _in_component(imported=imported, component=Component("cmk.fetchers")),
            _in_component(imported=imported, component=Component("cmk.snmplib")),
        )
    )


def _allow_default_plus_fetchers_checkers_and_snmplib(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    """
    Allow import of `cmk.fetchers`, `cmk.checkengine` and `cmk.snmplib`.

    The layering is such that `fetchers` and `snmplib` is between
    `utils` and `base` so that importing `fetchers` in `utils` is
    wrong but anywhere else is OK.
    """
    return any(
        (
            _allow_default_plus_fetchers_and_snmplib(
                imported=imported,
                component=component,
            ),
            _in_component(imported=imported, component=Component("cmk.checkengine")),
        )
    )


def _allowed_for_base(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    """
    Allow import of `cmk.checkengine`, `cmk.snmplib` and `cmk.cee.bakery`.

    Warning:
        Refactor to depend on `cmk.checkengine` only.

    """
    return any(
        (
            _allow_default_plus_fetchers_checkers_and_snmplib(
                imported=imported,
                component=component,
            ),
            _in_component(imported=imported, component=Component("cmk.cee.helpers")),
            _in_component(imported=imported, component=Component("cmk.cee.bakery")),
            _in_component(imported=imported, component=Component("cmk.server_side_calls_backend")),
        )
    )


def _allowed_for_base_cee(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _allowed_for_base(imported=imported, component=component),
            _in_component(imported=imported, component=Component("cmk.cee.robotmk.licensing")),
            _in_component(imported=imported, component=Component("cmk.cee.robotmk.html_log_dir")),
            _in_component(
                imported=imported, component=Component("cmk.cee.robotmk.bakery.core_bakelets")
            ),
        )
    )


def _allow_for_gui_plugins(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _is_allowed_import(imported=imported),
            _in_component(imported=imported, component=Component("cmk.gui")),
            _in_component(imported=imported, component=Component("cmk.checkengine")),
            _in_component(imported=imported, component=Component("cmk.fetchers")),
            _in_component(imported=imported, component=Component("cmk.cee.bakery")),
        )
    )


def _allow_for_gui(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _is_allowed_import(imported=imported),
            (
                _in_component(imported=imported, component=Component("cmk.gui"))
                and not _in_component(imported=imported, component=Component("cmk.gui.cee"))
                and not _in_component(imported=imported, component=Component("cmk.gui.cce"))
                and not _in_component(imported=imported, component=Component("cmk.gui.cme"))
                and not _is_a_plugin_import(imported=imported)
            ),
            _in_component(imported=imported, component=Component("cmk.checkengine")),
            _in_component(imported=imported, component=Component("cmk.messaging")),
            _in_component(imported=imported, component=Component("cmk.server_side_calls_backend")),
            _in_component(imported=imported, component=Component("cmk.diskspace.config")),
        )
    )


def _allow_for_gui_cee(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _is_allowed_import(imported=imported),
            (
                _in_component(imported=imported, component=Component("cmk.gui"))
                and not _in_component(imported=imported, component=Component("cmk.gui.cce"))
                and not _in_component(imported=imported, component=Component("cmk.gui.cme"))
                and not _is_a_plugin_import(imported=imported)
            ),
            _in_component(imported=imported, component=Component("cmk.checkengine")),
            _in_component(imported=imported, component=Component("cmk.fetchers")),
            _in_component(imported=imported, component=Component("cmk.cee.bakery")),
            _in_component(imported=imported, component=Component("cmk.cee.robotmk.gui")),
        )
    )


def _allow_for_gui_cce(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _is_allowed_import(imported=imported),
            (
                _in_component(imported=imported, component=Component("cmk.gui"))
                and not _in_component(imported=imported, component=Component("cmk.gui.cme"))
                and not _is_a_plugin_import(imported=imported)
            ),
            _in_component(imported=imported, component=Component("cmk.checkengine")),
            _in_component(imported=imported, component=Component("cmk.fetchers")),
            _in_component(imported=imported, component=Component("cmk.cee.bakery")),
            _in_component(imported=imported, component=Component("cmk.cee.robotmk.gui")),
        )
    )


def _allow_for_gui_cme(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _is_allowed_import(imported=imported),
            (
                _in_component(imported=imported, component=Component("cmk.gui"))
                and not _is_a_plugin_import(imported=imported)
            ),
            _in_component(imported=imported, component=Component("cmk.checkengine")),
            _in_component(imported=imported, component=Component("cmk.fetchers")),
            _in_component(imported=imported, component=Component("cmk.cee.bakery")),
            _in_component(imported=imported, component=Component("cmk.cee.robotmk.gui")),
        )
    )


def _allow_for_gui_cse(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _is_allowed_import(imported=imported),
            (
                _in_component(imported=imported, component=Component("cmk.gui"))
                and not _is_a_plugin_import(imported=imported)
            ),
            _in_component(imported=imported, component=Component("cmk.cee.robotmk.gui")),
        )
    )


def _is_a_plugin_import(*, imported: ModuleName) -> bool:
    return any(
        (
            _in_component(imported=imported, component=Component("cmk.gui.plugins")),
            _in_component(imported=imported, component=Component("cmk.gui.cee.plugins")),
            _in_component(imported=imported, component=Component("cmk.gui.cce.plugins")),
        )
    )


def _allow_default_plus_gui_and_base(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    """
    Allow import of `cmk.gui` and `cmk.base`.

    The `gui` and `base` are different components, but for specific cases, like `cmk_update_config`
    and `post_rename_site` it is allowed to import both.
    """
    return any(
        (
            _is_default_allowed_import(imported=imported, component=component),
            _in_component(imported=imported, component=Component("cmk.base")),
            _in_component(imported=imported, component=Component("cmk.gui")),
        )
    )


def _allow_for_cmk_update_config(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    """
    Allow import of `cmk.gui`, `cmk.base` and `cmk.cee.bakery`.

    The `gui`, `base` and `bakery` are different components, but for specific cases, like `cmk_update_config`
    and `post_rename_site` it is allowed to import both.
    """
    return any(
        (
            _is_default_allowed_import(imported=imported, component=component),
            _in_component(imported=imported, component=Component("cmk.checkengine")),
            _in_component(imported=imported, component=Component("cmk.fetchers")),
            _in_component(imported=imported, component=Component("cmk.cee.bakery")),
            _in_component(imported=imported, component=Component("cmk.base")),
            _in_component(imported=imported, component=Component("cmk.gui")),
            _in_component(imported=imported, component=Component("cmk.cee.robotmk")),
            _in_component(imported=imported, component=Component("cmk.diskspace.config")),
            _in_component(imported=imported, component=Component("cmk.validate_config")),
        )
    )


def _is_allowed_for_diskspace(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _in_component(imported=imported, component=Component("cmk.diskspace")),
            _in_component(imported=imported, component=Component("cmk.ccc")),
        )
    )


def _is_allowed_for_plugins(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _in_component(imported=imported, component=Component("cmk.agent_based.v1")),
            _in_component(imported=imported, component=Component("cmk.agent_based.v2")),
            _in_component(imported=imported, component=Component("cmk.graphing.v1")),
            _in_component(imported=imported, component=Component("cmk.rulesets.v1")),
            _in_component(imported=imported, component=Component("cmk.server_side_calls.v1")),
            _in_component(imported=imported, component=Component("cmk.special_agents.v0_unstable")),
            _in_component(imported=imported, component=Component("cmk.plugins")),
            _in_component(imported=imported, component=Component("cmk.utils")),
            _in_component(imported=imported, component=Component("cmk.ccc")),
        )
    )


def _is_allowed_for_robotmk_agent_based_cee_plugins(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return _in_component(
        imported=imported,
        component=Component("cmk.cee.robotmk.checking.agent_based"),
    )


def _is_allowed_for_robotmk_graphing_cee_plugins(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return _in_component(
        imported=imported,
        component=Component("cmk.cee.robotmk.checking.graphing"),
    )


def _is_allowed_for_robotmk_rulesets_cee_plugins(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _in_component(
                imported=imported,
                component=Component("cmk.cee.robotmk.checking.rulesets"),
            ),
            _in_component(
                imported=imported,
                component=Component("cmk.cee.robotmk.bakery.rulesets"),
            ),
        )
    )


def _allow_default_plus_component_under_test(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    if component.startswith("tests.unit.checks"):
        component_under_test = Component("cmk.plugins")
    elif component.startswith("tests.unit.") or component.startswith("tests.integration"):
        component_under_test = Component(".".join(component.split(".")[2:]))
    else:
        raise ValueError(f"Unhandled component: {component}")

    return any(
        (
            _is_default_allowed_import(imported=imported, component=component),
            _is_default_allowed_import(imported=imported, component=component_under_test),
        )
    )


def _is_allowed_for_legacy_checks(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _in_component(imported=imported, component=Component("cmk.base.legacy_checks")),
            _in_component(imported=imported, component=Component("cmk.base.check_legacy_includes")),
            _in_component(imported=imported, component=Component("cmk.plugins")),
            _in_component(imported=imported, component=Component("cmk.base.config")),
            _in_component(
                imported=imported, component=Component("cmk.agent_based.legacy.v0_unstable")
            ),
            _in_component(
                imported=imported,
                component=Component("cmk.base.plugins.agent_based"),
            ),
            _in_component(imported=imported, component=Component("cmk.agent_based")),
        )
    )


def _is_allowed_for_legacy_check_tests(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _allow_default_plus_component_under_test(imported=imported, component=component),
            _in_component(imported=imported, component=Component("cmk.base.legacy_checks")),
            _in_component(imported=imported, component=Component("cmk.base.check_legacy_includes")),
            _in_component(imported=imported, component=Component("cmk.server_side_calls_backend")),
            _in_component(imported=imported, component=Component("cmk.base.api.agent_based")),
            _in_component(imported=imported, component=Component("cmk.checkengine")),
            _in_component(imported=imported, component=Component("cmk.snmplib")),
            _in_component(imported=imported, component=Component("cmk.plugins")),
        )
    )


def _allow_default_plus_component_under_test_bakery_checkengine(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _allow_default_plus_component_under_test(imported=imported, component=component),
            _in_component(imported=imported, component=Component("cmk.checkengine")),
            _in_component(imported=imported, component=Component("cmk.cee.bakery")),
        )
    )


def _allowed_for_robotmk(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _allow_default_plus_gui_and_base(imported=imported, component=component),
            _is_allowed_for_plugins(imported=imported, component=component),
            _in_component(imported=imported, component=Component("cmk.checkengine")),
            _in_component(imported=imported, component=Component("cmk.cee.bakery")),
        )
    )


def _allow_for_cmk_checkengine(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _is_default_allowed_import(imported=imported, component=component),
            _in_component(imported=imported, component=Component("cmk.checkengine")),
            _in_component(imported=imported, component=Component("cmk.snmplib")),
        )
    )


def _allow_for_cmk_fetchers(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _is_default_allowed_import(imported=imported, component=component),
            _in_component(imported=imported, component=Component("cmk.fetchers")),
            _in_component(imported=imported, component=Component("cmk.snmplib")),
            _in_component(imported=imported, component=Component("cmk.checkengine")),
        )
    )


def _allow_for_cmk_piggyback_hub(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _is_default_allowed_import(imported=imported, component=component),
            _in_component(imported=imported, component=Component("cmk.messaging")),
        )
    )


def _allow_for_cmkpasswd(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _is_default_allowed_import(imported=imported, component=component),
            _in_component(imported=imported, component=Component("cmk.gui.utils.htpasswd")),
        )
    )


_COMPONENTS = (
    (Component("agents.special"), _is_allowed_for_special_agent_executable),
    (Component("tests.unit.cmk"), _allow_default_plus_component_under_test),
    (Component("tests.unit.checks"), _is_allowed_for_legacy_check_tests),
    (Component("tests.extension_compatibility"), _allow_default_plus_gui_and_base),
    (Component("tests.integration.cmk.post_rename_site"), _allow_default_plus_component_under_test),
    (Component("tests.integration.cmk.snmplib"), _allow_default_plus_component_under_test),
    (Component("tests.integration.cmk.gui"), _allow_default_plus_component_under_test),
    (Component("tests.integration.cmk.cee.liveproxy"), _allow_default_plus_component_under_test),
    (
        Component("tests.integration.cmk.base"),
        _allow_default_plus_component_under_test_bakery_checkengine,
    ),
    (
        Component("tests.integration.cmk.cee.robotmk"),
        _allow_default_plus_component_under_test,
    ),
    # Namespaces below cmk.base.api.agent_based are not really components,
    # but they (almost) adhere to the same import restrictions,
    # and we want to encourage that
    (Component("cmk.base.api.agent_based.value_store"), _allow_default_plus_checkers),
    (Component("cmk.base.api.agent_based"), _allow_default_plus_fetchers_checkers_and_snmplib),
    (Component("cmk.base.check_legacy_includes"), _is_allowed_for_legacy_checks),
    (Component("cmk.base.legacy_checks"), _is_allowed_for_legacy_checks),
    # importing config in ip_lookup repeatedly lead to import cycles. It's cleanup now.
    (Component("cmk.base.ip_lookup"), _is_default_allowed_import),
    (Component("cmk.base"), _allowed_for_base_cee),
    (Component("cmk.base.cee"), _allowed_for_base_cee),
    (Component("cmk.cmkpasswd"), _allow_for_cmkpasswd),
    (Component("cmk.checkengine"), _allow_for_cmk_checkengine),
    (Component("cmk.fetchers"), _allow_for_cmk_fetchers),
    (Component("cmk.cee.helpers"), _allow_default_plus_fetchers_checkers_and_snmplib),
    (Component("cmk.automations"), _allow_default_plus_checkers),
    (Component("cmk.snmplib"), _is_default_allowed_import),
    (Component("cmk.gui.plugins"), _allow_for_gui_plugins),
    (Component("cmk.gui.cee.plugins"), _allow_for_gui_plugins),
    (Component("cmk.gui.cce.plugins"), _allow_for_gui_plugins),
    (Component("cmk.gui.cee"), _allow_for_gui_cee),
    (Component("cmk.gui.cce"), _allow_for_gui_cce),
    (Component("cmk.gui.cme"), _allow_for_gui_cme),
    (Component("cmk.gui.cse"), _allow_for_gui_cse),
    (Component("cmk.gui"), _allow_for_gui),
    (Component("cmk.ec"), _is_default_allowed_import),
    (Component("cmk.notification_plugins"), _is_default_allowed_import),
    (Component("cmk.piggyback.hub"), _allow_for_cmk_piggyback_hub),
    (
        Component("cmk.plugins.robotmk.agent_based.cee"),
        _is_allowed_for_robotmk_agent_based_cee_plugins,
    ),
    (
        Component("cmk.plugins.robotmk.graphing.cee"),
        _is_allowed_for_robotmk_graphing_cee_plugins,
    ),
    (
        Component("cmk.plugins.robotmk.rulesets.cee"),
        _is_allowed_for_robotmk_rulesets_cee_plugins,
    ),
    (Component("cmk.plugins"), _is_allowed_for_plugins),
    (Component("cmk.server_side_calls_backend"), _is_default_allowed_import),
    (Component("cmk.special_agents"), _is_default_allowed_import),
    (Component("cmk.update_config"), _allow_for_cmk_update_config),
    (Component("cmk.validate_config"), _allow_default_plus_gui_and_base),
    (Component("cmk.validate_plugins"), _is_default_allowed_import),
    (Component("cmk.utils"), _is_default_allowed_import),
    (Component("cmk.cee.bakery"), _is_default_allowed_import),
    (Component("cmk.cee.dcd"), _is_default_allowed_import),
    (Component("cmk.cee.mknotifyd"), _is_default_allowed_import),
    (Component("cmk.cee.snmp_backend"), _is_default_allowed_import),
    (Component("cmk.cee.liveproxy"), _is_default_allowed_import),
    (Component("cmk.cee.notification_plugins"), _is_default_allowed_import),
    (Component("cmk.post_rename_site"), _allow_default_plus_gui_and_base),
    (Component("cmk.active_checks"), _is_default_allowed_import),
    (Component("cmk.cee.robotmk"), _allowed_for_robotmk),
    (Component("cmk.diskspace"), _is_allowed_for_diskspace),
)

_EXPLICIT_FILE_TO_COMPONENT = {
    ModulePath("web/app/index.wsgi"): Component("cmk.gui"),
    ModulePath("bin/check_mk"): Component("cmk.base"),
    ModulePath("bin/cmk-automation-helper"): Component("cmk.base"),
    ModulePath("bin/cmk-compute-api-spec"): Component("cmk.gui"),
    ModulePath("bin/cmk-passwd"): Component("cmk.cmkpasswd"),
    ModulePath("bin/cmk-piggyback-hub"): Component("cmk.piggyback"),
    ModulePath("bin/cmk-ui-job-scheduler"): Component("cmk.gui"),
    ModulePath("bin/cmk-update-config"): Component("cmk.update_config"),
    ModulePath("bin/cmk-validate-config"): Component("cmk.validate_config"),
    ModulePath("bin/cmk-validate-plugins"): Component("cmk.validate_plugins"),
    ModulePath("bin/post-rename-site"): Component("cmk.post_rename_site"),
    ModulePath("bin/mkeventd"): Component("cmk.ec"),
    ModulePath("omd/packages/enterprise/bin/liveproxyd"): Component("cmk.cee.liveproxy"),
    ModulePath("omd/packages/enterprise/bin/mknotifyd"): Component("cmk.cee.mknotifyd"),
    ModulePath("omd/packages/enterprise/bin/dcd"): Component("cmk.cee.dcd"),
    ModulePath("omd/packages/enterprise/bin/fetcher"): Component("cmk.cee.helpers"),
    # CEE specific notification plugins
    ModulePath("notifications/servicenow"): Component("cmk.cee.notification_plugins"),
    ModulePath("notifications/jira_issues"): Component("cmk.cee.notification_plugins"),
}


class CMKModuleLayerChecker(BaseChecker):
    name = "cmk-module-layer-violation"
    msgs = {
        "C8410": ("Import of %r not allowed in module %r", "cmk-module-layer-violation", "whoop?"),
    }

    # This doesn't change during a pylint run, so let's save a realpath() call per import.
    cmk_path_cached = repo_path()

    @only_required_for_messages("cmk-module-layer-violation")
    def visit_import(self, node: Import) -> None:
        for name, _ in node.names:
            self._check_import(node, ModuleName(name))

    @only_required_for_messages("cmk-module-layer-violation")
    def visit_importfrom(self, node: ImportFrom) -> None:
        # handle 'from . import foo, bar'
        imported = [node.modname] if node.modname else [n for n, _ in node.names]
        for modname in imported:
            self._check_import(
                node,
                (
                    ModuleName(modname)
                    if node.level is None
                    else get_absolute_importee(
                        root_name=node.root().name,
                        modname=modname,
                        level=node.level,
                        is_package=_is_package(node),
                    )
                ),
            )

    def _check_import(self, node: Import | ImportFrom, imported: ModuleName) -> None:
        # We only care about imports of our own modules.
        if not imported.startswith("cmk"):
            return

        # We use paths relative to our project root, but not for our "pasting magic".
        absolute_path: str = node.root().file
        importing_path = ModulePath(removeprefix(absolute_path, self.cmk_path_cached))

        # Tests are allowed to import everything for now. Should be cleaned up soon
        if str(importing_path).startswith("tests/testlib"):
            return

        importing = self._get_module_name_of_files(importing_path)
        if not self._is_import_allowed(importing_path, importing, imported):
            self.add_message("cmk-module-layer-violation", node=node, args=(imported, importing))

    @staticmethod
    def _get_module_name_of_files(importing_path: ModulePath) -> ModuleName:
        # Due to our symlinks and pasting magic, astroid gets confused, so we need to compute the
        # real module name from the file path of the module.
        parts = importing_path.split("/")
        parts[-1] = removesuffix(parts[-1], ".py")
        # Emacs' flycheck stores files to be checked in a temporary file with a prefix.
        parts[-1] = removeprefix(parts[-1], Path("flycheck_"))
        # For all modules which don't live below cmk after mangling, just assume a toplevel module.
        if parts[0] not in ("cmk", "tests"):
            parts = [parts[-1]]
        return ModuleName(".".join(parts))

    def _is_import_allowed(
        self, importing_path: ModulePath, importing: ModuleName, imported: ModuleName
    ) -> bool:
        for component, component_specific_checker in _COMPONENTS:
            if not self._is_part_of_component(importing, importing_path, component):
                continue

            return component_specific_checker(
                imported=imported,
                component=component,
            )

        # the rest (matched no component)
        return _is_allowed_import(imported)

    @staticmethod
    def _is_part_of_component(
        importing: ModuleName, importing_path: ModulePath, component: Component
    ) -> bool:
        if _in_component(imported=importing, component=component):
            return True

        explicit_component = _EXPLICIT_FILE_TO_COMPONENT.get(importing_path)
        if explicit_component is not None:
            return explicit_component == component

        if component == Component("cmk.notification_plugins") and importing_path.startswith(
            "notifications/"
        ):
            return True

        if component == Component("agents.special") and importing_path.startswith(
            "agents/special/"
        ):
            return True

        if component == Component("cmk.active_checks") and importing_path.startswith(
            "active_checks/"
        ):
            return True

        return False
