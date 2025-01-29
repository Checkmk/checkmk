#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime

import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

import cmk.plugins.netapp.agent_based.netapp_ontap_aggr as ontap_aggr
from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS
from cmk.plugins.netapp.agent_based.netapp_ontap_aggr import check_netapp_ontap_aggr
from cmk.plugins.netapp.models import AggregateModel, AggregateSpace

NOW_SIMULATED = "1988-06-08 17:00:00.000000"
LAST_TIME_EPOCH = (
    datetime.strptime("1988-06-08 16:00:00.000000", "%Y-%m-%d %H:%M:%S.%f") - datetime(1970, 1, 1)
).total_seconds()


class AggregateModelFactory(ModelFactory):
    __model__ = AggregateModel


class AggregateSpaceFactory(ModelFactory):
    __model__ = AggregateSpace


class BlockStorageFactory(ModelFactory):
    __model__ = AggregateSpace.BlockStorage


@pytest.fixture(name="value_store_patch")
def value_store_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    value_store_patched = {
        #                          last time, last value
        "aggregate1.delta": (LAST_TIME_EPOCH, 0.0),
    }
    monkeypatch.setattr(ontap_aggr, "get_value_store", lambda: value_store_patched)


def test_check_netapp_ontap_aggr_ok(
    value_store_patch: None,
) -> None:
    aggregate_model = AggregateModelFactory.build(
        name="aggregate1",
        space=AggregateSpaceFactory.build(
            block_storage=BlockStorageFactory.build(size=10_000_000_000, available=5_000_000_000)
        ),
    )
    section = {aggregate_model.name: aggregate_model}

    result = list(
        check_netapp_ontap_aggr(
            item="aggregate1",
            params=FILESYSTEM_DEFAULT_PARAMS,
            section=section,
        )
    )

    assert isinstance(result[2], Metric)
    assert result[2].name == "fs_used_percent"
    assert result[3] == Result(state=State.OK, summary="Used: 50.00% - 4.66 GiB of 9.31 GiB")


def test_check_netapp_ontap_aggr_warn(
    value_store_patch: None,
) -> None:
    aggregate_model = AggregateModelFactory.build(
        name="aggregate1",
        space=AggregateSpaceFactory.build(
            block_storage=BlockStorageFactory.build(size=10_000_000_000, available=5_000_000_000)
        ),
    )
    section = {aggregate_model.name: aggregate_model}

    result = list(
        check_netapp_ontap_aggr(
            item="aggregate1",
            params={**FILESYSTEM_DEFAULT_PARAMS, **{"levels": (10.0, 90.0)}},
            section=section,
        )
    )

    assert isinstance(result[2], Metric)
    assert result[2].name == "fs_used_percent"
    assert isinstance(result[3], Result)
    assert result[3].state == State.WARN and result[3].summary.startswith("Used: 50.00%")


def test_check_netapp_ontap_aggr_not_present(
    value_store_patch: None,
) -> None:
    aggregate_model = AggregateModelFactory.build(name="aggregate1")
    section = {aggregate_model.name: aggregate_model}

    result = check_netapp_ontap_aggr(
        item="aggregate_not_present",
        params=FILESYSTEM_DEFAULT_PARAMS,
        section=section,
    )
    assert len(list(result)) == 0


def test_check_netapp_ontap_aggr_without_data(
    value_store_patch: None,
) -> None:
    aggregate_model = AggregateModelFactory.build(
        name="aggregate1",
        space=AggregateSpaceFactory.build(
            block_storage=BlockStorageFactory.build(
                available=None,
                size=None,
            )
        ),
    )
    section = {aggregate_model.name: aggregate_model}

    result = check_netapp_ontap_aggr(
        item="aggregate1",
        params=FILESYSTEM_DEFAULT_PARAMS,
        section=section,
    )
    assert len(list(result)) == 0
