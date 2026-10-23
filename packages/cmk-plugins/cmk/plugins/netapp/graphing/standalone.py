#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import metrics, Title

UNIT_PER_SECOND = metrics.Unit(metrics.DecimalNotation("/s"))
UNIT_BYTES_PER_SECOND = metrics.Unit(metrics.IECNotation("B/s"))

metric_nfs_ios = metrics.Metric(
    name="nfs_ios",
    title=Title("NFS operations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfsv4_ios = metrics.Metric(
    name="nfsv4_ios",
    title=Title("NFSv4 operations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfsv4_1_ios = metrics.Metric(
    name="nfsv4_1_ios",
    title=Title("NFSv4.1 operations"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfs_read_ios = metrics.Metric(
    name="nfs_read_ios",
    title=Title("NFS read ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfs_write_ios = metrics.Metric(
    name="nfs_write_ios",
    title=Title("NFS write ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_nfs_read_throughput = metrics.Metric(
    name="nfs_read_throughput",
    title=Title("NFS read throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfs_write_throughput = metrics.Metric(
    name="nfs_write_throughput",
    title=Title("NFS write throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_nfsv4_read_throughput = metrics.Metric(
    name="nfsv4_read_throughput",
    title=Title("NFSv4 read throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfsv4_write_throughput = metrics.Metric(
    name="nfsv4_write_throughput",
    title=Title("NFSv4 write throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_nfsv4_1_read_throughput = metrics.Metric(
    name="nfsv4_1_read_throughput",
    title=Title("NFSv4.1 read throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_nfsv4_1_write_throughput = metrics.Metric(
    name="nfsv4_1_write_throughput",
    title=Title("NFSv4.1 write throughput"),
    unit=UNIT_BYTES_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
metric_cifs_read_ios = metrics.Metric(
    name="cifs_read_ios",
    title=Title("CIFS read ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.CYAN,
)
metric_cifs_write_ios = metrics.Metric(
    name="cifs_write_ios",
    title=Title("CIFS write ios"),
    unit=UNIT_PER_SECOND,
    color=metrics.Color.DARK_BLUE,
)
