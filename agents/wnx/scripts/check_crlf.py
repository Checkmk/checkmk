#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Simple python script to find that file line ending is correctly encoded
# Very Simple.

import sys

with open("install\\resources\\check_mk.user.yml", "rb") as f:
    content = f.read()
    if content.count(b"\r\n") < 10:
        sys.exit(1)

sys.exit(0)
