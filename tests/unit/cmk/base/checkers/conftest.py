#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress

import pytest  # type: ignore[import]

from cmk.base.checkers import ABCChecker, FileCacheConfigurer
from cmk.base.checkers.agent import AgentChecker
from cmk.base.checkers.snmp import SNMPChecker
from cmk.base.checkers.tcp import TCPSource


@pytest.fixture(autouse=True)
def reset_mutable_global_state():
    def reset(cls, attr, value):
        # Make sure we are not *adding* any field.
        assert hasattr(cls, attr)
        setattr(cls, attr, value)

    def delete(cls, attr):
        with suppress(AttributeError):
            delattr(cls, attr)

    yield
    delete(AgentChecker, "_use_outdated_persisted_sections")
    delete(SNMPChecker, "_use_outdated_persisted_sections")

    reset(FileCacheConfigurer, "disabled", False)
    reset(FileCacheConfigurer, "maybe", False)
    reset(FileCacheConfigurer, "use_outdated", False)
    reset(ABCChecker, "_use_outdated_persisted_sections", False)
    reset(TCPSource, "use_only_cache", False)
