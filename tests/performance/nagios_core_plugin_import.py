#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import importlib
import importlib.resources
import re
import sys
from collections.abc import Generator
from os import getenv
from pathlib import Path
from pprint import pformat
from types import ModuleType
from typing import Final, get_args

import cmk.base.core.nagios  # astrein: disable=cmk-module-layer-violation
from cmk.base.core.nagios import HostCheckConfig  # astrein: disable=cmk-module-layer-violation
from cmk.ccc.hostaddress import HostAddress, HostName  # astrein: disable=cmk-module-layer-violation
from cmk.discover_plugins import PluginLocation  # astrein: disable=cmk-module-layer-violation
from cmk.utils.plugin_loader import _find_modules  # astrein: disable=cmk-module-layer-violation
from cmk.validate_plugins import _AgentBasedPlugins  # astrein: disable=cmk-module-layer-violation


class NagiosCorePluginImport:
    """Utility class for creating a host check which imports all available agent-based plugins in a
    Checkmk monitoring environment.
    """

    def __init__(self) -> None:
        self.omd_site: Final[str] = getenv("OMD_SITE", "foobar")
        self.omd_root: Final[Path] = Path(getenv("OMD_ROOT", "/omd/sites/foobar"))
        self.host_name: Final[HostName] = HostName("localhost")
        self.host_ip: Final[HostAddress] = HostAddress("127.0.0.1")
        self.agent_based_plugins: dict[str, list[str]] = {}
        self.host_check_folder = (
            self.omd_root / "var/check_mk/core/helper_config/latest/host_checks"
        )
        self.host_check_file = self.host_check_folder / f"check_{self.host_name}.py"

    @staticmethod
    def load_agent_based_plugin_modules() -> Generator[tuple[str, ModuleType]]:
        """Load all agent based plugin modules

        This method imports all agent based plugin modules and yields the module name
        and the imported module.

        Returns:
            A generator of 2-tuples of module-name and module.

        Raises:
            ImportError
        """
        package_name = "cmk.plugins"
        module_pattern = r".*\.agent_based\..*"

        def onerror_func(name: str) -> None:
            if exc := sys.exc_info()[1]:
                raise ImportError(name=name) from exc

        try:
            __import__(package_name)
        except BaseException as exc:
            raise ImportError from exc
        for module_name in _find_modules(sys.modules[package_name], onerror=onerror_func):
            if not re.match(module_pattern, module_name):
                continue
            try:
                yield module_name, importlib.import_module(module_name)
            except BaseException as exc:
                raise ImportError from exc

    def list_agent_based_plugins(self) -> dict[str, list[str]]:
        """List all agent based plugins

        This method walks through all agent based plugin modules and returns
        a dictionary mapping module names to lists of plugin names.

        Returns:
            dict[str, list[str]]: A dictionary where keys are module names and values are lists of
                plugin names found in each module.
        """
        # Collecting plugin list by walking through all plugin modules recursively
        modules_and_plugins: dict[str, list[str]] = {}
        for module_name, module in self.load_agent_based_plugin_modules():
            for plugin_name in dir(module):
                try:
                    plugin_type = getattr(module, plugin_name).__class__.__name__
                    AgentBasedPluginTypes = [_.__name__ for _ in get_args(_AgentBasedPlugins)]
                    if plugin_type not in AgentBasedPluginTypes:
                        continue
                except AttributeError:
                    continue
                if module_name not in modules_and_plugins:
                    modules_and_plugins[module_name] = [plugin_name]
                if plugin_name not in modules_and_plugins[module_name]:
                    modules_and_plugins[module_name].append(plugin_name)
        return modules_and_plugins

    def dump_host_check_file(self) -> None:
        """Creates a host check file which loads all agent based plugins"""
        plugin_locations = [
            PluginLocation(module=module_name, name=plugin_name)
            for module_name, plugin_names in self.agent_based_plugins.items()
            for plugin_name in plugin_names
        ]
        host_check_config = HostCheckConfig(
            delay_precompile=False,
            src=self.host_check_file.as_posix(),
            dst=self.host_check_file.as_posix().removesuffix(".py"),
            verify_site_python=True,
            locations=plugin_locations,
            checks_to_load=[
                f"{self.omd_root}/share/check_mk/checks/kernel",
                f"{self.omd_root}/share/check_mk/checks/mem_linux",
            ],
            ipaddresses={self.host_name: self.host_ip},
            ipv6addresses={},
            hostname=self.host_name,
        )
        template_text = importlib.resources.read_text(
            cmk.base.core.nagios, "_host_check_template.py", encoding="utf-8"
        )
        startpos = template_text.find("CONFIG = HostCheckConfig(")
        endpos = template_text.find(")\n", startpos) + 1
        replacement = f"CONFIG = {pformat(host_check_config)}"
        host_check_text = template_text[0:startpos] + replacement + template_text[endpos:]
        self.host_check_file.write_text(host_check_text, encoding="utf-8")

    def main(self) -> None:
        self.agent_based_plugins = self.list_agent_based_plugins()
        self.dump_host_check_file()


if __name__ == "__main__":
    app = NagiosCorePluginImport()
    app.main()
