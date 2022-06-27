#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def transform_cpu_iowait(params):
    if params is None:
        return {}
    if isinstance(params, tuple):
        return {"iowait": params}

    return params
