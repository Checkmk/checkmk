#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress

import pytest

from cmk.core_helpers.cache import FileCacheGlobals

from cmk.base.sources import Source
from cmk.base.sources.agent import AgentSource
from cmk.base.sources.snmp import SNMPSource


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

    reset(FileCacheGlobals, "disabled", False)
    reset(FileCacheGlobals, "maybe", False)
    reset(FileCacheGlobals, "use_outdated", False)
    reset(Source, "use_outdated_persisted_sections", False)
    reset(FileCacheGlobals, "tcp_use_only_cache", False)
