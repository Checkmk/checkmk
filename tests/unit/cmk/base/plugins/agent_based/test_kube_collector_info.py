#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.base.plugins.agent_based import kube_collector_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.utils.kube import (
    CollectorComponents,
    CollectorHandlerLog,
    CollectorState,
)


def test_parse():
    string_table_element = json.dumps(
        {
            "container": {"status": "ok", "title": "title", "detail": "detail"},
            "machine": {"status": "ok", "title": "title", "detail": "detail"},
        }
    )
    assert kube_collector_info.parse([[string_table_element]]) == CollectorComponents(
        container=CollectorHandlerLog(status=CollectorState.OK, title="title", detail="detail"),
        machine=CollectorHandlerLog(status=CollectorState.OK, title="title", detail="detail"),
    )


def test_check_ok_connection():
    check_result = list(
        kube_collector_info.check(
            CollectorComponents(
                container=CollectorHandlerLog(status=CollectorState.OK, title="title", detail="OK"),
                machine=CollectorHandlerLog(status=CollectorState.OK, title="title", detail="OK"),
            )
        )
    )
    assert len(check_result) == 2
    assert all(isinstance(result, Result) for result in check_result)
    assert all(result.state == State.OK for result in check_result if isinstance(result, Result))
    assert all(
        result.summary.endswith("OK") for result in check_result if isinstance(result, Result)
    )


def test_check_errored_connection():
    check_result = list(
        kube_collector_info.check(
            CollectorComponents(
                container=CollectorHandlerLog(
                    status=CollectorState.ERROR, title="error", detail="ERROR"
                ),
                machine=CollectorHandlerLog(status=CollectorState.OK, title="ok", detail="OK"),
            )
        )
    )
    assert len(check_result) == 2
    assert all(isinstance(result, Result) for result in check_result)
    assert any(result.state == State.CRIT for result in check_result if isinstance(result, Result))
    assert any(result.state == State.OK for result in check_result if isinstance(result, Result))
