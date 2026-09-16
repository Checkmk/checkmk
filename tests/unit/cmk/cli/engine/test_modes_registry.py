#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk import trace
from cmk.base.community_app import make_app
from cmk.cli.engine.call import call
from cmk.cli.engine.modes import make_mode, make_option, parse_sub_options
from cmk.cli.internal import Args, CLICommand, CLIOption, GlobalOptions, Options


def _handler(_app: object, _global_options: GlobalOptions, _options: Options, _args: Args) -> int:
    return 0


def test_make_option_keeps_deprecated_long_options() -> None:
    option = make_option(
        CLIOption(
            long_option="plugins",
            short_help="Restrict to the given plug-ins",
            argument=True,
            argument_descr="PLUGINS",
            deprecated_long_options=frozenset({"checks"}),
        )
    )
    assert option.long_getopt_specs() == ["plugins=", "checks="]
    assert option.is_deprecated_option("--checks")


def test_make_mode_parses_sub_options_with_conversion() -> None:
    mode = make_mode(
        CLICommand(
            long_option="snmpwalk",
            handler_function=_handler,
            short_help="Walk",
            sub_options=[
                CLIOption(
                    long_option="oid",
                    short_help="Walk the given OID",
                    argument=True,
                    argument_descr="OID",
                    argument_conv=str.upper,
                ),
                CLIOption(long_option="verbose", short_help="Be verbose", repeat=True),
            ],
        )
    )
    assert parse_sub_options(
        mode.sub_options, [("--oid", "iso"), ("--verbose", ""), ("--verbose", "")]
    ) == {
        "oid": "ISO",
        "verbose": 2,
    }


@pytest.mark.parametrize(
    ["argument", "argument_optional", "expected_args"],
    [
        pytest.param(False, False, [], id="no argument: nothing is passed"),
        pytest.param(True, False, ["ARG"], id="required argument: exactly the option's argument"),
        pytest.param(True, True, ["ARG", "more"], id="optional argument: all remaining arguments"),
    ],
)
def test_call_shapes_the_positional_arguments(
    argument: bool, argument_optional: bool, expected_args: list[str]
) -> None:
    seen: list[Args] = []

    def _record(_app: object, _global_options: GlobalOptions, _options: Options, args: Args) -> int:
        seen.append(args)
        return 42

    mode = make_mode(
        CLICommand(
            long_option="thing",
            handler_function=_record,
            short_help="Do the thing",
            argument=argument,
            argument_descr="ARG" if argument else None,
            argument_optional=argument_optional,
        )
    )
    exit_status = call(
        make_app(),
        mode,
        GlobalOptions(),
        "ARG" if argument else "",
        [("--thing", "ARG" if argument else "")],
        ["ARG", "more"],
        trace.extract_context_from_environment({}),
    )
    assert exit_status == 42
    assert [list(args) for args in seen] == [expected_args]
