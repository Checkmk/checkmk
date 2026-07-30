#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import importlib
import importlib.resources
from collections.abc import Sequence
from os import getenv
from pathlib import Path
from pprint import pformat
from typing import Final

import cmk.base.core.nagios
from cmk.agent_based import v2, v3_unstable
from cmk.base.core.nagios import HostCheckConfig
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.discover_plugins import (
    discover_all_plugins,
    PluginGroup,
    PluginLocation,
)


class NagiosCorePluginImport:
    """Utility class for creating a host check which imports all available agent-based plugins in a
    Checkmk monitoring environment.
    """

    def __init__(self) -> None:
        self.omd_site: Final[str] = getenv("OMD_SITE", "foobar")
        self.omd_root: Final[Path] = Path(getenv("OMD_ROOT", "/omd/sites/foobar"))
        self.host_name: Final[HostName] = HostName("localhost")
        self.host_ip: Final[HostAddress] = HostAddress("127.0.0.1")
        self.host_check_folder = (
            self.omd_root / "var/check_mk/core/helper_config/latest/host_checks"
        )
        self.host_check_file = self.host_check_folder / f"check_{self.host_name}.py"

    def discover_agent_based_plugins(self) -> Sequence[PluginLocation]:
        return list(
            discover_all_plugins(
                PluginGroup.AGENT_BASED,
                {**v2.entry_point_prefixes(), **v3_unstable.entry_point_prefixes()},
                skip_wrong_types=False,
                raise_errors=True,
            ).plugins
        )

    def dump_host_check_file(self, plugin_locations: Sequence[PluginLocation]) -> None:
        """Creates a host check file which loads all agent based plugins"""
        host_check_config = HostCheckConfig(
            delay_precompile=False,
            src=self.host_check_file.as_posix(),
            dst=self.host_check_file.as_posix().removesuffix(".py"),
            verify_site_python=True,
            locations=list(plugin_locations),
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
        self.dump_host_check_file(self.discover_agent_based_plugins())


if __name__ == "__main__":
    app = NagiosCorePluginImport()
    app.main()
