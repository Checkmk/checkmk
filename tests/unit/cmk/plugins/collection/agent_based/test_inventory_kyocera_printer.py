#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Attributes
from cmk.plugins.collection.agent_based.inventory_kyocera_printer import (
    inventory_kyocera_printer,
    KyoceraPrinter,
    parse_kyocera_printer,
)


def test_parse_kyocera_printer() -> None:
    assert parse_kyocera_printer(
        [["2H7_2F00.013.006", "QJK1132449", "12345", "2022", "my_model"]]
    ) == KyoceraPrinter(
        device_number="12345",
        serial_number="QJK1132449",
        install_date="2022",
        system_firmware="2H7_2F00.013.006",
        model="my_model",
    )
    assert parse_kyocera_printer([]) is None


@pytest.fixture(name="section", scope="module")
def _get_section() -> KyoceraPrinter:
    return KyoceraPrinter(
        device_number="12345",
        serial_number="QJK1132449",
        install_date="2022",
        system_firmware="2H7_2F00.013.006",
        model="my_model",
    )


def test_inventory_kyocera_printer(section: KyoceraPrinter) -> None:
    assert list(inventory_kyocera_printer(section)) == [
        Attributes(
            path=["hardware", "system"],
            inventory_attributes={
                "manufacturer": "Kyocera",
                "model": "my_model",
                "device_number": "12345",
                "serial": "QJK1132449",
            },
        ),
        Attributes(
            path=["software", "firmware"],
            inventory_attributes={
                "vendor": "Kyocera",
                "version": "2H7_2F00.013.006",
            },
        ),
    ]
