#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse
import json
from pathlib import Path

import pytest
import requests
import responses

from cmk.plugins.mobileiron.special_agent.agent_mobileiron import agent_mobileiron_main

URL1 = "https://example.com/api/v1/device?rows=200&start=0&dmPartitionId=103881"
URL2 = "https://example.com/api/v1/device?rows=200&start=0&dmPartitionId=103882"
URL3 = "https://example.com/api/v1/device?rows=200&start=200&dmPartitionId=103881"

test_device1 = Path(Path(__file__).parent / "files" / "example_output.json").read_text()

test_device2 = Path(Path(__file__).parent / "files" / "example_output_partition_2.json").read_text()

test_device3 = Path(Path(__file__).parent / "files" / "example_output_overflow.json").read_text()


url_responses = list(zip((URL1, URL2, URL3), (test_device1, test_device2, test_device3)))


@responses.activate
def test_agent_output_2_partitions(capsys: pytest.CaptureFixture[str]) -> None:
    """Agent output contains piggyback data and sections from both partitions in args
    and from the second page of the first URL (in case total number of devices is more than 200)"""
    # standard request to the first partition but with more than 300 devices in reply
    # this triggers the URL3 request

    for u, r in url_responses:
        responses.add(
            responses.GET,
            u,
            json=json.loads(r),
            status=200,
        )

    args = argparse.Namespace(
        hostname="example.com",
        key_fields=("entityName",),
        android_regex=[".*"],
        ios_regex=["foo"],
        other_regex=["foo"],
        username="",
        password="",
        partition=[103881, 103882],
        proxy=None,
        debug=False,
    )
    agent_mobileiron_main(args)

    captured = capsys.readouterr()
    assert captured.err == "", "stderr is not empty"
    assert """<<<<device1>>>>\n<<<mobileiron_section:sep(0)>>>\n{""" in captured.out, (
        "piggyback header is not correct"
    )

    # make sure the device from the second partition is in
    assert """<<<<partition2device1>>>>\n<<<mobileiron_section:sep(0)>>>\n{""" in captured.out, (
        "piggyback header is not correct"
    )

    # make sure the device from the overflow is in
    assert """<<<<overflowdevice1>>>>\n<<<mobileiron_section:sep(0)>>>\n{""" in captured.out, (
        "piggyback header is not correct"
    )

    assert "1636109710590" in captured.out
    assert "device_duplication" in captured.out
    assert "device_duplication_2" in captured.out


@responses.activate
def test_agent_output_regexes(capsys: pytest.CaptureFixture[str]) -> None:
    """Agent output contains piggyback data and sections from both partitions in args
    and from the second page of the first URL (in case total number of devices is more than 200)"""

    for u, r in url_responses:
        responses.add(
            responses.GET,
            u,
            json=json.loads(r),
            status=200,
        )

    args = argparse.Namespace(
        hostname="example.com",
        key_fields=("entityName",),
        android_regex=[r"device[0-9]{1}"],
        ios_regex=["foo"],
        other_regex=["foo"],
        username="",
        password="",
        partition=[103881, 103882],
        proxy=None,
        debug=False,
    )
    agent_mobileiron_main(args)

    captured = capsys.readouterr()

    # fits the regex
    assert "device1" in captured.out

    # fits the regex but has wrong platform type
    assert "device2" not in captured.out

    # does not fit the regex
    assert "device_duplication" not in captured.out


@pytest.mark.parametrize(
    "exception",
    [
        pytest.param(requests.exceptions.HTTPError),
        pytest.param(requests.exceptions.SSLError),
        # some incompatibility with the latest request 2.28.1 or
        # responses. JSONDecodeError became a TypeError: https://github.com/psf/requests/pull/6097
        # pytest.param(requests.exceptions.JSONDecodeError),
    ],
)
@responses.activate
def test_agent_handles_exceptions(
    exception: type[requests.exceptions.HTTPError] | type[requests.exceptions.SSLError],
    capsys: pytest.CaptureFixture,
) -> None:
    args = argparse.Namespace(
        hostname="does_not_exist",
        key_fields=("entityName",),
        android_regex=["foo"],
        ios_regex=["foo"],
        other_regex=["foo"],
        username="",
        password="",
        partition=[103881],
        proxy=None,
        debug=False,
    )
    responses.get(
        f"https://{args.hostname}:/api/v1/device?rows=200&start=0&dmPartitionId={args.partition[0]}",
        body=exception("exception_message"),
    )

    return_code = agent_mobileiron_main(args)
    assert return_code == 1
    assert capsys.readouterr().err == f"{exception.__name__}: exception_message"
