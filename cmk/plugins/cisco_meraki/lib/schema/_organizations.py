#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypedDict


class Organisation(TypedDict):
    # See https://developer.cisco.com/meraki/api-v1/#!get-organizations
    # if you want to extend this
    id_: str
    name: str
