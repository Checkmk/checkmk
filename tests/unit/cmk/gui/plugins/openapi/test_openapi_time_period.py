# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.gui.watolib.timeperiods import load_timeperiod


def test_openapi_time_period(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

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
        status=200,
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


def test_openapi_time_period_collection(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    resp = wsgi_app.call_method(
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
        status=200,
        content_type='application/json',
    )

    resp_col = wsgi_app.call_method(
        'get',
        base + '/domain-types/time_period/collections/all',
        status=200,
    )
    assert len(resp_col.json_body["value"]) == 2

    _ = wsgi_app.call_method(
        'delete',
        base + "/objects/time_period/foo",
        headers={'If-Match': resp.headers['Etag']},
        status=204,
        content_type='application/json',
    )

    resp_col = wsgi_app.call_method(
        'get',
        base + '/domain-types/time_period/collections/all',
        status=200,
    )
    assert len(resp_col.json_body["value"]) == 1


def test_openapi_timeperiod_builtin(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    _resp = wsgi_app.call_method('get', base + "/objects/time_period/24X7", status=200)

    _ = wsgi_app.call_method('put', base + "/objects/time_period/24X7", status=405)


def test_openapi_timeperiod_unmodified_update(wsgi_app, with_automation_user,
                                              suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    _resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/time_period/collections/all",
        params=json.dumps({
            'active_time_ranges': [{
                'day': 'all',
                'time_ranges': [{
                    'end': '12:30',
                    'start': '08:00'
                }, {
                    'end': '17:00',
                    'start': '13:30'
                }]
            }],
            'alias': 'Test All days 8x5',
            'exceptions': [{
                'date': '2021-04-01',
                'time_ranges': [{
                    'end': '15:00',
                    'start': '14:00'
                }]
            }],
            'name': 'test_all_8x5'
        }),
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/time_period/test_all_8x5",
        status=200,
    )
    assert resp.json == {
        'active_time_ranges': [{
            'day': 'monday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }, {
            'day': 'tuesday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }, {
            'day': 'wednesday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }, {
            'day': 'thursday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }, {
            'day': 'friday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }, {
            'day': 'saturday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }, {
            'day': 'sunday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }],
        'alias': 'Test All days 8x5',
        'exceptions': [{
            'date': '2021-04-01',
            'time_ranges': [{
                'end': '15:00',
                'start': '14:00'
            }]
        }],
        'exclude': [],
    }

    _resp = wsgi_app.call_method(
        'put',
        base + "/objects/time_period/test_all_8x5",
        params=json.dumps({}),
        status=204,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/time_period/test_all_8x5",
        status=200,
    )
    assert resp.json == {
        'active_time_ranges': [{
            'day': 'monday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }, {
            'day': 'tuesday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }, {
            'day': 'wednesday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }, {
            'day': 'thursday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }, {
            'day': 'friday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }, {
            'day': 'saturday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }, {
            'day': 'sunday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }],
        'alias': 'Test All days 8x5',
        'exceptions': [{
            'date': '2021-04-01',
            'time_ranges': [{
                'end': '15:00',
                'start': '14:00'
            }]
        }],
        'exclude': [],
    }


def test_openapi_timeperiod_complex_update(wsgi_app, with_automation_user,
                                           suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    _resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/time_period/collections/all",
        params=json.dumps({
            'active_time_ranges': [{
                'day': 'all',
                'time_ranges': [{
                    'end': '12:30',
                    'start': '08:00'
                }, {
                    'end': '17:00',
                    'start': '13:30'
                }]
            }],
            'alias': 'Test All days 8x5',
            'exceptions': [{
                'date': '2021-04-01',
                'time_ranges': [{
                    'end': '15:00',
                    'start': '14:00'
                }]
            }],
            'name': 'test_all_8x5'
        }),
        status=200,
        content_type='application/json',
    )

    _resp = wsgi_app.call_method(
        'put',
        base + "/objects/time_period/test_all_8x5",
        params=json.dumps({
            'active_time_ranges': [{
                'day': 'all',
                'time_ranges': [{
                    'end': '12:30',
                    'start': '08:00'
                }, {
                    'end': '17:00',
                    'start': '13:30'
                }]
            }],
            'alias': 'Test All days 8x5 z',
            'exceptions': [{
                'date': '2021-04-01',
                'time_ranges': [{
                    'end': '15:00',
                    'start': '14:00'
                }]
            }]
        }),
        status=204,
        content_type='application/json',
    )

    internal_timeperiod = load_timeperiod("test_all_8x5")
    assert internal_timeperiod == {
        'alias': 'Test All days 8x5 z',
        '2021-04-01': [('14:00', '15:00')],
        'monday': [('08:00', '12:30'), ('13:30', '17:00')],
        'tuesday': [('08:00', '12:30'), ('13:30', '17:00')],
        'wednesday': [('08:00', '12:30'), ('13:30', '17:00')],
        'thursday': [('08:00', '12:30'), ('13:30', '17:00')],
        'friday': [('08:00', '12:30'), ('13:30', '17:00')],
        'saturday': [('08:00', '12:30'), ('13:30', '17:00')],
        'sunday': [('08:00', '12:30'), ('13:30', '17:00')],
        'exclude': [],
    }


def test_openapi_timeperiod_excluding_exclude(wsgi_app, with_automation_user,
                                              suppress_automation_calls):
    username, secret = with_automation_user
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/1.0'

    _resp = wsgi_app.call_method(
        'post',
        base + "/domain-types/time_period/collections/all",
        params=json.dumps({
            'active_time_ranges': [{
                'day': 'monday',
                'time_ranges': [{
                    'end': '12:30',
                    'start': '08:00'
                }, {
                    'end': '17:00',
                    'start': '13:30'
                }]
            }],
            'alias': 'Test All days 8x5',
            'exceptions': [],
            'name': 'test_all_8x5'
        }),
        status=200,
        content_type='application/json',
    )

    resp = wsgi_app.call_method(
        'get',
        base + "/objects/time_period/test_all_8x5",
        status=200,
    )
    assert resp.json_body == {
        'active_time_ranges': [{
            'day': 'monday',
            'time_ranges': [{
                'end': '12:30',
                'start': '08:00'
            }, {
                'end': '17:00',
                'start': '13:30'
            }]
        }],
        'alias': 'Test All days 8x5',
        'exceptions': [],
        'exclude': []
    }
