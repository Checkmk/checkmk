#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.rest_api_client import ClientRegistry

from cmk.gui.watolib.timeperiods import load_timeperiod


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_get_all_time_periods(clients: ClientRegistry) -> None:
    clients.TimePeriod.get_all()


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_get_a_time_period(clients: ClientRegistry) -> None:
    clients.TimePeriod.get(time_period_id="24X7")


def test_openapi_create_invalid_name(clients: ClientRegistry) -> None:
    clients.TimePeriod.create(
        time_period_data={
            "name": "foo$%",
            "alias": "foobar",
            "active_time_ranges": [{"day": "all"}],
            "exceptions": [{"date": "2020-01-01"}],
        },
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_create_two_time_periods_same_name(clients: ClientRegistry) -> None:
    clients.TimePeriod.create(
        time_period_data={
            "name": "foo",
            "alias": "foobar",
            "active_time_ranges": [{"day": "all"}],
            "exceptions": [{"date": "2020-01-01"}],
        }
    )
    clients.TimePeriod.create(
        time_period_data={
            "name": "foo",
            "alias": "foobar",
            "active_time_ranges": [{"day": "all"}],
            "exceptions": [{"date": "2020-01-01"}],
        },
        expect_ok=False,
    ).assert_status_code(400)


def test_openapi_time_period_invalid_active_time_ranges(
    clients: ClientRegistry,
) -> None:
    clients.TimePeriod.create(
        time_period_data={
            "name": "foo",
            "alias": "foo",
            "active_time_ranges": [
                {"time_ranges": [{"start": "non-time-format", "end": "23:45:59"}]}
            ],
            "exceptions": [{"date": "2020-01-01"}],
        },
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_send_invalid_request(clients: ClientRegistry) -> None:
    clients.TimePeriod.create(
        time_period_data={
            "name": "foo",
            "alias": "foobar",
            "active_active_time_ranges": [{"day": "all"}],
            "exceptions_exceptions": [{"date": "2020-01-01"}],
        },
        expect_ok=False,
    )


def test_openapi_time_period_active_time_ranges(clients: ClientRegistry) -> None:
    resp1 = clients.TimePeriod.create(
        time_period_data={
            "name": "foo",
            "alias": "foo",
            "active_time_ranges": [{}],
            "exceptions": [{"date": "2020-01-01"}],
        },
    )

    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    assert resp1.json["extensions"]["active_time_ranges"] == [
        {"day": day, "time_ranges": [{"end": "23:59", "start": "00:00"}]} for day in days
    ]

    resp2 = clients.TimePeriod.create(
        time_period_data={
            "name": "bar",
            "alias": "bar",
            "active_time_ranges": [{"day": "tuesday"}],
            "exceptions": [{"date": "2020-01-01"}],
        },
    )

    assert resp2.json["extensions"]["active_time_ranges"] == [
        {"day": "tuesday", "time_ranges": [{"end": "23:59", "start": "00:00"}]}
    ]

    resp3 = clients.TimePeriod.create(
        time_period_data={
            "name": "times_only",
            "alias": "times_only",
            "active_time_ranges": [{"time_ranges": [{"start": "18:11:34", "end": "23:45:59"}]}],
            "exceptions": [{"date": "2020-01-01"}],
        },
    )

    assert resp3.json["extensions"]["active_time_ranges"] == [
        {"day": day, "time_ranges": [{"start": "18:11", "end": "23:45"}]} for day in days
    ]


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_time_period_time_ranges(clients: ClientRegistry) -> None:
    clients.TimePeriod.create(
        time_period_data={
            "name": "foo",
            "alias": "foobar",
            "active_time_ranges": [{"day": "all"}],
            "exceptions": [{"date": "2020-01-01"}],
        }
    )

    resp1 = clients.TimePeriod.edit(
        time_period_id="foo",
        time_period_data={
            "active_time_ranges": [{"day": "friday"}],
            "exceptions": [
                {"date": "2023-02-02", "time_ranges": [{"start": "18:32", "end": "21:15"}]},
            ],
        },
    )
    assert resp1.json["extensions"]["active_time_ranges"] == [
        {"day": "friday", "time_ranges": [{"end": "23:59", "start": "00:00"}]}
    ]
    assert resp1.json["extensions"]["exceptions"][0] == {
        "date": "2023-02-02",
        "time_ranges": [{"start": "18:32", "end": "21:15"}],
    }

    resp2 = clients.TimePeriod.edit(
        time_period_id="foo",
        time_period_data={
            "active_time_ranges": [
                {"day": "saturday", "time_ranges": [{"start": "18:11", "end": "23:45"}]}
            ],
            "exceptions": [{"date": "2023-02-03"}],
        },
    )

    assert resp2.json["extensions"]["active_time_ranges"][0] == {
        "day": "saturday",
        "time_ranges": [{"start": "18:11", "end": "23:45"}],
    }
    assert resp2.json["extensions"]["exceptions"][0] == {"date": "2023-02-03", "time_ranges": []}


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_time_period(clients: ClientRegistry) -> None:
    clients.TimePeriod.create(
        time_period_data={
            "name": "foo",
            "alias": "foobar",
            "active_time_ranges": [
                {"day": "all", "time_ranges": [{"start": "12:00", "end": "14:00"}]}
            ],
            "exceptions": [
                {"date": "2020-01-01", "time_ranges": [{"start": "14:00", "end": "18:00"}]}
            ],
        },
    )

    clients.TimePeriod.edit(
        time_period_id="foo",
        time_period_data={
            "alias": "foo",
            "active_time_ranges": [
                {"day": "monday", "time_ranges": [{"start": "12:00", "end": "14:00"}]}
            ],
        },
    )
    clients.TimePeriod.get(time_period_id="foo")


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_time_period_collection(clients: ClientRegistry) -> None:
    clients.TimePeriod.create(
        time_period_data={
            "name": "foo",
            "alias": "foobar",
            "active_time_ranges": [
                {"day": "all", "time_ranges": [{"start": "12:00", "end": "14:00"}]}
            ],
            "exceptions": [
                {"date": "2020-01-01", "time_ranges": [{"start": "14:00", "end": "18:00"}]}
            ],
        },
    )

    resp = clients.TimePeriod.get_all()
    assert len(resp.json["value"]) == 2

    clients.TimePeriod.delete(time_period_id="foo")
    resp = clients.TimePeriod.get_all()
    assert len(resp.json["value"]) == 1


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_timeperiod_builtin(clients: ClientRegistry) -> None:
    resp = clients.TimePeriod.edit(
        time_period_id="24X7",
        time_period_data={
            "alias": "foo",
            "active_time_ranges": [
                {"day": "monday", "time_ranges": [{"start": "12:00", "end": "14:00"}]}
            ],
        },
        expect_ok=False,
    )
    assert resp.status_code == 405


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_timeperiod_unmodified_update(clients: ClientRegistry) -> None:
    expected_data = {
        "active_time_ranges": [
            {
                "day": "monday",
                "time_ranges": [
                    {"end": "12:30", "start": "08:00"},
                    {"end": "17:00", "start": "13:30"},
                ],
            },
            {
                "day": "tuesday",
                "time_ranges": [
                    {"end": "12:30", "start": "08:00"},
                    {"end": "17:00", "start": "13:30"},
                ],
            },
            {
                "day": "wednesday",
                "time_ranges": [
                    {"end": "12:30", "start": "08:00"},
                    {"end": "17:00", "start": "13:30"},
                ],
            },
            {
                "day": "thursday",
                "time_ranges": [
                    {"end": "12:30", "start": "08:00"},
                    {"end": "17:00", "start": "13:30"},
                ],
            },
            {
                "day": "friday",
                "time_ranges": [
                    {"end": "12:30", "start": "08:00"},
                    {"end": "17:00", "start": "13:30"},
                ],
            },
            {
                "day": "saturday",
                "time_ranges": [
                    {"end": "12:30", "start": "08:00"},
                    {"end": "17:00", "start": "13:30"},
                ],
            },
            {
                "day": "sunday",
                "time_ranges": [
                    {"end": "12:30", "start": "08:00"},
                    {"end": "17:00", "start": "13:30"},
                ],
            },
        ],
        "alias": "Test All days 8x5",
        "exceptions": [{"date": "2021-04-01", "time_ranges": [{"end": "15:00", "start": "14:00"}]}],
        "exclude": [],
    }
    resp = clients.TimePeriod.create(
        time_period_data={
            "name": "test_all_8x5",
            "active_time_ranges": [
                {
                    "day": "all",
                    "time_ranges": [
                        {"end": "12:30", "start": "08:00"},
                        {"end": "17:00", "start": "13:30"},
                    ],
                }
            ],
            "alias": "Test All days 8x5",
            "exceptions": [
                {"date": "2021-04-01", "time_ranges": [{"end": "15:00", "start": "14:00"}]}
            ],
        },
    )
    assert resp.json["extensions"] == expected_data

    resp = clients.TimePeriod.get(time_period_id="test_all_8x5")
    assert resp.json["extensions"] == expected_data

    resp2 = clients.TimePeriod.edit(
        time_period_id="test_all_8x5",
        time_period_data={},
    )
    assert resp2.json["extensions"] == expected_data


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_timeperiod_complex_update(clients: ClientRegistry) -> None:
    clients.TimePeriod.create(
        time_period_data={
            "name": "test_all_8x5",
            "active_time_ranges": [
                {
                    "day": "all",
                    "time_ranges": [
                        {"end": "12:30", "start": "08:00"},
                        {"end": "17:00", "start": "13:30"},
                    ],
                }
            ],
            "alias": "Test All days 8x5",
            "exceptions": [
                {"date": "2021-04-01", "time_ranges": [{"end": "15:00", "start": "14:00"}]}
            ],
        },
    )
    clients.TimePeriod.edit(
        time_period_id="test_all_8x5",
        time_period_data={
            "active_time_ranges": [
                {
                    "day": "all",
                    "time_ranges": [
                        {"end": "12:30", "start": "08:00"},
                        {"end": "17:00", "start": "13:30"},
                    ],
                }
            ],
            "alias": "Test All days 8x5 z",
            "exceptions": [
                {"date": "2021-04-01", "time_ranges": [{"end": "15:00", "start": "14:00"}]}
            ],
        },
    )

    internal_timeperiod = load_timeperiod("test_all_8x5")
    assert internal_timeperiod == {
        "alias": "Test All days 8x5 z",
        "2021-04-01": [("14:00", "15:00")],
        "monday": [("08:00", "12:30"), ("13:30", "17:00")],
        "tuesday": [("08:00", "12:30"), ("13:30", "17:00")],
        "wednesday": [("08:00", "12:30"), ("13:30", "17:00")],
        "thursday": [("08:00", "12:30"), ("13:30", "17:00")],
        "friday": [("08:00", "12:30"), ("13:30", "17:00")],
        "saturday": [("08:00", "12:30"), ("13:30", "17:00")],
        "sunday": [("08:00", "12:30"), ("13:30", "17:00")],
        "exclude": [],
    }


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_timeperiod_excluding_exclude(clients: ClientRegistry) -> None:
    assert clients.TimePeriod.create(
        time_period_data={
            "name": "test_all_8x5_2",
            "alias": "Test All days 8x5 - 2",
            "active_time_ranges": [
                {
                    "day": "monday",
                    "time_ranges": [
                        {"end": "12:30", "start": "08:00"},
                        {"end": "17:00", "start": "13:30"},
                    ],
                },
            ],
            "exceptions": [],
        },
    ).json["extensions"] == {
        "active_time_ranges": [
            {
                "day": "monday",
                "time_ranges": [
                    {"end": "12:30", "start": "08:00"},
                    {"end": "17:00", "start": "13:30"},
                ],
            }
        ],
        "alias": "Test All days 8x5 - 2",
        "exceptions": [],
        "exclude": [],
    }


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_timeperiod_exclude_builtin(clients: ClientRegistry) -> None:
    clients.TimePeriod.create(
        time_period_data={
            "name": "exclude_test_1",
            "alias": "exclude_test_alias_1",
            "active_time_ranges": [
                {
                    "day": "monday",
                    "time_ranges": [
                        {"end": "12:30", "start": "08:00"},
                        {"end": "17:00", "start": "13:30"},
                    ],
                },
            ],
            "exceptions": [],
            "exclude": [],
        },
    )

    clients.TimePeriod.create(
        time_period_data={
            "name": "exclude_test_2",
            "alias": "exclude_test_alias_2",
            "active_time_ranges": [
                {
                    "day": "monday",
                    "time_ranges": [
                        {"end": "12:30", "start": "08:00"},
                        {"end": "17:00", "start": "13:30"},
                    ],
                },
            ],
            "exceptions": [],
            "exclude": ["exclude_test_alias_1"],
        },
    )

    assert clients.TimePeriod.create(
        expect_ok=False,
        time_period_data={
            "name": "exclude_test_3",
            "alias": "exclude_test_alias_3",
            "active_time_ranges": [
                {
                    "day": "monday",
                    "time_ranges": [
                        {"end": "12:30", "start": "08:00"},
                        {"end": "17:00", "start": "13:30"},
                    ],
                },
            ],
            "exceptions": [],
            "exclude": ["Always"],
        },
    ).assert_status_code(400)


def test_openapi_delete_dependent_downtime(clients: ClientRegistry) -> None:
    clients.TimePeriod.create(
        time_period_data={
            "name": "time_period_1",
            "alias": "Time Period 1",
            "active_time_ranges": [
                {
                    "day": "monday",
                    "time_ranges": [{"start": "14:00", "end": "18:00"}],
                },
            ],
            "exceptions": [],
            "exclude": [],
        },
    )

    clients.TimePeriod.create(
        time_period_data={
            "name": "time_period_2",
            "alias": "Time Period 2",
            "active_time_ranges": [
                {
                    "day": "monday",
                    "time_ranges": [{"start": "12:00", "end": "14:00"}],
                },
            ],
            "exceptions": [],
            "exclude": ["Time Period 1"],
        },
    )

    resp = clients.TimePeriod.delete("time_period_1", expect_ok=False).assert_status_code(409)
    assert resp.json["detail"].endswith("Time Period 2 (excluded)).")
