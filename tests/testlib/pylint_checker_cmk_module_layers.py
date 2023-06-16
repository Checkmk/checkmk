#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checker to prevent disallowed imports of modules

See chapter "Module hierarchy" in coding_guidelines_python in wiki
for further information.
"""

from typing import NewType

from astroid.nodes import Import, ImportFrom, Statement  # type: ignore[import]
from pylint.checkers import BaseChecker, utils  # type: ignore[import]
from pylint.interfaces import IAstroidChecker  # type: ignore[import]

from tests.testlib import cmk_path

ModuleName = NewType("ModuleName", str)
ModulePath = NewType("ModulePath", str)  # TODO: use pathlib.Path
Component = NewType("Component", str)


def register(linter):
    linter.register_checker(CMKModuleLayerChecker(linter))


# https://www.python.org/dev/peps/pep-0616/
def removeprefix(text: str, prefix: str) -> str:
    return text[len(prefix) :] if text.startswith(prefix) else text


def removesuffix(text: str, suffix: str) -> str:
    return text[: -len(suffix)] if suffix and text.endswith(suffix) else text


def _get_absolute_importee(
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
        return parent.package
    except AttributeError:  # could be a try/except block, for instance.
        return _is_package(parent)


def _in_component(
    imported: ModuleName,
    component: Component,
) -> bool:
    return imported == ModuleName(component) or imported.startswith(component + ".")


def _is_allowed_import(imported: ModuleName) -> bool:
    """cmk, cmk.utils, cmk.fields, and cmk.automations are allowed to be imported from all over the place"""
    return any(
        (
            imported == "cmk",
            _in_component(imported, Component("cmk.utils")),
            _in_component(imported, Component("cmk.fields")),
            _in_component(imported, Component("cmk.automations")),
            _in_component(imported, Component("cmk.checkengine")),
            _in_component(imported, Component("cmk.bi")),
        )
    )


def _is_default_allowed_import(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return _is_allowed_import(imported) or _in_component(imported, component)


def _allow_default_plus_checkers(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    """`cmk.checkengine` is the generic (library) part to the check engine."""
    return any(
        (
            _is_default_allowed_import(imported=imported, component=component),
            _in_component(imported, Component("cmk.checkengine")),
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
            _in_component(imported, Component("cmk.fetchers")),
            _in_component(imported, Component("cmk.snmplib")),
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
            _in_component(imported, Component("cmk.checkengine")),
        )
    )


def _allow_default_plus_fetchers_checkers_snmplib_and_bakery(
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
            _in_component(imported, Component("cmk.cee.helpers")),
            _in_component(imported, Component("cmk.cee.bakery")),
        )
    )


def _allow_default_plus_fetchers_checkers_bakery(
    *,
    imported: ModuleName,
    component: Component,
) -> bool:
    return any(
        (
            _is_default_allowed_import(imported=imported, component=component),
            _in_component(imported, Component("cmk.checkengine")),
            _in_component(imported, Component("cmk.fetchers")),
            _in_component(imported, Component("cmk.cee.bakery")),
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
            _in_component(imported, Component("cmk.base")),
            _in_component(imported, Component("cmk.gui")),
        )
    )


def _allow_default_plus_gui_base_and_bakery(
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
            _in_component(imported, Component("cmk.checkengine")),
            _in_component(imported, Component("cmk.fetchers")),
            _in_component(imported, Component("cmk.cee.bakery")),
            _in_component(imported, Component("cmk.base")),
            _in_component(imported, Component("cmk.gui")),
        )
    )


def _is_allowed_for_agent_based_api(
    *,
    imported: ModuleName,
    component: Component,  # pylint: disable=unused-argument
) -> bool:
    return any(
        (
            _in_component(imported, Component("cmk.base.api.agent_based")),
            _in_component(imported, Component("cmk.base.plugins.agent_based.agent_based_api")),
        )
    )


def _is_allowed_for_agent_based_plugin(
    *,
    imported: ModuleName,
    component: Component,  # pylint: disable=unused-argument
) -> bool:
    return any(
        (
            _in_component(imported, Component("cmk.base.plugins.agent_based.agent_based_api")),
            _in_component(imported, Component("cmk.base.plugins.agent_based.utils")),
        )
    )


_COMPONENTS = (
    # Namespaces below cmk.base.api.agent_based are not really components,
    # but they (almost) adhere to the same import restrictions,
    # and we want to encourage that
    (Component("cmk.base.api.agent_based.value_store"), _allow_default_plus_checkers),
    (Component("cmk.base.api.agent_based"), _allow_default_plus_fetchers_checkers_and_snmplib),
    (Component("cmk.base.plugins.agent_based.agent_based_api"), _is_allowed_for_agent_based_api),
    (Component("cmk.base.plugins.agent_based"), _is_allowed_for_agent_based_plugin),
    # importing config in ip_lookup repeatedly lead to import cycles. It's cleanup now.
    (Component("cmk.base.ip_lookup"), _is_default_allowed_import),
    (Component("cmk.base"), _allow_default_plus_fetchers_checkers_snmplib_and_bakery),
    (Component("cmk.cmkpasswd"), _is_default_allowed_import),
    (Component("cmk.fetchers"), _allow_default_plus_fetchers_and_snmplib),
    (Component("cmk.cee.helpers"), _allow_default_plus_fetchers_checkers_and_snmplib),
    (Component("cmk.checkengine"), _allow_default_plus_fetchers_checkers_and_snmplib),
    (Component("cmk.automations"), _allow_default_plus_checkers),
    (Component("cmk.snmplib"), _is_default_allowed_import),
    (Component("cmk.gui"), _allow_default_plus_fetchers_checkers_bakery),
    (Component("cmk.ec"), _is_default_allowed_import),
    (Component("cmk.notification_plugins"), _is_default_allowed_import),
    (Component("cmk.special_agents"), _is_default_allowed_import),
    (Component("cmk.update_config"), _allow_default_plus_gui_base_and_bakery),
    (Component("cmk.utils"), _is_default_allowed_import),
    (Component("cmk.cee.bakery"), _is_default_allowed_import),
    (Component("cmk.cee.dcd"), _is_default_allowed_import),
    (Component("cmk.cee.mknotifyd"), _is_default_allowed_import),
    (Component("cmk.cee.snmp_backend"), _is_default_allowed_import),
    (Component("cmk.cee.liveproxy"), _is_default_allowed_import),
    (Component("cmk.cee.notification_plugins"), _is_default_allowed_import),
    (Component("cmk.post_rename_site"), _allow_default_plus_gui_and_base),
    (Component("cmk.active_checks"), _is_default_allowed_import),
)

_EXPLICIT_FILE_TO_COMPONENT = {
    ModulePath("web/app/index.wsgi"): Component("cmk.gui"),
    ModulePath("bin/check_mk"): Component("cmk.base"),
    ModulePath("bin/cmk-passwd"): Component("cmk.cmkpasswd"),
    ModulePath("bin/cmk-update-config"): Component("cmk.update_config"),
    ModulePath("bin/post-rename-site"): Component("cmk.post_rename_site"),
    ModulePath("bin/mkeventd"): Component("cmk.ec"),
    ModulePath("enterprise/bin/liveproxyd"): Component("cmk.cee.liveproxy"),
    ModulePath("enterprise/bin/mknotifyd"): Component("cmk.cee.mknotifyd"),
    ModulePath("enterprise/bin/dcd"): Component("cmk.cee.dcd"),
    ModulePath("enterprise/bin/fetcher"): Component("cmk.cee.helpers"),
    # CEE specific notification plugins
    ModulePath("notifications/servicenow"): Component("cmk.cee.notification_plugins"),
    ModulePath("notifications/jira_issues"): Component("cmk.cee.notification_plugins"),
}


class CMKModuleLayerChecker(BaseChecker):
    __implements__ = IAstroidChecker

    name = "cmk-module-layer-violation"
    msgs = {
        "C8410": ("Import of %r not allowed in module %r", "cmk-module-layer-violation", "whoop?"),
    }

    # This doesn't change during a pylint run, so let's save a realpath() call per import.
    cmk_path_cached = cmk_path() + "/"

    # NOTE: There are no type stubs for pylint itself, so the decorator effectively removes the types from the decorated function!
    @utils.check_messages("cmk-module-layer-violation")  # type: ignore[misc]
    def visit_import(self, node: Import) -> None:
        for name, _ in node.names:
            self._check_import(node, ModuleName(name))

    # NOTE: There are no type stubs for pylint itself, so the decorator effectively removes the types from the decorated function!
    @utils.check_messages("cmk-module-layer-violation")  # type: ignore[misc]
    def visit_importfrom(self, node: ImportFrom) -> None:
        # handle 'from . import foo, bar'
        imported = [node.modname] if node.modname else [n for n, _ in node.names]
        for modname in imported:
            self._check_import(
                node,
                ModuleName(modname)
                if node.level is None
                else _get_absolute_importee(
                    root_name=node.root().name,
                    modname=modname,
                    level=node.level,
                    is_package=_is_package(node),
                ),
            )

    def _check_import(self, node: Statement, imported: ModuleName) -> None:
        # We only care about imports of our own modules.
        if not imported.startswith("cmk"):
            return

        # We use paths relative to our project root, but not for our "pasting magic".
        absolute_path: str = node.root().file
        importing_path = ModulePath(removeprefix(absolute_path, self.cmk_path_cached))

        # Tests are allowed to import anyting.
        if str(importing_path).startswith("tests/"):
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
        parts[-1] = removeprefix(parts[-1], "flycheck_")
        # For all modules which don't live below cmk after mangling, just assume a toplevel module.
        if parts[0] != "cmk":
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
        if _in_component(importing, component):
            return True

        explicit_component = _EXPLICIT_FILE_TO_COMPONENT.get(importing_path)
        if explicit_component is not None:
            return explicit_component == component

        # The check and bakery plugins are all compiled together by tests/pylint/test_pylint.py.
        # They clearly belong to the cmk.base component.
        if component == Component("cmk.base") and importing.startswith("cmk_pylint"):
            return True

        if component == Component("cmk.notification_plugins") and importing_path.startswith(
            "notifications/"
        ):
            return True

        if component == Component("cmk.special_agents") and importing_path.startswith(
            "agents/special/"
        ):
            return True

        if component == Component("cmk.active_checks") and importing_path.startswith(
            "active_checks/"
        ):
            return True

        return False
