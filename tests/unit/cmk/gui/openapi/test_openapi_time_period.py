#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.unit.rest_api_client import ClientRegistry

from cmk.utils.timeperiod import TimeperiodSpec, TimeperiodSpecs

from cmk.gui.watolib.timeperiods import load_timeperiod

from cmk.validate_config import validate_timeperiods


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

    days = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
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
                {
                    "date": "2023-02-02",
                    "time_ranges": [{"start": "18:32", "end": "21:15"}],
                },
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
    assert resp2.json["extensions"]["exceptions"][0] == {
        "date": "2023-02-03",
        "time_ranges": [],
    }


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
                {
                    "date": "2020-01-01",
                    "time_ranges": [{"start": "14:00", "end": "18:00"}],
                }
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
                {
                    "date": "2020-01-01",
                    "time_ranges": [{"start": "14:00", "end": "18:00"}],
                }
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

    resp = clients.TimePeriod.delete(time_period_id="24X7", expect_ok=False).assert_status_code(405)
    assert resp.json["title"] == "Built-in time periods can not be deleted"
    assert resp.json["detail"] == "The built-in time period '24X7' cannot be deleted."


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
                {
                    "date": "2021-04-01",
                    "time_ranges": [{"end": "15:00", "start": "14:00"}],
                }
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
                {
                    "date": "2021-04-01",
                    "time_ranges": [{"end": "15:00", "start": "14:00"}],
                }
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
                {
                    "date": "2021-04-01",
                    "time_ranges": [{"end": "15:00", "start": "14:00"}],
                }
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
            "exclude": ["exclude_test_1"],
        },
    )

    clients.TimePeriod.create(
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
            "exclude": ["24x7"],
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
            "exclude": ["time_period_1"],
        },
    )

    resp = clients.TimePeriod.delete("time_period_1", expect_ok=False).assert_status_code(409)
    assert resp.json["detail"].endswith("Time Period 2 (excluded)).")


def test_openapi_time_period_24h_regression(clients: ClientRegistry) -> None:
    """The REST API sadly couldn't handle 24:00 in times as the GUI can."""
    clients.TimePeriod.create(
        time_period_data={
            "name": "all_of_monday",
            "alias": "All of Monday",
            "active_time_ranges": [
                {
                    "day": "monday",
                    "time_ranges": [{"start": "00:00", "end": "24:00"}],
                },
            ],
            "exceptions": [],
            "exclude": [],
        },
    )
    clients.TimePeriod.get(time_period_id="all_of_monday")
    clients.TimePeriod.get_all()
    clients.TimePeriod.edit(
        time_period_id="all_of_monday",
        time_period_data={"alias": "Everything in Monday"},
    )
    clients.TimePeriod.delete(time_period_id="all_of_monday")


def test_openapi_time_period_24h_is_end_of_day(clients: ClientRegistry) -> None:
    resp = clients.TimePeriod.create(
        time_period_data={
            "name": "time_flowing_backwards",
            "alias": "Time Flowing Backwards",
            "active_time_ranges": [
                {
                    "day": "monday",
                    "time_ranges": [{"start": "24:00", "end": "00:00"}],
                },
            ],
            "exceptions": [],
            "exclude": [],
        },
        expect_ok=False,
    ).assert_status_code(400)
    assert resp.json["detail"] == "These fields have problems: active_time_ranges"
    assert (
        resp.json["fields"]["active_time_ranges"]["0"]["time_ranges"]["0"]["_schema"][0]
        == "Start time (24:00) must be before end time (00:00)."
    )


def test_openapi_exclude_field(clients: ClientRegistry) -> None:
    time_period_1: dict[str, object] = {
        "name": "time_period_1",
        "alias": "TimePeriod1Alias",
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
        "exclude": ["time_period_1"],
    }

    alias_dependent_time_period: dict[str, object] = {
        "name": "time_period_3",
        "alias": "Time Period 3",
        "active_time_ranges": [
            {
                "day": "monday",
                "time_ranges": [{"start": "12:00", "end": "14:00"}],
            },
        ],
        "exceptions": [],
        "exclude": ["TimePeriod1Alias"],
    }

    referenced_time_period_does_not_exist = clients.TimePeriod.create(
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
        "Name missing: 'time_period_1'"
    ]

    clients.TimePeriod.create(time_period_data=time_period_1)
    clients.TimePeriod.create(time_period_data=dependent_time_period)
    response_dependent_time_period = clients.TimePeriod.get(time_period_id="time_period_2")
    assert (
        response_dependent_time_period.json["extensions"]["exclude"]
        == dependent_time_period["exclude"]
    )

    internal_time_period = load_timeperiod(name="time_period_2")
    assert internal_time_period["exclude"] == ["time_period_1"]

    referenced_time_period_by_alias = clients.TimePeriod.create(
        time_period_data=alias_dependent_time_period, expect_ok=False
    ).assert_status_code(400)
    assert referenced_time_period_by_alias.json["detail"] == "These fields have problems: exclude"
    assert referenced_time_period_by_alias.json["title"] == "Bad Request"
    assert "exclude" in referenced_time_period_by_alias.json["fields"]
    assert len(referenced_time_period_by_alias.json["fields"]["exclude"]) == 1
    assert referenced_time_period_by_alias.json["fields"]["exclude"]["0"] == [
        "Name missing: 'TimePeriod1Alias'"
    ]


def test_openapi_timeperiod_update_exclude(clients: ClientRegistry) -> None:
    time_period_name_1 = "time_period_1"
    time_period_1: dict[str, object] = {
        "name": time_period_name_1,
        "alias": "Time period 1 title",
        "active_time_ranges": [
            {
                "day": "monday",
                "time_ranges": [{"start": "14:00", "end": "18:00"}],
            },
        ],
        "exceptions": [],
        "exclude": [],
    }

    time_period_name_2 = "time_period_2"
    time_period_2: dict[str, object] = {
        "name": "time_period_2",
        "alias": "Time period 2 title",
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
        "alias": "Time Period 3 title",
        "active_time_ranges": [
            {
                "day": "monday",
                "time_ranges": [{"start": "14:00", "end": "18:00"}],
            },
        ],
        "exceptions": [],
        "exclude": [],
    }

    clients.TimePeriod.create(time_period_data=time_period_1)
    clients.TimePeriod.create(time_period_data=time_period_2)
    clients.TimePeriod.create(time_period_data=time_period_3)

    res_empty_exclude = clients.TimePeriod.get(time_period_id="time_period_3")
    assert res_empty_exclude.json["extensions"]["exclude"] == []

    clients.TimePeriod.edit(
        time_period_id="time_period_3",
        time_period_data={"exclude": [time_period_name_1]},
    )
    res_update_time_period = clients.TimePeriod.get(time_period_id="time_period_3")
    assert res_update_time_period.json["extensions"]["exclude"] == [time_period_name_1]

    clients.TimePeriod.edit(
        time_period_id="time_period_3",
        time_period_data={"exclude": [time_period_name_2]},
    )
    res_update_time_period = clients.TimePeriod.get(time_period_id="time_period_3")
    assert res_update_time_period.json["extensions"]["exclude"] == [time_period_name_2]

    clients.TimePeriod.edit(
        time_period_id="time_period_3",
        time_period_data={"exclude": ["I don't exist"]},
        expect_ok=False,
    ).assert_status_code(400)

    clients.TimePeriod.edit(
        time_period_id="time_period_3",
        time_period_data={"exclude": "This should be a list"},
        expect_ok=False,
    ).assert_status_code(400)


invalid_timeperiod_names = (
    "test_timeperiod\\n",
    "test_timeperiod\n",
    "test_time\nperiod",
    "\ntest_timeperiod",
)


@pytest.mark.parametrize("timeperiod_name", invalid_timeperiod_names)
def test_create_timeperiod_name_with_newline(
    clients: ClientRegistry,
    timeperiod_name: str,
) -> None:
    resp = clients.TimePeriod.create(
        time_period_data={
            "name": timeperiod_name,
            "alias": "foobar",
            "active_time_ranges": [{"day": "all"}],
            "exceptions": [{"date": "2020-01-01"}],
        },
        expect_ok=False,
    )
    resp.assert_status_code(400)
    assert (
        resp.json["fields"]["name"][0]
        == f"{timeperiod_name!r} does not match pattern '^[-a-z0-9A-Z_]+\\\\Z'."
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_timeperiod_update_with_same_alias(clients: ClientRegistry) -> None:
    timeperiod_name = "test_name"
    timeperiod_data: dict[str, object] = {
        "alias": "time_period_alias",
        "active_time_ranges": [{"day": "all"}],
        "exceptions": [{"date": "2020-01-01"}],
    }

    clients.TimePeriod.create(time_period_data={"name": timeperiod_name, **timeperiod_data})

    clients.TimePeriod.edit(time_period_id=timeperiod_name, time_period_data=timeperiod_data)


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_timeperiod_update_alias_in_use(clients: ClientRegistry) -> None:
    timeperiod_name = "test_name"

    timeperiod_data: dict[str, object] = {
        "alias": "time_period_alias",
        "active_time_ranges": [{"day": "all"}],
        "exceptions": [{"date": "2020-01-01"}],
    }

    other_timeperiod_data: dict[str, object] = {
        "alias": "other_time_period_alias",
        "active_time_ranges": [{"day": "all"}],
        "exceptions": [{"date": "2020-01-01"}],
    }

    clients.TimePeriod.create(time_period_data={"name": timeperiod_name, **timeperiod_data})
    clients.TimePeriod.create(time_period_data={"name": "other_test_name", **other_timeperiod_data})

    clients.TimePeriod.edit(
        time_period_id=timeperiod_name,
        time_period_data={"alias": "other_time_period_alias"},
        expect_ok=False,
    ).assert_status_code(400)


@pytest.mark.parametrize(
    "time_period, is_valid",
    [
        pytest.param(
            [],
            False,
            id="Reject empty data",
        ),
        pytest.param(
            {"alias": "test", "exclude": [], "monday": [("00:00", "24:00")]},
            True,
            id="Support 24:00",
        ),
        pytest.param(
            {"alias": "test", "exclude": [], "monday": [("00:00", "25:00")]},
            False,
            id="Reject incorrect hour value",
        ),
        pytest.param(
            {"alias": "test", "exclude": [], "monday": [("00:67", "18:00")]},
            False,
            id="Reject incorrect minute value",
        ),
        pytest.param(
            {"alias": "test", "exclude": [], "monday": [("14:00", "12:00")]},
            False,
            id="Reject end time earlier than beggining time",
        ),
        pytest.param(
            {"alias": "test", "exclude": [], "monday": [("12:00:33", "12:00")]},
            False,
            id="Reject time format is not HH:MM",
        ),
        pytest.param(
            {
                "alias": "test",
                "exclude": [],
                "monday": [("00:00", "24:00")],
                "2023-12-19": [("00:00", "24:00")],
            },
            True,
            id="Exception date is ISO date",
        ),
        pytest.param(
            {
                "alias": "test",
                "exclude": [],
                "monday": [("00:00", "24:00")],
                "2023-12-19": "I should be a list",
            },
            False,
            id="Reject exception date contains incorrect value type",
        ),
        pytest.param(
            {
                "alias": "test",
                "exclude": [],
                "monday": [("00:00", "24:00")],
                "2023-12-32": [("00:00", "24:00")],
            },
            False,
            id="Reject exception time is not ISO date",
        ),
        pytest.param(
            {
                "alias": "test",
                "exclude": [],
                "monday": [("00:00", "24:00")],
                "pendorcho": "I should not be here",
            },
            False,
            id="Reject strange fields",
        ),
        pytest.param(
            {
                "alias": "test",
            },
            False,
            id="Reject when no time periods specified",
        ),
        pytest.param(
            {
                "alias": "same all week days",
                "monday": [("13:00", "14:00")],
                "tuesday": [("00:00", "24:00")],
                "wednesday": [("12:00", "14:00")],
                "thursday": [("12:00", "14:00")],
                "friday": [("12:00", "14:00")],
                "saturday": [("12:00", "14:00")],
                "sunday": [("12:00", "14:00")],
            },
            True,
            id="Full week especification",
        ),
        pytest.param(
            {
                "alias": "test",
                "exclude": ["date1", "date2"],
                "monday": [("00:00", "24:00")],
            },
            True,
            id="Exclude field contains list of string",
        ),
        pytest.param(
            {
                "alias": "test",
                "exclude": "date1",
                "monday": [("00:00", "24:00")],
            },
            False,
            id="Reject exclude field contains string",
        ),
        pytest.param(
            {
                "alias": "test",
                "exclude": [],
                "monday": [("00:00", "24:00")],
            },
            True,
            id="Exclude field is empty",
        ),
    ],
)
def test_timeperiod_config_validator_fields(
    time_period: TimeperiodSpec, is_valid: bool, request: pytest.FixtureRequest
) -> None:
    result = True
    try:
        validate_timeperiods({request.node.name: time_period})
    except Exception:
        result = False

    assert result == is_valid


def test_timeperiod_config_validator_on_file() -> None:
    time_periods: TimeperiodSpecs = {
        "Nights": {
            "alias": "Nights",
            "friday": [("21:00", "24:00"), ("00:00", "06:00")],
            "monday": [("21:00", "24:00"), ("00:00", "06:00")],
            "saturday": [("21:00", "24:00"), ("00:00", "06:00")],
            "sunday": [("21:00", "24:00"), ("00:00", "06:00")],
            "thursday": [("21:00", "24:00"), ("00:00", "06:00")],
            "tuesday": [("21:00", "24:00"), ("00:00", "06:00")],
            "wednesday": [("21:00", "24:00"), ("00:00", "06:00")],
        },
        "Service1": {
            "alias": "Service1",
            "friday": [("06:00", "20:00")],
            "monday": [("06:00", "20:00")],
            "saturday": [("06:00", "20:00")],
            "sunday": [("06:00", "20:00")],
            "thursday": [("06:00", "20:00")],
            "tuesday": [("06:00", "20:00")],
            "wednesday": [("06:00", "20:00")],
        },
        "Sunday": {"alias": "Sunday", "sunday": [("00:00", "24:00")]},
        "Workdays": {
            "alias": "Workdays",
            "exclude": ["Sunday"],
            "friday": [("07:00", "20:00")],
            "monday": [("07:00", "20:00")],
            "saturday": [("07:00", "20:00")],
            "sunday": [("07:00", "20:00")],
            "thursday": [("07:00", "20:00")],
            "tuesday": [("07:00", "20:00")],
            "wednesday": [("07:00", "20:00")],
        },
        "Week": {
            "alias": "Week",
            "friday": [("06:00", "20:00")],
            "monday": [("06:00", "20:00")],
            "saturday": [("06:00", "20:00")],
            "sunday": [("06:00", "20:00")],
            "thursday": [("06:00", "20:00")],
            "tuesday": [("06:00", "20:00")],
            "wednesday": [("06:00", "20:00")],
        },
        "period_1": {
            "alias": "period_1",
            "exclude": ["Sunday"],
            "friday": [("08:00", "08:05"), ("16:20", "16:25"), ("13:20", "13:25")],
            "monday": [("08:00", "08:05"), ("16:20", "16:25"), ("13:20", "13:25")],
            "saturday": [("08:00", "08:05"), ("16:20", "16:25"), ("13:20", "13:25")],
            "sunday": [("08:00", "08:05"), ("16:20", "16:25"), ("13:20", "13:25")],
            "thursday": [("08:00", "08:05"), ("16:20", "16:25"), ("13:20", "13:25")],
            "tuesday": [("08:00", "08:05"), ("16:20", "16:25"), ("13:20", "13:25")],
            "wednesday": [("08:00", "08:05"), ("16:20", "16:25"), ("13:20", "13:25")],
        },
        "period_2": {
            "alias": "period_2",
            "exclude": ["Sunday"],
            "friday": [("09:05", "09:10"), ("17:25", "17:30"), ("14:25", "14:30")],
            "monday": [("09:05", "09:10"), ("17:25", "17:30"), ("14:25", "14:30")],
            "saturday": [("09:05", "09:10"), ("17:25", "17:30"), ("14:25", "14:30")],
            "sunday": [("09:05", "09:10"), ("17:25", "17:30"), ("14:25", "14:30")],
            "thursday": [("09:05", "09:10"), ("17:25", "17:30"), ("14:25", "14:30")],
            "tuesday": [("09:05", "09:10"), ("17:25", "17:30"), ("14:25", "14:30")],
            "wednesday": [("09:05", "09:10"), ("17:25", "17:30"), ("14:25", "14:30")],
        },
        "period_3": {
            "alias": "period_3",
            "exclude": ["Sunday"],
            "friday": [("07:05", "07:10"), ("15:45", "15:50"), ("12:55", "13:00")],
            "monday": [("07:05", "07:10"), ("15:45", "15:50"), ("12:55", "13:00")],
            "saturday": [("07:05", "07:10"), ("15:45", "15:50"), ("12:55", "13:00")],
            "sunday": [("07:05", "07:10"), ("15:45", "15:50"), ("12:55", "13:00")],
            "thursday": [("07:05", "07:10"), ("15:45", "15:50"), ("12:55", "13:00")],
            "tuesday": [("07:05", "07:10"), ("15:45", "15:50"), ("12:55", "13:00")],
            "wednesday": [("07:05", "07:10"), ("15:45", "15:50"), ("12:55", "13:00")],
        },
        "period_4": {
            "alias": "period_4",
            "exclude": ["Sunday"],
            "friday": [("08:45", "08:50"), ("17:10", "17:20"), ("14:30", "14:40")],
            "monday": [("08:45", "08:50"), ("17:10", "17:20"), ("14:30", "14:40")],
            "saturday": [("08:45", "08:50"), ("17:10", "17:20"), ("14:30", "14:40")],
            "sunday": [("08:45", "08:50"), ("17:10", "17:20"), ("14:30", "14:40")],
            "thursday": [("08:45", "08:50"), ("17:10", "17:20"), ("14:30", "14:40")],
            "tuesday": [("08:45", "08:50"), ("17:10", "17:20"), ("14:30", "14:40")],
            "wednesday": [("08:45", "08:50"), ("17:10", "17:20"), ("14:30", "14:40")],
        },
        "period_5": {
            "alias": "period_5",
            "friday": [("02:00", "19:00")],
            "monday": [("02:00", "19:00")],
            "saturday": [("02:00", "19:00")],
            "sunday": [("02:00", "19:00")],
            "thursday": [("02:00", "19:00")],
            "tuesday": [("02:00", "19:00")],
            "wednesday": [("02:00", "19:00")],
        },
    }
    validate_timeperiods(time_periods)


def test_openapi_time_period_time_range_shorter_than_one_minute(
    clients: ClientRegistry,
) -> None:
    clients.TimePeriod.create(
        time_period_data={
            "name": "foo",
            "alias": "foo",
            "active_time_ranges": [
                {"time_ranges": [{"start": "00:01:00.267271Z", "end": "00:01:32.724825Z"}]}
            ],
        },
    )
