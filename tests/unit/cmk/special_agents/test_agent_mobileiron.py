#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse
import json
from pathlib import Path

import responses

from cmk.special_agents.agent_mobileiron import agent_mobileiron_main

URL1 = "https://example.com:443/api/v1/device?rows=200&start=0&dmPartitionId=103881"
URL2 = "https://example.com:443/api/v1/device?rows=200&start=0&dmPartitionId=103882"
URL3 = "https://example.com:443/api/v1/device?rows=200&start=200&dmPartitionId=103881"

test_device1 = Path(
    Path(__file__).parent / "agent_mobileiron_files" / "example_output.json"
).read_text()

test_device2 = Path(
    Path(__file__).parent / "agent_mobileiron_files" / "example_output_partition_2.json"
).read_text()

test_device3 = Path(
    Path(__file__).parent / "agent_mobileiron_files" / "example_output_overflow.json"
).read_text()


@responses.activate
def test_agent_output_2_partitions(capsys):
    """Agent output contains piggyback data and sections from both partitions in args
    and from the second page of the first URL (in case total number of devices is more than 200)"""
    # standard request to the first partition but with more than 300 devices in reply
    # this triggers the URL3 request
    responses.add(
        responses.GET,
        URL1,
        json=json.loads(test_device1),
        status=200,
    )

    # standard request to the second partition
    responses.add(
        responses.GET,
        URL2,
        json=json.loads(test_device2),
        status=200,
    )

    # additional request to the first partition with the &start=200 param
    responses.add(
        responses.GET,
        URL3,
        json=json.loads(test_device3),
        status=200,
    )
    args = argparse.Namespace(
        hostname="example.com",
        port="443",
        username="",
        password="",
        partition=[103881, 103882],
        no_cert_check=False,
        proxy_host=None,
        proxy_port=None,
        proxy_user=None,
        proxy_password=None,
        debug=False,
    )
    agent_mobileiron_main(args)

    captured = capsys.readouterr()
    assert captured.err == "", "stderr is not empty"
    assert (
        """<<<<device1>>>>\n<<<mobileiron_section:sep(0)>>>\n{""" in captured.out
    ), "piggyback header is not correct"

    # make sure the device from the second partition is in
    assert (
        """<<<<partition2device1>>>>\n<<<mobileiron_section:sep(0)>>>\n{""" in captured.out
    ), "piggyback header is not correct"

    # make sure the device from the overflow is in
    assert (
        """<<<<overflowdevice1>>>>\n<<<mobileiron_section:sep(0)>>>\n{""" in captured.out
    ), "piggyback header is not correct"

    # make sure the latest registration is chosen
    assert "1636109710590" in captured.out
    assert "1634816307049" not in captured.out
