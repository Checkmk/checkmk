# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.rest_api_client import TimePeriodTestClient

from cmk.gui.watolib.timeperiods import load_timeperiod


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_get_all_time_periods(timeperiod_client: TimePeriodTestClient) -> None:
    timeperiod_client.get_all()


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_get_a_time_period(timeperiod_client: TimePeriodTestClient) -> None:
    timeperiod_client.get(time_period_id="24X7")


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_create_two_time_periods_same_name(timeperiod_client: TimePeriodTestClient) -> None:
    timeperiod_client.create(
        time_period_data={
            "name": "foo",
            "alias": "foobar",
            "active_time_ranges": [{"day": "all"}],
            "exceptions": [{"date": "2020-01-01"}],
        }
    )
    timeperiod_client.create(
        time_period_data={
            "name": "foo",
            "alias": "foobar",
            "active_time_ranges": [{"day": "all"}],
            "exceptions": [{"date": "2020-01-01"}],
        },
        expect_ok=False,
    ).assert_status_code(400)


def test_openapi_time_period_invalid_active_time_ranges(
    timeperiod_client: TimePeriodTestClient,
) -> None:
    timeperiod_client.create(
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


def test_openapi_time_period_active_time_ranges(timeperiod_client: TimePeriodTestClient) -> None:
    resp1 = timeperiod_client.create(
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

    resp2 = timeperiod_client.create(
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

    resp3 = timeperiod_client.create(
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
def test_openapi_time_period_time_ranges(timeperiod_client: TimePeriodTestClient) -> None:
    timeperiod_client.create(
        time_period_data={
            "name": "foo",
            "alias": "foobar",
            "active_time_ranges": [{"day": "all"}],
            "exceptions": [{"date": "2020-01-01"}],
        }
    )

    resp1 = timeperiod_client.edit(
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

    resp2 = timeperiod_client.edit(
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
def test_openapi_time_period(timeperiod_client: TimePeriodTestClient) -> None:
    timeperiod_client.create(
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

    timeperiod_client.edit(
        time_period_id="foo",
        time_period_data={
            "alias": "foo",
            "active_time_ranges": [
                {"day": "monday", "time_ranges": [{"start": "12:00", "end": "14:00"}]}
            ],
        },
    )
    timeperiod_client.get(time_period_id="foo")


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_time_period_collection(timeperiod_client: TimePeriodTestClient) -> None:
    timeperiod_client.create(
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

    resp = timeperiod_client.get_all()
    assert len(resp.json["value"]) == 2

    timeperiod_client.delete(time_period_id="foo")
    resp = timeperiod_client.get_all()
    assert len(resp.json["value"]) == 1


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_timeperiod_builtin(timeperiod_client: TimePeriodTestClient) -> None:
    resp = timeperiod_client.edit(
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

    resp = timeperiod_client.delete(time_period_id="24X7", expect_ok=False).assert_status_code(405)
    assert resp.json["title"] == "Builtin time periods can not be deleted"
    assert resp.json["detail"] == "The built-in time period '24X7' cannot be deleted."


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_timeperiod_unmodified_update(timeperiod_client: TimePeriodTestClient) -> None:
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
    resp = timeperiod_client.create(
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

    resp = timeperiod_client.get(time_period_id="test_all_8x5")
    assert resp.json["extensions"] == expected_data

    resp2 = timeperiod_client.edit(
        time_period_id="test_all_8x5",
        time_period_data={},
    )
    assert resp2.json["extensions"] == expected_data


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_timeperiod_complex_update(timeperiod_client: TimePeriodTestClient) -> None:
    timeperiod_client.create(
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
    timeperiod_client.edit(
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
def test_openapi_timeperiod_excluding_exclude(timeperiod_client: TimePeriodTestClient) -> None:
    assert timeperiod_client.create(
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
def test_openapi_timeperiod_exclude_builtin(timeperiod_client: TimePeriodTestClient) -> None:
    timeperiod_client.create(
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

    timeperiod_client.create(
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

    assert timeperiod_client.create(
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


def test_openapi_delete_dependent_downtime(timeperiod_client: TimePeriodTestClient) -> None:
    timeperiod_client.create(
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

    timeperiod_client.create(
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

    resp = timeperiod_client.delete("time_period_1", expect_ok=False).assert_status_code(409)
    assert resp.json["detail"].endswith("Time Period 2 (excluded)).")


def test_openapi_exclude_field(timeperiod_client: TimePeriodTestClient) -> None:
    time_period_1: dict[str, object] = {
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
    }

    dependent_time_period: dict[str, object] = {
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
    }

    name_dependent_time_period: dict[str, object] = {
        "name": "time_period_3",
        "alias": "Time Period 3",
        "active_time_ranges": [
            {
                "day": "monday",
                "time_ranges": [{"start": "12:00", "end": "14:00"}],
            },
        ],
        "exceptions": [],
        "exclude": ["time_period_1"],
    }

    referenced_time_period_does_not_exist = timeperiod_client.create(
        time_period_data=dependent_time_period, expect_ok=False
    ).assert_status_code(400)
    assert (
        referenced_time_period_does_not_exist.json["detail"]
        == "These fields have problems: exclude"
    )
    assert referenced_time_period_does_not_exist.json["title"] == "Bad Request"
    assert "exclude" in referenced_time_period_does_not_exist.json["fields"]
    assert len(referenced_time_period_does_not_exist.json["fields"]["exclude"]) == 1
    assert referenced_time_period_does_not_exist.json["fields"]["exclude"]["0"] == [
        "Time period alias does not exist: 'Time Period 1'"
    ]

    timeperiod_client.create(time_period_data=time_period_1)
    timeperiod_client.create(time_period_data=dependent_time_period)
    response_dependent_time_period = timeperiod_client.get(time_period_id="time_period_2")
    assert (
        response_dependent_time_period.json["extensions"]["exclude"]
        == dependent_time_period["exclude"]
    )

    internal_time_period = load_timeperiod(name="time_period_2")
    assert internal_time_period["exclude"] == ["time_period_1"]

    referenced_time_period_by_name = timeperiod_client.create(
        time_period_data=name_dependent_time_period, expect_ok=False
    ).assert_status_code(400)
    assert referenced_time_period_by_name.json["detail"] == "These fields have problems: exclude"
    assert referenced_time_period_by_name.json["title"] == "Bad Request"
    assert "exclude" in referenced_time_period_by_name.json["fields"]
    assert len(referenced_time_period_by_name.json["fields"]["exclude"]) == 1
    assert referenced_time_period_by_name.json["fields"]["exclude"]["0"] == [
        "Time period alias does not exist: 'time_period_1'"
    ]


def test_openapi_timeperiod_update_exclude(timeperiod_client: TimePeriodTestClient) -> None:
    time_period_alias_1 = "Time Period 1"
    time_period_1: dict[str, object] = {
        "name": "time_period_1",
        "alias": time_period_alias_1,
        "active_time_ranges": [
            {
                "day": "monday",
                "time_ranges": [{"start": "14:00", "end": "18:00"}],
            },
        ],
        "exceptions": [],
        "exclude": [],
    }

    time_period_alias_2 = "Time Period 2"
    time_period_2: dict[str, object] = {
        "name": "time_period_2",
        "alias": time_period_alias_2,
        "active_time_ranges": [
            {
                "day": "monday",
                "time_ranges": [{"start": "14:00", "end": "18:00"}],
            },
        ],
        "exceptions": [],
        "exclude": [],
    }

    time_period_3: dict[str, object] = {
        "name": "time_period_3",
        "alias": "Time Period 3",
        "active_time_ranges": [
            {
                "day": "monday",
                "time_ranges": [{"start": "14:00", "end": "18:00"}],
            },
        ],
        "exceptions": [],
        "exclude": [],
    }

    timeperiod_client.create(time_period_data=time_period_1)
    timeperiod_client.create(time_period_data=time_period_2)
    timeperiod_client.create(time_period_data=time_period_3)

    res_empty_exclude = timeperiod_client.get(time_period_id="time_period_3")
    assert res_empty_exclude.json["extensions"]["exclude"] == []

    timeperiod_client.edit(
        time_period_id="time_period_3", time_period_data={"exclude": [time_period_alias_1]}
    )
    res_update_time_period = timeperiod_client.get(time_period_id="time_period_3")
    assert res_update_time_period.json["extensions"]["exclude"] == [time_period_alias_1]

    timeperiod_client.edit(
        time_period_id="time_period_3", time_period_data={"exclude": [time_period_alias_2]}
    )
    res_update_time_period = timeperiod_client.get(time_period_id="time_period_3")
    assert res_update_time_period.json["extensions"]["exclude"] == [time_period_alias_2]

    timeperiod_client.edit(
        time_period_id="time_period_3",
        time_period_data={"exclude": ["I don't exist"]},
        expect_ok=False,
    ).assert_status_code(400)

    timeperiod_client.edit(
        time_period_id="time_period_3",
        time_period_data={"exclude": "This should be a list"},
        expect_ok=False,
    ).assert_status_code(400)
