#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.livestatus_helpers.expressions import ScalarExpression


def test_no_lq_injection() -> None:
    """Newlines are capable to inject other headers, that's bad and this test
    should check that"""

    with pytest.raises(ValueError):
        ScalarExpression("f\noo")

    with pytest.raises(ValueError):
        ScalarExpression("foo") == "bar\nfoo"
