#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.check_utils import maincheckify

from cmk.gui.plugins.metrics.utils import check_metrics


def test_all_keys_migrated():
    for key in check_metrics:
        if key.startswith("check_mk-"):
            assert key[9:] == maincheckify(key[9:])
