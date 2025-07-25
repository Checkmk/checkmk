#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.graphing._legacy import check_metrics
from cmk.utils.check_utils import maincheckify


def test_all_keys_migrated() -> None:
    for key in check_metrics:
        if key.startswith("check_mk-"):
            assert key[9:] == maincheckify(key[9:])
