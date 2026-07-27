#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

import os
from typing import Union

from _pytest.capture import CaptureFixture

from cmk.plugins.collection.agents import isc_dhcpd


def test_parse_config_emits_pool_ranges(tmpdir: Union[str, bytes], capsys: CaptureFixture) -> None:
    included_file = os.path.join(str(tmpdir), "included.conf")
    with open(included_file, "w") as f:
        f.write("range 10.0.0.100 10.0.0.200;\n")

    conf_file = os.path.join(str(tmpdir), "dhcpd.conf")
    with open(conf_file, "w") as f:
        f.write('include "%s";\n' % included_file)
        f.write("option domain-name-servers 10.0.0.1;\n")
        f.write("range\t192.168.0.10 192.168.0.50;\n")

    isc_dhcpd.parse_config(conf_file)

    out, _err = capsys.readouterr()
    assert out == "10.0.0.100 10.0.0.200\n192.168.0.10 192.168.0.50\n"
