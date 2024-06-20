#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.graphing.v1 import translations

# Added in 2.3 patch set => can be safely removed in 2.5.0
translation_msexch_database = translations.Translation(
    name="msexch_database",
    check_commands=[
        translations.PassiveCheck("msexch_database"),
    ],
    translations={
        "db_read_latency": translations.RenameToAndScaleBy(
            "db_read_latency_s",
            0.001,
        ),
        "db_read_recovery_latency": translations.RenameToAndScaleBy(
            "db_read_recovery_latency_s",
            0.001,
        ),
        "db_write_latency": translations.RenameToAndScaleBy(
            "db_write_latency_s",
            0.001,
        ),
        "db_log_latency": translations.RenameToAndScaleBy(
            "db_log_latency_s",
            0.001,
        ),
    },
)

# Added in 2.3 patch set => can be safely removed in 2.5.0
translation_msexch_isclienttype = translations.Translation(
    name="msexch_isclienttype",
    check_commands=[
        translations.PassiveCheck("msexch_isclienttype"),
    ],
    translations={
        "average_latency": translations.RenameToAndScaleBy(
            "average_latency_s",
            0.001,
        ),
    },
)

# Added in 2.3 patch set => can be safely removed in 2.5.0
translation_msexch_isstore = translations.Translation(
    name="msexch_isstore",
    check_commands=[
        translations.PassiveCheck("msexch_isstore"),
    ],
    translations={
        "average_latency": translations.RenameToAndScaleBy(
            "average_latency_s",
            0.001,
        ),
    },
)

# Added in 2.3 patch set => can be safely removed in 2.5.0
translation_msexch_rpcclientaccess = translations.Translation(
    name="msexch_rpcclientaccess",
    check_commands=[
        translations.PassiveCheck("msexch_rpcclientaccess"),
    ],
    translations={
        "average_latency": translations.RenameToAndScaleBy(
            "average_latency_s",
            0.001,
        ),
    },
)
