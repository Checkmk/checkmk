#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from requests import Session

from cmk.server_side_programs.v1_unstable import HostnameValidationAdapter


class TestHostnameValidationAdapter:
    def test__init__(self) -> None:
        """Alibi test to at least make sure the dependencies are fulfilled"""
        Session().mount("https://example.com", HostnameValidationAdapter("my_server_name"))
