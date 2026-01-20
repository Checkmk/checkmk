#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from collections import defaultdict

from cmk.livestatus_client import LocalConnection
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables import Services
from cmk.product_telemetry.exceptions import (
    ServicesInfoLengthError,
)
from cmk.product_telemetry.schema import CheckData, Checks


def collect() -> Checks:
    connection = LocalConnection()
    return merge_check_data(
        _get_services(connection),
        _get_disabled_services(connection),
    )


def _get_services(connection: LocalConnection) -> Checks:
    count_checks_on_hosts = defaultdict(set)

    query = Query([Services.check_type, Services.host_name, Services.check_command]).compile()

    rows = connection.query(query)
    checks: Checks = {}

    if len(rows) == 0:
        return checks
        # raise NoServicesInfoError

    for row in rows:
        if len(row) != 3:
            raise ServicesInfoLengthError

        host_name = row[1].strip()

        # We do not want to include anything after a "!" in the check command, this might contain sensitive info
        check_command = row[2].split("!")[0]

        # Add the check command to the dict if it doesn't exist and increment the count
        value = checks.setdefault(
            check_command,
            {"count_hosts": 0, "count": 0, "count_disabled": 0},
        )
        value["count"] += 1

        # Keep track which host uses a particular check
        count_checks_on_hosts[check_command].add(host_name)

    # Count of unique hosts for each service and add to the checks dict
    for service, service_hosts in count_checks_on_hosts.items():
        value = checks.setdefault(
            service,
            {"count_hosts": 0, "count": 0, "count_disabled": 0},
        )
        value["count_hosts"] = len(service_hosts)

    return checks


def _get_disabled_services(connection: LocalConnection) -> Checks:
    query = (
        Query([Services.long_plugin_output])
        .filter(Services.check_command.equals("check-mk-inventory"))
        .compile()
    )

    rows = connection.query(query)
    checks: Checks = {}

    for row in rows:
        long_output = row[0]

        if not long_output:
            continue

        # This is a long string divided by \n so we split on it and have the individual lines
        # We are only interested in the lines that start with ""Service ignored: "". These describe disabled services
        for line in long_output.splitlines():
            if not line.startswith("Service ignored: "):
                continue

            match = re.search(r"Service ignored: (.*?)(:|$)", line)
            if not match:
                continue

            ignored_service = match.group(1)
            value = checks.setdefault(
                ignored_service,
                {"count_hosts": 0, "count": 0, "count_disabled": 0},
            )
            value["count_disabled"] += 1

    return checks


def merge_check_data(checks1: Checks, checks2: Checks) -> Checks:
    result = checks1.copy()
    for key, value in checks2.items():
        if key in result:
            result[key] = CheckData(
                count=result[key]["count"] + value["count"],
                count_hosts=result[key]["count_hosts"] + value["count_hosts"],
                count_disabled=result[key]["count_disabled"] + value["count_disabled"],
            )
        else:
            result[key] = value

    return result
