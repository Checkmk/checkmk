#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from decimal import Decimal
from typing import Any

import pytest

from cmk.gui.inventory import _xml


def test_dict_to_document() -> None:
    payload = {
        "alpha": 1.0,
        "beta": [1, 2, 3],
        "charlie": {
            "delta": {
                "echo": [4, 5, 6],
            },
        },
    }

    value = _xml.dict_to_document(payload).toprettyxml(indent="  ")
    expected = """\
<?xml version="1.0" ?>
<root>
  <alpha type="float">1.0</alpha>
  <beta type="list">
    <item type="int">1</item>
    <item type="int">2</item>
    <item type="int">3</item>
  </beta>
  <charlie type="dict">
    <delta type="dict">
      <echo type="list">
        <item type="int">4</item>
        <item type="int">5</item>
        <item type="int">6</item>
      </echo>
    </delta>
  </charlie>
</root>
"""

    assert value == expected


def test_dict_to_document_empty_payload() -> None:
    value = _xml.dict_to_document({}).toxml()
    expected = '<?xml version="1.0" ?><root/>'
    assert value == expected


@pytest.mark.parametrize(
    "obj, content",
    [
        pytest.param({"a": True}, '<a type="bool">true</a>', id="boolean"),
        pytest.param({"a": 1}, '<a type="int">1</a>', id="integer"),
        pytest.param({"a": 1.0}, '<a type="float">1.0</a>', id="float"),
        pytest.param({"a": Decimal(1.5)}, '<a type="number">1.5</a>', id="number"),
        pytest.param({"a": datetime.date(2025, 1, 1)}, '<a type="str">2025-01-01</a>', id="date"),
        pytest.param({"a": "x"}, '<a type="str">x</a>', id="string"),
        pytest.param({"a": [1]}, '<a type="list"><item type="int">1</item></a>', id="list(int)"),
        pytest.param({"a": {"b": "c"}}, '<a type="dict"><b type="str">c</b></a>', id="dict"),
    ],
)
def test_dict_to_document_common_types(obj: dict[str, Any], content: str) -> None:
    value = _xml.dict_to_document(obj).toxml()
    expected = f'<?xml version="1.0" ?><root>{content}</root>'
    assert value == expected


@pytest.mark.parametrize(
    "payload, content",
    [
        pytest.param({"a": None}, '<a type="null"/>', id="none"),
        pytest.param({"a": ""}, '<a type="str"/>', id="string"),
        pytest.param({"a": []}, '<a type="list"/>', id="list"),
        pytest.param({"a": {}}, '<a type="dict"/>', id="dict"),
    ],
)
def test_dict_to_document_empty_value(payload: dict[str, Any], content: str) -> None:
    value = _xml.dict_to_document(payload).toxml()
    expected = f'<?xml version="1.0" ?><root>{content}</root>'
    assert value == expected


@pytest.mark.parametrize(
    "payload, content",
    [
        pytest.param({"a": "&"}, '<a type="str">&amp;</a>', id="ampersand"),
        pytest.param({"a": "<"}, '<a type="str">&lt;</a>', id="less-than"),
        pytest.param({"a": ">"}, '<a type="str">&gt;</a>', id="greater-than"),
        pytest.param({"a": '"'}, '<a type="str">&quot;</a>', id="quote"),
    ],
)
def test_dict_to_document_escaped_value(payload: dict[str, Any], content: str) -> None:
    value = _xml.dict_to_document(payload).toxml()
    expected = f'<?xml version="1.0" ?><root>{content}</root>'
    assert value == expected


@pytest.mark.parametrize(
    "payload, content",
    [
        pytest.param({"&": "a"}, '<key name="&amp;" type="str">a</key>', id="ampersand"),
        pytest.param({"<": "a"}, '<key name="&lt;" type="str">a</key>', id="less-than"),
        pytest.param({">": "a"}, '<key name="&gt;" type="str">a</key>', id="greater-than"),
        pytest.param({'"': "a"}, '<key name="&quot;" type="str">a</key>', id="greater-than"),
    ],
)
def test_dict_to_document_escaped_tag_name(payload: dict[str, Any], content: str) -> None:
    value = _xml.dict_to_document(payload).toxml()
    expected = f'<?xml version="1.0" ?><root>{content}</root>'
    assert value == expected
