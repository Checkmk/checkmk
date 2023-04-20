#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def hitachin_hnas_scan_function(oid):
    return (
        oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.11096.6")
        or
        # e.g. HM800 report "linux" as type. Check the vendor tree too
        (
            oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.8072.3.2.10")
            and oid(".1.3.6.1.4.1.11096.6.1.*")
        )
    )
