#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The host attributes the REST API does not model, and what a full replacement does to them."""

from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId
from cmk.gui.openapi.api_endpoints.host_config._utils import (
    carry_over_unexposed_attributes,
    UNEXPOSED_HOST_ATTRIBUTES,
    UNREMOVABLE_HOST_ATTRIBUTES,
)
from cmk.gui.watolib.host_attributes import HostAttributes


def test_relations_are_not_managed_through_the_api() -> None:
    """They are stored on both hosts of a relation, so the API cannot set one side alone."""
    assert "relations" in UNEXPOSED_HOST_ATTRIBUTES


def test_only_a_relation_is_refused_to_be_removed() -> None:
    """Removing a relation would leave its other half behind; "meta_data" is carried over a
    replacement but stays as removable as it was before relations existed."""
    assert UNREMOVABLE_HOST_ATTRIBUTES == ("relations",)


def test_a_full_replacement_keeps_the_attributes_the_api_cannot_express() -> None:
    """Without this a PUT would drop configuration the request never saw - and for relations it
    would leave the other half of every relation on the related host without its counterpart."""
    stored = HostAttributes(
        {
            "relations": [{"kind": "management", "direction": "child", "host": HostName("os1")}],
            "meta_data": {"created_by": UserId("cmkadmin")},
            "alias": "old",
        }
    )

    replaced = carry_over_unexposed_attributes(stored, HostAttributes({"alias": "new"}))

    assert replaced["alias"] == "new"
    assert replaced["relations"] == [
        {"kind": "management", "direction": "child", "host": HostName("os1")}
    ]
    assert replaced["meta_data"] == {"created_by": UserId("cmkadmin")}


def test_the_replacement_value_is_left_alone() -> None:
    """The caller keeps using it - the endpoints hand their request model straight to it."""
    attributes = HostAttributes({"alias": "new"})

    carry_over_unexposed_attributes(
        HostAttributes(
            {"relations": [{"kind": "management", "direction": "child", "host": HostName("os1")}]}
        ),
        attributes,
    )

    assert attributes == HostAttributes({"alias": "new"})


def test_nothing_is_invented_for_a_host_that_has_none() -> None:
    replaced = carry_over_unexposed_attributes(HostAttributes({"alias": "old"}), HostAttributes())

    assert "relations" not in replaced
    assert "meta_data" not in replaced
