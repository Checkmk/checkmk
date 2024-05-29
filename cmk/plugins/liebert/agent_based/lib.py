#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Mapping, Sequence
from typing import TypeVar

from cmk.agent_based.v2 import startswith, StringTable

TParsed = TypeVar("TParsed")

Section = Mapping[str, tuple[TParsed, str]]

SectionWithoutUnit = Mapping[str, TParsed]

SystemSection = SectionWithoutUnit[str]

DETECT_LIEBERT = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.476.1.42")


def parse_liebert_float(string_table: StringTable) -> Section[float]:
    return parse_liebert([string_table], float)


def parse_liebert_float_without_unit(string_table: StringTable) -> SectionWithoutUnit[float]:
    return parse_liebert_without_unit([string_table], float)


def parse_liebert_str_without_unit(string_table: StringTable) -> SectionWithoutUnit[str]:
    return parse_liebert_without_unit([string_table], str)


def parse_liebert_without_unit(
    string_table: Sequence[StringTable],
    type_func: Callable[[str], TParsed],
) -> SectionWithoutUnit[TParsed]:
    parsed = {}
    used_names = set()

    def get_item_name(name: str) -> str:
        counter = 2
        new_name = name
        while True:
            if new_name in used_names:
                new_name = "%s %d" % (name, counter)
                counter += 1
            else:
                used_names.add(new_name)
                break
        return new_name

    for line in string_table[0]:
        for element in zip(line[0::2], line[1::2]):
            if not element[0]:
                continue
            name = get_item_name(element[0])
            try:
                parsed[name] = type_func(element[1])
            except ValueError:
                continue

    return parsed


def parse_liebert(
    string_table: Sequence[StringTable],
    type_func: Callable[[str], TParsed],
) -> Section[TParsed]:
    parsed = {}
    used_names = set()

    def get_item_name(name: str) -> str:
        counter = 2
        new_name = name
        while True:
            if new_name in used_names:
                new_name = "%s %d" % (name, counter)
                counter += 1
            else:
                used_names.add(new_name)
                break
        return new_name

    for line in string_table[0]:
        for element in zip(line[0::3], line[1::3], line[2::3]):
            if not element[0]:
                continue
            name = get_item_name(element[0])
            try:
                parsed[name] = (type_func(element[1]), element[2])
            except ValueError:
                continue

    return parsed


def temperature_to_celsius(reading: float, unit: str) -> float:
    """
    >>> temperature_to_celsius(12.3, "deg C")
    12.3
    >>> f"{temperature_to_celsius(40.1, 'deg F'):.2f}"
    '4.50'

    """
    match unit.replace("deg ", "").lower():
        case "c" | "%":
            # '%' should probably be dealt with elsewhere...
            return reading
        case "f":
            return (reading - 32) * (5.0 / 9.0)
        case "k":
            return reading - 273.15
    raise ValueError(f"Unknown unit: {unit}")
