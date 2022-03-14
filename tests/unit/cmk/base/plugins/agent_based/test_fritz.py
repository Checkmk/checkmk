#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.fritz import inventory_fritz


def test_inventroy_fritz():
    assert list(
        inventory_fritz({"VersionOS": "Fritz!OS 1970.12.19", "VersionDevice": "Tyson Beckford"})
    ) == [
        Attributes(path=["hardware", "system"], inventory_attributes={"model": "Tyson Beckford"}),
        Attributes(
            path=["software", "os"], inventory_attributes={"version": "Fritz!OS 1970.12.19"}
        ),
    ]
