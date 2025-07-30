#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from dataclasses import dataclass

from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import SiteId
from cmk.shared_typing.agent_slideout import AgentInstallCmds, AgentRegistrationCmds

WINDOWS_AGENT_INSTALL_CMD = """curl.exe -fOG {ip_address}/{site}/check_mk/agents/windows/check_mk_agent.msi && ^
msiexec /i check_mk_agent.msi"""

LINUX_DEBIAN_AGENT_INSTALL_CMD = """curl -fOG {ip_address}/{site}/check_mk/agents/linux/check-mk-agent_{version}-1_all.deb && \\
sudo dpkg -i check-mk-agent_{version}-1_all.deb"""

LINUX_RPM_AGENT_INSTALL_CMD = """curl -fOG {ip_address}/{site}/check_mk/agents/linux/check-mk-agent_{version}-1_noarch.rpm && \\
sudo rpm -Uvh check-mk-agent_{version}-1_noarch.rpm"""


def build_agent_install_cmds(
    site: SiteId,
    ip_address: str,
    version: str,
) -> AgentInstallCmds:
    return AgentInstallCmds(
        windows=WINDOWS_AGENT_INSTALL_CMD.format(ip_address=ip_address, site=site),
        linux_deb=LINUX_DEBIAN_AGENT_INSTALL_CMD.format(
            ip_address=ip_address, site=site, version=version
        ),
        linux_rpm=LINUX_RPM_AGENT_INSTALL_CMD.format(
            ip_address=ip_address, site=site, version=version
        ),
    )


WINDOWS_AGENT_REGISTRATION_CMD = """C:\\Program Files (x86)\\checkmk\\service\\cmk-agent-ctl.exe register ^
    --hostname [HOSTNAME] ^
    --server {ip_address} ^
    --site {site} ^
    --user agent_registration"""

LINUX_REGISTRATION_CMD = """sudo cmk-agent-ctl register \\
    --hostname [HOSTNAME] \\
    --server {ip_address} \\
    --site {site} \\
    --user agent_registration"""

AIX_REGISTRATION_CMD = """sudo cmk-agent-ctl register \\
    --hostname [HOSTNAME] \\
    --server {ip_address} \\
    --site {site} \\
    --user agent_registration"""

SOLARIS_REGISTRATION_CMD = """sudo cmk-agent-ctl register \\
    --hostname [HOSTNAME] \\
    --server {ip_address} \\
    --site {site} \\
    --user agent_registration"""


def build_agent_registration_cmds(site: SiteId, ip_address: str) -> AgentRegistrationCmds:
    return AgentRegistrationCmds(
        windows=WINDOWS_AGENT_REGISTRATION_CMD.format(ip_address=ip_address, site=site),
        linux=LINUX_REGISTRATION_CMD.format(ip_address=ip_address, site=site),
        aix=AIX_REGISTRATION_CMD.format(ip_address=ip_address, site=site),
        solaris=SOLARIS_REGISTRATION_CMD.format(ip_address=ip_address, site=site),
    )


@dataclass(kw_only=True)
class AgentCommands:
    install_cmds: Callable[[SiteId, str, str], AgentInstallCmds]
    registration_cmds: Callable[[SiteId, str], AgentRegistrationCmds]


class AgentCommandsRegistry(Registry[AgentCommands]):
    def plugin_name(self, instance: AgentCommands) -> str:
        return "agent_commands"


agent_commands_registry = AgentCommandsRegistry()


def register(registry: AgentCommandsRegistry) -> None:
    registry.register(
        AgentCommands(
            install_cmds=build_agent_install_cmds,
            registration_cmds=build_agent_registration_cmds,
        )
    )
