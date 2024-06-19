#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.object_diff import make_diff_text


def test_make_object_diff_nothing_changed() -> None:
    assert make_diff_text({}, {}) == "Nothing was changed."
    assert make_diff_text([], []) == "Nothing was changed."


def test_make_object_diff_handling_none() -> None:
    with pytest.raises(ValueError):
        make_diff_text(None, None)
    with pytest.raises(ValueError):
        make_diff_text(None, {})
    with pytest.raises(ValueError):
        make_diff_text({"a": "2"}, None)


def test_make_object_diff_str() -> None:
    assert make_diff_text("a", "b") == 'Value of object changed from "a" to "b".'


def test_make_object_diff_new_dict_key() -> None:
    assert make_diff_text({}, {"a": "1"}) == 'Attribute "a" with value "1" added.'


def test_make_object_diff_removed_dict_key() -> None:
    assert make_diff_text({"a": "1"}, {}) == 'Attribute "a" with value "1" removed.'


def test_make_object_diff_changed_dict_value() -> None:
    assert make_diff_text({"a": "0"}, {"a": "1"}) == 'Value of "a" changed from "0" to "1".'


def test_make_object_diff_multiple_changes() -> None:
    assert (
        make_diff_text({"a": "0", "b": "1"}, {"a": "1"})
        == 'Value of "a" changed from "0" to "1".\nAttribute "b" with value "1" removed.'
    )


def test_make_object_diff_list_remove_item() -> None:
    assert make_diff_text([1, 2], [1]) == "Item 1 with value 2 removed."


def test_make_object_diff_list_remove_dict() -> None:
    assert make_diff_text([1, {"1": "a"}], [1]) == "Item 1 with value {'1': 'a'} removed."
