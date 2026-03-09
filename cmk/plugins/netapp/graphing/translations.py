#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translations

translation_netapp_ontap_snapshots = translations.Translation(
    name="netapp_ontap_snapshots",
    check_commands=[translations.PassiveCheck("netapp_ontap_snapshots")],
    translations={"bytes": translations.RenameTo("snapshot_reserve_used")},
)
