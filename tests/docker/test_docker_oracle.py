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

    oracle_services = [
        _
        for _ in checkmk_docker_api_request(
            checkmk, "get", f"/objects/host/{hostname}/collections/services"
        ).json()["value"]
        if _.get("title").startswith("ORA")
    ]

    assert len(oracle_services) >= 18
