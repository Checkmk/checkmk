#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import logging

import docker  # type: ignore[import-untyped]

from tests.testlib.docker import checkmk_docker_api_request

logger = logging.getLogger()


def test_docker_oracle(
    checkmk: docker.models.containers.Container,
    oracle: docker.models.containers.Container,
) -> None:
    hostname = "oracle"
    service_prefix = "ORA FREE"
    instance = "FREEPDB1"
    expected_services = [
        {"state": 0} | _
        for _ in [
            {"description": f"{service_prefix}.CDB$ROOT Locks"},
            {"description": f"{service_prefix}.CDB$ROOT Long Active Sessions"},
            {"description": f"{service_prefix}.CDB$ROOT Performance"},
            {"description": f"{service_prefix}.CDB$ROOT Sessions"},
            {"description": f"{service_prefix}.{instance} Instance"},
            {"description": f"{service_prefix}.{instance} Locks"},
            {"description": f"{service_prefix}.{instance} Long Active Sessions"},
            {"description": f"{service_prefix}.{instance} Performance"},
            {"description": f"{service_prefix}.{instance} Recovery Status"},
            {"description": f"{service_prefix}.{instance} Sessions"},
            {"description": f"{service_prefix}.{instance} Uptime"},
            {"description": f"{service_prefix} Instance"},
            {"description": f"{service_prefix} Locks"},
            {"description": f"{service_prefix} Logswitches"},
            {"description": f"{service_prefix} Long Active Sessions"},
            {"description": f"{service_prefix}.PDB$SEED Instance"},
            {"description": f"{service_prefix}.PDB$SEED Performance"},
            {"description": f"{service_prefix}.PDB$SEED Recovery Status"},
            {"description": f"{service_prefix}.PDB$SEED Uptime"},
            {"description": f"{service_prefix} Processes"},
            {"description": f"{service_prefix} Recovery Status"},
            {"description": f"{service_prefix} Sessions"},
            {"description": f"{service_prefix} Undo Retention"},
            {"description": f"{service_prefix} Uptime"},
        ]
    ]
    actual_services = [
        _.get("extensions")
        for _ in checkmk_docker_api_request(
            checkmk,
            "get",
            f"/objects/host/{hostname}/collections/services?columns=state&columns=description",
        ).json()["value"]
        if _.get("title").upper().startswith(service_prefix)
    ]

    missing_services = [
        f'{service.get("description")} (expected state: {service.get("state")}'
        for service in expected_services
        if service.get("description") not in [_.get("description") for _ in actual_services]
    ]
    assert len(missing_services) == 0, f"Missing services: {missing_services}"

    unexpected_services = [
        f'{service.get("description")} (actual state: {service.get("state")}'
        for service in actual_services
        if service.get("description") not in [_.get("description") for _ in expected_services]
    ]
    assert len(unexpected_services) == 0, f"Unexpected services: {unexpected_services}"

    invalid_services = [
        f'{service.get("description")} ({expected_state=}; {actual_state=})'
        for service in actual_services
        if (actual_state := service.get("state"))
        != (
            expected_state := next(
                (
                    _.get("state", 0)
                    for _ in expected_services
                    if _.get("description") == service.get("description")
                ),
                0,
            )
        )
    ]
    assert len(invalid_services) == 0, f"Invalid services: {invalid_services}"
