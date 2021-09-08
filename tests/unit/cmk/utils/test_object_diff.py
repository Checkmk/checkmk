#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.object_diff import make_object_diff


def test_make_object_diff_nothing_changed():
    assert make_object_diff(None, None) == "Nothing was changed."
    assert make_object_diff({}, {}) == "Nothing was changed."
    assert make_object_diff([], []) == "Nothing was changed."


def test_make_object_diff_str():
    assert make_object_diff("a", "b") == 'Value of object changed from "a" to "b".'


def test_make_object_diff_new_dict_key():
    assert make_object_diff({}, {"a": "1"}) == 'Attribute "a" with value "1" added.'


def test_make_object_diff_removed_dict_key():
    assert make_object_diff({"a": "1"}, {}) == 'Attribute "a" with value "1" removed.'


def test_make_object_diff_changed_dict_value():
    assert make_object_diff({"a": "0"}, {"a": "1"}) == 'Value of "a" changed from "0" to "1".'


def test_make_object_diff_multiple_changes():
    assert (
        make_object_diff({"a": "0", "b": "1"}, {"a": "1"})
        == 'Attribute "b" with value "1" removed.\nValue of "a" changed from "0" to "1".'
    )


def test_make_object_diff_list_remove_item():
    assert make_object_diff([1, 2], [1]) == "Item 1 with value 2 removed."


def test_make_object_diff_list_remove_dict():
    assert make_object_diff([1, {"1": "a"}], [1]) == "Item 1 with value {'1': 'a'} removed."
