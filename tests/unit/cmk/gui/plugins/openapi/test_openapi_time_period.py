# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.gui.watolib.timeperiods import load_timeperiod

from tests.unit.cmk.gui.conftest import WebTestAppForCMK


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_time_period(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/time_period/collections/all",
        params=json.dumps(
            {
                "name": "foo",
                "alias": "foobar",
                "active_time_ranges": [
                    {"day": "all", "time_ranges": [{"start": "12:00", "end": "14:00"}]}
                ],
                "exceptions": [
                    {"date": "2020-01-01", "time_ranges": [{"start": "14:00", "end": "18:00"}]}
                ],
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/time_period/foo",
        params=json.dumps(
            {
                "alias": "foo",
                "active_time_ranges": [
                    {"day": "monday", "time_ranges": [{"start": "12:00", "end": "14:00"}]}
                ],
            }
        ),
        headers={"Accept": "application/json"},
        status=204,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/time_period/foo",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json == {
        "alias": "foo",
        "active_time_ranges": [
            {"day": "monday", "time_ranges": [{"start": "12:00", "end": "14:00"}]}
        ],
        "exceptions": [{"date": "2020-01-01", "time_ranges": [{"start": "14:00", "end": "18:00"}]}],
        "exclude": [],
    }


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_time_period_collection(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/time_period/collections/all",
        params=json.dumps(
            {
                "name": "foo",
                "alias": "foobar",
                "active_time_ranges": [
                    {"day": "all", "time_ranges": [{"start": "12:00", "end": "14:00"}]}
                ],
                "exceptions": [
                    {"date": "2020-01-01", "time_ranges": [{"start": "14:00", "end": "18:00"}]}
                ],
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp_col = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/time_period/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert len(resp_col.json_body["value"]) == 2

    _ = aut_user_auth_wsgi_app.call_method(
        "delete",
        base + "/objects/time_period/foo",
        headers={"If-Match": resp.headers["Etag"], "Accept": "application/json"},
        status=204,
        content_type="application/json",
    )

    resp_col = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/domain-types/time_period/collections/all",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert len(resp_col.json_body["value"]) == 1


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_timeperiod_builtin(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    _resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/time_period/24X7",
        headers={"Accept": "application/json"},
        status=200,
    )

    _ = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/time_period/24X7",
        headers={"Accept": "application/json"},
        status=405,
    )


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_timeperiod_unmodified_update(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/time_period/collections/all",
        params=json.dumps(
            {
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
                "name": "test_all_8x5",
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/time_period/test_all_8x5",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json == {
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

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/time_period/test_all_8x5",
        params=json.dumps({}),
        headers={"Accept": "application/json"},
        status=204,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/time_period/test_all_8x5",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json == {
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


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_timeperiod_complex_update(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/time_period/collections/all",
        params=json.dumps(
            {
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
                "name": "test_all_8x5",
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    _resp = aut_user_auth_wsgi_app.call_method(
        "put",
        base + "/objects/time_period/test_all_8x5",
        params=json.dumps(
            {
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
            }
        ),
        headers={"Accept": "application/json"},
        status=204,
        content_type="application/json",
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
def test_openapi_timeperiod_excluding_exclude(aut_user_auth_wsgi_app: WebTestAppForCMK) -> None:
    base = "/NO_SITE/check_mk/api/1.0"

    _resp = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/time_period/collections/all",
        params=json.dumps(
            {
                "active_time_ranges": [
                    {
                        "day": "monday",
                        "time_ranges": [
                            {"end": "12:30", "start": "08:00"},
                            {"end": "17:00", "start": "13:30"},
                        ],
                    }
                ],
                "alias": "Test All days 8x5",
                "exceptions": [],
                "name": "test_all_8x5",
            }
        ),
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    resp = aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/time_period/test_all_8x5",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json_body == {
        "active_time_ranges": [
            {
                "day": "monday",
                "time_ranges": [
                    {"end": "12:30", "start": "08:00"},
                    {"end": "17:00", "start": "13:30"},
                ],
            }
        ],
        "alias": "Test All days 8x5",
        "exceptions": [],
        "exclude": [],
    }
