#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Simple python script to replace version in the file
# first param is a file usually wnx\src\common\wnx_version.h
# second param is version without double quotes, for example, 2.0.0i1

import re
import sys

print(f"Windows agent version to be set to '{sys.argv[1]}' in file '{sys.argv[2]}'")
content = ""
with open(sys.argv[1], "r") as f:
    content = f.read()

with open(sys.argv[1], "w") as f:
    pattern = r'(^#define CMK_WIN_AGENT_VERSION )("[^"]*")'
    ret = re.sub(pattern, f'\\1"{sys.argv[2]}"', content)
    f.write(ret)

print("Windows agent version has been set successfully")
