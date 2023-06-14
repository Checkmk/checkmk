#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.watolib.config_domain_name import filter_unknown_settings


def test_filter_unknown_settings() -> None:
    assert filter_unknown_settings(
        {
            "default_language": "en",
            "snmp_backend_default": "Inline",
            "unknown": "filtered_out",
            "wato_enabled": False,
        }
    ) == {
        "default_language": "en",
        "snmp_backend_default": "Inline",
        "wato_enabled": False,
    }
