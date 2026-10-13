#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The agent slideout rewrites these command templates in the browser.

`packages/cmk-frontend-vue/src/mode-host/agent-connection-test/lib/commandTemplate.ts`
substitutes the macros and the token placeholders below. Nothing else ties the
two ends together, so renaming one here without the other would leave the
slideout handing out commands that cannot be run.

The commercial editions build their install commands in
`cmk/gui/nonfree/pro/agent_commands.py`; the same contract is checked for those
in `tests/unit/cmk/gui/nonfree/pro/test_agent_commands.py`.
"""

from dataclasses import asdict

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.gui.agent_commands import (
    build_agent_install_cmds,
    build_agent_registration_cmds,
    build_agent_status_cmds,
    build_kubernetes_helm_cmd,
    KUBERNETES_VALUES,
)
from cmk.shared_typing.agent_slideout import AgentInstallCmds

DOWNLOAD_TOKEN_PLACEHOLDER = "[AGENT_DOWNLOAD_OTT]"
REGISTRATION_USER_FLAG = "--user agent_registration"
REGISTRATION_TOKEN_PLACEHOLDER = "[AGENT_REGISTRATION_OTT]"
MACROS = ("{{HOSTNAME}}", "{{SITE}}", "{{SERVER}}")

#: Commands hitting one of these endpoints have to authorize with a token.
DOWNLOAD_ENDPOINT_MARKER = "download_by"


def download_commands(install_cmds: AgentInstallCmds) -> dict[str, str]:
    """Every command that fetches the agent, whatever the field is called."""
    return {
        name: cmd
        for name, cmd in asdict(install_cmds).items()
        if cmd and DOWNLOAD_ENDPOINT_MARKER in cmd
    }


def test_download_commands_carry_the_token_placeholder() -> None:
    commands = download_commands(build_agent_install_cmds("2.5.0", HostName("my-host")))
    assert commands, "no download command found - has the endpoint been renamed?"
    for name, cmd in commands.items():
        assert DOWNLOAD_TOKEN_PLACEHOLDER in cmd, f"{name} cannot be authorized"


def test_registration_commands_offer_the_registration_user() -> None:
    for name, cmd in asdict(build_agent_registration_cmds()).items():
        assert cmd is None or REGISTRATION_USER_FLAG in cmd, f"{name} has no token anchor"


def test_registration_commands_use_the_known_macros() -> None:
    for name, cmd in asdict(build_agent_registration_cmds()).items():
        if cmd is None:
            continue
        for macro in MACROS:
            assert macro in cmd, f"{name} does not resolve {macro}"


def test_kubernetes_helm_command_carries_the_token_placeholder() -> None:
    assert REGISTRATION_TOKEN_PLACEHOLDER in build_kubernetes_helm_cmd("2.5.0")


def test_kubernetes_values_use_the_known_macros() -> None:
    for macro in MACROS:
        assert macro in KUBERNETES_VALUES, f"values.yaml does not resolve {macro}"


@pytest.mark.parametrize(
    "version, chart_range",
    [
        pytest.param("2.5.0p12", "~2.5.0", id="patch release"),
        pytest.param("3.0.0b1", "~3.0.0", id="beta release"),
    ],
)
def test_kubernetes_chart_takes_the_newest_patch_of_the_checkmk_major_minor(
    version: str, chart_range: str
) -> None:
    assert f'--version "{chart_range}" ' in build_kubernetes_helm_cmd(version)


def test_kubernetes_chart_of_a_daily_build_uses_the_master_tag() -> None:
    assert '--version "0.0.0-master" ' in build_kubernetes_helm_cmd("2026.09.23")


def test_status_commands_need_no_substitution() -> None:
    for name, cmd in asdict(build_agent_status_cmds()).items():
        if cmd is None:
            continue
        assert not any(macro in cmd for macro in MACROS), f"{name} is rendered without macros"
        assert DOWNLOAD_TOKEN_PLACEHOLDER not in cmd, f"{name} is rendered without a token"
