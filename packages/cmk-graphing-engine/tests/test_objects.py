#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing_engine import MetricName


def test_metric_name_pnp_cleans_path_hostile_characters() -> None:
    # A metric name is a PNP4Nagios / RRD path element: spaces, ":", "/" and "\" map to "_".
    assert MetricName("disk read:sda/1\\x") == "disk_read_sda_1_x"


def test_metric_name_removes_embedded_null_byte() -> None:
    # Some SNMP devices emit a metric name with a stray NUL byte. The cleaned name is used as a
    # filesystem path element, so it must not contain an embedded null byte or open() raises
    # "ValueError: embedded null byte" when the RRD is created.
    assert "\x00" not in MetricName("temp\x00")


def test_metric_name_leaves_a_clean_name_unchanged() -> None:
    assert MetricName("if_in_octets") == "if_in_octets"


def test_metric_name_construction_is_idempotent() -> None:
    assert MetricName(MetricName("disk read")) == MetricName("disk read")
