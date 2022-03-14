#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file


def scan_domino(oid):
    return (
        oid(".1.3.6.1.2.1.1.2.0", "").startswith(".1.3.6.1.4.1.311.1.1.3.1.2")
        or oid(".1.3.6.1.2.1.1.2.0", "").startswith(".1.3.6.1.4.1.8072.3.1.10")
        or oid(".1.3.6.1.2.1.1.2.0", "").startswith(".1.3.6.1.4.1.8072.3.2.10")
    )
