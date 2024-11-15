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


def test_check_netapp_luns_no_used_space() -> None:
    lun_model = LunModelFactory.build(
        name="/vol/test/lun1",
        volume_name="test_volume_name",
        svm_name="test_svm_name",
        space_used=None,
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

    assert result == [
        Result(state=State.OK, summary="Volume: test_volume_name"),
        Result(state=State.OK, summary="SVM: test_svm_name"),
        Result(state=State.UNKNOWN, summary="Space used is unknown"),
    ]


def test_check_netapp_luns_no_read_only() -> None:
    lun_model = LunModelFactory.build(
        name="/vol/test/lun1",
        volume_name="test_volume_name",
        svm_name="test_svm_name",
        read_only=None,
        space_used=20,
        enabled=False,
    )
    section = {lun_model.item_name(): lun_model}

    result = list(
        _check_netapp_ontap_luns(
            "lun1",
            {
                "read_only": False,
                # not revelevant for this test - but needed:
                "levels": (80.0, 90.0),
                "trend_range": 24,
            },
            section,
            # not revelevant for this test - but needed:
            {"lun1.delta": (0.0, 0.0)},
            0.0,
        )
    )

    assert result[:4] == [
        Result(state=State.OK, summary="Volume: test_volume_name"),
        Result(state=State.OK, summary="SVM: test_svm_name"),
        Result(state=State.CRIT, summary="LUN is offline"),
        Result(state=State.WARN, summary="read-only is unknown (expected: false)"),
    ]


def test_check_netapp_luns_read_only_false() -> None:
    lun_model = LunModelFactory.build(
        name="/vol/test/lun1",
        volume_name="test_volume_name",
        svm_name="test_svm_name",
        read_only=False,
        space_used=20,
        enabled=False,
    )
    section = {lun_model.item_name(): lun_model}

    result = list(
        _check_netapp_ontap_luns(
            "lun1",
            {
                "read_only": True,
                # not revelevant for this test - but needed:
                "levels": (80.0, 90.0),
                "trend_range": 24,
            },
            section,
            # not revelevant for this test - but needed:
            {"lun1.delta": (0.0, 0.0)},
            0.0,
        )
    )

    assert result[:4] == [
        Result(state=State.OK, summary="Volume: test_volume_name"),
        Result(state=State.OK, summary="SVM: test_svm_name"),
        Result(state=State.CRIT, summary="LUN is offline"),
        Result(state=State.WARN, summary="read-only is false (expected: true)"),
    ]
