#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest

from .local import local_test


@pytest.fixture(name="testfile")
def testfile_engine():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(make_yaml_config):
    section = "systemtime"
    make_yaml_config["global"]["sections"] = "systemtime"
    return make_yaml_config


@pytest.fixture(name="expected_output")
def expected_output_engine():
    return [r"<<<systemtime>>>", r"\d+"]


def test_section_systemtime(testconfig, expected_output, actual_output, testfile):
    local_test(expected_output, actual_output, testfile)
