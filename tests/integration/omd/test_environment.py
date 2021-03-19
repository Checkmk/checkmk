#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess


def test_locales(site):
    p = site.execute(["locale"], stdout=subprocess.PIPE)
    output = p.communicate()[0]

    assert "LANG=C.UTF-8" in output \
        or "LANG=C.utf8" in output \
        or "LANG=en_US.utf8" in output

    assert "LC_ALL=C.UTF-8" in output \
        or "LC_ALL=C.utf8" in output \
        or "LC_ALL=en_US.utf8" in output
