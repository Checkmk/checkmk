#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import subprocess

from tests.testlib.site import Site


def test_net_snmp_mib_search_paths(site: Site) -> None:
    p = site.execute(
        ["snmptranslate", "-Dinit_mib", ".1.3"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output = p.communicate()[0]

    # Match and extract these lines:
    # init_mib: Seen MIBDIRS: Looking in '/omd/sites/heute/.snmp/mibs:<HOME>/.cache/bazel/_bazel_...build_tmpdir/net-snmp/share/snmp/mibs' for mib dirs ...
    matches = re.search(r"init_mib: Seen MIBDIRS: Looking in '(.+)' for mib dirs ...", output)
    assert matches is not None, output
    paths = matches.group(1).split(":")

    assert paths == [
        f"/omd/sites/{site.id}/local/share/snmp/mibs",
        f"/omd/sites/{site.id}/share/snmp/mibs",
        "/usr/share/snmp/mibs",
    ]
