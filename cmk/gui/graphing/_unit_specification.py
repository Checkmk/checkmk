#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

from pydantic import BaseModel, Field

from cmk.gui.unit_formatter import AutoPrecision, StrictPrecision


class DecimalNotation(BaseModel, frozen=True):
    type: Literal["decimal"] = "decimal"
    symbol: str


class SINotation(BaseModel, frozen=True):
    type: Literal["si"] = "si"
    symbol: str


class IECNotation(BaseModel, frozen=True):
    type: Literal["iec"] = "iec"
    symbol: str


class StandardScientificNotation(BaseModel, frozen=True):
    type: Literal["standard_scientific"] = "standard_scientific"
    symbol: str


class EngineeringScientificNotation(BaseModel, frozen=True):
    type: Literal["engineering_scientific"] = "engineering_scientific"
    symbol: str


class TimeNotation(BaseModel, frozen=True):
    type: Literal["time"] = "time"
    symbol: str


class ConvertibleUnitSpecification(BaseModel, frozen=True):
    type: Literal["convertible"] = "convertible"
    notation: (
        DecimalNotation
        | SINotation
        | IECNotation
        | StandardScientificNotation
        | EngineeringScientificNotation
        | TimeNotation
    ) = Field(
        ...,
        discriminator="type",
    )
    precision: AutoPrecision | StrictPrecision = Field(
        ...,
        discriminator="type",
    )


class NonConvertibleUnitSpecification(BaseModel, frozen=True):
    type: Literal["non_convertible"] = "non_convertible"
    notation: (
        DecimalNotation
        | SINotation
        | IECNotation
        | StandardScientificNotation
        | EngineeringScientificNotation
        | TimeNotation
    ) = Field(
        ...,
        discriminator="type",
    )
    precision: AutoPrecision | StrictPrecision = Field(
        ...,
        discriminator="type",
    )
