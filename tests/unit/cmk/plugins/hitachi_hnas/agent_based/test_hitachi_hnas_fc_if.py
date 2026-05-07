#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.hitachi_hnas.agent_based.hitachi_hnas_fc_if import parse_hitachi_hnas_fc_if

_CLASSIC_HNAS_ROW = ["1", "0", "1", "32", "25088", "51200", "1", "2", "3", "4", "5", "6", "7", "8"]


def test_parse_classic_hnas_all_columns_populated() -> None:
    section = parse_hitachi_hnas_fc_if([[_CLASSIC_HNAS_ROW]])
    assert len(section) == 1
    iface = section[0]
    assert iface.attributes.descr == "1.0"
    assert iface.attributes.speed == 32 * 10**9
    assert iface.attributes.oper_status == "1"
    assert iface.counters.in_octets == 25088
    assert iface.counters.out_octets == 51200
    assert iface.counters.in_err == 1 + 2 + 3 + 4 + 5 + 6 + 7
    assert iface.counters.in_disc == 8


def test_parse_vsp_one_missing_error_and_discard_columns() -> None:
    # Customer's reproducer: VSP One leaves columns 17/19/20 (RXEOF, BadCRC,
    # ProtocolErrors) and 18 (DiscardedFrameErrors) as empty strings. The
    # plugin used to crash on int(""); we now leave the affected counters
    # unset so the library omits the metrics rather than fabricating zeros.
    row = ["1", "0", "1", "32", "25088", "51200", "0", "0", "0", "0", "", "", "", ""]
    section = parse_hitachi_hnas_fc_if([[row]])
    assert len(section) == 1
    iface = section[0]
    assert iface.attributes.descr == "1.0"
    assert iface.attributes.speed == 32 * 10**9
    assert iface.attributes.oper_status == "1"
    assert iface.counters.in_octets == 25088
    assert iface.counters.out_octets == 51200
    assert iface.counters.in_err is None
    assert iface.counters.in_disc is None


def test_parse_partial_error_columns_yields_none() -> None:
    # Even a single empty cell in line[6:13] degrades in_err to None;
    # we never publish a partial sum that mixes real values with assumed zeros.
    row = ["1", "0", "1", "32", "25088", "51200", "1", "2", "3", "4", "5", "6", "", "9"]
    section = parse_hitachi_hnas_fc_if([[row]])
    assert section[0].counters.in_err is None
    assert section[0].counters.in_disc == 9
