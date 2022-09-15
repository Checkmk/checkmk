#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# mypy: disallow_untyped_defs
import datetime

import pytest

from cmk.base.plugins.agent_based import gcp_health
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

# This is an edited incident report from google to facilitate testing. It follows the published schema, but leaves out fields not used by the check.
# https://status.cloud.google.com/incidents.schema.json
STRING_TABLE: StringTable = [
    ['{"date": "2022-07-20"}'],
    [
        r"""[
    {
        "id": "mLBHeCxhRia17anXCSX1",
        "number": "14970871909327597787",
        "begin": "2022-07-19T14:17:00+00:00",
        "created": "2022-07-20T13:39:01+00:00",
        "modified": "2022-07-20T13:46:32+00:00",
        "external_desc": "Secret Manager experienced service unavailability in europe-west2",
        "most_recent_update": {
            "created": "2022-07-20T13:44:35+00:00",
            "modified": "2022-07-20T13:44:36+00:00",
            "when": "2022-07-20T13:44:35+00:00",
            "text": "We experienced an issue with Secret Manager beginning at Tuesday, 2022-07-19 07:17 US/Pacific.\nSelf-diagnosis: Customers who had their secrets exclusively in europe-west2 or attempted to create a secret in europe-west2 were seeing UNAVAILABLE / 5xx errors\nThe issue has been resolved for all affected projects as of Tuesday, 2022-07-19 08:47 US/Pacific.\nWe thank you for your patience while we worked on resolving the issue.",
            "status": "SERVICE_OUTAGE",
            "affected_locations": [{"title": "London (europe-west2)", "id": "europe-west2"}]
        },
        "status_impact": "SERVICE_DISRUPTION",
        "severity": "medium",
        "service_key": "kzGfErQK3HzkFhptoeHH",
        "service_name": "Secret Manager",
        "affected_products": [{"title": "Secret Manager", "id": "kzGfErQK3HzkFhptoeHH"}],
        "uri": "incidents/mLBHeCxhRia17anXCSX1",
        "currently_affected_locations": [],
        "previously_affected_locations": [{"title": "London (europe-west2)", "id": "europe-west2"}]
    },
    {
        "id": "mLBHeCxhRia17anXCSX1",
        "number": "14970871909327597787",
        "begin": "2022-07-09T14:17:00+00:00",
        "created": "2022-07-20T13:39:01+00:00",
        "end": "2022-07-10T15:47:00+00:00",
        "modified": "2022-07-20T13:46:32+00:00",
        "external_desc": "Secret Manager experienced service unavailability in europe-west2",
        "most_recent_update": {
            "created": "2022-07-20T13:44:35+00:00",
            "modified": "2022-07-20T13:44:36+00:00",
            "when": "2022-07-20T13:44:35+00:00",
            "text": "We experienced an issue with Secret Manager beginning at Tuesday, 2022-07-19 07:17 US/Pacific.\nSelf-diagnosis: Customers who had their secrets exclusively in europe-west2 or attempted to create a secret in europe-west2 were seeing UNAVAILABLE / 5xx errors\nThe issue has been resolved for all affected projects as of Tuesday, 2022-07-19 08:47 US/Pacific.\nWe thank you for your patience while we worked on resolving the issue.",
            "status": "AVAILABLE",
            "affected_locations": [{"title": "London (europe-west2)", "id": "europe-west2"}, {"title": "Global", "id": "global"}]
        },
        "status_impact": "SERVICE_DISRUPTION",
        "severity": "medium",
        "service_key": "kzGfErQK3HzkFhptoeHH",
        "service_name": "Secret Manager",
        "affected_products": [{"title": "Secret Manager", "id": "kzGfErQK3HzkFhptoeHH"},{"title": "Google Cloud SQL", "id": "hV87iK5DcEXKgWU2kDri"}],
        "uri": "incidents/mLBHeCxhRia17anXCSX1",
        "currently_affected_locations": [],
        "previously_affected_locations": [{"title": "London (europe-west2)", "id": "europe-west2"}, {"title": "Global", "id": "global"}]
    },
    {
        "id": "mLBHeCxhRia17anXCSX1",
        "number": "14970871909327597787",
        "begin": "2022-07-19T14:17:00+00:00",
        "created": "2022-07-20T13:39:01+00:00",
        "end": "2022-07-19T15:47:00+00:00",
        "modified": "2022-07-19T13:46:32+00:00",
        "external_desc": "Secret Manager experienced service\n unavailability in europe-west1",
        "most_recent_update": {
            "created": "2022-07-20T13:44:35+00:00",
            "modified": "2022-07-20T13:44:36+00:00",
            "when": "2022-07-20T13:44:35+00:00",
            "text": "We experienced an issue with Secret Manager beginning at Tuesday, 2022-07-19 07:17 US/Pacific.\nSelf-diagnosis: Customers who had their secrets exclusively in europe-west1 or attempted to create a secret in europe-west1 were seeing UNAVAILABLE / 5xx errors\nThe issue has been resolved for all affected projects as of Tuesday, 2022-07-19 08:47 US/Pacific.\nWe thank you for your patience while we worked on resolving the issue.",
            "status": "AVAILABLE",
            "affected_locations": [{"title": "London (europe-west1)", "id": "europe-west1"}]
        },
        "status_impact": "SERVICE_DISRUPTION",
        "severity": "medium",
        "service_key": "kzGfErQK3HzkFhptoeHH",
        "service_name": "Secret Manager",
        "affected_products": [{"title": "Secret Manager", "id": "kzGfErQK3HzkFhptoeHH"}],
        "uri": "incidents/mLBHeCxhRia17anXCSX1",
        "currently_affected_locations": [],
        "previously_affected_locations": [{"title": "London (europe-west1)", "id": "europe-west1"}, {"title": "Global", "id": "global"}]
    }
]"""
    ],
]


@pytest.fixture(name="section", scope="module")
def _section() -> gcp_health.Section:
    return gcp_health.parse(STRING_TABLE)


def test_parsing(section: gcp_health.Section) -> None:
    assert section.date == datetime.datetime(
        year=2022, month=7, day=20, tzinfo=datetime.timezone.utc
    )
    assert section.incidents == [
        gcp_health.Incident(
            affected_products=["Secret Manager"],
            affected_location=["europe-west2"],
            begin=datetime.datetime(2022, 7, 19, 14, 17, tzinfo=datetime.timezone.utc),
            end=None,
            description="Secret Manager experienced service unavailability in europe-west2",
            is_on_going=True,
            uri="incidents/mLBHeCxhRia17anXCSX1",
        ),
        gcp_health.Incident(
            affected_products=["Secret Manager", "Google Cloud SQL"],
            affected_location=["europe-west2", "global"],
            begin=datetime.datetime(2022, 7, 9, 14, 17, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2022, 7, 10, 15, 47, tzinfo=datetime.timezone.utc),
            description="Secret Manager experienced service unavailability in europe-west2",
            is_on_going=False,
            uri="incidents/mLBHeCxhRia17anXCSX1",
        ),
        gcp_health.Incident(
            affected_products=["Secret Manager"],
            affected_location=["europe-west1"],
            begin=datetime.datetime(2022, 7, 19, 14, 17, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2022, 7, 19, 15, 47, tzinfo=datetime.timezone.utc),
            description="Secret Manager experienced service unavailability in " "europe-west1",
            is_on_going=False,
            uri="incidents/mLBHeCxhRia17anXCSX1",
        ),
    ]


def test_no_indicents() -> None:
    section = gcp_health.Section(date=datetime.datetime(year=1999, month=3, day=12), incidents=[])
    results = list(
        gcp_health.check(
            params={"time_window": 24, "region_filter": [], "product_filter": []},
            section=section,
        )
    )
    assert results == [
        Result(
            state=State.OK,
            summary="No known incident in the past 24 days https://status.cloud.google.com/",
        ),
    ]


def test_one_result_per_incident(section: gcp_health.Section) -> None:
    results = list(
        gcp_health.check(
            params={"time_window": 24, "region_filter": [], "product_filter": []},
            section=section,
        )
    )
    assert results == [
        Result(
            state=State.CRIT,
            summary="Secret Manager experienced service unavailability in europe-west2",
            details="Products: Secret Manager \n Locations: europe-west2, \n https://status.cloud.google.com/incidents/mLBHeCxhRia17anXCSX1",
        ),
        Result(
            state=State.WARN,
            summary="Secret Manager experienced service unavailability in europe-west2",
            details="Products: Secret Manager, Google Cloud SQL \n Locations: europe-west2, global, \n https://status.cloud.google.com/incidents/mLBHeCxhRia17anXCSX1",
        ),
        Result(
            state=State.WARN,
            summary="Secret Manager experienced service unavailability in europe-west1",
            details="Products: Secret Manager \n Locations: europe-west1, \n https://status.cloud.google.com/incidents/mLBHeCxhRia17anXCSX1",
        ),
    ]


def test_indicents_in_selected_time_window(section: gcp_health.Section) -> None:
    results = list(
        gcp_health.check(
            params={"time_window": 2, "region_filter": [], "product_filter": []},
            section=section,
        )
    )
    assert results == [
        # always show ongoing incidents
        Result(
            state=State.CRIT,
            summary="Secret Manager experienced service unavailability in europe-west2",
            details="Products: Secret Manager \n Locations: europe-west2, \n https://status.cloud.google.com/incidents/mLBHeCxhRia17anXCSX1",
        ),
        Result(
            state=State.WARN,
            summary="Secret Manager experienced service unavailability in europe-west1",
            details="Products: Secret Manager \n Locations: europe-west1, \n https://status.cloud.google.com/incidents/mLBHeCxhRia17anXCSX1",
        ),
    ]


def test_product_filter(section: gcp_health.Section) -> None:
    results = list(
        gcp_health.check(
            params={
                "time_window": 24,
                "region_filter": [],
                "product_filter": [
                    "Cloud",
                ],
            },
            section=section,
        )
    )
    assert results == [
        Result(
            state=State.WARN,
            summary="Secret Manager experienced service unavailability in europe-west2",
            details="Products: Secret Manager, Google Cloud SQL \n Locations: europe-west2, global, \n https://status.cloud.google.com/incidents/mLBHeCxhRia17anXCSX1",
        ),
    ]


def test_region_filter(section: gcp_health.Section) -> None:
    results = list(
        gcp_health.check(
            params={"time_window": 24, "region_filter": ["europe-west1"], "product_filter": []},
            section=section,
        )
    )
    # global is special. It is the set of all regions. So it should always come through
    assert results == [
        Result(
            state=State.WARN,
            summary="Secret Manager experienced service unavailability in europe-west2",
            details="Products: Secret Manager, Google Cloud SQL \n Locations: europe-west2, global, \n https://status.cloud.google.com/incidents/mLBHeCxhRia17anXCSX1",
        ),
        Result(
            state=State.WARN,
            summary="Secret Manager experienced service unavailability in europe-west1",
            details="Products: Secret Manager \n Locations: europe-west1, \n https://status.cloud.google.com/incidents/mLBHeCxhRia17anXCSX1",
        ),
    ]
