#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from urllib3.connectionpool import HTTPSConnectionPool

from cmk.server_side_programs.v1 import HostnameValidationAdapter


class TestHostnameValidationAdapter:
    def test_https_pool_checks_the_reference_hostname(self) -> None:
        """Pools for proxied requests get assert_hostname only from cert_verify."""
        pool = HTTPSConnectionPool("192.0.2.1")

        HostnameValidationAdapter("my_server_name").cert_verify(
            pool, "https://192.0.2.1/", verify=True, cert=None
        )

        assert pool.assert_hostname == "my_server_name"
