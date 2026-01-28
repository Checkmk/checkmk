#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from omdlib.args_site_user import args_to_command_line, Finalize, parse_arguments, Restore


@pytest.mark.parametrize(
    "finalize",
    [
        Restore(
            site="a",
            old_site="b",
            verbose=False,
            reuse=False,
        ),
        Restore(
            site="a",
            old_site="b",
            verbose=True,
            reuse=True,
        ),
        Restore(
            site="a",
            old_site="b",
            verbose=True,
            reuse=False,
        ),
        Restore(
            site="a",
            old_site="b",
            verbose=False,
            reuse=True,
        ),
    ],
)
def test_args_roundtrip(finalize: Finalize) -> None:
    sysv = args_to_command_line(finalize, version="any")[1:]
    parsed_model = parse_arguments(sysv)
    assert parsed_model == finalize
