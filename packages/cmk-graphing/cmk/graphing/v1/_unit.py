#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
https://www.technologyuk.net/science/measurement-and-units/physical-quantities-and-si-units.shtml#ID02
"""

from dataclasses import dataclass
from enum import auto, Enum

from ._localize import Localizable


class Unit(Enum):
    # CMK
    BAR = auto()  # "bar"
    BIT_IEC = auto()  # "bits, factor 1024
    BIT_SI = auto()  # "bits, factor 1000
    BIT_IEC_PER_SECOND = auto()  # "bits/s, factor 1024
    BIT_SI_PER_SECOND = auto()  # "bits/s, factor 1000
    BYTE_IEC = auto()  # "bytes, factor 1024
    BYTE_SI = auto()  # "bytes, factor 1000
    BYTE_IEC_PER_SECOND = auto()  # "bytes/s, factor 1024
    BYTE_SI_PER_SECOND = auto()  # "bytes/s, factor 1000
    BYTE_IEC_PER_DAY = auto()  # "bytes/d, factor 1024
    BYTE_SI_PER_DAY = auto()  # "bytes/d, factor 1000
    BYTE_IEC_PER_OPERATION = auto()  # "bytes/op, factor 1024
    BYTE_SI_PER_OPERATION = auto()  # "bytes/op, factor 1000
    COUNT = auto()  # ", integer
    DECIBEL = auto()  # "dB"
    DECIBEL_MILLIVOLT = auto()  # "dBmV"
    DECIBEL_MILLIWATT = auto()  # "dBm"
    DOLLAR = auto()  # "$"
    ELETRICAL_ENERGY = auto()  # "Wh"
    EURO = auto()  # "€"
    LITER_PER_SECOND = auto()  # "l/s"
    NUMBER = auto()  # ", float
    PARTS_PER_MILLION = auto()  # "ppm"
    PERCENTAGE = auto()  # "%"
    PERCENTAGE_PER_METER = auto()  # "%/m"
    PER_SECOND = auto()  # "1/s"
    READ_CAPACITY_UNIT = auto()  # "RCU"
    REVOLUTIONS_PER_MINUTE = auto()  # "rpm"
    SECONDS_PER_SECOND = auto()  # "s/s"
    VOLT_AMPERE = auto()  # "VA"
    WRITE_CAPACITY_UNIT = auto()  # "WCU"
    # SI base unit
    AMPERE = auto()  # "A"
    CANDELA = auto()  # "cd"
    KELVIN = auto()  # "K"
    KILOGRAM = auto()  # "kg"
    METRE = auto()  # "m"
    MOLE = auto()  # "mol"
    SECOND = auto()  # "s"
    # SI Units with Special Names and Symbols
    BECQUEREL = auto()  # "Bq"
    COULOMB = auto()  # "C"
    DEGREE_CELSIUS = auto()  # "°C"
    FARAD = auto()  # "F"
    GRAY = auto()  # "Gy"
    HENRY = auto()  # "H"
    HERTZ = auto()  # "Hz"
    JOULE = auto()  # "J"
    KATAL = auto()  # "kat"
    LUMEN = auto()  # "lm"
    LUX = auto()  # "lx"
    NEWTON = auto()  # "N"
    OHM = auto()  # "Ω"
    PASCAL = auto()  # "Pa"
    RADIAN = auto()  # "rad"
    SIEMENS = auto()  # "S"
    SIEVERT = auto()  # "Sv"
    STERADIAN = auto()  # "sr"
    TESLA = auto()  # "T"
    VOLT = auto()  # "V"
    WATT = auto()  # "W"
    WEBER = auto()  # "Wb"


@dataclass(frozen=True)
class PhysicalUnit:
    """
    A physical unit is rendered with decimals.
    """

    title: Localizable
    symbol: str

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError(self.symbol)


@dataclass(frozen=True)
class ScientificUnit:
    """
    A scientific unit is using scientific notation while rendering.
    """

    title: Localizable
    symbol: str

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError(self.symbol)
