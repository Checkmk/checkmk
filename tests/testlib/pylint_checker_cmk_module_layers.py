#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checker to prevent disallowed imports of modules

See chapter "Module hierarchy" in coding_guidelines_python in wiki
for further information.
"""

from typing import NewType

from astroid.node_classes import Statement, Import, ImportFrom  # type: ignore[import]
from pylint.checkers import BaseChecker, utils  # type: ignore[import]
from pylint.interfaces import IAstroidChecker  # type: ignore[import]
from testlib import cmk_path

ModuleName = NewType('ModuleName', str)
ModulePath = NewType('ModulePath', str)  # TODO: use pathlib.Path
Component = NewType('Component', str)


def register(linter):
    linter.register_checker(CMKModuleLayerChecker(linter))


# https://www.python.org/dev/peps/pep-0616/
def removeprefix(text: str, prefix: str) -> str:
    return text[len(prefix):] if text.startswith(prefix) else text


def removesuffix(text: str, suffix: str, /) -> str:
    return text[:-len(suffix)] if suffix and text.endswith(suffix) else text

_COMPONENTS = (
    Component("cmk.base"),
    Component("cmk.fetchers"),
    Component("cmk.snmplib"),
    Component("cmk.gui"),
    Component("cmk.ec"),
    Component("cmk.notification_plugins"),
    Component("cmk.special_agents"),
    Component("cmk.update_config"),
    Component("cmk.cee.dcd"),
    Component("cmk.cee.mknotifyd"),
    Component("cmk.cee.snmp_backend"),
    Component("cmk.cee.liveproxy"),
    Component("cmk.cee.notification_plugins"),
)

_EXPLICIT_FILE_TO_COMPONENT = {
    ModulePath("web/app/index.wsgi"): Component("cmk.gui"),
    ModulePath("bin/update_rrd_fs_names.py"): Component("cmk.base"),
    ModulePath("bin/check_mk"): Component("cmk.base"),
    ModulePath("bin/cmk-update-config"): Component("cmk.update_config"),
    ModulePath("bin/mkeventd"): Component("cmk.ec"),
    ModulePath("enterprise/bin/liveproxyd"): Component("cmk.cee.liveproxy"),
    ModulePath("enterprise/bin/mknotifyd"): Component("cmk.cee.mknotifyd"),
    ModulePath("enterprise/bin/dcd"): Component("cmk.cee.dcd"),
    ModulePath("enterprise/bin/fetcher"): Component("cmk.fetchers"),
    # CEE specific notification plugins
    ModulePath("notifications/servicenow"): Component("cmk.cee.notification_plugins"),
    ModulePath("notifications/jira_issues"): Component("cmk.cee.notification_plugins"),
}


class CMKModuleLayerChecker(BaseChecker):
    __implements__ = IAstroidChecker

    name = 'cmk-module-layer-violation'
    msgs = {
        'C8410': ('Import of %r not allowed in module %r', 'cmk-module-layer-violation', 'whoop?'),
    }

    # This doesn't change during a pylint run, so let's save a realpath() call per import.
    cmk_path_cached = cmk_path() + "/"

    @utils.check_messages('cmk-module-layer-violation')
    def visit_import(self, node: Import) -> None:
        for name, _ in node.names:
            self._check_import(node, ModuleName(name))

    @utils.check_messages('cmk-module-layer-violation')
    def visit_importfrom(self, node: ImportFrom) -> None:
        self._check_import(node, ModuleName(node.modname))

    def _check_import(self, node: Statement, imported: ModuleName) -> None:
        # We only care about imports of our own modules.
        if not imported.startswith("cmk"):
            return

        # We use paths relative to our project root, but not for our "pasting magic".
        absolute_path: str = node.root().file
        importing_path = ModulePath(removeprefix(absolute_path, self.cmk_path_cached))

        # Tests are allowed to import anyting.
        if importing_path.startswith("tests/"):
            return

        importing = self._get_module_name_of_files(importing_path)
        if not self._is_import_allowed(importing_path, importing, imported):
            self.add_message("cmk-module-layer-violation", node=node, args=(imported, importing))

    def _get_module_name_of_files(self, importing_path: ModulePath) -> ModuleName:
        # Due to our symlinks and pasting magic, astroid gets confused, so we need to compute the
        # real module name from the file path of the module.
        parts = importing_path.split("/")
        parts[-1] = removesuffix(parts[-1], ".py")
        # Emacs' flycheck stores files to be checked in a temporary file with a prefix.
        parts[-1] = removeprefix(parts[-1], "flycheck_")
        # Strip CEE/CME prefix, we use symlink magic to combine editions. :-P
        if parts[:2] in (["enterprise", "cmk"], ["managed", "cmk"]):
            parts = parts[1:]
        # Pretend that the combined checks and inventory/bakery plugins live below cmk.base.
        if len(parts) >= 2 and parts[-2].startswith("cmk_pylint_"):
            parts = ["cmk", "base", parts[-1]]
        # For all modules which don't live below cmk after mangling, just assume a toplevel module.
        if parts[0] != "cmk":
            parts = [parts[-1]]
        return ModuleName(".".join(parts))

    def _is_import_allowed(self, importing_path: ModulePath, importing: ModuleName,
                           imported: ModuleName) -> bool:
        for component in _COMPONENTS:
            if not self._is_part_of_component(importing, importing_path, component):
                continue

            if self._is_disallowed_snmplib_import(importing, component):
                return True

            if self._is_disallowed_fetchers_import(importing, component):
                return True

            if self._is_import_in_component(imported, component):
                return True

            if self._is_import_in_cee_component_part(importing, imported, component):
                return True

        return self._is_utility_import(imported)

    def _is_part_of_component(self, importing: ModuleName, importing_path: ModulePath,
                              component: Component) -> bool:
        if self._is_import_in_component(importing, component):
            return True

        explicit_component = _EXPLICIT_FILE_TO_COMPONENT.get(importing_path)
        if explicit_component is not None:
            return explicit_component == component

        # The check and bakery plugins are all compiled together by tests/pylint/test_pylint.py.
        # They clearly belong to the cmk.base component.
        if component == Component("cmk.base") and importing.startswith("cmk_pylint"):
            return True

        if component == Component("cmk.notification_plugins") and importing_path.startswith(
                "notifications/"):
            return True

        if component == Component("cmk.special_agents") and importing_path.startswith(
                "agents/special/"):
            return True

        return False

    def _is_disallowed_fetchers_import(self, importing: ModuleName, component: Component) -> bool:
        """Disallow import of `fetchers` in `cmk.utils`.

        The layering is such that `fetchers` is between `utils` and
        `base` so that importing `fetchers` in `utils` is wrong but
        anywhere else is OK.

        """
        return not (component.startswith("cmk.fetchers") and importing.startswith("cmk.utils"))

    def _is_disallowed_snmplib_import(self, importing: ModuleName, component: Component) -> bool:
        """Disallow import of `snmplib` in `cmk.utils`."""
        return not component.startswith("cmk.snmplib") and importing.startswith("cmk.utils")

    def _is_import_in_component(self, imported: ModuleName, component: Component) -> bool:
        return imported == ModuleName(component) or imported.startswith(component + ".")

    def _is_import_in_cee_component_part(self, importing: ModuleName, imported: ModuleName,
                                         component: Component) -> bool:
        """If a module is split into cmk.cee.[mod] and cmk.[mod] it's allowed
        to import non-cee parts in the cee part."""
        return importing.startswith("cmk.cee.") and self._is_import_in_component(
            imported, component)

    def _is_utility_import(self, imported: ModuleName) -> bool:
        """cmk and cmk.utils are allowed to be imported from all over the place"""
        return imported in {"cmk", "cmk.utils"} or imported.startswith("cmk.utils.")
