#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.werks.error import WerkError
from cmk.werks.parse import markdown_table_to_dict


def test_parse_simple() -> None:
    tables = [
        """key | value
--- | ---
a | 1
b | 2""",
        """| key | value |
| ------- | -------   |
| a | 1 |
| b | 2 |""",
        """| key | value |
| ----: | :---- |
| a | 1 |
| b | 2 |""",
    ]

    for table in tables:
        assert markdown_table_to_dict(table) == {"a": "1", "b": "2"}


def test_table_too_short() -> None:
    with pytest.raises(WerkError, match="contain at least header and"):
        markdown_table_to_dict("k|v")


def test_table_key_value() -> None:
    with pytest.raises(WerkError, match="Table should have a header with columns"):
        markdown_table_to_dict("k|v\n-|-")


def test_table_wrong_separator() -> None:
    with pytest.raises(WerkError, match="Second row in markdown table"):
        markdown_table_to_dict("key|value\n-|-")


def test_table_wrong_column_count() -> None:
    with pytest.raises(WerkError, match="exactly two columns"):
        markdown_table_to_dict("key|value|third\n-|-")


def test_table_allow_empty_value() -> None:
    assert markdown_table_to_dict("key|value\n---|----\na|") == {"a": ""}
