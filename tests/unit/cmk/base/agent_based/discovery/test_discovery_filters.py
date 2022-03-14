#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import pytest

from cmk.base.agent_based.discovery import _filters


@pytest.mark.parametrize(
    "parameters_rediscovery",
    [
        {},
        {
            "service_whitelist": [],
        },
        {
            "service_blacklist": [],
        },
        {
            "service_whitelist": [],
            "service_blacklist": [],
        },
        {
            "vanished_service_whitelist": [],
        },
        {
            "vanished_service_blacklist": [],
        },
        {
            "vanished_service_whitelist": [],
            "vanished_service_blacklist": [],
        },
    ],
)
def test__get_service_filter_func_no_lists(parameters_rediscovery):
    service_filters = _filters.ServiceFilters.from_settings(parameters_rediscovery)
    assert service_filters.new is _filters._accept_all_services
    assert service_filters.vanished is _filters._accept_all_services


@pytest.mark.parametrize(
    "whitelist, result",
    [
        (["^Test"], True),
        (["^test"], False),
        ([".*Description"], True),
        ([".*Descript$"], False),
    ],
)
def test__get_service_filter_func_same_lists(monkeypatch, whitelist, result):
    service_filters = _filters.ServiceFilters.from_settings({"service_whitelist": whitelist})
    assert service_filters.new is not None
    assert service_filters.new("Test Description") is result

    service_filters_inv = _filters.ServiceFilters.from_settings({"service_blacklist": whitelist})
    assert service_filters_inv.new is not None
    assert service_filters_inv.new("Test Description") is not result

    service_filters_both = _filters.ServiceFilters.from_settings(
        {
            "service_whitelist": whitelist,
            "service_blacklist": whitelist,
        }
    )
    assert service_filters_both.new is not None
    assert service_filters_both.new("Test Description") is False


@pytest.mark.parametrize(
    "parameters_rediscovery, result",
    [
        (
            {
                # Matches
                "service_whitelist": ["^Test"],
                # Does not match
                "service_blacklist": [".*Descript$"],
            },
            True,
        ),
        (
            {
                # Matches
                "service_whitelist": ["^Test"],
                # Matches
                "service_blacklist": [".*Description$"],
            },
            False,
        ),
        (
            {
                # Does not match
                "service_whitelist": ["^test"],
                # Matches
                "service_blacklist": [".*Description$"],
            },
            False,
        ),
        (
            {
                # Does not match
                "service_whitelist": ["^test"],
                # Does not match
                "service_blacklist": [".*Descript$"],
            },
            False,
        ),
    ],
)
def test__get_service_filter_func(monkeypatch, parameters_rediscovery, result):
    service_filters = _filters.ServiceFilters.from_settings(parameters_rediscovery)
    assert service_filters.new is not None
    assert service_filters.new("Test Description") is result


@pytest.mark.parametrize(
    "parameters, new_whitelist, new_blacklist, vanished_whitelist, vanished_blacklist",
    [
        ({}, None, None, None, None),
        ({}, None, None, None, None),
        (
            {
                "service_whitelist": ["white"],
            },
            ["white"],
            None,
            ["white"],
            None,
        ),
        (
            {
                "service_blacklist": ["black"],
            },
            None,
            ["black"],
            None,
            ["black"],
        ),
        (
            {
                "service_whitelist": ["white"],
                "service_blacklist": ["black"],
            },
            ["white"],
            ["black"],
            ["white"],
            ["black"],
        ),
        (
            {
                "service_filters": ("combined", {}),
            },
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "combined",
                    {
                        "service_whitelist": ["white"],
                    },
                ),
            },
            ["white"],
            None,
            ["white"],
            None,
        ),
        (
            {
                "service_filters": (
                    "combined",
                    {
                        "service_blacklist": ["black"],
                    },
                ),
            },
            None,
            ["black"],
            None,
            ["black"],
        ),
        (
            {
                "service_filters": (
                    "combined",
                    {
                        "service_whitelist": ["white"],
                        "service_blacklist": ["black"],
                    },
                ),
            },
            ["white"],
            ["black"],
            ["white"],
            ["black"],
        ),
        (
            {
                "service_filters": ("dedicated", {}),
            },
            None,
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white"],
                    },
                ),
            },
            ["white"],
            None,
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_blacklist": ["black"],
                    },
                ),
            },
            None,
            ["black"],
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white"],
                        "service_blacklist": ["black"],
                    },
                ),
            },
            ["white"],
            ["black"],
            None,
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "vanished_service_whitelist": ["white"],
                    },
                ),
            },
            None,
            None,
            ["white"],
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "vanished_service_blacklist": ["black"],
                    },
                ),
            },
            None,
            None,
            None,
            ["black"],
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "vanished_service_whitelist": ["white"],
                        "vanished_service_blacklist": ["black"],
                    },
                ),
            },
            None,
            None,
            ["white"],
            ["black"],
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white_new"],
                        "vanished_service_whitelist": ["white_vanished"],
                    },
                ),
            },
            ["white_new"],
            None,
            ["white_vanished"],
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white_new"],
                        "vanished_service_blacklist": ["black_vanished"],
                    },
                ),
            },
            ["white_new"],
            None,
            None,
            ["black_vanished"],
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_blacklist": ["black_new"],
                        "vanished_service_whitelist": ["white_vanished"],
                    },
                ),
            },
            None,
            ["black_new"],
            ["white_vanished"],
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_blacklist": ["black_new"],
                        "vanished_service_blacklist": ["black_vanished"],
                    },
                ),
            },
            None,
            ["black_new"],
            None,
            ["black_vanished"],
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white_new"],
                        "service_blacklist": ["black_new"],
                        "vanished_service_whitelist": ["white_vanished"],
                    },
                ),
            },
            ["white_new"],
            ["black_new"],
            ["white_vanished"],
            None,
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white_new"],
                        "service_blacklist": ["black_new"],
                        "vanished_service_blacklist": ["black_vanished"],
                    },
                ),
            },
            ["white_new"],
            ["black_new"],
            None,
            ["black_vanished"],
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white_new"],
                        "service_blacklist": ["black_new"],
                        "vanished_service_whitelist": ["white_vanished"],
                        "vanished_service_blacklist": ["black_vanished"],
                    },
                ),
            },
            ["white_new"],
            ["black_new"],
            ["white_vanished"],
            ["black_vanished"],
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_whitelist": ["white_new"],
                        "vanished_service_whitelist": ["white_vanished"],
                        "vanished_service_blacklist": ["black_vanished"],
                    },
                ),
            },
            ["white_new"],
            None,
            ["white_vanished"],
            ["black_vanished"],
        ),
        (
            {
                "service_filters": (
                    "dedicated",
                    {
                        "service_blacklist": ["black_new"],
                        "vanished_service_whitelist": ["white_vanished"],
                        "vanished_service_blacklist": ["black_vanished"],
                    },
                ),
            },
            None,
            ["black_new"],
            ["white_vanished"],
            ["black_vanished"],
        ),
    ],
)
def test__get_service_filters_lists(
    parameters, new_whitelist, new_blacklist, vanished_whitelist, vanished_blacklist
):
    service_filter_lists = _filters._get_service_filter_lists(parameters)
    assert service_filter_lists.new_whitelist == new_whitelist
    assert service_filter_lists.new_blacklist == new_blacklist
    assert service_filter_lists.vanished_whitelist == vanished_whitelist
    assert service_filter_lists.vanished_blacklist == vanished_blacklist

    service_filters = _filters.ServiceFilters.from_settings(parameters)
    assert service_filters.new is not None
    assert service_filters.vanished is not None
