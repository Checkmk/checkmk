#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pydantic_factories

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.inventory_kube_cronjob import inventory_kube_cronjob
from cmk.base.plugins.agent_based.utils.kube import CronJobInfo


class CronJobInfoFactory(pydantic_factories.ModelFactory):
    __model__ = CronJobInfo


def test_inventory_kube_cronjob() -> None:
    section = CronJobInfoFactory.build(name="name", namespace="namespace")
    attributes = list(inventory_kube_cronjob(section))
    assert attributes == [
        Attributes(
            path=["software", "applications", "kube", "metadata"],
            inventory_attributes={
                "object": "CronJob",
                "name": "name",
                "namespace": "namespace",
            },
        )
    ]
