#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.licensing.basics.protocol_version import (
    parse_usage_history_version,
    parse_verification_request_version,
    parse_verification_response_version,
)


@pytest.mark.parametrize(
    "version",
    ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1", "3.2"],
)
def test_usage_history_version_accepts_known_versions(version: str) -> None:
    assert parse_usage_history_version({"VERSION": version}) == version


def test_usage_history_version_rejects_unknown_version() -> None:
    with pytest.raises(ValueError, match="Unknown protocol version for the usage history: '0.9'"):
        parse_usage_history_version({"VERSION": "0.9"})


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param([], id="not a mapping"),
        pytest.param({}, id="no version"),
        pytest.param({"VERSION": 3.2}, id="version not a string"),
    ],
)
def test_usage_history_version_rejects_malformed_report(raw: object) -> None:
    with pytest.raises(TypeError):
        parse_usage_history_version(raw)


@pytest.mark.parametrize(
    "version",
    ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1", "3.2"],
)
def test_verification_request_version_accepts_known_versions(version: str) -> None:
    assert parse_verification_request_version({"VERSION": version}) == version


def test_verification_request_version_rejects_unknown_version() -> None:
    with pytest.raises(
        ValueError, match="Unknown protocol version for the verification request: '0.9'"
    ):
        parse_verification_request_version({"VERSION": "0.9"})


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param([], id="not a mapping"),
        pytest.param({}, id="no version"),
        pytest.param({"VERSION": 3.2}, id="version not a string"),
    ],
)
def test_verification_request_version_rejects_malformed_request(raw: object) -> None:
    with pytest.raises(TypeError):
        parse_verification_request_version(raw)


@pytest.mark.parametrize(
    "version",
    ["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1", "3.2"],
)
def test_verification_response_version_accepts_known_versions(version: str) -> None:
    assert parse_verification_response_version({"VERSION": version}) == version


def test_verification_response_version_rejects_unknown_version() -> None:
    with pytest.raises(
        ValueError, match="Unknown protocol version for the verification response: '0.9'"
    ):
        parse_verification_response_version({"VERSION": "0.9"})


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param([], id="not a mapping"),
        pytest.param({}, id="no version"),
        pytest.param({"VERSION": 3.2}, id="version not a string"),
    ],
)
def test_verification_response_version_rejects_malformed_response(raw: object) -> None:
    with pytest.raises(TypeError):
        parse_verification_response_version(raw)
