#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import IgnoreResultsError
from cmk.base.plugins.agent_based.domino_tasks import check_domino_tasks


def test_check_domino_tasks_no_domino_data_goes_stale():
    with pytest.raises(IgnoreResultsError):
        list(check_domino_tasks("someitem", {}, None, {"somememstuff": 1}))
