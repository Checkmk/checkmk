#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The Veeam REST API revisions the special agent knows and supports.

The agent sections keep the format of the oldest revision, 1.3-rev1, so that the check
plug-ins read the same whichever revision the backup server answers in. For each newer
revision, `_CHANGES` lists the endpoints it changed compared with the revision before it,
each with a function that maps its response to the format of the revision before it.
`in_section_format` applies them to every response.
"""

from collections.abc import Callable, Iterable, Mapping
from enum import StrEnum

from cmk.plugins.veeam.lib import parse_iso8601_epoch


class ApiRevision(StrEnum):
    """A revision of the Veeam REST API, as sent in the `x-api-version` header."""

    V1_3_REV1 = "1.3-rev1"
    V1_3_REV2 = "1.3-rev2"


API_REVISIONS = (ApiRevision.V1_3_REV2, ApiRevision.V1_3_REV1)
"""The revisions the login tries, newest first: it settles on the first one the backup
server supports."""

MIN_VEEAM_VERSION = "13.0.1.180"
"""The first Veeam Backup & Replication build that supports the oldest of `API_REVISIONS`."""


type _ToPreviousRevision = Callable[[Mapping[str, object]], Mapping[str, object]]
"""Maps one object of an endpoint (one item, for a list endpoint) from a revision to the
format of the revision before it."""


def _protection_group_from_rev2(group: Mapping[str, object]) -> Mapping[str, object]:
    """1.3-rev2 made isDisabled optional and documents only `true` as disabled."""
    return {"isDisabled": False, **group}


def _replica_from_rev2(replica: Mapping[str, object]) -> Mapping[str, object]:
    """1.3-rev2 renamed the replica type Regular to Snapshot."""
    return {**replica, "type": "Regular"} if replica.get("type") == "Snapshot" else replica


_REV2_TO_REV1_REPOSITORY_TYPES = {
    "DellDataDomain": "DDBoost",
    "HPEStoreOnce": "HPStoreOnceIntegration",
    "QuantumDXi": "Quantum",
    "S3Integrated": "SmartObjectS3",
}
"""The repository types 1.3-rev2 renamed: their 1.3-rev1 name by their 1.3-rev2 name."""


def _repository_from_rev2(repository: Mapping[str, object]) -> Mapping[str, object]:
    """1.3-rev2 renamed four repository types."""
    match repository.get("type"):
        case str(rev2_type) if rev2_type in _REV2_TO_REV1_REPOSITORY_TYPES:
            return {**repository, "type": _REV2_TO_REV1_REPOSITORY_TYPES[rev2_type]}
        case _:
            return repository


def _earliest(dates: Iterable[object]) -> str | None:
    parsed: list[tuple[float, str]] = [
        (epoch, date)
        for date in dates
        if isinstance(date, str) and (epoch := parse_iso8601_epoch(date)) is not None
    ]
    return min(parsed)[1] if parsed else None


def _license_from_rev2(installed: Mapping[str, object]) -> Mapping[str, object]:
    """1.3-rev2 moved the license's expiry and support expiry into each license section
    (socket and instance).

    A license with several sections expires when the first of them does, so it takes the
    earliest dates of its sections.
    """
    sections = [
        section
        for key in ("socketLicenseSummary", "instanceLicenseSummary")
        if isinstance(section := installed.get(key), dict)
    ]
    dates = {
        key: earliest
        for key in ("expirationDate", "supportExpirationDate")
        if (earliest := _earliest(section.get(key) for section in sections)) is not None
    }
    return {**dates, **installed}


_REV2_CHANGES: Mapping[str, _ToPreviousRevision] = {
    "/api/v1/agents/protectionGroups": _protection_group_from_rev2,
    "/api/v1/replicas": _replica_from_rev2,
    "/api/v1/backupInfrastructure/repositories/states": _repository_from_rev2,
    "/api/v1/license": _license_from_rev2,
}


_CHANGES: Mapping[ApiRevision, Mapping[str, _ToPreviousRevision]] = {
    ApiRevision.V1_3_REV2: _REV2_CHANGES,
}
"""Per revision newer than 1.3-rev1, what it changed compared with the revision before it,
by endpoint path. An endpoint a revision did not change has no entry."""


def in_section_format(revision: ApiRevision, path: str, body: object) -> object:
    """The response `body` of `path`, answered in `revision`, as 1.3-rev1 returns it.

    Maps it to the format of each revision before `revision`, newest first, down to
    1.3-rev1. `path` may carry a query string; for a list endpoint, each item of `data` is
    mapped.
    """
    endpoint = path.split("?", 1)[0]
    converted = body
    # API_REVISIONS is newest first: walk from the server's revision down to 1.3-rev1.
    for rev in API_REVISIONS[API_REVISIONS.index(revision) :]:
        rev_change_callers = _CHANGES.get(rev, {})
        if endpoint in rev_change_callers:
            converted = _apply(rev_change_callers[endpoint], converted)
    return converted


def _apply(to_previous: _ToPreviousRevision, body: object) -> object:
    if isinstance(body, dict) and isinstance(items := body.get("data"), list):
        return {
            **body,
            "data": [to_previous(item) if isinstance(item, dict) else item for item in items],
        }
    return to_previous(body) if isinstance(body, dict) else body
