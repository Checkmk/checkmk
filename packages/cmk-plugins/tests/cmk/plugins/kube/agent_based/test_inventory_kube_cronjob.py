#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"


import polyfactory.factories.pydantic_factory

from cmk.agent_based.v2 import Attributes
from cmk.plugins.kube.agent_based.inventory_kube_cronjob import inventorize_kube_cronjob
from cmk.plugins.kube.schemata.section import CronJobInfo


class CronJobInfoFactory(polyfactory.factories.pydantic_factory.ModelFactory):
    __model__ = CronJobInfo


def test_inventorize_kube_cronjob() -> None:
    section = CronJobInfoFactory.build(name="name", namespace="namespace")
    attributes = list(inventorize_kube_cronjob(section))
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
