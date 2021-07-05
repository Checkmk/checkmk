#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import CMKWebSession


def test_01_login_and_logout(site):
    web = CMKWebSession(site)
    web.login()

    url = f"/{web.site.id}/check_mk/api/v0/domain-types/host_config/collections/all"

    attributes = {
        "ipaddress": "127.0.0.1",
        "tag_criticality": "prod",
        "snmp_community": {
            "type": "v1_v2_community",
            "community": "blah",
        },
    }

    req = web.post(
        url,
        json={
            "host_name": "foobar",
            "folder": "/",
            "attributes": attributes,
        },
    )
    if not req.ok:
        raise Exception(f"Request to {url} failed with {req.status_code}. Payload: {req.text!r}")

    web.logout()
