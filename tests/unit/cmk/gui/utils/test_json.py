#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.utils.json import CustomObjectJSONEncoder


def test_json_dumps_prevent_close_tag_attack_via_onclick_attribute() -> None:
    assert str(
        HTMLWriter.render_a(
            "abc",
            href="javascript:void(0);",
            target="_self",
            onclick=f"js_func({json.dumps({'1': '</a><script>alert(1)</script>'})})",
        )
    ) == (
        '<a href="javascript:void(0);" target="_self" '
        r'onclick="js_func({&quot;1&quot;: &quot;&lt;/a&gt;&lt;script&gt;alert(1)&lt;/script&gt;&quot;})">abc</a>'
    )


def test_json_dumps_prevent_close_tag_attack_via_script_tag() -> None:
    assert str(
        HTMLWriter.render_javascript(
            f"js_func({json.dumps({'1': '</script><script>alert(1)</script>'})})",
        )
    ) == (
        r'<script>js_func({"1": "\u003c/script\u003e\u003cscript\u003ealert(1)\u003c/script\u003e"})</script>'
    )


def test_custom_object_json_encoder() -> None:
    class Ding:
        def __init__(self) -> None:
            self._a = 1

        def to_json(self):
            return self.__dict__

    assert json.dumps(Ding(), cls=CustomObjectJSONEncoder) == '{"_a": 1}'


def test_custom_object_json_encoder_no_to_json_method() -> None:
    class Ding:
        pass

    with pytest.raises(TypeError, match="not JSON serializable"):
        assert json.dumps(Ding(), cls=CustomObjectJSONEncoder) == '{"_a": 1}'


def test_custom_object_json_encoder_non_callable() -> None:
    class Ding:
        to_json = "x"

    with pytest.raises(TypeError, match="not JSON serializable"):
        assert json.dumps(Ding(), cls=CustomObjectJSONEncoder) == '{"_a": 1}'
