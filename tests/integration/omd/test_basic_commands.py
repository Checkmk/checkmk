#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import stat


def test_basic_commands(site):
    commands = [
        "bin/mkp",
        "bin/check_mk",
        "bin/cmk",
        "bin/omd",
        "bin/stunnel",
        "bin/cmk-update-config",
    ]

    for rel_path in commands:
        path = os.path.join(site.root, rel_path)
        assert os.path.exists(path)
