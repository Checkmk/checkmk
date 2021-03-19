#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import ActiveCheck  # type: ignore[import]

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [({
    "fetch": ("IMAP", ({
        "ssl": (True, 143),
        "auth": ("foo", "bar"),
    }))
}, [
    "--fetch-protocol=IMAP",
    "--fetch-server=$HOSTADDRESS$",
    "--fetch-tls",
    "--fetch-port=143",
    "--fetch-username=foo",
    "--fetch-password=bar",
])])
def test_check_mail_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_mail")
    assert active_check.run_argument_function(params) == expected_args
