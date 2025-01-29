#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Result, State
from cmk.plugins.collection.agent_based.kube_cronjob_info import check_kube_cronjob_info
from cmk.plugins.kube.schemata.api import ConcurrencyPolicy, NamespaceName, Timestamp
from cmk.plugins.kube.schemata.section import CronJobInfo, FilteredAnnotations


def test_check_kube_cronjob_info() -> None:
    section = CronJobInfo(
        name="cronjob",
        namespace=NamespaceName("checkmk-monitoring"),
        creation_timestamp=Timestamp(1600000000.0),
        labels={},
        annotations=FilteredAnnotations({}),
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
