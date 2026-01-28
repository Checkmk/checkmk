#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, overload
from urllib.parse import urlparse

from cmk.ccc.plugin_registry import Registry
from cmk.gui.config import Config
from cmk.gui.utils.urls import doc_reference_url, DocReference
from cmk.shared_typing.agent_slideout import AgentInstallCmds, AgentRegistrationCmds
from cmk.shared_typing.mode_host import ModeHostServerPerSite
from cmk.shared_typing.setup import AgentDownloadServerPerSite

WINDOWS_AGENT_INSTALL_CMD = """curl.exe -fOG {{SERVER}}/{{SITE}}/check_mk/agents/windows/check_mk_agent.msi && ^
msiexec /i check_mk_agent.msi"""

LINUX_DEBIAN_AGENT_INSTALL_CMD = """curl -fOG {{{{SERVER}}}}/{{{{SITE}}}}/check_mk/agents/check-mk-agent_{version}-1_all.deb && \\
sudo dpkg -i check-mk-agent_{version}-1_all.deb"""

LINUX_RPM_AGENT_INSTALL_CMD = """curl -fOG {{{{SERVER}}}}/{{{{SITE}}}}/check_mk/agents/check-mk-agent_{version}-1.noarch.rpm && \\
sudo rpm -Uvh check-mk-agent_{version}-1.noarch.rpm"""


def build_agent_install_cmds(
    version: str,
) -> AgentInstallCmds:
    return AgentInstallCmds(
        windows=WINDOWS_AGENT_INSTALL_CMD,
        linux_deb=LINUX_DEBIAN_AGENT_INSTALL_CMD.format(version=version),
        linux_rpm=LINUX_RPM_AGENT_INSTALL_CMD.format(version=version),
    )


WINDOWS_AGENT_REGISTRATION_CMD = """\"C:\\Program Files (x86)\\checkmk\\service\\cmk-agent-ctl.exe\" register ^
    --hostname {{HOSTNAME}} ^
    --server {{SERVER}} ^
    --site {{SITE}} ^
    --user agent_registration"""

LINUX_REGISTRATION_CMD = """sudo cmk-agent-ctl register \\
    --hostname {{HOSTNAME}} \\
    --server {{SERVER}} \\
    --site {{SITE}} \\
    --user agent_registration"""

AIX_REGISTRATION_CMD = """sudo cmk-agent-ctl register \\
    --hostname {{HOSTNAME}} \\
    --server {{SERVER}} \\
    --site {{SITE}} \\
    --user agent_registration"""

SOLARIS_REGISTRATION_CMD = """sudo cmk-agent-ctl register \\
    --hostname {{HOSTNAME}} \\
    --server {{SERVER}} \\
    --site {{SITE}} \\
    --user agent_registration"""


def build_agent_registration_cmds() -> AgentRegistrationCmds:
    return AgentRegistrationCmds(
        windows=WINDOWS_AGENT_REGISTRATION_CMD,
        linux=LINUX_REGISTRATION_CMD,
        aix=AIX_REGISTRATION_CMD,
        solaris=SOLARIS_REGISTRATION_CMD,
    )


@dataclass(kw_only=True)
class AgentCommands:
    install_cmds: Callable[[str], AgentInstallCmds]
    registration_cmds: Callable[[], AgentRegistrationCmds]
    legacy_agent_url: Callable[[], str | None] = lambda: None


class AgentCommandsRegistry(Registry[AgentCommands]):
    def plugin_name(self, instance: AgentCommands) -> str:
        return "agent_commands"


agent_commands_registry = AgentCommandsRegistry()


def register(registry: AgentCommandsRegistry) -> None:
    registry.register(
        AgentCommands(
            install_cmds=build_agent_install_cmds,
            registration_cmds=build_agent_registration_cmds,
            legacy_agent_url=lambda: doc_reference_url(DocReference.AGENT_LINUX_LEGACY),
        )
    )


@overload
def get_server_per_site(
    active_config: Config,
    cls: type[ModeHostServerPerSite],
) -> Sequence[ModeHostServerPerSite]: ...


@overload
def get_server_per_site(
    active_config: Config,
    cls: type[AgentDownloadServerPerSite],
) -> Sequence[AgentDownloadServerPerSite]: ...


def get_server_per_site(
    active_config: Config,
    cls: type[ModeHostServerPerSite] | type[AgentDownloadServerPerSite],
) -> Sequence[Any]:
    return [
        cls(
            site_id=site_id,
            server=(
                f"{parsed.scheme}://{parsed.netloc}"
                if config_key.get("multisiteurl")
                and (parsed := urlparse(config_key["multisiteurl"]))
                else ""
            ),
        )
        for site_id, config_key in active_config.sites.items()
    ]
