#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any
from unittest import mock

import pytest

import cmk.plugins.jenkins.agent_based.jenkins_version as jv
from cmk.agent_based.v2 import Result, Service, State


@pytest.fixture(scope="module", name="section")
def _section() -> jv.Section:
    if (parsed_section := jv.parse_jenkins_version([["2.345.6"]])) is None:
        raise ValueError("Unable to parse Jenkins version")

    return parsed_section


def test_discovery(section: jv.Section) -> None:
    assert list(jv.discover_jenkins_version(section)) == [Service()]


@pytest.fixture(scope="module", name="simulated_release_feed")
def _simulated_release_feed() -> dict[str, Any]:
    # Use this feed example to not perform a call to the web.
    # We simulate the data returned from the feed https://www.jenkins.io/changelog-stable/rss.xml
    # The simulated data is truncated to only two entries.
    return {
        "bozo": False,
        "entries": [
            {
                "title": "Jenkins 2.440.2",
                "title_detail": {
                    "type": "text/plain",
                    "language": None,
                    "base": "https://www.jenkins.io/changelog-stable/rss.xml",
                    "value": "Jenkins 2.440.2",
                },
                "links": [
                    {
                        "rel": "alternate",
                        "type": "text/html",
                        "href": "https://jenkins.io/changelog-stable//#v2.440.2",
                    }
                ],
                "link": "https://jenkins.io/changelog-stable//#v2.440.2",
                "summary": "<em>\nContent removed because irrelevant for test.\n</em>",
                "summary_detail": {
                    "type": "text/html",
                    "language": None,
                    "base": "https://www.jenkins.io/changelog-stable/rss.xml",
                    "value": "<em>\nContent removed because irrelevant for test.\n</em>",
                },
                "id": "jenkins-2.440.2",
                "guidislink": False,
                "published": "Wed, 20 Mar 2024 00:00:00 +0000",
                "published_parsed": time.strptime(
                    "Wed, 20 Mar 2024 00:00:00 +0000", "%a, %d %b %Y %H:%M:%S +0000"
                ),
            },
            {
                "title": "Jenkins 2.440.1",
                "title_detail": {
                    "type": "text/plain",
                    "language": None,
                    "base": "https://www.jenkins.io/changelog-stable/rss.xml",
                    "value": "Jenkins 2.440.1",
                },
                "links": [
                    {
                        "rel": "alternate",
                        "type": "text/html",
                        "href": "https://jenkins.io/changelog-stable//#v2.440.1",
                    }
                ],
                "link": "https://jenkins.io/changelog-stable//#v2.440.1",
                "summary": "<em>\nContent removed because irrelevant for test.\n</em>",
                "summary_detail": {
                    "type": "text/html",
                    "language": None,
                    "base": "https://www.jenkins.io/changelog-stable/rss.xml",
                    "value": "<em>\nContent removed because irrelevant for test.\n</em>",
                },
                "id": "jenkins-2.440.1",
                "guidislink": False,
                "published": "Wed, 21 Feb 2024 00:00:00 +0000",
                "published_parsed": time.strptime(
                    "Wed, 21 Feb 2024 00:00:00 +0000", "%a, %d %b %Y %H:%M:%S +0000"
                ),
            },
        ],
    }


def test_check_jenkins_version(section: jv.Section, simulated_release_feed: dict) -> None:
    with mock.patch("feedparser.parse", return_value=simulated_release_feed):
        assert list(jv.check_jenkins_version(params={}, section=section)) == [
            Result(state=State.OK, summary="Version: 2.345.6"),
            Result(state=State.WARN, notice="Update to 2.440.2 available"),
            Result(
                state=State.OK, summary="Changelog: https://jenkins.io/changelog-stable//#v2.440.2"
            ),
        ]


def test_check_jenkins_version_with_different_state(
    section: jv.Section, simulated_release_feed: dict
) -> None:
    with mock.patch("feedparser.parse", return_value=simulated_release_feed):
        assert list(
            jv.check_jenkins_version(
                params={
                    "diff_state": State.CRIT.value,
                },
                section=section,
            )
        ) == [
            Result(state=State.OK, summary="Version: 2.345.6"),
            Result(state=State.CRIT, notice="Update to 2.440.2 available"),
            Result(
                state=State.OK, summary="Changelog: https://jenkins.io/changelog-stable//#v2.440.2"
            ),
        ]


def test_check_jenkins_version_no_feed(section: jv.Section) -> None:
    # This test does not perform a call to the web.
    # We simulate no receiving any entries
    simulated_feed: dict[str, list | bool] = {"bozo": True, "entries": []}

    with mock.patch("feedparser.parse", return_value=simulated_feed):
        assert list(jv.check_jenkins_version(params={}, section=section)) == [
            Result(state=State.OK, summary="Version: 2.345.6"),
            Result(
                state=State.UNKNOWN,
                notice="Unable to receive feed data from 'https://www.jenkins.io/changelog-stable/rss.xml'",
            ),
        ]


def test_check_jenkins_version_feed_without_version_link(section: jv.Section) -> None:
    # This test does not perform a call to the web.
    # We simulate the data returned from the feed https://www.jenkins.io/changelog-stable/rss.xml
    # The simulated data is displays a link that can't be split
    simulated_feed = {
        "bozo": False,
        "entries": [
            {
                "link": "https://jenkins.io/changelog-stable/",
            },
        ],
    }

    with mock.patch("feedparser.parse", return_value=simulated_feed):
        assert list(jv.check_jenkins_version(params={}, section=section)) == [
            Result(state=State.OK, summary="Version: 2.345.6"),
            Result(state=State.UNKNOWN, summary="Unable to find a comparable version"),
        ]
