#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import Result, State
from cmk.plugins.netapp.agent_based.netapp_ontap_luns import _check_netapp_ontap_luns
from cmk.plugins.netapp.models import LunModel


class LunModelFactory(ModelFactory):
    __model__ = LunModel


def test_check_netapp_luns() -> None:
    lun_model = LunModelFactory.build(
        name="/vol/test/lun1", volume_name="test_volume_name", svm_name="test_svm_name"
    )
    section = {lun_model.item_name(): lun_model}

    result = list(
        _check_netapp_ontap_luns(
            "lun1",
            {  # not revelevant for this test - but needed
                "levels": (80.0, 90.0),
                "trend_range": 24,
            },
            section,
            # not revelevant for this test - but needed:
            {"lun1.delta": (0.0, 0.0)},
            0.0,
        )
    )

    assert result[:2] == [
        Result(state=State.OK, summary="Volume: test_volume_name"),
        Result(state=State.OK, summary="SVM: test_svm_name"),
    ]
