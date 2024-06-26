#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1.translations import PassiveCheck, RenameToAndScaleBy, ScaleBy, Translation
from cmk.plugins.ceph.constants import MIB

translation_ceph = Translation(
    name="ceph",
    check_commands=[
        PassiveCheck("cephstatus"),
        PassiveCheck("cephdf"),
        PassiveCheck("cephdfclass"),
        PassiveCheck("cephosd"),
        PassiveCheck("cephosdbluefs_db"),
        PassiveCheck("cephosdbluefs_wal"),
        PassiveCheck("cephosdbluefs_slow"),
    ],
    translations={
        "~(?!%s).*$": RenameToAndScaleBy("fs_used", MIB),
        "fs_used": ScaleBy(MIB),
        "fs_size": ScaleBy(MIB),
        "reserved": ScaleBy(MIB),
        "fs_free": ScaleBy(MIB),
        "growth": RenameToAndScaleBy("fs_growth", MIB / 86400.0),
        "trend": RenameToAndScaleBy("fs_trend", MIB / 86400.0),
        "trend_hoursleft": ScaleBy(3600),
        "uncommitted": ScaleBy(MIB),
        "overprovisioned": ScaleBy(MIB),
    },
)
