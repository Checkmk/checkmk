#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import rrd_metric_name


def test_rrd_metric_name_pnp_cleans_path_hostile_characters() -> None:
    # An RRD metric name is a PNP4Nagios / RRD path element: spaces, ":", "/" and "\" map to "_".
    assert rrd_metric_name("disk read:sda/1\\x") == "disk_read_sda_1_x"


def test_rrd_metric_name_removes_embedded_null_byte() -> None:
    # Some SNMP devices emit a metric name with a stray NUL byte. The cleaned name is used as a
    # filesystem path element, so it must not contain an embedded null byte or open() raises
    # "ValueError: embedded null byte" when the RRD is created.
    assert "\x00" not in rrd_metric_name("temp\x00")


def test_rrd_metric_name_leaves_a_clean_name_unchanged() -> None:
    assert rrd_metric_name("if_in_octets") == "if_in_octets"


def test_rrd_metric_name_is_idempotent() -> None:
    assert rrd_metric_name(rrd_metric_name("disk read")) == rrd_metric_name("disk read")
