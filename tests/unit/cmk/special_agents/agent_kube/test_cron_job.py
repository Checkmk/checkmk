#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable

import pytest
from pydantic_factories import ModelFactory

from cmk.special_agents import agent_kube as agent
from cmk.special_agents.utils_kubernetes.schemata import api


class CronJobFactory(ModelFactory):
    __model__ = api.CronJob


@pytest.fixture(name="api_cron_job")
def fixture_api_cron_job() -> api.CronJob:
    return CronJobFactory.build()


@pytest.fixture(name="cron_job")
def fixture_cron_job(api_cron_job: api.CronJob) -> agent.CronJob:
    return agent.CronJob(
        metadata=api_cron_job.metadata,
        spec=api_cron_job.spec,
    )


@pytest.mark.parametrize("cron_job_pods", [0, 10, 20])
def test_cron_job_pods(
    cron_job_pods: int, cron_job: agent.CronJob, new_pod: Callable[[], agent.Pod]
):
    for _ in range(cron_job_pods):
        cron_job.add_pod(new_pod())
    assert len(cron_job.pods()) == cron_job_pods
