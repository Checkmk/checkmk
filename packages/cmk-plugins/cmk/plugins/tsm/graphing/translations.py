#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translations

translation_tsm_stagingpools = translations.Translation(
    name="tsm_stagingpools",
    check_commands=[translations.PassiveCheck("tsm_stagingpools")],
    translations={
        "free": translations.RenameTo("tapes_free"),
        "tapes": translations.RenameTo("tapes_total"),
        "util": translations.RenameTo("tapes_util"),
    },
)

translation_tsm_storagepools = translations.Translation(
    name="tsm_storagepools",
    check_commands=[translations.PassiveCheck("tsm_storagepools")],
    translations={"used": translations.RenameTo("used_space")},
)
