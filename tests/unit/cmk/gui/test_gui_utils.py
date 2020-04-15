#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from cmk.gui.utils import _drop_comments


@pytest.mark.parametrize(
    "text, result",
    [("# -*- encoding: utf-8\nfrom cmk.gui.log import logger", "from cmk.gui.log import logger"),
     ("def fun(args):\n    # do something\n    return _wrap(*args)",
      "def fun(args):\n    return _wrap(*args)")])
def test_drop_comments(text, result):
    assert _drop_comments(text) == result
