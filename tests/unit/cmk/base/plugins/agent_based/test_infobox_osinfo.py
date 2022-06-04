#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.infoblox_osinfo as iboi
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes


@pytest.fixture(name="section", scope="module")
def _get_section() -> iboi._OSInfo:
    section = iboi.parse_infoblox_osinfo(
        [
            [
                "'--host=x86_64-unknown-linux-gnu' '--build=x86_64-unknown-linux-gnu' "
                "'--target=x86_64-redhat-linux' '--program-prefix=' '--prefix=/usr' "
                "'--exec-prefix=/usr' '--bindir=/usr/bin' '--sbindir=/usr/sbin' "
                "'--datadir=/usr/share' '--includedir=/usr/include' '--libdir=/usr/lib64' "
                "'--libexecdir=/usr/libexec' '--localstatedir=/var' '--sharedstatedir=/var/lib' "
                "'--mandir=/usr/share/man' '--infodir=/usr/share/info' '--disable-static' "
                "'--enable-shared' '--without-rpm' '--with-cflags=-O2 -g -D_FORTIFY_SOURCE=2' "
                "'--with-sys-location=Unknown' '--with-logfile=/var/log/snmpd.log' "
                "'--with-persistent-directory=/var/lib/net-snmp' '--with-default-snmp-version=3' "
                "'--with-mib-modules=agentx' '--with-libwrap=yes' '--sysconfdir=/etc' "
                "'--enable-ipv6' '--enable-ucd-snmp-compatibility' '--disable-embedded-perl' "
                "'--enable-as-needed' '--with-perl-modules=INSTALLDIRS=vendor' "
                "'--enable-local-smux' "
                "'--with-temp-file-pattern=/var/run/net-snmp/snmp-tmp-XXXXXX' "
                "'--with-transports=DTLSUDP TLSTCP' '--with-security-modules=tsm' "
                "'--with-sys-contact=c"
            ]
        ]
    )
    assert section
    return section


def test_inventroy_infoblox_osinfo(section: iboi._OSInfo) -> None:
    assert list(iboi.inventory_infoblox_osinfo(section)) == [
        Attributes(
            path=["software", "os"],
            inventory_attributes={
                "type": "Linux",
                "Vendor": "RedHat",
                "arch": "x86_64",
            },
        ),
    ]
