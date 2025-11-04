#!/usr/bin/python
'''Translation for graphing values'''
# -*- encoding: utf-8; py-indent-offst: 4 -*-

# (c) Andreas Doehler <andreas.doehler@bechtle.com/andreas.doehler@gmail.com>
# License: GNU General Public License v2

from cmk.graphing.v1 import translations


translation_hyperv = translations.Translation(
    name="hyperv",
    check_commands=[
        translations.PassiveCheck("hyperv_cluster_csv"),
        translations.PassiveCheck("hyperv_vm_vhd"),
    ],
    translations={
        "fs_free": translations.ScaleBy(1048576),
        "fs_size": translations.ScaleBy(1048576),
        "fs_used": translations.ScaleBy(1048576),
        "growth": translations.RenameToAndScaleBy(
            "fs_growth",
            12.136296296296296,
        ),
        "overprovisioned": translations.ScaleBy(1048576),
        "reserved": translations.ScaleBy(1048576),
        "trend": translations.RenameToAndScaleBy(
            "fs_trend",
            12.136296296296296,
        ),
        "trend_hoursleft": translations.ScaleBy(3600),
        "uncommitted": translations.ScaleBy(1048576),
        "~(?!inodes_used|fs_size|growth|trend|reserved|fs_free|fs_provisioning|uncommitted|overprovisioned|dedup_rate|file_count|fs_used_percent).*$": translations.RenameToAndScaleBy(
            "fs_used",
            1048576,
        ),
    },
)
