#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.base.data_sources.abstract as _abstract


def test_mgmt_board_data_source_is_ip_address():
    _is_ipaddress = _abstract.ManagementBoardDataSource._is_ipaddress
    assert _is_ipaddress(None) is False
    assert _is_ipaddress("localhost") is False
    assert _is_ipaddress("abc 123") is False
    assert _is_ipaddress("127.0.0.1") is True
    assert _is_ipaddress("::1") is True
    assert _is_ipaddress("fe80::807c:f8ff:fea9:9f12") is True


def test_normalize_ip():
    assert _abstract._normalize_ip_addresses("1.2.{3,4,5}.6") == ["1.2.3.6", "1.2.4.6", "1.2.5.6"]
    assert _abstract._normalize_ip_addresses(["0.0.0.0", "1.1.1.1/32"]) == ["0.0.0.0", "1.1.1.1/32"]
    assert _abstract._normalize_ip_addresses("0.0.0.0 1.1.1.1/32") == ["0.0.0.0", "1.1.1.1/32"]
