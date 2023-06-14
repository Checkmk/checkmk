#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State
from cmk.base.plugins.agent_based.kube_cronjob_info import check_kube_cronjob_info
from cmk.base.plugins.agent_based.utils.kube import (
    ConcurrencyPolicy,
    CronJobInfo,
    NamespaceName,
    Timestamp,
)


def test_check_kube_cronjob_info() -> None:
    section = CronJobInfo(
        name="cronjob",
        namespace=NamespaceName("checkmk-monitoring"),
        creation_timestamp=Timestamp(1600000000.0),
        labels={},
        annotations={},
        schedule="0 * * * *",
        concurrency_policy=ConcurrencyPolicy.Allow,
        failed_jobs_history_limit=10,
        successful_jobs_history_limit=10,
        suspend=False,
        cluster="cluster",
        kubernetes_cluster_hostname="host",
    )

    assert tuple(check_kube_cronjob_info(1600000001.0, section)) == (
        Result(state=State.OK, summary="Name: cronjob"),
        Result(state=State.OK, summary="Schedule: 0 * * * *"),
        Result(state=State.OK, summary="Age: 1 second"),
        Result(state=State.OK, notice="Concurrency policy: ConcurrencyPolicy.Allow"),
        Result(state=State.OK, notice="Failed jobs history limit: 10"),
        Result(state=State.OK, notice="Successful jobs history limit: 10"),
        Result(state=State.OK, notice="Suspend: False"),
    )
