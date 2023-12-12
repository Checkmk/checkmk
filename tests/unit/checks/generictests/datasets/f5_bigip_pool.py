#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "f5_bigip_pool"

info = [
    [
        ["/Common/ad_testch-pool", "2", "2"],
        ["/Common/ad_hubservice-pool", "2", "2"],
        ["/Common/ldap_testch-pool", "2", "2"],
        ["/Common/ldap_testhk-pool", "2", "2"],
    ],
    [
        ["/Common/ad_testch-pool", "0", "4", "4", "1", "/Common/11.11.128.61"],
        ["/Common/ad_testch-pool", "0", "4", "4", "1", "/Common/11.11.129.61"],
        ["/Common/ad_hubservice-pool", "0", "4", "4", "1", "/Common/11.11.81.201"],
        ["/Common/ad_hubservice-pool", "0", "4", "4", "1", "/Common/11.11.81.202"],
        ["/Common/ldap_testch-pool", "389", "4", "4", "1", "/Common/11.11.128.61"],
        ["/Common/ldap_testch-pool", "389", "4", "4", "1", "/Common/11.11.129.61"],
        ["/Common/ldap_testhk-pool", "389", "4", "4", "1", "/Common/rozrhvad22.testhk.testint.net"],
        ["/Common/ldap_testhk-pool", "389", "4", "4", "1", "/Common/rozrhvad23.testhk.testint.net"],
    ],
]

discovery = {
    "": [
        ("/Common/ad_hubservice-pool", {}),
        ("/Common/ad_testch-pool", {}),
        ("/Common/ldap_testch-pool", {}),
        ("/Common/ldap_testhk-pool", {}),
    ]
}

checks = {
    "": [
        ("/Common/ad_hubservice-pool", {"levels_lower": (2, 1)}, [(0, "2 of 2 members are up", [])]),
        ("/Common/ad_testch-pool", {"levels_lower": (2, 1)}, [(0, "2 of 2 members are up", [])]),
        ("/Common/ldap_testch-pool", {"levels_lower": (2, 1)}, [(0, "2 of 2 members are up", [])]),
        ("/Common/ldap_testhk-pool", {"levels_lower": (2, 1)}, [(0, "2 of 2 members are up", [])]),
    ]
}
