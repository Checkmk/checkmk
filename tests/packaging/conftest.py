#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest


# TODO: Better hand over arguments using pytest mechanisms (http://doc.pytest.org/en/latest/example/parametrize.html)
@pytest.fixture(scope="module")
def package_path():
    path = os.environ.get("PACKAGE_PATH")
    if not path:
        raise Exception(
            "PACKAGE_PATH environment variable pointing to the package to be tested is missing"
        )
    return path


# TODO: Better hand over arguments using pytest mechanisms (http://doc.pytest.org/en/latest/example/parametrize.html)
@pytest.fixture(scope="module")
def cmk_version():
    version = os.environ.get("VERSION")
    if not version:
        raise Exception("VERSION environment variable, e.g. 2016.12.22, is missing")
    return version
