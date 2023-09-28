#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest

from .local import local_test


@pytest.fixture(name="testfile")
def testfile_engine():
    return os.path.basename(__file__)


@pytest.fixture(name="testconfig")
def fixture_testconfig(make_yaml_config):
    make_yaml_config["global"]["sections"] = "systemtime"
    return make_yaml_config


@pytest.fixture(name="expected_output")
def expected_output_engine():
    return [r"<<<systemtime>>>", r"\d+"]


def test_section_systemtime(  # type: ignore[no-untyped-def]
    testconfig, expected_output, actual_output, testfile
) -> None:
    local_test(expected_output, actual_output, testfile)
