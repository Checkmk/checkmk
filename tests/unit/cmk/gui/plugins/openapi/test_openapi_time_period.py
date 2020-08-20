# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json


def test_openapi_time_period(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    _resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/time_period/collections/all",
        params=json.dumps({
            "name": "foo",
            "alias": "foobar",
            "active_time_ranges": [{
                "day": "all",
                "time_ranges": [{
                    "start": "12:00",
                    "end": "14:00"
                }]
            }],
            "exceptions": [{
                "date": "2020-01-01",
                "time_ranges": [{
                    "start": "14:00",
                    "end": "18:00"
                }]
            }]
        }),
        status=204,
        content_type='application/json',
    )

    _resp = wsgi_app.call_method(
        'put',
        base + "/objects/time_period/foo",
        params=json.dumps({
            "alias": "foo",
            "active_time_ranges": [{
                "day": "monday",
                "time_ranges": [{
                    "start": "12:00",
                    "end": "14:00"
                }]
            }]
        }),
        status=204,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/time_period/foo",
        status=200,
    )
    assert resp.json == {
        'alias': 'foo',
        'active_time_ranges': [{
            'day': 'monday',
            'time_ranges': [{
                'start': '12:00',
                'end': '14:00'
            }]
        }],
        'exceptions': [{
            'date': '2020-01-01',
            'time_ranges': [{
                'start': '14:00',
                'end': '18:00'
            }]
        }],
        'exclude': []
    }
