#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The host attributes a full replacement keeps although the request does not name them."""

from cmk.ccc.user import UserId
from cmk.gui.openapi.api_endpoints.host_config._utils import carry_over_unexposed_attributes
from cmk.gui.watolib.host_attributes import HostAttributes


def test_a_full_replacement_keeps_the_attributes_the_api_cannot_express() -> None:
    """Without this a PUT would drop configuration the request never saw."""
    stored = HostAttributes({"meta_data": {"created_by": UserId("cmkadmin")}, "alias": "old"})

    replaced = carry_over_unexposed_attributes(stored, HostAttributes({"alias": "new"}))

    assert replaced["alias"] == "new"
    assert replaced["meta_data"] == {"created_by": UserId("cmkadmin")}


def test_the_replacement_value_is_left_alone() -> None:
    """The caller keeps using it - the endpoints hand their request model straight to it."""
    attributes = HostAttributes({"alias": "new"})

    carry_over_unexposed_attributes(
        HostAttributes({"meta_data": {"created_by": UserId("cmkadmin")}}), attributes
    )

    assert attributes == HostAttributes({"alias": "new"})


def test_nothing_is_invented_for_a_host_that_has_none() -> None:
    replaced = carry_over_unexposed_attributes(HostAttributes({"alias": "old"}), HostAttributes())

    assert "meta_data" not in replaced
