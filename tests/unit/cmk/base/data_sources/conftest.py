#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress

import pytest  # type: ignore[import]

from cmk.base.data_sources import ABCDataSource
from cmk.base.data_sources.agent import AgentDataSource
from cmk.base.data_sources.snmp import SNMPDataSource


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
    delete(AgentDataSource, "_use_outdated_cache_file")
    delete(AgentDataSource, "_use_outdated_persisted_sections")
    delete(SNMPDataSource, "_no_cache")
    delete(SNMPDataSource, "_use_outdated_persisted_sections")

    reset(ABCDataSource, "_no_cache", False)
    reset(ABCDataSource, "_may_use_cache_file", False)
    reset(ABCDataSource, "_use_outdated_cache_file", False)
    reset(ABCDataSource, "_use_outdated_persisted_sections", False)
