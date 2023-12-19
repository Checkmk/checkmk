#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
https://www.technologyuk.net/science/measurement-and-units/physical-quantities-and-si-units.shtml#ID02
"""

from dataclasses import dataclass
from enum import Enum

from ._localize import Localizable


class Unit(Enum):
    # CMK
    BAR = "bar"
    BIT_IEC = "bits"  # factor 1024
    BIT_IEC_PER_SECOND = "bits/s"  # factor 1024
    BIT_SI = "bits"  # factor 1000
    BIT_SI_PER_SECOND = "bits/s"  # factor 1000
    BYTE_IEC = "bytes"  # factor 1024
    BYTE_IEC_PER_DAY = "bytes/d"  # factor 1024
    BYTE_IEC_PER_OPERATION = "bytes/op"  # factor 1024
    BYTE_IEC_PER_SECOND = "bytes/s"  # factor 1024
    BYTE_SI = "bytes"  # factor 1000
    BYTE_SI_PER_DAY = "bytes/d"  # factor 1000
    BYTE_SI_PER_OPERATION = "bytes/op"  # factor 1000
    BYTE_SI_PER_SECOND = "bytes/s"  # factor 1000
    COUNT = ""  # integer
    DECIBEL = "dB"
    DECIBEL_MILLIVOLT = "dBmV"
    DECIBEL_MILLIWATT = "dBm"
    DOLLAR = "$"
    ELETRICAL_ENERGY = "Wh"
    EURO = "€"
    LITER_PER_SECOND = "l/s"
    NUMBER = ""  # float
    PARTS_PER_MILLION = "ppm"
    PERCENTAGE = "%"
    PERCENTAGE_PER_METER = "%/m"
    PER_SECOND = "1/s"
    READ_CAPACITY_UNIT = "RCU"
    REVOLUTIONS_PER_MINUTE = "rpm"
    SECONDS_PER_SECOND = "s/s"
    VOLT_AMPERE = "VA"
    WRITE_CAPACITY_UNIT = "WCU"
    # SI base unit
    AMPERE = "A"
    CANDELA = "cd"
    KELVIN = "K"
    KILOGRAM = "kg"
    METRE = "m"
    MOLE = "mol"
    SECOND = "s"
    # SI Units with Special Names and Symbols
    BECQUEREL = "Bq"
    COULOMB = "C"
    DEGREE_CELSIUS = "°C"
    FARAD = "F"
    GRAY = "Gy"
    HENRY = "H"
    HERTZ = "Hz"
    JOULE = "J"
    KATAL = "kat"
    LUMEN = "lm"
    LUX = "lx"
    NEWTON = "N"
    OHM = "Ω"
    PASCAL = "Pa"
    RADIAN = "rad"
    SIEMENS = "S"
    SIEVERT = "Sv"
    STERADIAN = "sr"
    TESLA = "T"
    VOLT = "V"
    WATT = "W"
    WEBER = "Wb"


@dataclass(frozen=True)
class PhysicalUnit:
    title: Localizable
    symbol: str

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError(self.symbol)


@dataclass(frozen=True)
class ScientificUnit:
    title: Localizable
    symbol: str

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError(self.symbol)
