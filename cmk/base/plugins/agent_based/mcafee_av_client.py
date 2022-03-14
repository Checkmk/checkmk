#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from .agent_based_api.v1 import check_levels, register, render, Service


def parse_mcafee_av_client(string_table):
    """
    Section:
      # <<<mcafee_av_client>>>
      # 2015/05/06

    >>> timestamp = parse_mcafee_av_client([
    ...     ['2015/05/06'],
    ... ])
    >>> 1400000000.0 < timestamp < 1500000000.0  # exact value is timezone dependent
    True
    """
    # We assume that the timestamp is to be interpreted in the timezone of
    # the Checkmk server. This might be a problem, if e.g. the agent is located
    # in China and the Checkmk server in USA.
    return time.mktime(time.strptime(string_table[0][0], "%Y/%m/%d"))


register.agent_section(
    name="mcafee_av_client",
    parse_function=parse_mcafee_av_client,
)


def discover_mcafee_av_client(section):
    yield Service()


def check_mcafee_av_client(params, section):
    yield from check_levels(
        time.time() - section,
        levels_upper=params.get("signature_age"),
        render_func=render.timespan,
        label="Time since last update of signatures",
    )


register.check_plugin(
    name="mcafee_av_client",
    service_name="McAfee AV",
    discovery_function=discover_mcafee_av_client,
    check_function=check_mcafee_av_client,
    check_ruleset_name="mcafee_av_client",
    check_default_parameters={
        "signature_age": (86400, 7 * 86400),
    },
)
