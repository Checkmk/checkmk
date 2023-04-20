#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access
import pytest

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import HostName

from cmk.base import item_state
from cmk.base.api.agent_based import value_store

_TEST_KEY = ("check", "item", "user-key")


def test_item_state_prefix_required(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        value_store._global_state,
        "_active_host_value_store",
        value_store.ValueStoreManager(HostName("test-host")),
    )
    # we *must* set a prefix:
    with pytest.raises(MKGeneralException):
        _ = item_state.get_item_state("user-key", None)
