#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from omdlib.args_site_user import (
    args_to_command_line,
    Copy,
    Finalize,
    Move,
    parse_arguments,
    Restore,
)
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
        Move(
            site="a",
            old_site="b",
            verbose=False,
            skeleton=Skeleton.INSTALL,
        ),
        Move(
            site="a",
            old_site="b",
            verbose=True,
            skeleton=Skeleton.KEEPOLD,
        ),
        Move(
            site="a",
            old_site="b",
            verbose=True,
            skeleton=Skeleton.ABORT,
        ),
        Move(
            site="a",
            old_site="b",
            verbose=False,
            skeleton=Skeleton.ASK,
        ),
        Copy(
            site="a",
            old_site="b",
            verbose=False,
            skeleton=Skeleton.INSTALL,
        ),
        Copy(
            site="a",
            old_site="b",
            verbose=True,
            skeleton=Skeleton.KEEPOLD,
        ),
        Copy(
            site="a",
            old_site="b",
            verbose=True,
            skeleton=Skeleton.ABORT,
        ),
        Copy(
            site="a",
            old_site="b",
            verbose=False,
            skeleton=Skeleton.ASK,
        ),
    ],
)
def test_args_roundtrip(finalize: Finalize) -> None:
    sysv = args_to_command_line(finalize, version="any")[1:]
    parsed_model = parse_arguments(sysv)
    assert parsed_model == finalize
