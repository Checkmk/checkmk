#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
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


class String(base.OpenAPIAttributes, fields.String):
    pass


class Integer(base.OpenAPIAttributes, fields.Integer):
    pass


class List(base.OpenAPIAttributes, fields.List):
    pass


class Nested(base.OpenAPIAttributes, fields.Nested):
    pass


__all__ = ["Boolean", "Constant", "Dict", "String", "Integer", "List", "Nested"]
