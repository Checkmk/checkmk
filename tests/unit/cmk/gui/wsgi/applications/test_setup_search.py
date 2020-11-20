#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from webtest import TestApp  # type: ignore[import]
from cmk.gui.watolib.search import (
    Index,
    get_index_store,
    MatchItem,
)
from cmk.gui.wsgi.applications.setup_search import CheckmkSetupSearchApp


@pytest.fixture(name="search_app", scope="session")
def fixture_search_app():
    return TestApp(CheckmkSetupSearchApp())


@pytest.fixture(name="extra_environ_user", scope="function")
def fixture_extra_environ_user(with_user):
    return {"REMOTE_USER": with_user[0]}


def test_not_logged_in(search_app):
    response = search_app.get(
        "/ajax_search_setup.py",
        params={"_ajaxid": "123"},
        expect_errors=True,
    )
    assert response.status_int == 401


def test_wrong_page(search_app, extra_environ_user):
    response = search_app.get(
        "/wrong.py",
        params={"_ajaxid": "123"},
        extra_environ=extra_environ_user,
        expect_errors=True,
    )
    assert response.status_int == 404


def test_missing_query(search_app, extra_environ_user):
    response = search_app.get(
        "/ajax_search_setup.py",
        params={"_ajaxid": "123"},
        extra_environ=extra_environ_user,
        expect_errors=True,
    )
    assert response.status_int == 400
    assert response.text == r'{"result_code": 1, "result": "The parameter \"q\" is missing."}'


def test_normal_call(search_app, extra_environ_user):
    # write search index with one entry to check if this entry will be found
    get_index_store().store_index(
        Index(
            localization_dependent={
                'default': {
                    'some_topic': [
                        MatchItem(
                            title='Network interfaces',
                            topic='Rules',
                            url='some_url',
                            match_texts=['network interfaces'],
                        ),
                    ],
                },
            }))

    response = search_app.get(
        "/ajax_search_setup.py",
        params={
            "_ajaxid": "123",
            "q": "inter",
        },
        extra_environ=extra_environ_user,
    )
    assert response.status_int == 200
    for exp_str in ['"result_code": 0', 'Rules', 'Network interfaces', 'some_url']:
        assert exp_str in response.text
