#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress

import pytest

from cmk.core_helpers.cache import FileCacheFactory

from cmk.base.sources import Source
from cmk.base.sources.agent import AgentSource
from cmk.base.sources.snmp import SNMPSource
from cmk.base.sources.tcp import TCPSource


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
    delete(AgentSource, "use_outdated_persisted_sections")
    delete(SNMPSource, "use_outdated_persisted_sections")

    reset(FileCacheFactory, "disabled", False)
    reset(FileCacheFactory, "maybe", False)
    reset(FileCacheFactory, "use_outdated", False)
    reset(Source, "use_outdated_persisted_sections", False)
    reset(TCPSource, "use_only_cache", False)
