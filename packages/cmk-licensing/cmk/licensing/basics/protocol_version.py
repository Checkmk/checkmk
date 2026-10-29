#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pathlib import Path
from typing import Final, Literal

from cmk.ccc.version import Edition, edition

AllowedUsageHistoryVersions = Literal[
    "1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1", "3.2"
]
CURRENT_USAGE_HISTORY_VERSION: Final[AllowedUsageHistoryVersions] = "3.2"

AllowedVerificationRequestVersions = Literal[
    "1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1", "3.2"
]
CURRENT_VERIFICATION_REQUEST_VERSION: Final[AllowedVerificationRequestVersions] = "3.2"

AllowedVerificationResponseVersions = Literal[
    "1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1", "3.2"
]
CURRENT_VERIFICATION_RESPONSE_VERSION: Final[AllowedVerificationResponseVersions] = "3.2"


def parse_usage_history_version(raw: object) -> AllowedUsageHistoryVersions:
    if not isinstance(raw, dict):
        raise TypeError(raw)
    if not isinstance(raw_version := raw.get("VERSION"), str):
        raise TypeError(raw_version)
    match raw_version:
        case "1.0" | "1.1" | "1.2" | "1.3" | "1.4" | "1.5" | "2.0" | "2.1" | "3.0" | "3.1" | "3.2":
            return raw_version
        case other:
            raise ValueError(f"Unknown protocol version for the usage history: {other!r}")


def parse_verification_request_version(raw: object) -> AllowedVerificationRequestVersions:
    if not isinstance(raw, dict):
        raise TypeError(raw)
    if not isinstance(raw_version := raw.get("VERSION"), str):
        raise TypeError(raw_version)
    match raw_version:
        case "1.0" | "1.1" | "1.2" | "1.3" | "1.4" | "1.5" | "2.0" | "2.1" | "3.0" | "3.1" | "3.2":
            return raw_version
        case other:
            raise ValueError(f"Unknown protocol version for the verification request: {other!r}")


def parse_verification_response_version(raw: object) -> AllowedVerificationResponseVersions:
    if not isinstance(raw, dict):
        raise TypeError(raw)
    if not isinstance(raw_version := raw.get("VERSION"), str):
        raise TypeError(raw_version)
    match raw_version:
        case "1.0" | "1.1" | "1.2" | "1.3" | "1.4" | "1.5" | "2.0" | "2.1" | "3.0" | "3.1" | "3.2":
            return raw_version
        case other:
            raise ValueError(f"Unknown protocol version for the verification response: {other!r}")


def get_licensing_protocol_version(
    omd_root: Path,
) -> Literal["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1", "3.2"]:
    """Returns the current licensing protocol version."""
    if edition(omd_root) == Edition.CLOUD:
        return "3.2"
    return "3.2"
