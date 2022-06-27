#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.special_agents.agent_aws import AWSSectionResult, AWSSectionsGeneric


class TestAWSSections:
    @pytest.fixture
    def services(self):
        return "testservice"

    @pytest.fixture
    def region(self):
        return "testregion"

    @pytest.fixture
    def config(self):
        return "testconfig"

    @pytest.fixture
    def generic_section(self, services, region, config):
        return AWSSectionsGeneric(services, region, config)

    def test_section_header(self, generic_section, capsys) -> None:
        cached_data = {
            ("costs_and_usage", 1606382471.693873, 38582.763184): [
                AWSSectionResult(
                    piggyback_hostname="",
                    content=[
                        {
                            "TimePeriod": {
                                "Start": "2020-11-25",
                                "End": "2020-11-26",
                            },
                            "Total": {
                                "UnblendedCost": {
                                    "Amount": "0",
                                    "Unit": "USD",
                                }
                            },
                            "Groups": [],
                            "Estimated": True,
                        },
                    ],
                )
            ],
        }
        generic_section._write_section_results(cached_data)
        section_stdout = capsys.readouterr().out
        assert section_stdout.split("\n")[0] == "<<<aws_costs_and_usage:cached(1606382471,38642)>>>"
