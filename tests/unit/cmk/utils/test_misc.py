#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.misc import pnp_cleanup


def test_pnp_cleanup_replaces_known_separators() -> None:
    assert pnp_cleanup("foo bar:baz/qux\\quux") == "foo_bar_baz_qux_quux"


def test_pnp_cleanup_removes_embedded_null_byte() -> None:
    # Some SNMP devices emit a service description with a stray NUL byte
    # (crash group 4763: service "PDU Bank B6\x00"). The cleaned string is used
    # as a filesystem path element, so it must not contain an embedded null byte
    # or open() raises "ValueError: embedded null byte" when the RRD is created.
    cleaned = pnp_cleanup("PDU Bank B6\x00")
    assert "\x00" not in cleaned
