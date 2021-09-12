#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections

from marshmallow import Schema
from marshmallow.decorators import post_dump, post_load


class BaseSchema(Schema):
    """The Base Schema for all request and response schemas."""

    class Meta:
        """Holds configuration for marshmallow"""

        ordered = True  # we want to have documentation in definition-order

    cast_to_dict: bool = False

    @post_load
    @post_dump
    def remove_ordered_dict(self, data, **kwargs):
        # This is a post-load hook to cast the OrderedDict instances to normal dicts. This would
        # lead to problems with the *.mk file persisting logic otherwise.
        if self.cast_to_dict and isinstance(data, collections.OrderedDict):
            return dict(data)
        return data
