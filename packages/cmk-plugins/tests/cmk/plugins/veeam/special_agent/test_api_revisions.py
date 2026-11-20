#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.veeam.special_agent.api_revisions import ApiRevision, in_section_format


def _page(*items: dict[str, object]) -> dict[str, object]:
    return {"data": list(items), "pagination": {"total": len(items)}}


def test_each_item_of_a_rev2_list_is_converted() -> None:
    page = _page({"id": "1", "type": "Snapshot"}, {"id": "2", "type": "CDP"})

    assert in_section_format(ApiRevision.V1_3_REV2, "/api/v1/replicas?skip=0", page) == _page(
        {"id": "1", "type": "Regular"}, {"id": "2", "type": "CDP"}
    )


def test_a_rev2_object_is_converted() -> None:
    installed = {"instanceLicenseSummary": {"expirationDate": "2027-02-23T00:00:00Z"}}

    assert in_section_format(ApiRevision.V1_3_REV2, "/api/v1/license", installed) == {
        "expirationDate": "2027-02-23T00:00:00Z",
        **installed,
    }


def test_a_rev1_response_is_not_converted() -> None:
    page = _page({"id": "1", "type": "Snapshot"})

    assert in_section_format(ApiRevision.V1_3_REV1, "/api/v1/replicas", page) == page


def test_a_rev2_response_of_an_endpoint_rev2_did_not_change_is_not_converted() -> None:
    body = {"name": "veeam-server"}

    assert in_section_format(ApiRevision.V1_3_REV2, "/api/v1/serverInfo", body) == body
