#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import entry_point_prefixes as cli_entry_point_prefixes
from cmk.cli.internal import no_options as cli_no_options


def test_entry_point_prefixes() -> None:
    assert cli_entry_point_prefixes() == {CLICommand: "cli_command_"}


def test_a_command_name_must_be_an_identifier() -> None:
    with pytest.raises(ValueError, match="identifier"):
        CLICommand(
            name="greet-loudly",
            handler="cmk.plugins.greetings.cli.handlers.greet:cli_handler_greet",
            long="greet-loudly",
            help="Greet loudly",
            request=cli_no_options,
        )
