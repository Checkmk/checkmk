#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.graphing.v1 import translations

translation_aws_v2_network = translations.Translation(
    name="aws_v2_network",
    check_commands=[
        translations.PassiveCheck("aws_v2_ec2_network_io"),
    ],
    translations={
        "in": translations.RenameToAndScaleBy(
            "if_in_bps",
            8,
        ),
        "inbcast": translations.RenameTo("if_in_bcast"),
        "indisc": translations.RenameTo("if_in_discards"),
        "inerr": translations.RenameTo("if_in_errors"),
        "inmcast": translations.RenameTo("if_in_mcast"),
        "innucast": translations.RenameTo("if_in_non_unicast"),
        "inucast": translations.RenameTo("if_in_unicast"),
        "out": translations.RenameToAndScaleBy(
            "if_out_bps",
            8,
        ),
        "outbcast": translations.RenameTo("if_out_bcast"),
        "outdisc": translations.RenameTo("if_out_discards"),
        "outerr": translations.RenameTo("if_out_errors"),
        "outmcast": translations.RenameTo("if_out_mcast"),
        "outnucast": translations.RenameTo("if_out_non_unicast"),
        "outucast": translations.RenameTo("if_out_unicast"),
        "total": translations.RenameToAndScaleBy(
            "if_total_bps",
            8,
        ),
    },
)
