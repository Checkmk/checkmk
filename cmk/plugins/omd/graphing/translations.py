#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translations

translation_omd_diskusage = translations.Translation(
    name="omd_diskusage",
    check_commands=[translations.PassiveCheck("omd_diskusage")],
    translations={"omd_metric_backend_size": translations.RenameTo("omd_data_backend_size")},
)
