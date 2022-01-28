#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.plugins.agent_based import kube_collector_connection
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.utils.kube import CollectorLog, CollectorLogs, CollectorState


def test_check_ok_connection():
    check_result = list(
        kube_collector_connection.check(
            CollectorLogs(
                logs=[
                    CollectorLog(
                        status=CollectorState.OK, component="Machine Metrics", message="OK"
                    )
                ]
            )
        )
    )
    assert len(check_result) == 1
    assert isinstance(check_result[0], Result)
    assert check_result[0].state == State.OK


def test_check_errored_connection():
    check_result = list(
        kube_collector_connection.check(
            CollectorLogs(
                logs=[
                    CollectorLog(
                        status=CollectorState.ERROR, component="Machine Metrics", message="ERROR"
                    )
                ]
            )
        )
    )
    assert len(check_result) == 1
    assert isinstance(check_result[0], Result)
    assert check_result[0].details.startswith("Machine Metrics: ")
    assert check_result[0].state == State.CRIT


def test_multi_logs_connection():
    check_result = list(
        kube_collector_connection.check(
            CollectorLogs(
                logs=[
                    CollectorLog(
                        status=CollectorState.OK, component="Machine Metrics", message="OK"
                    ),
                    CollectorLog(
                        status=CollectorState.OK, component="Container Metrics", message="OK"
                    ),
                ]
            )
        )
    )
    assert len(check_result) == 2
    assert all(isinstance(result, Result) for result in check_result)
