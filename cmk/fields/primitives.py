#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from marshmallow import fields

from cmk.fields import base


class Constant(base.OpenAPIAttributes, fields.Constant):
    pass


class Boolean(base.OpenAPIAttributes, fields.Boolean):
    pass


class Dict(base.OpenAPIAttributes, fields.Dict):
    pass


class Date(base.OpenAPIAttributes, fields.Date):
    pass


class DateTime(base.OpenAPIAttributes, fields.DateTime):
    pass


class Decimal(base.OpenAPIAttributes, fields.Decimal):
    pass


class Email(base.OpenAPIAttributes, fields.Email):
    pass


class Function(base.OpenAPIAttributes, fields.Function):
    pass


class IPv4(base.OpenAPIAttributes, fields.IPv4):
    pass


class IPv4Interface(base.OpenAPIAttributes, fields.IPv4Interface):
    pass


class IPv6(base.OpenAPIAttributes, fields.IPv6):
    pass


class IPv6Interface(base.OpenAPIAttributes, fields.IPv6Interface):
    pass


class Time(base.OpenAPIAttributes, fields.Time):
    pass


class UUID(base.OpenAPIAttributes, fields.UUID):
    pass


class URL(base.OpenAPIAttributes, fields.URL):
    pass
