#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.gui.utils.json import patch_json


# Override the GUI unit test global fixture to test the context manager
@pytest.fixture(scope="function", name="patch_json")
def fixture_patch_json():
    yield


def test_patch_json_slash_escape() -> None:
    assert json.dumps("a/b") == '"a/b"'
    with patch_json(json):
        assert json.dumps("a/b") == '"a\\/b"'
    assert json.dumps("a/b") == '"a/b"'


def test_patch_json_to_json_method() -> None:
    class Ding:
        def __init__(self):
            self._a = 1

        def to_json(self):
            return self.__dict__

    with pytest.raises(TypeError, match="is not JSON serializable"):
        assert json.dumps(Ding()) == ""

    with patch_json(json):
        assert json.dumps(Ding()) == '{"_a": 1}'

    with pytest.raises(TypeError, match="is not JSON serializable"):
        assert json.dumps(Ding()) == ""
