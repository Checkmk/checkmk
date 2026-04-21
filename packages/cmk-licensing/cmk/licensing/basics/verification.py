#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import base64
import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import auto, Enum
from pathlib import Path
from typing import Literal, TypedDict
from uuid import UUID

from cmk.ccc import store
from cmk.crypto.certificate import Certificate, CertificatePEM
from cmk.licensing.basics.paths import get_verification_response_file_path
from cmk.licensing.basics.protocol_version import get_licensing_protocol_version


class InvalidVerificationResponse(ValueError):
    pass


class VerificationStatus(Enum):
    successful = auto()
    failed = auto()


class OperationalState(Enum):
    active = auto()
    confirmed_renewal = auto()
    suspended = auto()
    in_termination = auto()


class CheckmkEdition(Enum):
    cee = auto()
    cce = auto()
    cme = auto()
    cse = auto()


class RawAdditionalFeature(TypedDict):
    name: Literal["ntop", "virt1_appliance"]
    enabled: bool


class RawAdditionalLimitFeature(TypedDict):
    name: Literal["synthetic_monitoring"]
    enabled: bool
    limit: int


@dataclass(frozen=True)
class AdditionalFeature:
    name: Literal["ntop", "virt1_appliance"]
    enabled: bool

    def for_report(self) -> RawAdditionalFeature:
        return RawAdditionalFeature(name=self.name, enabled=self.enabled)


@dataclass(frozen=True)
class AdditionalLimitFeature:
    name: Literal["synthetic_monitoring"]
    enabled: bool
    limit: int

    def for_report(self) -> RawAdditionalLimitFeature:
        return RawAdditionalLimitFeature(name=self.name, enabled=self.enabled, limit=self.limit)


@dataclass(frozen=True)
class PlainVerificationResponse:
    """
    This class has the exact same fields as `VerificationResponse`.
    The sole purpose of this class is to represent a plain verification response
    without any additional methods or behavior, that introduce additional dependencies.
    We're creating this very early on during import.
    """

    VERSION: str
    request_id: UUID
    response_id: UUID
    created_at: int
    signature: bytes
    certificate: Certificate
    status: VerificationStatus
    message: str
    group_and_managed_services_use: bool
    reseller_name: str
    checkmk_edition: CheckmkEdition
    checkmk_max_version: str
    subscription_start_ts: int
    subscription_expiration_ts: int
    grace_period_after_expiration: int
    subscription_recurrence_unit: str
    subscription_auto_renewal: bool
    operational_state: OperationalState
    service_limit: int
    active_metric_series_limit: int
    unbound_license: bool
    additional_features: Sequence[AdditionalFeature | AdditionalLimitFeature]


def load_plain_verification_response(omd_root: Path) -> PlainVerificationResponse | None:
    if not (
        raw_dump := store.load_bytes_from_file(
            get_verification_response_file_path(omd_root), default=b""
        )
    ):
        return None

    try:
        raw = json.loads(raw_dump.decode("utf-8"))
        return parse(parse_protocol_version(raw), raw, omd_root=omd_root)
    except json.decoder.JSONDecodeError as e:
        raise InvalidVerificationResponse(f"Failed to load verification response: {e}") from e
    except (TypeError, ValueError, KeyError) as e:
        raise InvalidVerificationResponse(f"Failed to parse verification response: {e}") from e


def parse_protocol_version(
    raw: object,
) -> Literal["1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1", "3.2"]:
    if not isinstance(raw, dict):
        raise TypeError(raw)
    if not isinstance(raw_protocol_version := raw.get("VERSION"), str):
        raise TypeError(raw_protocol_version)
    match raw_protocol_version:
        case "1.0":
            return "1.0"
        case "1.1":
            return "1.1"
        case "1.2":
            return "1.2"
        case "1.3":
            return "1.3"
        case "1.4":
            return "1.4"
        case "1.5":
            return "1.5"
        case "2.0":
            return "2.0"
        case "2.1":
            return "2.1"
        case "3.0":
            return "3.0"
        case "3.1":
            return "3.1"
        case "3.2":
            return "3.2"
        case other:
            raise ValueError(f"Unknown protocol version: {other!r}")


def parse(
    protocol_version: Literal[
        "1.0", "1.1", "1.2", "1.3", "1.4", "1.5", "2.0", "2.1", "3.0", "3.1", "3.2"
    ],
    raw: object,
    *,
    omd_root: Path,
) -> PlainVerificationResponse:
    match protocol_version:
        case "1.0" | "1.1" | "1.2" | "1.3" | "1.4" | "1.5":
            raise ValueError(protocol_version)
        case "2.0" | "2.1":
            return parse_verification_response_v2_0(raw, omd_root=omd_root)
        case "3.0" | "3.1":
            return parse_verification_response_v3_0(raw, omd_root=omd_root)
        case "3.2":
            return parse_verification_response_v3_2(raw, omd_root=omd_root)


def parse_verification_response_v2_0(raw: object, *, omd_root: Path) -> PlainVerificationResponse:
    if not isinstance(raw, dict):
        raise TypeError(
            "Parse verification response for protocol versions 2.0/2.1: Wrong report type: %r"
            % type(raw)
        )
    if not isinstance(payload := raw.get("payload"), dict):
        raise TypeError("wrong payload type: %r" % type(payload))
    return PlainVerificationResponse(
        # After parsing we have the latest license protocol version
        VERSION=get_licensing_protocol_version(omd_root),
        request_id=UUID(raw["request_id"]),
        response_id=UUID(raw["response_id"]),
        created_at=int(raw["created_at"]),
        signature=base64.b64decode(str(raw["signature"]).encode("utf-8")),
        certificate=Certificate.load_pem(CertificatePEM(raw["certificate"])),
        status=VerificationStatus[payload["status"]],
        message=str(payload["message"]),
        group_and_managed_services_use=bool(payload["group_and_managed_services_use"]),
        reseller_name=str(payload["reseller_name"]),
        checkmk_edition=CheckmkEdition[payload["checkmk_edition"]],
        checkmk_max_version=str(payload["checkmk_max_version"]),
        subscription_start_ts=int(payload["subscription_start_ts"]),
        subscription_expiration_ts=int(payload["subscription_expiration_ts"]),
        grace_period_after_expiration=2592000,  # seconds in 30 days
        subscription_recurrence_unit="yearly",
        subscription_auto_renewal=bool(payload["subscription_auto_renewal"]),
        operational_state=OperationalState[payload["operational_state"]],
        service_limit=payload["limits"]["services"],
        active_metric_series_limit=payload["limits"]["services"],
        unbound_license=bool(payload["unbound_license"]),
        additional_features=[
            (
                AdditionalFeature(name="ntop", enabled=True)
                if "ntop" in payload["additional_features"]
                else AdditionalFeature(name="ntop", enabled=False)
            ),
            (
                AdditionalFeature(name="virt1_appliance", enabled=True)
                if "virt1_appliance" in payload["additional_features"]
                else AdditionalFeature(name="virt1_appliance", enabled=False)
            ),
        ],
    )


def parse_verification_response_v3_0(raw: object, *, omd_root: Path) -> PlainVerificationResponse:
    if not isinstance(raw, dict):
        raise TypeError(
            "Parse verification response for protocol versions 3.0/3.1: Wrong report type: %r"
            % type(raw)
        )
    if not isinstance(payload := raw.get("payload"), dict):
        raise TypeError("wrong payload type: %r" % type(payload))
    return PlainVerificationResponse(
        # After parsing we have the latest license protocol version
        VERSION=get_licensing_protocol_version(omd_root),
        request_id=UUID(raw["request_id"]),
        response_id=UUID(raw["response_id"]),
        created_at=int(raw["created_at"]),
        signature=base64.b64decode(str(raw["signature"]).encode("utf-8")),
        certificate=Certificate.load_pem(CertificatePEM(raw["certificate"])),
        status=VerificationStatus[payload["status"]],
        message=str(payload["message"]),
        group_and_managed_services_use=bool(payload["group_and_managed_services_use"]),
        reseller_name=str(payload["reseller_name"]),
        checkmk_edition=CheckmkEdition[payload["checkmk_edition"]],
        checkmk_max_version=str(payload["checkmk_max_version"]),
        subscription_start_ts=int(payload["subscription_start_ts"]),
        subscription_expiration_ts=int(payload["subscription_expiration_ts"]),
        grace_period_after_expiration=2592000,  # seconds in 30 days
        subscription_recurrence_unit="yearly",
        subscription_auto_renewal=bool(payload["subscription_auto_renewal"]),
        operational_state=OperationalState[payload["operational_state"]],
        service_limit=payload["service_limit"],
        active_metric_series_limit=payload["service_limit"],
        unbound_license=bool(payload["unbound_license"]),
        additional_features=parse_additional_features(payload["additional_features"]),
    )


def parse_verification_response_v3_2(raw: object, *, omd_root: Path) -> PlainVerificationResponse:
    if not isinstance(raw, dict):
        raise TypeError(
            "Parse verification response for protocol version 3.2: Wrong report type: %r"
            % type(raw)
        )
    if not isinstance(payload := raw.get("payload"), dict):
        raise TypeError("wrong payload type: %r" % type(payload))

    return PlainVerificationResponse(
        # After parsing we have the latest license protocol version
        VERSION=get_licensing_protocol_version(omd_root),
        request_id=UUID(raw["request_id"]),
        response_id=UUID(raw["response_id"]),
        created_at=int(raw["created_at"]),
        signature=base64.b64decode(str(raw["signature"]).encode("utf-8")),
        certificate=Certificate.load_pem(CertificatePEM(raw["certificate"])),
        status=VerificationStatus[payload["status"]],
        message=str(payload["message"]),
        group_and_managed_services_use=bool(payload["group_and_managed_services_use"]),
        reseller_name=str(payload["reseller_name"]),
        checkmk_edition=CheckmkEdition[payload["checkmk_edition"]],
        checkmk_max_version=str(payload["checkmk_max_version"]),
        subscription_start_ts=int(payload["subscription_start_ts"]),
        subscription_expiration_ts=int(payload["subscription_expiration_ts"]),
        grace_period_after_expiration=int(payload["grace_period_after_expiration"]),
        subscription_recurrence_unit=str(payload["subscription_recurrence_unit"]),
        subscription_auto_renewal=bool(payload["subscription_auto_renewal"]),
        operational_state=OperationalState[payload["operational_state"]],
        service_limit=payload["service_limit"],
        active_metric_series_limit=payload["active_metric_series_limit"],
        unbound_license=bool(payload["unbound_license"]),
        additional_features=parse_additional_features(payload["additional_features"]),
    )


def parse_additional_features(
    raw_additional_features: object,
) -> Sequence[AdditionalFeature | AdditionalLimitFeature]:
    """
    >>> parse_additional_features([{"name": "ntop", "enabled": True}, {"name": "virt1_appliance", "enabled": False}, {"name": "synthetic_monitoring", "enabled": True, "limit": 1000}])
    [AdditionalFeature(name='ntop', enabled=True), AdditionalFeature(name='virt1_appliance', enabled=False), AdditionalLimitFeature(name='synthetic_monitoring', enabled=True, limit=1000)]
    >>> parse_additional_features([{"name": "ntop", "enabled": False}, {"name": "virt1_appliance", "enabled": True}, {"name": "synthetic_monitoring", "enabled": False, "limit": 0}])
    [AdditionalFeature(name='ntop', enabled=False), AdditionalFeature(name='virt1_appliance', enabled=True), AdditionalLimitFeature(name='synthetic_monitoring', enabled=False, limit=0)]
    """
    if not isinstance(raw_additional_features, list):
        raise TypeError("wrong additional features type: %r" % type(raw_additional_features))
    features_by_name: dict[str, AdditionalFeature | AdditionalLimitFeature] = {}
    for raw_feature in raw_additional_features:
        if not isinstance(raw_feature, dict):
            raise TypeError("wrong additional features content type: %r" % type(raw_feature))
        if not isinstance(name := raw_feature.get("name"), str):
            raise TypeError(name)
        if not isinstance(enabled := raw_feature.get("enabled"), bool):
            raise TypeError(enabled)
        match name:
            case "ntop" | "virt1_appliance":
                features_by_name[name] = AdditionalFeature(name, enabled)
            case "synthetic_monitoring":
                if not isinstance(limit := raw_feature.get("limit"), int):
                    raise TypeError(limit)
                features_by_name[name] = AdditionalLimitFeature(name, enabled, limit)
            case _:
                raise TypeError("wrong additional feature: %r" % raw_feature)
    return list(features_by_name.values())
