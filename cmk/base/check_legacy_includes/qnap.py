#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def scan(oid):
    return (oid('.1.3.6.1.2.1.1.1.0').startswith('Linux TS-') or
            oid('.1.3.6.1.2.1.1.1.0').startswith('NAS Q'))
