#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.storeonce4x_appliances import (
    check_storeonce4x_appliances,
    check_storeonce4x_appliances_license,
    check_storeonce4x_appliances_storage,
    check_storeonce4x_appliances_summaries,
    discover_storeonce4x_appliances,
    parse_storeonce4x_appliances,
    Section,
)
from cmk.plugins.lib import storeonce
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

STRING_TABLE = [
    [
        '{"members": [{"uuid": "bcc0842d7420290ccc3d061ec23ce", "address": "127.0.0.1", "hostname": "myhostname", "productName": "HPE StoreOnce 5250", "serialNumber": "123456789", "localhost": true, "applianceState": 0, "stateUpdatedDate": "2020-05-11T10:45:51.807Z", "federationApiVersion": 1, "applianceStateString": "Reachable", "sinceStateUpdatedSeconds": 1493050}]}'
    ],
    [
        '{"uuid": "bcc0842d7420290ccc3d061ec23ce", "hostname": "myhostname", "platformType": "HPE StoreOnce 5250", "softwareVersion": "4.1.3-1921.10", "softwareUpdateRecommended": false, "recommendedSoftwareVersion": "", "localDiskBytes": 100792069099520, "localUserBytes": 1014343032520056, "localFreeBytes": 258734285025280, "localCapacityBytes": 359526354124800, "cloudDiskBytes": 0, "cloudUserBytes": 0, "cloudFreeBytes": 0, "cloudCapacityBytes": 0, "catalystDataJobSessions": 10, "nasNumDedupeSessions": 0, "vtlNumActiveSessions": 0, "catalystInboundCopyJobSessions": 0, "catalystOutboundCopyJobSessions": 0, "repNumSourceJobs": 0, "repNumTargetJobs": 0, "maxStreamsLimit": 512, "metricsCpuTotal": 8.49826, "metricsMemoryTotalPhysical": 506482655232, "metricsMemoryUsedPercent": 6.7811, "metricsDataDiskUtilisationPercent": 97.3215, "applianceStatus": "WARNING", "applianceStatusString": "Warning", "dataServicesStatus": "OK", "dataServicesStatusString": "OK", "licenseStatus": "OK", "licenseStatusString": "OK", "userStorageStatus": "OK", "userStorageStatusString": "OK", "hardwareStatus": "WARNING", "hardwareStatusString": "Warning", "remoteSupportStatus": "OK", "remoteSupportStatusString": "OK", "catStoresSummary": {"statusSummary": {"numOk": 4, "numWarning": 0, "numCritical": 0, "numUnknown": 0, "total": 4}}, "cloudBankStoresSummary": {"statusSummary": {"numOk": 0, "numWarning": 0, "numCritical": 0, "numUnknown": 0, "total": 0}}, "nasSharesSummary": {"statusSummary": {"numOk": 0, "numWarning": 0, "numCritical": 0, "numUnknown": 0, "total": 0}}, "vtlLibrariesSummary": {"statusSummary": {"numOk": 0, "numWarning": 0, "numCritical": 0, "numUnknown": 0, "total": 0}}, "nasRepMappingSummary": {"statusSummary": {"numOk": 0, "numWarning": 0, "numCritical": 0, "numUnknown": 0, "total": 0}}, "vtlRepMappingSummary": {"statusSummary": {"numOk": 0, "numWarning": 0, "numCritical": 0, "numUnknown": 0, "total": 0}}, "systemLocation": "ZH1", "contactName": "Roger Huegi", "contactNumber": "+41 34 426 13 13", "contactEmail": "tm-system@wagner.ch", "diskBytes": 100792069099520, "userBytes": 1014343032520056, "totalActiveSessions": 10, "capacitySavedBytes": 913550963420536, "capacitySavedPercent": 90.06332, "dedupeRatio": 10.06372}'
    ],
]


@pytest.fixture(name="section", scope="module")
def _get_section() -> Section:
    return parse_storeonce4x_appliances(STRING_TABLE)


def test_discovery(section: Section) -> None:
    assert list(discover_storeonce4x_appliances(section)) == [Service(item="myhostname")]


def test_check(section: Section) -> None:
    assert list(check_storeonce4x_appliances("myhostname", section)) == [
        Result(
            state=State.OK,
            summary=(
                "State: Reachable, Serial Number: 123456789, "
                "Software version: 4.1.3-1921.10, Product Name: HPE StoreOnce 5250"
            ),
        ),
    ]


def test_check_storage(monkeypatch: pytest.MonkeyPatch, section: Section) -> None:
    monkeypatch.setattr(
        storeonce,
        "get_value_store",
        lambda: {"myhostname.delta": (1356034260.0, 96122807.59765625)},
    )
    with time_machine.travel(datetime.datetime(2012, 12, 20, 20, 12, tzinfo=ZoneInfo("UTC"))):
        assert list(
            check_storeonce4x_appliances_storage("myhostname", FILESYSTEM_DEFAULT_PARAMS, section)
        ) == [
            Metric(
                "fs_used",
                96122807.59765625,
                levels=(274296840.0, 308583945.0),
                boundaries=(0, 342871050.0),
            ),
            Metric("fs_free", 246748242.40234375, boundaries=(0, None)),
            Metric(
                "fs_used_percent", 28.034681725872236, levels=(80.0, 90.0), boundaries=(0.0, 100.0)
            ),
            Result(
                state=State.OK,
                summary="Used: 28.03% - 91.7 TiB of 327 TiB",
            ),
            Metric("fs_size", 342871050.0, boundaries=(0, None)),
            Metric("growth", 0.0),
            Result(state=State.OK, summary="trend per 1 day 0 hours: +0 B"),
            Result(state=State.OK, summary="trend per 1 day 0 hours: +0%"),
            Metric("trend", 0.0),
            Result(state=State.OK, summary="Total local: 327 TiB"),
            Result(state=State.OK, summary="Free local: 235 TiB"),
            Result(state=State.OK, summary="Dedup ratio: 10.06"),
            Metric("dedup_rate", 10.06372),
        ]


def test_check_licenses(section: Section) -> None:
    assert list(check_storeonce4x_appliances_license("myhostname", section)) == [
        Result(
            state=State.OK,
            summary="Status: OK",
        ),
    ]


def test_check_summaries(section: Section) -> None:
    assert list(check_storeonce4x_appliances_summaries("myhostname", section)) == [
        Result(
            state=State.OK,
            summary="Cat stores Ok (4 of 4)",
        ),
    ]
