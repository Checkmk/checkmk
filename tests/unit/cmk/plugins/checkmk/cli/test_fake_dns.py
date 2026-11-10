#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.cli.engine.readers import RecordedOptions as CLIRecordedOptions
from cmk.cli.internal import Command as CLICommand
from cmk.plugins.checkmk.cli.check import cli_command_check
from cmk.plugins.checkmk.cli.core_config import (
    cli_command_nagios_config,
    cli_command_reload,
    cli_command_restart,
    cli_command_update,
)
from cmk.plugins.checkmk.cli.discovery import cli_command_check_discovery, cli_command_discover
from cmk.plugins.checkmk.cli.dump import cli_command_dump, cli_command_dump_agent
from cmk.plugins.checkmk.cli.inventory import (
    cli_command_inventorize_marked_hosts,
    cli_command_inventory,
)
from cmk.plugins.checkmk.cli.maintenance import cli_command_update_dns_cache
from cmk.plugins.checkmk.cli.options import FAKE_DNS_VALUE
from cmk.plugins.checkmk.cli.snmp import cli_command_snmpget, cli_command_snmpwalk


@pytest.mark.parametrize(
    "command",
    [
        cli_command_check,
        cli_command_nagios_config,
        cli_command_update,
        cli_command_restart,
        cli_command_reload,
        cli_command_check_discovery,
        cli_command_discover,
        cli_command_dump_agent,
        cli_command_dump,
        cli_command_inventory,
        cli_command_inventorize_marked_hosts,
        cli_command_update_dns_cache,
        cli_command_snmpwalk,
        cli_command_snmpget,
    ],
    ids=lambda command: command.long,
)
def test_a_command_looking_up_addresses_takes_fake_dns[R](command: CLICommand[R]) -> None:
    recorded = CLIRecordedOptions()
    command.request(recorded)

    assert FAKE_DNS_VALUE in recorded.options
