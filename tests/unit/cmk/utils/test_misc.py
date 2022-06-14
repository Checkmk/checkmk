#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.misc import normalize_ip_addresses


def test_normalize_ip() -> None:
    assert normalize_ip_addresses("1.2.{3,4,5}.6") == ["1.2.3.6", "1.2.4.6", "1.2.5.6"]
    assert normalize_ip_addresses(["0.0.0.0", "1.1.1.1/32"]) == ["0.0.0.0", "1.1.1.1/32"]
    assert normalize_ip_addresses("0.0.0.0 1.1.1.1/32") == ["0.0.0.0", "1.1.1.1/32"]
