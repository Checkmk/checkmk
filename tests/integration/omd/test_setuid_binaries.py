#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import stat
import subprocess
import pytest  # type: ignore[import]


@pytest.mark.parametrize("rel_path,expected_capability", [
    ("bin/mkeventd_open514", "cap_net_bind_service=ep"),
    ("lib/nagios/plugins/check_icmp", "cap_net_raw=ep"),
    ("lib/nagios/plugins/check_dhcp", "cap_net_bind_service,cap_net_raw=ep"),
    ("lib/cmc/icmpsender", "cap_net_raw=ep"),
    ("lib/cmc/icmpreceiver", "cap_net_raw=ep"),
])
def test_binary_capability(site, rel_path, expected_capability):
    path = site.path(rel_path)
    assert os.path.exists(path)

    # can not use "getcap" with PATH because some paths are not in sites PATH
    getcap_bin = None
    for candidate in ["/sbin/getcap", "/usr/sbin/getcap"]:
        if os.path.exists(candidate):
            getcap_bin = candidate
            break

    if getcap_bin is None:
        raise Exception("Unable to find getcap")

    p = subprocess.Popen([getcap_bin, path], stdout=subprocess.PIPE, encoding="utf-8")
    assert p.stdout
    stdout = p.stdout.read()

    assert oct(stat.S_IMODE(os.stat(path).st_mode)) == '0o750'

    # getcap 2.41 introduced a new output format. As long as we have distros with newer and older
    # versions, we need to support both formats.
    if "%s =" % path in stdout:
        # pre 2.41 format:
        # > getcap test
        # test = cap_net_raw+ep
        assert stdout == "%s = %s\n" % (path, expected_capability.replace("=", "+"))
    else:
        # 2.41 format:
        # > getcap test
        # test cap_net_raw=ep
        assert stdout == "%s %s\n" % (path, expected_capability)
