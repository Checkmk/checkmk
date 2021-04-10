#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from marshmallow import Schema as _Schema


class Schema(_Schema):
    class Meta:
        # Even if we hard-wire the dict below, we still need to set this
        # property to get a stably ordered spec-file generated.
        ordered = True

    @property
    def dict_class(self) -> type:
        # Having an OrderedDict breaks bi, having an OrderedDict with a __repr__() which doesn't
        # break bi, breaks the OpenAPI yaml spec generator instead. It's a lose-lose situation.
        return dict
