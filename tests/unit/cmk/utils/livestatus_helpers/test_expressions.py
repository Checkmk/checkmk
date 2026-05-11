#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.livestatus_client.expressions import ScalarExpression


def test_newline_in_field_name_raises() -> None:
    with pytest.raises(ValueError):
        ScalarExpression("f\noo")


def test_newline_in_field_value_raises() -> None:
    with pytest.raises(ValueError):
        ScalarExpression("foo") == "bar\nfoo"
