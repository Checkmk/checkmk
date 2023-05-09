#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ast import literal_eval

from cmk.utils.type_defs import EvalableFloat


def test_evalable_float():
    inf = EvalableFloat("inf")
    assert literal_eval("%r" % inf) == float("inf")
