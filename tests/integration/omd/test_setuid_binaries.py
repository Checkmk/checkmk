#!/usr/bin/env python
# encoding: utf-8

import os
import stat


def test_setuid_binaries(site):
    setuid_binaries = [
        "bin/mkeventd_open514",
        "lib/nagios/plugins/check_dhcp",
        "lib/nagios/plugins/check_icmp",
    ]

    if site.version.edition() == "enterprise":
        setuid_binaries += [
            "lib/cmc/icmpreceiver",
            "lib/cmc/icmpsender",
        ]

    for rel_path in setuid_binaries:
        path = os.path.join(site.root, rel_path)
        assert os.path.exists(path)
        assert os.stat(path).st_mode & stat.S_ISUID == stat.S_ISUID, \
            "Missing setuid bit on %s" % path
