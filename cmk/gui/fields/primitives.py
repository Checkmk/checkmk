#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from marshmallow import fields

from cmk.gui.fields.base import OpenAPIAttributes


class Constant(OpenAPIAttributes, fields.Constant):
    pass


class Boolean(OpenAPIAttributes, fields.Boolean):
    pass


Bool = Boolean


class Date(OpenAPIAttributes, fields.Date):
    pass


class DateTime(OpenAPIAttributes, fields.DateTime):
    pass


class Decimal(OpenAPIAttributes, fields.Decimal):
    pass


class Dict(OpenAPIAttributes, fields.Dict):
    pass


class Email(OpenAPIAttributes, fields.Email):
    pass


class Function(OpenAPIAttributes, fields.Function):
    pass


class IPv4(OpenAPIAttributes, fields.IPv4):
    pass


class IPv4Interface(OpenAPIAttributes, fields.IPv4Interface):
    pass


class IPv6(OpenAPIAttributes, fields.IPv6):
    pass


class IPv6Interface(OpenAPIAttributes, fields.IPv6Interface):
    pass


class Time(OpenAPIAttributes, fields.Time):
    pass


class UUID(OpenAPIAttributes, fields.UUID):
    pass


class URL(OpenAPIAttributes, fields.URL):
    pass


__all__ = [
    "Bool",
    "Boolean",
    "Constant",
    "Date",
    "DateTime",
    "Decimal",
    "Dict",
    "Email",
    "Function",
    "IPv4",
    "IPv4Interface",
    "IPv6",
    "IPv6Interface",
    "Time",
    "URL",
    "UUID",
]
