#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.gui.inventory import (
    load_delta_tree,
    load_tree,
)
from cmk.inventory.delta import ImmutableDeltaTree
from cmk.inventory.filtering import SDFilterChoice
from cmk.inventory.trees import ImmutableTree


@pytest.mark.usefixtures("request_context")
def test_load_tree_of_a_row_without_a_host_is_empty() -> None:
    assert load_tree(host_name=HostName(""), raw_status_data_tree=b"") == ImmutableTree()


class FakeHistoryStore:
    def load_delta_tree_at(
        self,
        _host_name: HostName,
        _timestamp: int,
        *,
        delta_tree_filters: Sequence[SDFilterChoice] | None,  # noqa: ARG002 - keyword of the protocol
    ) -> tuple[ImmutableDeltaTree, Sequence[str]] | None:
        return None


@pytest.mark.usefixtures("request_context")
def test_load_delta_tree_without_a_history_entry_at_the_timestamp_fails() -> None:
    with pytest.raises(MKGeneralException, match="Found no history entry at the time of '-1'"):
        load_delta_tree(FakeHistoryStore(), HostName("inv-host"), -1)
