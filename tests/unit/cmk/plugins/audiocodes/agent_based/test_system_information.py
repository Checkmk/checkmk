#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Attributes, StringTable
from cmk.plugins.audiocodes.agent_based.system_information import (
    inventory_audiocodes_system_information,
    parse_audiocodes_system_information,
)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        pytest.param(
            [
                [["Product: MG 4K ESBC ;SW Version: 7.20A.258.459"]],
                [
                    [
                        "Mediant 4000B",
                        "13045783",
                        "70",
                        "7.20A.258.459",
                        "\n\nKey features:\nBoard Type: Mediant 4000B \nIP Media: VXML \nDSP Voice features: IpmDetector \nCoders: G723 G729 G727 ILBC G722 SILK_NB SILK_WB OPUS_NB OPUS_WB \nChannel Type: RTP DspCh=12600 \nHA \nSecurity: IPSEC MediaEncryption StrongEncryption EncryptControlProtocol \nControl Protocols: SIP SBC=1302 TEAMS MSFT CLI FEU=120 CODER-TRANSCODING=1300 \nDefault features:\nCoders: G711 G726\n",
                        "germany_12v1.0.dat",
                    ]
                ],
            ],
            [
                Attributes(
                    path=["hardware", "system"],
                    inventory_attributes={
                        "product": "MG 4K ESBC ;SW Version: 7.20A.258.459",
                        "model": "Mediant 4000B",
                        "type": "70",
                        "serial": "13045783",
                        "software_version": "7.20A.258.459",
                        "license_key_list": "\n\nKey features:\nBoard Type: Mediant 4000B \nIP Media: VXML \nDSP Voice features: IpmDetector \nCoders: G723 G729 G727 ILBC G722 SILK_NB SILK_WB OPUS_NB OPUS_WB \nChannel Type: RTP DspCh=12600 \nHA \nSecurity: IPSEC MediaEncryption StrongEncryption EncryptControlProtocol \nControl Protocols: SIP SBC=1302 TEAMS MSFT CLI FEU=120 CODER-TRANSCODING=1300 \nDefault features:\nCoders: G711 G726\n",
                    },
                    status_attributes={},
                ),
                Attributes(
                    path=["hardware", "uploaded_files"],
                    inventory_attributes={"call_progress_tones": "germany_12v1.0.dat"},
                    status_attributes={},
                ),
            ],
        ),
    ],
)
def test_inventory_system_information(
    string_table: Sequence[StringTable], expected_result: Sequence[Attributes]
) -> None:
    section = parse_audiocodes_system_information(string_table)
    assert section is not None
    assert list(inventory_audiocodes_system_information(section)) == expected_result
