#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checker to prevent disallowed imports of modules"""

from collections.abc import Callable, Sequence
from pathlib import Path

from astroid.nodes import Import, ImportFrom  # type: ignore[import-untyped]
from mypy_extensions import NamedArg
from pylint.checkers import BaseChecker
from pylint.checkers.utils import only_required_for_messages
from pylint.lint.pylinter import PyLinter

from tests.testlib.common.repo import repo_path


class ModulePath(Path):
    def is_below(self, path: str) -> bool:
        return is_prefix_of(Path(path).parts, self.parts)


class Component:
    def __init__(self, name: str):
        self._parts = name.split(".")

    @property
    def parts(self) -> Sequence[str]:
        return self._parts

    def __repr__(self) -> str:
        return ".".join(self.parts)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Component):
            return NotImplemented
        return self.parts == other.parts

    def is_below(self, component: str) -> bool:
        return is_prefix_of(Component(component).parts, self.parts)


class ModuleName:
    def __init__(self, name: str):
        self._parts = name.split(".")

    @property
    def parts(self) -> Sequence[str]:
        return self._parts

    def __repr__(self) -> str:
        return ".".join(self.parts)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ModuleName):
            return NotImplemented
        return self.parts == other.parts

    def in_component(self, component: Component) -> bool:
        return is_prefix_of(component.parts, self.parts)


def is_prefix_of[T](x: Sequence[T], y: Sequence[T]) -> bool:
    return x == y[: len(x)]


def register(linter: PyLinter) -> None:
    linter.register_checker(CMKModuleLayerChecker(linter))


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


def _allow(
    *modules: str,
) -> Callable[[NamedArg(ModuleName, "imported"), NamedArg(Component, "component")], bool]:
    def _is_allowed(
        *,
        imported: ModuleName,
        component: Component,
    ) -> bool:
        return imported.in_component(component) or any(
            imported.in_component(Component(m)) for m in modules
        )

    return _is_allowed


def _is_allowed_import(imported: ModuleName) -> bool:
    """these are allowed to be imported from all over the place"""
    return any(
        (
            imported == ModuleName("cmk"),
            imported.in_component(Component("cmk.ccc")),
            imported.in_component(Component("cmk.crypto")),
            imported.in_component(Component("cmk.utils")),
            imported.in_component(Component("cmk.fields")),
            imported.in_component(Component("cmk.automations")),
            imported.in_component(Component("cmk.bi")),
            imported.in_component(Component("cmk.piggyback")),
            imported.in_component(Component("cmk.discover_plugins")),
            imported.in_component(Component("cmk.agent_based")),
            imported.in_component(Component("cmk.rulesets")),
            imported.in_component(Component("cmk.shared_typing")),
            imported.in_component(Component("cmk.server_side_calls")),
            imported.in_component(Component("cmk.werks")),
            imported.in_component(Component("cmk.messaging")),
            imported.in_component(Component("cmk.mkp_tool")),
            imported.in_component(Component("cmk.graphing")),
            imported.in_component(Component("cmk.trace")),
            imported.in_component(Component("cmk.events")),
            imported.in_component(Component("cmk.otel_collector")),
        )
    )


def _is_default_allowed_import(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return _is_allowed_import(imported) or imported.in_component(component)


def _allow_default_plus_checkers(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    """`cmk.checkengine` is the generic (library) part to the check engine."""
    return any(
        (
            _is_default_allowed_import(imported=imported, component=component),
            imported.in_component(Component("cmk.checkengine")),
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
            imported.in_component(Component("cmk.fetchers")),
            imported.in_component(Component("cmk.snmplib")),
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
            imported.in_component(Component("cmk.checkengine")),
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
            imported.in_component(Component("cmk.cee.helpers")),
            imported.in_component(Component("cmk.cee.bakery")),
            imported.in_component(Component("cmk.server_side_calls_backend")),
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
            imported.in_component(Component("cmk.cee.robotmk.licensing")),
            imported.in_component(Component("cmk.cee.robotmk.html_log_dir")),
            imported.in_component(Component("cmk.cee.robotmk.bakery.core_bakelets")),
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
            imported.in_component(Component("cmk.gui")),
            imported.in_component(Component("cmk.checkengine")),
            imported.in_component(Component("cmk.fetchers")),
            imported.in_component(Component("cmk.cee.bakery")),
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
                imported.in_component(Component("cmk.gui"))
                and not imported.in_component(Component("cmk.gui.cee"))
                and not imported.in_component(Component("cmk.gui.cce"))
                and not imported.in_component(Component("cmk.gui.cme"))
                and not _is_a_plugin_import(imported=imported)
            ),
            imported.in_component(Component("cmk.checkengine")),
            imported.in_component(Component("cmk.messaging")),
            imported.in_component(Component("cmk.server_side_calls_backend")),
            imported.in_component(Component("cmk.diskspace.config")),
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
                imported.in_component(Component("cmk.gui"))
                and not imported.in_component(Component("cmk.gui.cce"))
                and not imported.in_component(Component("cmk.gui.cme"))
                and not _is_a_plugin_import(imported=imported)
            ),
            imported.in_component(Component("cmk.checkengine")),
            imported.in_component(Component("cmk.fetchers")),
            imported.in_component(Component("cmk.cee.bakery")),
            imported.in_component(Component("cmk.cee.robotmk.gui")),
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
                imported.in_component(Component("cmk.gui"))
                and not imported.in_component(Component("cmk.gui.cme"))
                and not _is_a_plugin_import(imported=imported)
            ),
            imported.in_component(Component("cmk.checkengine")),
            imported.in_component(Component("cmk.fetchers")),
            imported.in_component(Component("cmk.cee.bakery")),
            imported.in_component(Component("cmk.cee.robotmk.gui")),
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
                imported.in_component(Component("cmk.gui"))
                and not _is_a_plugin_import(imported=imported)
            ),
            imported.in_component(Component("cmk.checkengine")),
            imported.in_component(Component("cmk.fetchers")),
            imported.in_component(Component("cmk.cee.bakery")),
            imported.in_component(Component("cmk.cee.robotmk.gui")),
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
                imported.in_component(Component("cmk.gui"))
                and not _is_a_plugin_import(imported=imported)
            ),
            imported.in_component(Component("cmk.cee.robotmk.gui")),
        )
    )


def _is_a_plugin_import(*, imported: ModuleName) -> bool:
    return any(
        (
            imported.in_component(Component("cmk.gui.plugins")),
            imported.in_component(Component("cmk.gui.cee.plugins")),
            imported.in_component(Component("cmk.gui.cce.plugins")),
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
            imported.in_component(Component("cmk.base")),
            imported.in_component(Component("cmk.gui")),
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
            imported.in_component(Component("cmk.checkengine")),
            imported.in_component(Component("cmk.fetchers")),
            imported.in_component(Component("cmk.cee.bakery")),
            imported.in_component(Component("cmk.base")),
            imported.in_component(Component("cmk.gui")),
            imported.in_component(Component("cmk.cee.robotmk")),
            imported.in_component(Component("cmk.diskspace.config")),
            imported.in_component(Component("cmk.validate_config")),
        )
    )


def _is_allowed_for_diskspace(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            imported.in_component(Component("cmk.diskspace")),
            imported.in_component(Component("cmk.ccc")),
        )
    )


def _is_allowed_for_plugins(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            imported.in_component(Component("cmk.agent_based.v1")),
            imported.in_component(Component("cmk.agent_based.v2")),
            imported.in_component(Component("cmk.graphing.v1")),
            imported.in_component(Component("cmk.rulesets.v1")),
            imported.in_component(Component("cmk.server_side_calls.v1")),
            imported.in_component(Component("cmk.special_agents.v0_unstable")),
            imported.in_component(Component("cmk.plugins")),
            imported.in_component(Component("cmk.utils")),
            imported.in_component(Component("cmk.ccc")),
        )
    )


def _is_allowed_for_robotmk_agent_based_cee_plugins(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return imported.in_component(Component("cmk.cee.robotmk.checking.agent_based"))


def _is_allowed_for_robotmk_graphing_cee_plugins(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return imported.in_component(Component("cmk.cee.robotmk.checking.graphing"))


def _is_allowed_for_robotmk_rulesets_cee_plugins(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            imported.in_component(Component("cmk.cee.robotmk.checking.rulesets")),
            imported.in_component(Component("cmk.cee.robotmk.bakery.rulesets")),
        )
    )


def _allow_default_plus_component_under_test(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    if component.is_below("tests.unit.checks"):
        component_under_test = Component("cmk.plugins")
    elif (
        component.is_below("tests.unit")
        or component.is_below("tests.integration")
        or component.is_below("tests.integration_redfish")
    ):
        component_under_test = Component(".".join(component.parts[2:]))
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
            imported.in_component(Component("cmk.base.legacy_checks")),
            imported.in_component(Component("cmk.base.check_legacy_includes")),
            imported.in_component(Component("cmk.plugins")),
            imported.in_component(Component("cmk.base.config")),
            imported.in_component(Component("cmk.agent_based.legacy.v0_unstable")),
            imported.in_component(Component("cmk.agent_based")),
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
            imported.in_component(Component("cmk.base.legacy_checks")),
            imported.in_component(Component("cmk.base.check_legacy_includes")),
            imported.in_component(Component("cmk.server_side_calls_backend")),
            imported.in_component(Component("cmk.checkengine")),
            imported.in_component(Component("cmk.snmplib")),
            imported.in_component(Component("cmk.plugins")),
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
            imported.in_component(Component("cmk.checkengine")),
            imported.in_component(Component("cmk.cee.bakery")),
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
            _allow(
                "cmk.agent_based.v2",
                "cmk.graphing.v1",
                "cmk.rulesets.v1",
                "cmk.server_side_calls.v1",
                "cmk.special_agents.v0_unstable",
                "cmk.plugins",
                "cmk.checkengine",
                "cmk.cee.bakery",
            ),
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
            imported.in_component(Component("cmk.checkengine")),
            imported.in_component(Component("cmk.snmplib")),
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
            imported.in_component(Component("cmk.fetchers")),
            imported.in_component(Component("cmk.snmplib")),
            imported.in_component(Component("cmk.checkengine")),
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
            imported.in_component(Component("cmk.messaging")),
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
            imported.in_component(Component("cmk.gui.utils.htpasswd")),
        )
    )


def _is_allowed_for_rrd(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            imported.in_component(Component("cmk.rrd")),
            imported.in_component(Component("cmk.ccc")),
            imported.in_component(Component("cmk.utils")),
        )
    )


_COMPONENTS = (
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
    (Component("cmk.bakery"), _allow()),  # only allow itself, this is the future :-)
    (
        Component("cmk.base.api.bakery"),
        _allow(
            "cmk.bakery",
            "cmk.ccc",
            "cmk.utils",
        ),
    ),
    (
        Component("cmk.base.cee.bakery"),
        _allow(
            "cmk.bakery",
            "cmk.base.api.bakery",
            "cmk.base.plugins.bakery.bakery_api",
            "cmk.base.cee.cap",
            "cmk.base.cee.plugins.bakery.bakery_api",
            "cmk.crypto.certificate",
            "cmk.cee.robotmk.bakery",
            "cmk.ccc",
            "cmk.cee.bakery",
            "cmk.utils",
        ),
    ),
    (Component("cmk.base.check_legacy_includes"), _is_allowed_for_legacy_checks),
    (Component("cmk.base.legacy_checks"), _is_allowed_for_legacy_checks),
    # importing config in ip_lookup repeatedly lead to import cycles. It's cleanup now.
    (Component("cmk.base.ip_lookup"), _is_default_allowed_import),
    (
        Component("cmk.base.plugins.bakery.bakery_api"),
        _allow(
            "cmk.bakery",
            "cmk.base.api.bakery",
            "cmk.utils",
        ),
    ),
    (Component("cmk.base"), _allowed_for_base_cee),
    (Component("cmk.base.cee"), _allowed_for_base_cee),
    (Component("cmk.cmkpasswd"), _allow_for_cmkpasswd),
    (Component("cmk.checkengine.value_store"), _allow("cmk.utils", "cmk.ccc")),
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
    (
        Component("cmk.plugins.checkmk"),
        _allow(
            "cmk.agent_based.v2",
            "cmk.rulesets.v1",
            "cmk.graphing.v1",
            "cmk.server_side_calls.v1",
            "cmk.base",
            "cmk.fetchers",
            "cmk.checkengine",
            "cmk.utils",
            "cmk.ccc",
        ),
    ),
    (
        Component("cmk.plugins.otel"),
        _allow(
            "cmk.agent_based.v1",
            "cmk.agent_based.v2",
            "cmk.graphing.v1",
            "cmk.rulesets.v1",
            "cmk.gui.form_specs.private",
            "cmk.server_side_calls.v1",
            "cmk.special_agents.v0_unstable",
            "cmk.plugins",
        ),
    ),
    (
        Component("cmk.plugins"),
        _allow(
            "cmk.agent_based.v1",
            "cmk.agent_based.v2",
            "cmk.graphing.v1",
            "cmk.rulesets.v1",
            "cmk.server_side_calls.v1",
            "cmk.special_agents.v0_unstable",
            "cmk.plugins",
            "cmk.utils",  # FIXME (should only be password store)
            "cmk.ccc",  # FIXME
        ),
    ),
    (Component("cmk.server_side_calls_backend"), _is_default_allowed_import),
    (Component("cmk.special_agents"), _is_default_allowed_import),
    (Component("cmk.update_config"), _allow_for_cmk_update_config),
    (
        Component("cmk.validate_config"),
        _allow("cmk.base", "cmk.gui", "cmk.checkengine", "cmk.utils", "cmk.ccc"),
    ),
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
    (Component("cmk.rrd"), _is_allowed_for_rrd),
    (Component("cmk.inventory"), _is_default_allowed_import),
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
    ModulePath("bin/cmk-migrate-http"): Component("cmk.update_config"),
    ModulePath("bin/cmk-validate-config"): Component("cmk.validate_config"),
    ModulePath("bin/cmk-validate-plugins"): Component("cmk.validate_plugins"),
    ModulePath("bin/cmk-transform-inventory-trees"): Component("cmk.inventory"),
    ModulePath("bin/post-rename-site"): Component("cmk.post_rename_site"),
    ModulePath("bin/mkeventd"): Component("cmk.ec"),
    ModulePath("bin/cmk-convert-rrds"): Component("cmk.rrd"),
    ModulePath("bin/cmk-create-rrd"): Component("cmk.rrd"),
    ModulePath("omd/packages/enterprise/bin/liveproxyd"): Component("cmk.cee.liveproxy"),
    ModulePath("omd/packages/enterprise/bin/mknotifyd"): Component("cmk.cee.mknotifyd"),
    ModulePath("omd/packages/enterprise/bin/dcd"): Component("cmk.cee.dcd"),
    ModulePath("omd/packages/enterprise/bin/cmk-dcd"): Component("cmk.cee.dcd"),
    ModulePath("omd/packages/enterprise/bin/fetcher"): Component("cmk.cee.helpers"),
    ModulePath("omd/packages/appliance/webconf_snapin.py"): Component("cmk.gui"),
    ModulePath("cmk/active_checks/check_cmk_inv.py"): Component("cmk.base"),
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
        if not imported.in_component(Component("cmk")):
            return

        # We use paths relative to our project root, but not for our "pasting magic".
        importing_path = ModulePath(node.root().file).relative_to(self.cmk_path_cached)

        # Tests are allowed to import everything for now. Should be cleaned up soon
        if importing_path.is_below("tests/testlib"):
            return

        importing = self._get_module_name_of_files(importing_path)
        if not self._is_import_allowed(importing_path, importing, imported):
            self.add_message("cmk-module-layer-violation", node=node, args=(imported, importing))

    @staticmethod
    def _get_module_name_of_files(path: ModulePath) -> ModuleName:
        # Due to our symlinks and pasting magic, astroid gets confused, so we need to compute the
        # real module name from the file path of the module.
        # Emacs' flycheck stores files to be checked in a temporary file with a prefix.
        p = path.with_name(path.name.removeprefix("flycheck_").removesuffix(".py"))
        # For all modules which don't live below cmk after mangling, just assume a toplevel module.
        return ModuleName(
            ".".join(p.parts) if p.is_below("cmk") or p.is_below("tests") else p.parts[-1]
        )

    def _is_import_allowed(
        self, importing_path: ModulePath, importing: ModuleName, imported: ModuleName
    ) -> bool:
        for component, component_specific_checker in _COMPONENTS:
            if self._is_part_of_component(importing, importing_path, component):
                return component_specific_checker(imported=imported, component=component)

        # the rest (matched no component)
        return _is_allowed_import(imported)

    @staticmethod
    def _is_part_of_component(
        importing: ModuleName, importing_path: ModulePath, component: Component
    ) -> bool:
        if importing.in_component(component):
            return True

        explicit_component = _EXPLICIT_FILE_TO_COMPONENT.get(importing_path)
        if explicit_component is not None:
            return explicit_component == component

        return (
            component == Component("cmk.notification_plugins")
            and importing_path.is_below("notifications")
        ) or (
            component == Component("cmk.active_checks") and importing_path.is_below("active_checks")
        )
