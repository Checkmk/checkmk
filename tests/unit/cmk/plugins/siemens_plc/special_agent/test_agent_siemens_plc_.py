#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from snap7.type import Areas

from cmk.plugins.siemens_plc.special_agent.agent_siemens_plc import (
    _addresses_from_area_values,
    _area_name_to_area_id,
    _cast_values,
    _group_device_values,
    parse_spec,
)


@pytest.mark.parametrize(
    "hostspec, expected_parsed_device",
    [
        (
            "4fcm;10.2.90.20;0;2;102;merker,5.3,bit,flag,Filterturm_Sammelstoerung_Telefon",
            {
                "host_name": "4fcm",
                "host_address": "10.2.90.20",
                "rack": 0,
                "slot": 2,
                "port": 102,
                "values": [
                    {
                        "area_name": "merker",
                        "db_number": None,
                        "byte": 5,
                        "bit": 3,
                        "datatype": "bit",
                        "valuetype": "flag",
                        "ident": "Filterturm_Sammelstoerung_Telefon",
                    }
                ],
            },
        ),
        (
            'a885-sps2;10.2.90.131;0;2;102;merker,5.0,bit,None,""',
            {
                "host_name": "a885-sps2",
                "host_address": "10.2.90.131",
                "rack": 0,
                "slot": 2,
                "port": 102,
                "values": [
                    {
                        "area_name": "merker",
                        "db_number": None,
                        "byte": 5,
                        "bit": 0,
                        "datatype": "bit",
                        "valuetype": "None",
                        "ident": '""',
                    }
                ],
            },
        ),
        (
            (
                'ut020;10.2.90.60;0;0;102;merker,5.0,bit,flag,"Kuehlanlage1_Sammelstoerung_Telefon"'
                ';merker,5.1,bit,flag,"Kuehlanlage1_Sammelstoerung_Email"'
            ),
            {
                "host_name": "ut020",
                "host_address": "10.2.90.60",
                "rack": 0,
                "slot": 0,
                "port": 102,
                "values": [
                    {
                        "area_name": "merker",
                        "db_number": None,
                        "byte": 5,
                        "bit": 0,
                        "datatype": "bit",
                        "valuetype": "flag",
                        "ident": '"Kuehlanlage1_Sammelstoerung_Telefon"',
                    },
                    {
                        "area_name": "merker",
                        "db_number": None,
                        "byte": 5,
                        "bit": 1,
                        "datatype": "bit",
                        "valuetype": "flag",
                        "ident": '"Kuehlanlage1_Sammelstoerung_Email"',
                    },
                ],
            },
        ),
    ],
)
def test_parse_spec(
    hostspec: str, expected_parsed_device: dict[str, str | int | list[dict[str, str | None | int]]]
) -> None:
    assert parse_spec(hostspec) == expected_parsed_device


@pytest.mark.parametrize(
    "area_name, expected_id",
    [
        ("merker", Areas.MK),
    ],
)
def test__area_name_to_area_id(area_name: str, expected_id: Areas) -> None:
    assert _area_name_to_area_id(area_name) is expected_id


@pytest.mark.parametrize(
    "values, expected_addresses",
    [
        (
            [
                {
                    "area_name": "merker",
                    "db_number": None,
                    "byte": 5,
                    "bit": 3,
                    "datatype": "bit",
                    "valuetype": "flag",
                    "ident": "Filterturm_Sammelstoerung_Telefon",
                }
            ],
            (5, 6),
        ),
        (
            [
                {
                    "area_name": "merker",
                    "db_number": None,
                    "byte": 5,
                    "bit": 0,
                    "datatype": "bit",
                    "valuetype": "None",
                    "ident": '""',
                }
            ],
            (5, 6),
        ),
    ],
)
def test__addresses_from_area_values(
    values: list[dict[str, str | None | int]], expected_addresses: tuple[int, int]
) -> None:
    assert _addresses_from_area_values(values) == expected_addresses


@pytest.mark.parametrize(
    "values, start_address, area_value, expected_value",
    [
        (
            [
                {
                    "area_name": "merker",
                    "db_number": None,
                    "byte": 5,
                    "bit": 3,
                    "datatype": "bit",
                    "valuetype": "flag",
                    "ident": "Filterturm_Sammelstoerung_Telefon",
                }
            ],
            5,
            b"\x08",
            [
                ("flag", "Filterturm_Sammelstoerung_Telefon", True),
            ],
        ),
        (
            [
                {
                    "area_name": "merker",
                    "db_number": None,
                    "byte": 5,
                    "bit": 0,
                    "datatype": "bit",
                    "valuetype": "None",
                    "ident": '""',
                }
            ],
            5,
            b"\x00",
            [
                ("None", '""', False),
            ],
        ),
    ],
)
def test__cast_values(
    values: list[dict[str, str | None | int]],
    start_address: int,
    area_value: bytes,
    expected_value: list[tuple[str, str]],
) -> None:
    assert _cast_values(values, start_address, area_value) == expected_value


@pytest.mark.parametrize(
    "device, expected_grouped_values",
    [
        (
            {
                "host_name": "4fcm",
                "host_address": "10.2.90.20",
                "rack": 0,
                "slot": 2,
                "port": 102,
                "values": [
                    {
                        "area_name": "merker",
                        "db_number": None,
                        "byte": 5,
                        "bit": 3,
                        "datatype": "bit",
                        "valuetype": "flag",
                        "ident": "Filterturm_Sammelstoerung_Telefon",
                    },
                    {
                        "area_name": "timer",
                        "db_number": None,
                        "byte": 5,
                        "bit": 0,
                        "datatype": "bit",
                        "valuetype": "None",
                        "ident": "",
                    },
                    {
                        "area_name": "merker",
                        "db_number": None,
                        "byte": 3,
                        "bit": 1,
                        "datatype": "bit",
                        "valuetype": "flag",
                        "ident": "Filterturm_Sammelstoerung_Email",
                    },
                ],
            },
            [
                (
                    ("merker", None),
                    [
                        {
                            "area_name": "merker",
                            "db_number": None,
                            "byte": 5,
                            "bit": 3,
                            "datatype": "bit",
                            "valuetype": "flag",
                            "ident": "Filterturm_Sammelstoerung_Telefon",
                        },
                        {
                            "area_name": "merker",
                            "db_number": None,
                            "byte": 3,
                            "bit": 1,
                            "datatype": "bit",
                            "valuetype": "flag",
                            "ident": "Filterturm_Sammelstoerung_Email",
                        },
                    ],
                ),
                (
                    ("timer", None),
                    [
                        {
                            "area_name": "timer",
                            "db_number": None,
                            "byte": 5,
                            "bit": 0,
                            "datatype": "bit",
                            "valuetype": "None",
                            "ident": "",
                        },
                    ],
                ),
            ],
        ),
    ],
)
def test__group_device_values(
    device: dict[str, str | int | list[dict[str, str | None | int]]],
    expected_grouped_values: list[tuple[tuple[str, None], list[dict[str, str | None | int]]]],
) -> None:
    actual_values = [(i, list(j)) for i, j in _group_device_values(device)]
    assert actual_values == expected_grouped_values
