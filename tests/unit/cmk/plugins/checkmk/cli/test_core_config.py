#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.cli.engine.readers import RecordedOptions as CLIRecordedOptions
from cmk.cli.internal import Command as CLICommand
from cmk.plugins.checkmk.cli.core_config import (
    cli_command_nagios_config,
    cli_command_reload,
    cli_command_restart,
    cli_command_update,
)


@pytest.mark.parametrize(
    "command",
    [cli_command_nagios_config, cli_command_update, cli_command_restart, cli_command_reload],
    ids=lambda command: command.long,
)
def test_a_core_config_command_declares_the_fake_dns_option_alone[R](
    command: CLICommand[R],
) -> None:
    recorded = CLIRecordedOptions()
    command.request(recorded)

    assert [option.name for option in recorded.options] == ["fake-dns"]
