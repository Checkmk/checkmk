#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.utils.paths

import cmk.core_helpers.paths as paths


@pytest.fixture(name="serial")
def serial_fixture():
    yield paths.ConfigSerial("1")
    (cmk.utils.paths.core_helper_config_dir / "serial.mk").unlink(missing_ok=True)


def test_next_helper_config_serial(serial):
    serial = paths.next_helper_config_serial(serial)
    assert serial == paths.current_helper_config_serial() == paths.ConfigSerial("2")

    serial = paths.next_helper_config_serial(serial)
    assert serial == paths.current_helper_config_serial() == paths.ConfigSerial("3")

    serial = paths.next_helper_config_serial(serial)
    assert serial == paths.current_helper_config_serial() == paths.ConfigSerial("4")
