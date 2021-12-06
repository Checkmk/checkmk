#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import argparse
import json
from pathlib import Path

import responses

from cmk.special_agents.agent_mobileiron import agent_mobileiron_main

URL = "https://example.com:443/api/v1/device?rows=200&start=0&dmPartitionId=103881"


test_device = Path(
    Path(__file__).parent / "agent_mobileiron_files" / "example_output.json"
).read_text()


@responses.activate
def test_agent_output(capsys):
    """Agent output contains piggyback data and sections"""
    responses.add(
        responses.GET,
        URL,
        json=json.loads(test_device),
        status=200,
    )
    args = argparse.Namespace(
        hostname="example.com",
        port="443",
        username="",
        password="",
        partition=[103881],
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

    # make sure the latest registration is chosen
    assert "1636109710590" in captured.out
    assert "1634816307049" not in captured.out
