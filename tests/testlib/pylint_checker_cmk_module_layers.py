#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checker to prevent disallowed imports of modules

See chapter "Module hierarchy" in coding_guidelines_python in wiki
for further information.
"""

import os
from pylint.checkers import BaseChecker, utils  # type: ignore[import]
from pylint.interfaces import IAstroidChecker  # type: ignore[import]
from testlib import cmk_path


def register(linter):
    linter.register_checker(CMKModuleLayerChecker(linter))


_COMPONENTS = (
    "cmk.base",
    "cmk.gui",
    "cmk.ec",
    "cmk.notification_plugins",
    "cmk.special_agents",
    "cmk.update_config",
    "cmk.cee.dcd",
    "cmk.cee.mknotifyd",
    "cmk.cee.liveproxy",
    "cmk.cee.notification_plugins",
)

_EXPLICIT_FILE_TO_COMPONENT = {
    "web/app/index.wsgi": "cmk.gui",
    "bin/update_rrd_fs_names.py": "cmk.base",
    "bin/check_mk": "cmk.base",
    "bin/cmk-update-config": "cmk.update_config",
    "bin/mkeventd": "cmk.ec",
    "enterprise/bin/liveproxyd": "cmk.cee.liveproxy",
    "enterprise/bin/mknotifyd": "cmk.cee.mknotifyd",
    "enterprise/bin/dcd": "cmk.cee.dcd",
    # CEE specific notification plugins
    "notifications/servicenow": "cmk.cee.notification_plugins",
    "notifications/jira_issues": "cmk.cee.notification_plugins",
}


class CMKModuleLayerChecker(BaseChecker):
    __implements__ = IAstroidChecker

    name = 'cmk-module-layer-violation'
    msgs = {
        'C8410': ('Import of %r not allowed in module %r', 'cmk-module-layer-violation', 'whoop?'),
    }

    @utils.check_messages('cmk-module-layer-violation')
    def visit_import(self, node):
        names = [name for name, _ in node.names]
        for name in names:
            self._check_import(node, name)

    @utils.check_messages('cmk-module-layer-violation')
    def visit_importfrom(self, node):
        self._check_import(node, node.modname)

    def _check_import(self, node, import_modname):
        file_path = node.root().file

        if not import_modname.startswith("cmk"):
            return  # We only care about our own modules, ignore this

        file_path = file_path[len(cmk_path()) + 1:]  # Make relative

        if file_path.startswith("tests/") or file_path.startswith("tests-py3/"):
            return  # No validation in tests

        # Pylint fails to detect the correct module path here. Instead of realizing that the file
        # cmk/base/automations/cee.py is cmk.base.automations.cee it thinks the module is "cee".
        # We can silently ignore these files because the linked files at enterprise/... are checked.
        if os.path.islink(file_path):
            return  # Ignore symlinked files instead of checking them twice, ignore this

        mod_name = self._get_module_name_of_file(node, file_path)

        if not self._is_import_allowed(file_path, mod_name, import_modname):
            self.add_message("cmk-module-layer-violation",
                             node=node,
                             args=(import_modname, mod_name))

    def _get_module_name_of_file(self, node, file_path):
        """Fixup module names
        """
        module_name = node.root().name

        for segments in [
            ("cmk", "base", "plugins", "agent_based", "utils", ""),
            ("cmk", "base", "plugins", "agent_based", ""),
        ]:
            if file_path.startswith('/'.join(segments)):
                return '.'.join(segments) + module_name

        # Fixup managed and enterprise module names
        # astroid does not produce correct module names, because it does not know
        # that we link/copy our CEE/CME parts to the cmk.* module in the site.
        # Fake the final module name here.
        for component in ["base", "gui"]:
            for prefix in [
                    "cmk/%s/cee/" % component,
                    "cmk/%s/cme/" % component,
                    "enterprise/cmk/%s/cee/" % component,
                    "managed/cmk/%s/cme/" % component,
            ]:
                if file_path.startswith(prefix):
                    return "cmk.%s.%s" % (component, module_name)

        if module_name.startswith("cee.") or module_name.startswith("cme."):
            return "cmk.%s" % module_name
        return module_name

    def _is_import_allowed(self, file_path, mod_name, import_modname):
        for component in _COMPONENTS:
            if not self._is_part_of_component(mod_name, file_path, component):
                continue

            if self._is_import_in_component(import_modname, component):
                return True

            if self._is_import_in_cee_component_part(mod_name, import_modname, component):
                return True

        return self._is_utility_import(import_modname)

    def _is_part_of_component(self, mod_name, file_path, component):
        if self._is_import_in_component(mod_name, component):
            return True

        explicit_component = _EXPLICIT_FILE_TO_COMPONENT.get(file_path)
        if explicit_component is not None:
            return explicit_component == component

        # The check and bakery plugins are all compiled together by tests/pylint/test_pylint.py.
        # They clearly belong to the cmk.base component.
        if component == "cmk.base" and mod_name.startswith("cmk_pylint"):
            return True

        if component == "cmk.notification_plugins" and file_path.startswith("notifications/"):
            return True

        if component == "cmk.special_agents" and file_path.startswith("agents/special/"):
            return True

        return False

    def _is_import_in_component(self, import_modname, component):
        return import_modname == component or import_modname.startswith(component + ".")

    def _is_import_in_cee_component_part(self, mod_name, import_modname, component):
        """If a module is split into cmk.cee.[mod] and cmk.[mod] it's allowed
        to import non-cee parts in the cee part."""
        return mod_name.startswith("cmk.cee.") and self._is_import_in_component(
            import_modname, component)

    def _is_utility_import(self, import_modname):
        """cmk and cmk.utils are allowed to be imported from all over the place"""
        return import_modname in {"cmk", "cmk.utils"} or import_modname.startswith("cmk.utils.")
