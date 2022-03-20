#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, TypedDict


class Interface(TypedDict, total=False):
    status: str
    mode: str
    hwaddr: str
    failures: int
    aggregator_id: str


class Bond(TypedDict, total=False):
    status: str
    mode: str
    interfaces: Mapping[str, Interface]
    aggregator_id: str
    active: str
    primary: str


Section = Mapping[str, Bond]
