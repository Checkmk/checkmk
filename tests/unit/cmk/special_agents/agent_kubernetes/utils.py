#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json


class FakeResponse:
    def __init__(self, data: dict):
        self.data: str = json.dumps(data)


class FakeByteResponse:
    def __init__(self, data: str):
        self.data = bytes(data, "utf-8")
