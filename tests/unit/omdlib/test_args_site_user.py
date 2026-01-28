#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from omdlib.args_site_user import args_to_command_line, Finalize, parse_arguments, Restore
from omdlib.type_defs import Skeleton


@pytest.mark.parametrize(
    "finalize",
    [
        Restore(
            site="a",
            old_site="b",
            descriptor=1,
            verbose=False,
            reuse=False,
            skeleton=Skeleton.INSTALL,
            kill=False,
        ),
        Restore(
            site="a",
            old_site="b",
            descriptor=2,
            verbose=True,
            reuse=True,
            skeleton=Skeleton.KEEPOLD,
            kill=True,
        ),
        Restore(
            site="a",
            old_site="b",
            descriptor=6,
            verbose=True,
            reuse=False,
            skeleton=Skeleton.ABORT,
            kill=False,
        ),
        Restore(
            site="a",
            old_site="b",
            descriptor=9,
            verbose=False,
            reuse=True,
            kill=True,
            skeleton=Skeleton.ASK,
        ),
        Restore(
            site="a",
            old_site="b",
            descriptor=11,
            verbose=False,
            reuse=True,
            kill=True,
            skeleton=Skeleton.ASK,
        ),
    ],
)
def test_args_roundtrip(finalize: Finalize) -> None:
    sysv = args_to_command_line(finalize, version="any")[1:]
    parsed_model = parse_arguments(sysv)
    assert parsed_model == finalize
