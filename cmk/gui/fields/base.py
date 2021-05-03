#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from marshmallow import Schema


class BaseSchema(Schema):
    """The Base Schema for all request and response schemas."""
    class Meta:
        """Holds configuration for marshmallow"""
        ordered = True  # we want to have documentation in definition-order
