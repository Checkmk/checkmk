#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.legacy_checks.dell_poweredge_status import parse_dell_poweredge_status


def test_parse_dell_poweredge_status_empty_string_table_returns_none() -> None:
    # When the SNMP walk under .1.3.6.1.4.1.674.10892.5.* yields no rows
    # (device quirk, ACL, MIB missing, ...), the parse function must return
    # None so the section resolver skips the check instead of calling it with
    # an empty list.
    assert parse_dell_poweredge_status([]) is None
