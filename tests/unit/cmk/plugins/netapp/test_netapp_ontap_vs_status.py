#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from cmk.agent_based.v2 import CheckResult, Result, State
from cmk.plugins.netapp.agent_based.netapp_ontap_vs_status import (
    check_netapp_ontap_vs_status,
)
from cmk.plugins.netapp.models import SvmModel


class SvmModelFactory(ModelFactory):
    __model__ = SvmModel


@pytest.mark.parametrize(
    "svm_models, expected_result",
    [
        pytest.param(
            [SvmModelFactory.build(name="svm_name", state=None, subtype=None)],
            [],
            id="Svm without state",
        ),
        pytest.param(
            [SvmModelFactory.build(name="svm_name", state="running", subtype=None)],
            [Result(state=State.OK, summary="State: running")],
            id="Svm running",
        ),
        pytest.param(
            [SvmModelFactory.build(name="svm_name", state="stopped", subtype="dp_destination")],
            [
                Result(state=State.OK, summary="State: stopped"),
                Result(state=State.OK, summary="Subtype: dp_destination"),
            ],
            id="Svm stopped dp_destination",
        ),
        pytest.param(
            [SvmModelFactory.build(name="svm_name", state="stopped", subtype="sync_destination")],
            [
                Result(state=State.OK, summary="State: stopped"),
                Result(state=State.OK, summary="Subtype: sync_destination"),
            ],
            id="Svm stopped sync_destination",
        ),
        pytest.param(
            [SvmModelFactory.build(name="svm_name", state="stopped", subtype="other_subtype")],
            [
                Result(state=State.CRIT, summary="State: stopped"),
                Result(state=State.OK, summary="Subtype: other_subtype"),
            ],
            id="Svm stopped other subtype",
        ),
    ],
)
def test_check_netapp_ontap_vs_status(
    svm_models: Sequence[SvmModel], expected_result: CheckResult
) -> None:
    svm_section = {svm.name: svm for svm in svm_models}

    result = list(check_netapp_ontap_vs_status("svm_name", svm_section))
    assert result == expected_result
