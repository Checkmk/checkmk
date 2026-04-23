#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any, overload
from urllib.parse import urlparse

from cmk.ccc.hostaddress import HostName
from cmk.ccc.plugin_registry import Registry
from cmk.gui.config import Config
from cmk.gui.utils.urls import doc_reference_url, DocReference
from cmk.shared_typing.agent_slideout import AgentInstallCmds, AgentRegistrationCmds
from cmk.shared_typing.mode_host import (
    AgentInstallCmds as ModeHostAgentInstallCmds,
)
from cmk.shared_typing.mode_host import (
    AgentRegistrationCmds as ModeHostAgentRegistrationCmds,
)
from cmk.shared_typing.mode_host import (
    AgentSlideout as ModeHostAgentSlideout,
)
from cmk.shared_typing.mode_host import (
    ModeHostServerPerSite,
)
from cmk.shared_typing.setup import AgentDownloadServerPerSite
from cmk.shared_typing.setup import AgentInstallCmds as SetupAgentInstallCmds
from cmk.shared_typing.setup import AgentRegistrationCmds as SetupAgentRegistrationCmds
from cmk.shared_typing.setup import AgentSlideout as SetupAgentSlideout

WINDOWS_AGENT_DOWNLOAD_CMD = (
    "curl.exe -o check-mk-agent_{version}.msi -fG"
    ' "{{{{SERVER}}}}/{{{{SITE}}}}/check_mk/api/internal/domain-types/agent/actions/download_by_token/invoke"'
    ' --header "Accept: application/octet-stream"'
    ' --header "Authorization: CMK-TOKEN 0:[AGENT_DOWNLOAD_OTT]"'
    ' --data-urlencode "os_type=windows_msi"'
)

WINDOWS_AGENT_DOWNLOAD_CMD_POWERSHELL = (
    "Invoke-WebRequest `\n"
    '    -Uri "{{{{SERVER}}}}/{{{{SITE}}}}/check_mk/api/internal/domain-types/agent/actions/download_by_token/invoke?os_type=windows_msi" `\n'
    '    -OutFile "check-mk-agent_{version}.msi" `\n'
    '    -Method "GET" `\n'
    "    -Headers @{{\n"
    '        "Accept" = "application/octet-stream";\n'
    '        "Authorization" = "CMK-TOKEN 0:[AGENT_DOWNLOAD_OTT]"\n'
    "    }}"
)

WINDOWS_AGENT_INSTALL_CMD = "msiexec /i check-mk-agent_{version}.msi /quiet /norestart"

WINDOWS_AGENT_INSTALL_CMD_POWERSHELL = 'Start-Process msiexec.exe -ArgumentList "/i `"$PWD\\check-mk-agent_{version}.msi`" /quiet /norestart" -Wait'

LINUX_DEBIAN_AGENT_INSTALL_CMD = """curl -o check-mk-agent_{version}-1_all.deb -fJG \\
    '{{{{SERVER}}}}/{{{{SITE}}}}/check_mk/api/internal/domain-types/agent/actions/download_by_token/invoke' \\
    --header 'Accept: application/octet-stream' \\
    --header 'Authorization: CMK-TOKEN 0:[AGENT_DOWNLOAD_OTT]' \\
    --data-urlencode 'os_type=linux_deb' && \\
sudo dpkg -i check-mk-agent_{version}-1_all.deb"""

LINUX_RPM_AGENT_INSTALL_CMD = """curl -o check-mk-agent_{version}-1.noarch.rpm -fJG  \\
    '{{{{SERVER}}}}/{{{{SITE}}}}/check_mk/api/internal/domain-types/agent/actions/download_by_token/invoke' \\
    --header 'Accept: application/octet-stream' \\
    --header 'Authorization: CMK-TOKEN 0:[AGENT_DOWNLOAD_OTT]' \\
    --data-urlencode 'os_type=linux_rpm' && \\
sudo rpm -Uvh check-mk-agent_{version}-1.noarch.rpm"""


def build_agent_install_cmds(
    version: str,
    hostname: HostName,
) -> AgentInstallCmds:
    return AgentInstallCmds(
        windows_download=WINDOWS_AGENT_DOWNLOAD_CMD.format(version=version),
        windows_download_powershell=WINDOWS_AGENT_DOWNLOAD_CMD_POWERSHELL.format(version=version),
        windows=WINDOWS_AGENT_INSTALL_CMD.format(version=version),
        windows_powershell=WINDOWS_AGENT_INSTALL_CMD_POWERSHELL.format(version=version),
        linux_deb=LINUX_DEBIAN_AGENT_INSTALL_CMD.format(version=version),
        linux_rpm=LINUX_RPM_AGENT_INSTALL_CMD.format(version=version),
    )


WINDOWS_AGENT_REGISTRATION_CMD = (
    '"C:\\Program Files (x86)\\checkmk\\service\\cmk-agent-ctl.exe" register'
    " --hostname {{HOSTNAME}}"
    " --server {{SERVER}}"
    " --site {{SITE}}"
    " --user agent_registration"
)

WINDOWS_AGENT_REGISTRATION_CMD_POWERSHELL = (
    '& "C:\\Program Files (x86)\\checkmk\\service\\cmk-agent-ctl.exe" register'
    " --hostname {{HOSTNAME}}"
    " --server {{SERVER}}"
    " --site {{SITE}}"
    " --user agent_registration"
)

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
        windows_powershell=WINDOWS_AGENT_REGISTRATION_CMD_POWERSHELL,
        linux=LINUX_REGISTRATION_CMD,
        aix=AIX_REGISTRATION_CMD,
        solaris=SOLARIS_REGISTRATION_CMD,
    )


@dataclass(kw_only=True)
class AgentCommands:
    install_cmds: Callable[[str, HostName], AgentInstallCmds]
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
) -> list[ModeHostServerPerSite]: ...


@overload
def get_server_per_site(
    active_config: Config,
    cls: type[AgentDownloadServerPerSite],
) -> list[AgentDownloadServerPerSite]: ...


def get_server_per_site(
    active_config: Config,
    cls: type[ModeHostServerPerSite] | type[AgentDownloadServerPerSite],
) -> list[Any]:
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


@overload
def get_agent_slideout(
    hostname: HostName,
    save_host: bool,
    host_exists: bool,
    all_agents_url: str,
    user_settings_url: str,
    agent_slideout_cls: type[SetupAgentSlideout],
    agent_install_cls: type[SetupAgentInstallCmds | ModeHostAgentInstallCmds],
    agent_registration_cls: type[SetupAgentRegistrationCmds | ModeHostAgentRegistrationCmds],
    version: str,
) -> SetupAgentSlideout: ...


@overload
def get_agent_slideout(
    hostname: HostName,
    save_host: bool,
    host_exists: bool,
    all_agents_url: str,
    user_settings_url: str,
    agent_slideout_cls: type[ModeHostAgentSlideout],
    agent_install_cls: type[SetupAgentInstallCmds | ModeHostAgentInstallCmds],
    agent_registration_cls: type[SetupAgentRegistrationCmds | ModeHostAgentRegistrationCmds],
    version: str,
) -> ModeHostAgentSlideout: ...


def get_agent_slideout(
    hostname: HostName,
    save_host: bool,
    host_exists: bool,
    all_agents_url: str,
    user_settings_url: str,
    agent_slideout_cls: type[SetupAgentSlideout | ModeHostAgentSlideout],
    agent_install_cls: type,
    agent_registration_cls: type,
    version: str,
) -> Any:
    return agent_slideout_cls(
        all_agents_url=all_agents_url,
        user_settings_url=user_settings_url,
        host_name=hostname,
        agent_install_cmds=agent_install_cls(
            **asdict(agent_commands_registry["agent_commands"].install_cmds(version, hostname))
        ),
        agent_registration_cmds=agent_registration_cls(
            **asdict(agent_commands_registry["agent_commands"].registration_cmds())
        ),
        legacy_agent_url=agent_commands_registry["agent_commands"].legacy_agent_url(),
        save_host=save_host,
        host_exists=host_exists,
    )
