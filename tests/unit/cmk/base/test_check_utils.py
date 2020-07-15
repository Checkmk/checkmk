#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base import check_utils


def test_get_default_params_clean_case():
    # with params
    assert check_utils.get_default_parameters(
        check_info_dict={"default_levels_variable": "foo"},
        factory_settings={"foo": {
            "levels": (23, 42)
        }},
        check_context={},
    ) == {
        "levels": (23, 42)
    }

    # without params
    assert check_utils.get_default_parameters(
        check_info_dict={},
        factory_settings={},
        check_context={},
    ) is None


def test_get_default_params_with_user_update():
    # with params
    assert check_utils.get_default_parameters(
        check_info_dict={"default_levels_variable": "foo"},
        factory_settings={"foo": {
            "levels": (23, 42),
            "overwrite_this": None
        }},
        check_context={"foo": {
            "overwrite_this": 3.14,
            "more": "is better!"
        }},
    ) == {
        "levels": (23, 42),
        "overwrite_this": 3.14,
        "more": "is better!",
    }


def test_get_default_params_ignore_user_defined_tuple():
    # with params
    assert check_utils.get_default_parameters(
        check_info_dict={"default_levels_variable": "foo"},
        factory_settings={},
        check_context={"foo": (23, 42)},
    ) == {}
