#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.snmplib.type_defs import SpecialColumn
from cmk.base.api.agent_based.type_defs import OIDEnd


def test_oid_end_repr():
    assert repr(OIDEnd()) == "OIDEnd()"


def test_oid_end_compat_with_backend():
    assert SpecialColumn(OIDEnd()) == SpecialColumn.END
