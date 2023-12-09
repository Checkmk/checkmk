#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from base64 import b64decode
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

import xmltodict
from pydantic import BaseModel, BeforeValidator, Field
from typing_extensions import Annotated

from .robotmk_rebot_xml import Rebot, RFTest, Suite


class AttemptOutcome(Enum):
    AllTestsPassed = "AllTestsPassed"
    TestFailures = "TestFailures"
    RobotFrameworkFailure = "RobotFrameworkFailure"
    EnvironmentFailure = "EnvironmentFailure"
    TimedOut = "TimedOut"


class AttemptOutcomeOtherError(BaseModel, frozen=True):
    OtherError: str


def _parse_xml(xml_value: str) -> Rebot:
    return Rebot.model_validate(xmltodict.parse(xml_value))


def _decode_b64(encoded: str) -> bytes:
    return b64decode(encoded)


class XML(BaseModel, frozen=True):
    raw_xml: str
    rebot: Rebot

    @classmethod
    def from_raw_xml(cls, raw_xml: str) -> typing.Self:
        return cls(
            raw_xml=raw_xml,
            rebot=_parse_xml(raw_xml),
        )


class RebotResult(BaseModel, frozen=True):
    xml: Annotated[XML, BeforeValidator(XML.from_raw_xml)]
    # Note: pydantic complains if we replace _decode_b64 --> b64decode
    html: Annotated[bytes, BeforeValidator(_decode_b64)] = Field(alias="html_base64")
    timestamp: int


class RebotOutcomeResult(BaseModel, frozen=True):
    Ok: RebotResult


class RebotOutcomeError(BaseModel, frozen=True):
    Error: str


class AttemptsConfig(BaseModel, frozen=True):
    interval: int
    timeout: int
    n_attempts_max: int


class SuiteExecutionReport(BaseModel, frozen=True):
    suite_id: str
    attempts: Sequence[AttemptOutcome | AttemptOutcomeOtherError]
    rebot: RebotOutcomeResult | RebotOutcomeError | None
    config: AttemptsConfig


@dataclass(frozen=True, kw_only=True)
class SuiteRebotReport:
    top_level_suite: Suite
    timestamp: int


@dataclass(frozen=True, kw_only=True)
class SuiteReport:
    attempts: Sequence[AttemptOutcome | AttemptOutcomeOtherError]
    config: AttemptsConfig
    rebot: SuiteRebotReport | RebotOutcomeError | None


@dataclass(frozen=True, kw_only=True)
class TestReport:
    test: RFTest
    html: bytes
    attempts_config: AttemptsConfig
    rebot_timestamp: int


@dataclass(frozen=True, kw_only=True)
class Section:
    suites: Mapping[str, SuiteReport]
    tests: Mapping[str, TestReport]
