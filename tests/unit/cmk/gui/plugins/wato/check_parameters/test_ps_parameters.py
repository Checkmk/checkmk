#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.wato.check_parameters.cpu_utilization import transform_cpu_iowait
from cmk.gui.plugins.wato.check_parameters.ps import (
    convert_inventory_processes,
    CPU_RESCALE_MAX_UNSPEC,
    forbid_re_delimiters_inside_groups,
    ps_cleanup_params,
    validate_process_discovery_descr_option,
)


@pytest.mark.parametrize("pattern", ["(test)$", "foo\\b", "^bar", "\\bfoo\\b", "(a)\\b"])
def test_validate_ps_allowed_regex(pattern):
    assert forbid_re_delimiters_inside_groups(pattern, "") is None


@pytest.mark.parametrize("pattern", ["(test$)", "(foo\\b)", "(^bar)", "(\\bfoo\\b)"])
def test_validate_ps_forbidden_regex(pattern):
    with pytest.raises(MKUserError):
        forbid_re_delimiters_inside_groups(pattern, "")


@pytest.mark.parametrize("description", ["%s%5"])
def test_validate_process_discovery_descr_option(description):
    with pytest.raises(MKUserError):
        validate_process_discovery_descr_option(description, "")


@pytest.mark.parametrize(
    "params, result",
    [
        (
            (10, 20),
            {"iowait": (10, 20)},
        ),
        ({}, {}),
        (
            {"util": (50, 60)},
            {"util": (50, 60)},
        ),
    ],
)
def test_transform_cpu_iowait(params, result):
    assert transform_cpu_iowait(params) == result


@pytest.mark.parametrize(
    "params, result",
    [
        (
            {},
            {
                "default_params": {
                    "cpu_rescale_max": CPU_RESCALE_MAX_UNSPEC,
                }
            },
        ),
        (
            {
                "levels": (1, 1, 50, 50),
            },
            {
                "default_params": {
                    "levels": (1, 1, 50, 50),
                    "cpu_rescale_max": CPU_RESCALE_MAX_UNSPEC,
                },
            },
        ),
        (
            {
                "user": False,
                "default_params": {
                    "virtual_levels": (50, 100),
                },
            },
            {
                "user": False,
                "default_params": {
                    "virtual_levels": (50, 100),
                    "cpu_rescale_max": CPU_RESCALE_MAX_UNSPEC,
                },
            },
        ),
        (
            {
                "default_params": {"cpu_rescale_max": True},
                "match": "/usr/lib/firefox/firefox",
                "descr": "firefox",
                "user": False,
            },
            {
                "default_params": {"cpu_rescale_max": True},
                "match": "/usr/lib/firefox/firefox",
                "descr": "firefox",
                "user": False,
            },
        ),
        (
            # Legacy-style rule without default_params. This is from v1.5 or before, since the key
            # default_params was made non-optional in v1.6.
            {
                "perfdata": True,
                "levels": (1, 1, 20, 20),
                "descr": "cron",
                "match": "/usr/sbin/cron",
                "user": None,
            },
            {
                "default_params": {
                    "cpu_rescale_max": "cpu_rescale_max_unspecified",
                    "levels": (1, 1, 20, 20),
                },
                "descr": "cron",
                "match": "/usr/sbin/cron",
                "user": None,
            },
        ),
    ],
)
def test_convert_inventory_process(params, result):
    assert convert_inventory_processes(params) == result


@pytest.mark.parametrize(
    "params, result",
    [
        (
            ("sshd", 1, 1, 99, 200),
            {
                "process": "sshd",
                "user": None,
                "levels": (1, 1, 99, 200),
                "cpu_rescale_max": CPU_RESCALE_MAX_UNSPEC,
            },
        ),
        (
            ("sshd", "root", 2, 2, 5, 5),
            {
                "process": "sshd",
                "user": "root",
                "levels": (2, 2, 5, 5),
                "cpu_rescale_max": CPU_RESCALE_MAX_UNSPEC,
            },
        ),
        (
            {
                "user": "foo",
                "process": "/usr/bin/foo",
                "warnmin": 1,
                "okmin": 1,
                "okmax": 3,
                "warnmax": 3,
            },
            {
                "user": "foo",
                "process": "/usr/bin/foo",
                "levels": (1, 1, 3, 3),
                "cpu_rescale_max": CPU_RESCALE_MAX_UNSPEC,
            },
        ),
        (
            {
                "user": "foo",
                "process": "/usr/bin/foo",
                "levels": (1, 1, 3, 3),
                "cpu_rescale_max": True,
            },
            {
                "user": "foo",
                "process": "/usr/bin/foo",
                "levels": (1, 1, 3, 3),
                "cpu_rescale_max": True,
            },
        ),
    ],
)
def test_ps_cleanup_params(params, result):
    assert ps_cleanup_params(params) == result
