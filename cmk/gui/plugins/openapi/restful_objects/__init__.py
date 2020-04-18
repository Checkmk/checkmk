#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.plugins.openapi.restful_objects.decorators import endpoint_schema
from cmk.gui.plugins.openapi.restful_objects.specification import SPEC

__all__ = ['endpoint_schema', 'SPEC']
