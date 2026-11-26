#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Count the hosts per operating system and release series of their Checkmk agent

The operating system comes from the host labels the "check_mk" agent section creates. The
agent version is in no livestatus column, only in the output of the "Check_MK Agent"
service, so it is read from there. test_checkmk_agent_product_usage.py, next to the tests
of the check plug-in, makes sure its output still has the format read here.

Only the release series of the agent and the first two parts of the OS version are sent:
exact patch levels would tell which sites run agents with known vulnerabilities.
"""

import re
from collections import Counter
from collections.abc import Mapping

from cmk.ccc.version import Version
from cmk.livestatus_client import LocalConnection
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables import Services
from cmk.product_usage.schema import AgentsData

_SERVICE_DESCRIPTION = "Check_MK Agent"

# The check engine joins the summaries of the results with ", " and may append a state
# marker, the check plug-in may append a version mismatch:
# "Version: 2.3.0p30 (expected ...)(!)"
_RE_VERSION = re.compile(r"(?:^|, )Version: ([^\s,(]+)")

_UNKNOWN = "unknown"
_OTHER = "other"


def collect() -> AgentsData:
    query = Query([Services.host_labels, Services.plugin_output]).filter(
        Services.description == _SERVICE_DESCRIPTION
    )

    by_version: dict[str, Counter[str]] = {}
    by_os: dict[str, Counter[str]] = {}
    for labels, plugin_output in LocalConnection().query(query.compile()):
        os_family = labels.get("cmk/os_family", _UNKNOWN)
        raw_version = parse_agent_version(plugin_output)
        version = _UNKNOWN if raw_version is None else release_series(raw_version)
        by_version.setdefault(version, Counter())[os_family] += 1

        os_name = labels.get("cmk/os_name", _UNKNOWN)
        os_version = labels.get("cmk/os_version")
        by_os.setdefault(os_name, Counter())[
            _UNKNOWN if os_version is None else shorten_os_version(os_version)
        ] += 1

    return AgentsData(by_version=_to_dict(by_version), by_os=_to_dict(by_os))


def _to_dict(histogram: Mapping[str, Counter[str]]) -> dict[str, dict[str, int]]:
    return {key: dict(counts) for key, counts in histogram.items()}


def parse_agent_version(plugin_output: str) -> str | None:
    """Read the agent version from the output of the "Check_MK Agent" service"""
    return match.group(1) if (match := _RE_VERSION.search(plugin_output)) else None


def release_series(raw_version: str) -> str:
    """The release series of an agent version, "2.4.0" for "2.4.0p12"

    A version that is no release, such as a daily build of the master branch, is "other".
    """
    try:
        base = Version.from_str(raw_version).version_base
    except ValueError:
        return _OTHER
    return base or _OTHER


def shorten_os_version(os_version: str) -> str:
    """The first two parts of an OS version, split at "." and "-"

    "10.0.17763" -> "10.0", "7200-05-03-2148" -> "7200-05"
    """
    return "".join(re.split(r"([.-])", os_version)[:3])
