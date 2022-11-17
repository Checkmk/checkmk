#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib.site import Site

from cmk.utils.type_defs import HostName


def query_hosts_service_count(site: Site, hostname: HostName) -> int:
    services_response = site.openapi.get(f"objects/host/{hostname}/collections/services")
    assert services_response.ok
    return len(services_response.json()["value"])
