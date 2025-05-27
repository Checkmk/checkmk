#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import cast, Literal, Required, TypedDict

from cmk.utils.notify_types import (
    AlwaysBulkParameters,
    AsciiMailPluginName,
    CaseState,
    CaseStateStr,
    CiscoPluginName,
    ConditionEventConsoleAlertsType,
    CustomPluginName,
    EmailBodyElementsType,
    EmailFromOrTo,
    EventConsoleOption,
    GroupbyType,
    HostEventType,
    IlertAPIKey,
    IlertPluginName,
    IncidentState,
    IncidentStateStr,
    is_always_bulk,
    is_auto_urlprefix,
    is_manual_urlprefix,
    is_timeperiod_bulk,
    JiraPluginName,
    MailPluginName,
    MatchRegex,
    MgmntPriorityType,
    MgmntUrgencyType,
    MkeventdPluginName,
    MSTeamsPluginName,
    NotifyBulkType,
    OpsGeniePluginName,
    OpsGeniePriorityPValueType,
    OpsGeniePriorityStrType,
    PagerdutyPluginName,
    PasswordType,
    PluginOptions,
    ProxyUrl,
    PushoverPluginName,
    PushOverPriorityNumType,
    PushOverPriorityStringType,
    RegexModes,
    RoutingKeyType,
    ServiceEventType,
    ServiceNowPluginName,
    Signl4PluginName,
    SlackPluginName,
    SmsApiPluginName,
    SmsPluginName,
    SMTPAuthAttrs,
    SortOrder,
    SoundType,
    SpectrumPluginName,
    SplunkPluginName,
    SyncDeliverySMTP,
    SysLogFacilityIntType,
    SysLogFacilityStrType,
    SyslogPriorityIntType,
    SysLogPriorityStrType,
    TimeperiodBulkParameters,
    URLPrefix,
    WebHookUrl,
)

from cmk.ec.export import (  # pylint:disable=cmk-module-layer-violation
    SyslogFacility,
    SyslogPriority,
)

CheckboxState = Literal["enabled", "disabled"]


class CheckboxStateType(TypedDict):
    state: CheckboxState


# ----------------------------------------------------------------


class CheckboxStrAPIType(CheckboxStateType, total=False):
    value: str


@dataclass
class CheckboxWithStrValue:
    value: str | None = None

    @classmethod
    def from_mk_file_format(cls, data: str | None) -> CheckboxWithStrValue:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: CheckboxStrAPIType) -> CheckboxWithStrValue:
        if data["state"] == "disabled":
            return cls()
        return cls(value=data["value"])

    def api_response(self) -> CheckboxStrAPIType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: CheckboxStrAPIType = {"state": state}
        if self.value is not None:
            r["value"] = self.value
        return r

    def to_mk_file_format(self) -> str | None:
        return self.value


# ----------------------------------------------------------------


class CheckboxListOfStrAPIType(CheckboxStateType, total=False):
    value: list[str]


@dataclass
class CheckboxWithListOfStrValues:
    value: list[str] | None = None

    @classmethod
    def from_mk_file_format(cls, data: list[str] | None) -> CheckboxWithListOfStrValues:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: CheckboxListOfStrAPIType) -> CheckboxWithListOfStrValues:
        if data["state"] == "disabled":
            return cls()
        return cls(value=data["value"])

    def api_response(self) -> CheckboxListOfStrAPIType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: CheckboxListOfStrAPIType = {"state": state}
        if self.value is not None:
            r["value"] = self.value
        return r

    def to_mk_file_format(self) -> list[str] | None:
        return self.value


# ----------------------------------------------------------------


@dataclass
class CheckboxWithBoolValue:
    value: bool = False

    @classmethod
    def from_mk_file_format(cls, data: bool | None) -> CheckboxWithBoolValue:
        if data is None:
            return cls()
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: CheckboxStateType) -> CheckboxWithBoolValue:
        if data["state"] == "disabled":
            return cls()
        return cls(value=True)

    def api_response(self) -> CheckboxStateType:
        state: CheckboxState = "disabled" if not self.value else "enabled"
        r: CheckboxStateType = {"state": state}
        return r

    def to_mk_file_format(self) -> bool:
        return self.value


# ----------------------------------------------------------------
@dataclass
class CheckboxTrueOrNone:
    value: Literal[True] | None = None

    @classmethod
    def from_mk_file_format(cls, data: Literal[True] | None) -> CheckboxTrueOrNone:
        if data is None:
            return cls()
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: CheckboxStateType) -> CheckboxTrueOrNone:
        if data["state"] == "disabled":
            return cls()
        return cls(value=True)

    def api_response(self) -> CheckboxStateType:
        state: CheckboxState = "disabled" if not self.value else "enabled"
        r: CheckboxStateType = {"state": state}
        return r

    def to_mk_file_format(self) -> Literal[True] | None:
        return self.value


# ----------------------------------------------------------------


class CheckboxIntAPIType(CheckboxStateType, total=False):
    value: int


@dataclass
class CheckboxWithIntValue:
    value: int | None = None

    @classmethod
    def from_mk_file_format(cls, data: int | None) -> CheckboxWithIntValue:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: CheckboxIntAPIType) -> CheckboxWithIntValue:
        if data["state"] == "disabled":
            return cls()
        return cls(value=data["value"])

    def api_response(self) -> CheckboxIntAPIType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: CheckboxIntAPIType = {"state": state}
        if self.value is not None:
            r["value"] = self.value
        return r

    def to_mk_file_format(self) -> int | None:
        return self.value


# ----------------------------------------------------------------
class CheckboxSortOrderAPIType(CheckboxStateType, total=False):
    value: SortOrder


@dataclass
class CheckboxSortOrder:
    value: SortOrder | None = None

    @classmethod
    def from_mk_file_format(cls, data: SortOrder | None) -> CheckboxSortOrder:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: CheckboxSortOrderAPIType) -> CheckboxSortOrder:
        if data["state"] == "disabled":
            return cls()
        return cls(value=data["value"])

    def api_response(self) -> CheckboxSortOrderAPIType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: CheckboxSortOrderAPIType = {"state": state}
        if self.value is not None:
            r["value"] = self.value
        return r

    def to_mk_file_format(self) -> SortOrder | None:
        return self.value


# ----------------------------------------------------------------
class CheckboxUseSiteIDPrefixAPIType(CheckboxStateType, total=False):
    value: Literal["deactivated", "use_site_id_prefix"]


@dataclass
class CheckboxUseSiteIDPrefix:
    value: bool | None = None

    @classmethod
    def from_mk_file_format(cls, data: bool | None) -> CheckboxUseSiteIDPrefix:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: CheckboxUseSiteIDPrefixAPIType) -> CheckboxUseSiteIDPrefix:
        if data["state"] == "disabled":
            return cls()

        if data["value"] == "use_site_id_prefix":
            return cls(value=True)
        return cls(value=False)

    def api_response(self) -> CheckboxUseSiteIDPrefixAPIType:
        state: CheckboxState = "disabled" if not self.value else "enabled"
        r: CheckboxUseSiteIDPrefixAPIType = {"state": state}

        if self.value is not None:
            r["value"] = "use_site_id_prefix" if self.value else "deactivated"

        return r

    def to_mk_file_format(self) -> bool | None:
        return self.value


# ----------------------------------------------------------------
class CheckboxEmailBodyInfoAPIType(CheckboxStateType, total=False):
    value: list[EmailBodyElementsType]


@dataclass
class CheckboxEmailBodyInfo:
    value: list[EmailBodyElementsType] | None = None

    @classmethod
    def from_mk_file_format(cls, data: list[EmailBodyElementsType] | None) -> CheckboxEmailBodyInfo:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: CheckboxEmailBodyInfoAPIType) -> CheckboxEmailBodyInfo:
        if data["state"] == "disabled":
            return cls()
        return cls(value=data["value"])

    def api_response(self) -> CheckboxEmailBodyInfoAPIType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: CheckboxEmailBodyInfoAPIType = {"state": state}
        if self.value is not None:
            r["value"] = self.value
        return r

    def to_mk_file_format(self) -> list[EmailBodyElementsType] | None:
        return self.value


# ----------------------------------------------------------------
class MatchLabel(TypedDict):
    key: str
    value: str


class MatchLabelsAPIValueType(CheckboxStateType, total=False):
    value: list[MatchLabel]


@dataclass
class MatchLabels:
    value: Mapping[str, str] | None = None

    @classmethod
    def from_mk_file_format(cls, data: Mapping[str, str] | None) -> MatchLabels:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: MatchLabelsAPIValueType) -> MatchLabels:
        if data["state"] == "disabled":
            return cls()
        return cls(value={d["key"]: d["value"] for d in data["value"]})

    def api_response(self) -> MatchLabelsAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: MatchLabelsAPIValueType = {"state": state}
        if self.value is not None:
            r["value"] = [{"key": k, "value": v} for k, v in self.value.items()]
        return r

    def to_mk_file_format(self) -> Mapping[str, str] | None:
        return self.value


# ----------------------------------------------------------------
class ContactMatchMacro(TypedDict):
    macro_name: str
    match_regex: str


class ContactMatchMacrosAPIValueType(CheckboxStateType, total=False):
    value: list[ContactMatchMacro]


@dataclass
class ContactMatchMacros:
    value: list[tuple[str, str]] | None = None

    @classmethod
    def from_mk_file_format(cls, data: list[tuple[str, str]] | None) -> ContactMatchMacros:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: ContactMatchMacrosAPIValueType) -> ContactMatchMacros:
        if data["state"] == "disabled":
            return cls()

        return cls(value=[(z["macro_name"], z["match_regex"]) for z in data["value"]])

    def api_response(self) -> ContactMatchMacrosAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: ContactMatchMacrosAPIValueType = {"state": state}
        if self.value is not None:
            r["value"] = [{"macro_name": a, "match_regex": b} for a, b in self.value]
        return r

    def to_mk_file_format(self) -> list[tuple[str, str]] | None:
        return self.value


# ----------------------------------------------------------------
PRIORITY_VALUES: Mapping[PushOverPriorityNumType, PushOverPriorityStringType] = {
    "-2": "lowest",
    "-1": "low",
    "0": "normal",
    "1": "high",
}


class CheckboxPushoverPriorityAPIType(CheckboxStateType, total=False):
    value: PushOverPriorityStringType


@dataclass
class CheckboxPushoverPriority:
    value: PushOverPriorityNumType | None = None

    @classmethod
    def from_mk_file_format(cls, data: PushOverPriorityNumType | None) -> CheckboxPushoverPriority:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: CheckboxPushoverPriorityAPIType) -> CheckboxPushoverPriority:
        if data["state"] == "disabled":
            return cls()

        values: Mapping[PushOverPriorityStringType, PushOverPriorityNumType] = {
            v: k for k, v in PRIORITY_VALUES.items()
        }
        return cls(value=values[data["value"]])

    def api_response(self) -> CheckboxPushoverPriorityAPIType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: CheckboxPushoverPriorityAPIType = {"state": state}
        if self.value is not None:
            r["value"] = PRIORITY_VALUES[self.value]
        return r

    def to_mk_file_format(self) -> PushOverPriorityNumType | None:
        return self.value


# ----------------------------------------------------------------
class CheckboxPushoverSoundAPIType(CheckboxStateType, total=False):
    value: SoundType


@dataclass
class CheckboxPushoverSound:
    value: SoundType | None = None

    @classmethod
    def from_mk_file_format(cls, data: SoundType | None) -> CheckboxPushoverSound:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: CheckboxPushoverSoundAPIType) -> CheckboxPushoverSound:
        if data["state"] == "disabled":
            return cls()

        return cls(value=data["value"])

    def api_response(self) -> CheckboxPushoverSoundAPIType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: CheckboxPushoverSoundAPIType = {"state": state}
        if self.value is not None:
            r["value"] = self.value
        return r

    def to_mk_file_format(self) -> SoundType | None:
        return self.value


# ----------------------------------------------------------------


class API_AuthValueType(CheckboxStateType, total=False):
    value: SMTPAuthAttrs


class API_EnableSyncViaSMTPAttrs(TypedDict, total=False):
    auth: API_AuthValueType
    encryption: Literal["ssl_tls", "starttls"]
    port: int
    smarthosts: list[str]


class API_EnableSyncViaSMTPValueType(CheckboxStateType, total=False):
    value: API_EnableSyncViaSMTPAttrs


@dataclass
class SMTPAuth:
    value: SMTPAuthAttrs | None = None

    @classmethod
    def from_mk_file_format(cls, data: SMTPAuthAttrs | None) -> SMTPAuth:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: API_AuthValueType) -> SMTPAuth:
        if data["state"] == "disabled":
            return cls()
        return cls(value=data["value"])

    def api_response(self) -> API_AuthValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: API_AuthValueType = {"state": state}
        if self.value is not None:
            r["value"] = self.value
        return r

    def to_mk_file_format(self) -> SMTPAuthAttrs | None:
        if self.value is None:
            return None

        return self.value


# ----------------------------------------------------------------


@dataclass
class EnableSyncDeliveryViaSMTP:
    value: SyncDeliverySMTP | None = None

    @classmethod
    def from_mk_file_format(cls, data: SyncDeliverySMTP | None) -> EnableSyncDeliveryViaSMTP:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: API_EnableSyncViaSMTPValueType) -> EnableSyncDeliveryViaSMTP:
        if data["state"] == "disabled":
            return cls(value=None)

        v = data["value"]

        smarthosts = v["smarthosts"]
        if len(v["smarthosts"]) > 2:
            smarthosts = v["smarthosts"][:2]  # TODO only two allowed - set in schema

        value = SyncDeliverySMTP(
            port=v["port"],
            smarthosts=smarthosts,
        )

        if (auth := SMTPAuth.from_api_request(v["auth"]).to_mk_file_format()) is not None:
            value["auth"] = auth

        if (encryption := v.get("encryption")) is not None:
            value["encryption"] = encryption

        return cls(value=value)

    def api_response(self) -> API_EnableSyncViaSMTPValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: API_EnableSyncViaSMTPValueType = {"state": state}

        if self.value is not None:
            r["value"] = {
                "auth": SMTPAuth.from_mk_file_format(self.value.get("auth")).api_response(),
                "port": self.value["port"],
                "smarthosts": self.value["smarthosts"],
            }
            if (encryption := self.value.get("encryption")) is not None:
                r["value"]["encryption"] = encryption

        return r

    def to_mk_file_format(self) -> SyncDeliverySMTP | None:
        return self.value


# ----------------------------------------------------------------
OPS_GENIE_PRIORITY_MAP: Mapping[OpsGeniePriorityStrType, OpsGeniePriorityPValueType] = {
    "critical": "P1",
    "high": "P2",
    "moderate": "P3",
    "low": "P4",
    "informational": "P5",
}


class OpsGeniePriorityAPIType(CheckboxStateType, total=False):
    value: OpsGeniePriorityStrType


@dataclass
class CheckboxOpsGeniePriority:
    value: OpsGeniePriorityPValueType | None = None

    @classmethod
    def from_mk_file_format(
        cls, data: OpsGeniePriorityPValueType | None
    ) -> CheckboxOpsGeniePriority:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: OpsGeniePriorityAPIType) -> CheckboxOpsGeniePriority:
        if data["state"] == "disabled":
            return cls()
        return cls(value=OPS_GENIE_PRIORITY_MAP[data["value"]])

    def api_response(self) -> OpsGeniePriorityAPIType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: OpsGeniePriorityAPIType = {"state": state}
        if self.value is not None:
            values: Mapping[OpsGeniePriorityPValueType, OpsGeniePriorityStrType] = {
                v: k for k, v in OPS_GENIE_PRIORITY_MAP.items()
            }
            r["value"] = values[self.value]
        return r

    def to_mk_file_format(self) -> OpsGeniePriorityPValueType | None:
        return self.value

    def disable(self) -> None:
        self.value = None


# ----------------------------------------------------------------
class MatchServiceFromToLevels(TypedDict):
    from_level: int
    to_level: int


class MatchServiceLevelsAPIValueType(CheckboxStateType, total=False):
    value: MatchServiceFromToLevels


@dataclass
class MatchServiceLevels:
    value: tuple[int, int] | None = None

    @classmethod
    def from_mk_file_format(cls, data: tuple[int, int] | None) -> MatchServiceLevels:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: MatchServiceLevelsAPIValueType) -> MatchServiceLevels:
        if data["state"] == "disabled":
            return cls()

        return cls(
            value=(data["value"]["from_level"], data["value"]["to_level"]),
        )

    def api_response(self) -> MatchServiceLevelsAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: MatchServiceLevelsAPIValueType = {"state": state}
        if self.value is not None:
            r["value"] = {
                "from_level": self.value[0],
                "to_level": self.value[1],
            }
        return r

    def to_mk_file_format(self) -> tuple[int, int] | None:
        return self.value

    def disable(self) -> None:
        self.value = None


# ----------------------------------------------------------------
class MatchRegexAPI(TypedDict, total=False):
    match_type: RegexModes
    regex_list: list[str]


class MatchServiceGroupsRegexAPIValueType(CheckboxStateType, total=False):
    value: MatchRegexAPI


@dataclass
class MatchServiceGroupsRegex:
    value: MatchRegex | None = None

    @classmethod
    def from_mk_file_format(cls, data: MatchRegex | None) -> MatchServiceGroupsRegex:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: MatchServiceGroupsRegexAPIValueType) -> MatchServiceGroupsRegex:
        if data["state"] == "disabled":
            return cls()
        value = data["value"]
        return cls(value=(value["match_type"], value["regex_list"]))

    def api_response(self) -> MatchServiceGroupsRegexAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: MatchServiceGroupsRegexAPIValueType = {"state": state}
        if self.value is not None:
            r["value"] = {
                "match_type": self.value[0],
                "regex_list": self.value[1],
            }
        return r

    def to_mk_file_format(self) -> MatchRegex | None:
        return self.value

    def disable(self) -> None:
        self.value = None


# ----------------------------------------------------------------
class NotificationNumbers(TypedDict, total=False):
    beginning_from: int
    up_to: int


class NotificationNumbersAPIValueType(CheckboxStateType, total=False):
    value: NotificationNumbers


@dataclass
class RestrictToNotificationNumbers:
    value: tuple[int, int] | None = None

    @classmethod
    def from_mk_file_format(cls, data: tuple[int, int] | None) -> RestrictToNotificationNumbers:
        return cls(value=data)

    @classmethod
    def from_api_request(
        cls, data: NotificationNumbersAPIValueType
    ) -> RestrictToNotificationNumbers:
        if data["state"] == "disabled":
            return cls()
        return cls(value=(data["value"]["beginning_from"], data["value"]["up_to"]))

    def api_response(self) -> NotificationNumbersAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: NotificationNumbersAPIValueType = {"state": state}
        if self.value is not None:
            r["value"] = {
                "beginning_from": self.value[0],
                "up_to": self.value[1],
            }
        return r

    def to_mk_file_format(self) -> tuple[int, int] | None:
        return self.value

    def disable(self) -> None:
        self.value = None


# ----------------------------------------------------------------
class FromAndToEmailFieldsAPIValueType(CheckboxStateType, total=False):
    value: EmailFromOrTo


@dataclass
class FromAndToEmailFields:
    value: EmailFromOrTo | None = None

    @classmethod
    def from_mk_file_format(cls, data: EmailFromOrTo | None) -> FromAndToEmailFields:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: FromAndToEmailFieldsAPIValueType) -> FromAndToEmailFields:
        if data["state"] == "disabled":
            return cls()
        return cls(value=data["value"])

    def api_response(self) -> FromAndToEmailFieldsAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: FromAndToEmailFieldsAPIValueType = {"state": state}
        if self.value is None:
            return r

        r["value"] = {
            "address": self.value.get("address", ""),
            "display_name": self.value.get("display_name", ""),
        }
        return r

    def to_mk_file_format(self) -> EmailFromOrTo | None:
        return self.value

    def disable(self) -> None:
        self.value = None


# ---------------------------------------------------------------


class MatchHostTagsAPIValueType(CheckboxStateType, total=False):
    value: list


@dataclass
class CheckboxMatchHostTags:
    value: list[str] | None = None

    @classmethod
    def from_mk_file_format(cls, data: list[str] | None) -> CheckboxMatchHostTags:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: MatchHostTagsAPIValueType) -> CheckboxMatchHostTags:
        if data["state"] == "disabled":
            return cls()

        tagids: list[str] = []
        for value in data["value"]:
            if "is_not" in value["operator"]:
                tagids.append(
                    f"!{value['tag_id']}",
                )
            else:
                tagids.append(value["tag_id"])

        return cls(value=tagids)

    def api_response(self) -> MatchHostTagsAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        resp: MatchHostTagsAPIValueType = {"state": state}
        if self.value is None:
            return resp

        resp["value"] = self.value
        return resp

    def to_mk_file_format(self) -> list[str] | None:
        return self.value

    def disable(self) -> None:
        self.value = None


# ----------------------------------------------------------------
HOST_EVENT_MAP: Mapping[str, HostEventType] = {
    "up_down": "rd",
    "up_unreachable": "ru",
    "down_up": "dr",
    "down_unreachable": "du",
    "unreachable_down": "ud",
    "unreachable_up": "ur",
    "any_up": "?r",
    "any_down": "?d",
    "any_unreachable": "?u",
    "start_or_end_of_flapping_state": "f",
    "start_or_end_of_scheduled_downtime": "s",
    "acknowledgement_of_problem": "x",
    "alert_handler_execution_successful": "as",
    "alert_handler_execution_failed": "af",
}


class MatchHostEventsAPIType(TypedDict):
    up_down: bool
    up_unreachable: bool
    down_up: bool
    down_unreachable: bool
    unreachable_down: bool
    unreachable_up: bool
    any_up: bool
    any_down: bool
    any_unreachable: bool
    start_or_end_of_flapping_state: bool
    start_or_end_of_scheduled_downtime: bool
    acknowledgement_of_problem: bool
    alert_handler_execution_successful: bool
    alert_handler_execution_failed: bool


class MatchHostEventsAPIValueType(CheckboxStateType, total=False):
    value: MatchHostEventsAPIType


@dataclass
class CheckboxMatchHostEvents:
    value: Sequence[HostEventType] | None = None

    @classmethod
    def from_mk_file_format(cls, data: Sequence[HostEventType] | None) -> CheckboxMatchHostEvents:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: MatchHostEventsAPIValueType) -> CheckboxMatchHostEvents:
        if data["state"] == "disabled":
            return cls()

        value = data["value"]
        return cls(value=[HOST_EVENT_MAP[k] for k, v in value.items() if v])

    def api_response(self) -> MatchHostEventsAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: MatchHostEventsAPIValueType = {"state": state}
        if self.value is not None:
            r["value"] = cast(
                MatchHostEventsAPIType,
                {k: bool(set(self.value) & {v}) for k, v in HOST_EVENT_MAP.items()},
            )
        return r

    def to_mk_file_format(self) -> Sequence[HostEventType] | None:
        return self.value

    def disable(self) -> None:
        self.value = None


# ----------------------------------------------------------------
SE_MAPPER: Mapping[str, ServiceEventType] = {
    "ok_warn": "rw",
    "ok_ok": "rr",
    "ok_crit": "rc",
    "ok_unknown": "ru",
    "warn_ok": "wr",
    "warn_crit": "wc",
    "warn_unknown": "wu",
    "crit_ok": "cr",
    "crit_warn": "cw",
    "crit_unknown": "cu",
    "unknown_ok": "ur",
    "unknown_warn": "uw",
    "unknown_crit": "uc",
    "any_ok": "?r",
    "any_warn": "?w",
    "any_crit": "?c",
    "any_unknown": "?u",
    "start_or_end_of_flapping_state": "f",
    "start_or_end_of_scheduled_downtime": "s",
    "acknowledgement_of_problem": "x",
    "alert_handler_execution_successful": "as",
    "alert_handler_execution_failed": "af",
}


class MatchServiceEventsAPIType(TypedDict):
    ok_warn: bool
    ok_ok: bool
    ok_crit: bool
    ok_unknown: bool
    warn_ok: bool
    warn_crit: bool
    warn_unknown: bool
    crit_ok: bool
    crit_warn: bool
    crit_unknown: bool
    unknown_ok: bool
    unknown_warn: bool
    unknown_crit: bool
    any_ok: bool
    any_warn: bool
    any_crit: bool
    any_unknown: bool
    start_or_end_of_flapping_state: bool
    start_or_end_of_scheduled_downtime: bool
    acknowledgement_of_problem: bool
    alert_handler_execution_successful: bool
    alert_handler_execution_failed: bool


class MatchServiceEventsAPIValueType(CheckboxStateType, total=False):
    value: MatchServiceEventsAPIType


@dataclass
class CheckboxMatchServiceEvents:
    value: Sequence[ServiceEventType] | None = None

    @classmethod
    def from_mk_file_format(
        cls, data: Sequence[ServiceEventType] | None
    ) -> CheckboxMatchServiceEvents:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: MatchServiceEventsAPIValueType) -> CheckboxMatchServiceEvents:
        if data["state"] == "disabled":
            return cls()

        value = data["value"]
        return cls(value=[SE_MAPPER[k] for k, v in value.items() if v])

    def api_response(self) -> MatchServiceEventsAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: MatchServiceEventsAPIValueType = {"state": state}
        if self.value is not None:
            r["value"] = cast(
                MatchServiceEventsAPIType,
                {k: bool(set(self.value) & {v}) for k, v in SE_MAPPER.items()},
            )
        return r

    def to_mk_file_format(self) -> Sequence[ServiceEventType] | None:
        return self.value

    def disable(self) -> None:
        self.value = None


# ----------------------------------------------------------------
class ThrottleNotifications(TypedDict):
    beginning_from: int
    send_every_nth_notification: int


class ThrottlePeriodicNotificationsAPIValueType(CheckboxStateType, total=False):
    value: ThrottleNotifications


@dataclass
class CheckboxThrottlePeriodicNotifications:
    value: tuple[int, int] | None = None

    @classmethod
    def from_mk_file_format(
        cls, data: tuple[int, int] | None
    ) -> CheckboxThrottlePeriodicNotifications:
        return cls(value=data)

    @classmethod
    def from_api_request(
        cls, data: ThrottlePeriodicNotificationsAPIValueType
    ) -> CheckboxThrottlePeriodicNotifications:
        if data["state"] == "disabled":
            return cls()

        value = data["value"]
        return cls(value=(value["beginning_from"], value["send_every_nth_notification"]))

    def api_response(self) -> ThrottlePeriodicNotificationsAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: ThrottlePeriodicNotificationsAPIValueType = {"state": state}
        if self.value is not None:
            r["value"] = {
                "beginning_from": self.value[0],
                "send_every_nth_notification": self.value[1],
            }
        return r

    def to_mk_file_format(self) -> tuple[int, int] | None:
        return self.value

    def disable(self) -> None:
        self.value = None


# ----------------------------------------------------------------
FACILITIES = cast(
    Mapping[SysLogFacilityIntType, SysLogFacilityStrType],
    SyslogFacility.NAMES,
)


@dataclass
class CheckboxSysLogFacility:
    value: SysLogFacilityIntType | None = None

    @classmethod
    def from_mk_file_format(cls, data: SysLogFacilityIntType | None) -> CheckboxSysLogFacility:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: SysLogFacilityAPIValueType) -> CheckboxSysLogFacility:
        if data["state"] == "disabled":
            return cls()
        return cls(value={v: k for k, v in FACILITIES.items()}.get(data["value"]))

    def api_response(self) -> SysLogFacilityAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: SysLogFacilityAPIValueType = {"state": state}
        if self.value is not None:
            r["value"] = FACILITIES[self.value]
        return r

    def to_mk_file_format(self) -> SysLogFacilityIntType | None:
        return self.value

    def disable(self) -> None:
        self.value = None


# ----------------------------------------------------------------
PRIORITIES = cast(Mapping[SyslogPriorityIntType, SysLogPriorityStrType], SyslogPriority.NAMES)


@dataclass
class CheckboxSysLogPriority:
    value: tuple[SyslogPriorityIntType, SyslogPriorityIntType] | None = None

    @classmethod
    def from_mk_file_format(
        cls, data: tuple[SyslogPriorityIntType, SyslogPriorityIntType] | None
    ) -> CheckboxSysLogPriority:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: SysLogPriorityAPIValueType) -> CheckboxSysLogPriority:
        if data["state"] == "disabled":
            return cls()
        value = data["value"]
        priorities_reversed = {v: k for k, v in PRIORITIES.items()}
        return cls(
            value=(
                priorities_reversed[value["from_priority"]],
                priorities_reversed[value["to_priority"]],
            )
        )

    def api_response(self) -> SysLogPriorityAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: SysLogPriorityAPIValueType = {"state": state}
        if self.value is not None:
            r["value"] = {
                "from_priority": PRIORITIES[self.value[0]],
                "to_priority": PRIORITIES[self.value[1]],
            }
        return r

    def to_mk_file_format(
        self,
    ) -> tuple[SyslogPriorityIntType, SyslogPriorityIntType] | None:
        return self.value

    def disable(self) -> None:
        self.value = None


# ----------------------------------------------------------------
class UrlPrefixAPIAttrs(TypedDict, total=False):
    option: Literal["automatic", "manual"]
    schema: Literal["http", "https"]
    url: str


class CheckboxURLPrefixAPIValueType(CheckboxStateType, total=False):
    value: UrlPrefixAPIAttrs


@dataclass
class CheckboxURLPrefix:
    value: URLPrefix | None = None

    @classmethod
    def from_mk_file_format(cls, data: URLPrefix | None) -> CheckboxURLPrefix:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: CheckboxURLPrefixAPIValueType) -> CheckboxURLPrefix:
        if data["state"] == "disabled":
            return cls()

        value = data["value"]

        match value["option"]:
            case "automatic":
                return cls(value={"automatic": value["schema"]})
            case "manual":
                return cls(value={"manual": value["url"]})

    def api_response(self) -> CheckboxURLPrefixAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: CheckboxURLPrefixAPIValueType = {"state": state}
        if self.value is None:
            return r

        if is_auto_urlprefix(self.value):
            r["value"] = {"option": "automatic", "schema": self.value["automatic"]}

        if is_manual_urlprefix(self.value):
            r["value"] = {"option": "manual", "url": self.value["manual"]}

        return r

    def to_mk_file_format(self) -> URLPrefix | None:
        return self.value

    def disable(self) -> None:
        self.state = "disabled"
        self.value = None


# ----------------------------------------------------------------


class HttpProxyAPINoProxy(TypedDict):
    option: Literal["no_proxy"]


class HttpProxyAPIEnvironment(TypedDict):
    option: Literal["environment"]


class HttpProxyAPIUrl(TypedDict):
    option: Literal["url"]
    url: str


class HttpProxyAPIGlobal(TypedDict):
    option: Literal["global"]
    global_proxy_id: str


class HttpProxyAPIValueType(CheckboxStateType, total=False):
    value: HttpProxyAPINoProxy | HttpProxyAPIEnvironment | HttpProxyAPIUrl | HttpProxyAPIGlobal


@dataclass
class CheckboxHttpProxy:
    value: ProxyUrl | None = None

    @classmethod
    def from_mk_file_format(cls, data: ProxyUrl | None) -> CheckboxHttpProxy:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: HttpProxyAPIValueType) -> CheckboxHttpProxy:
        match data:
            case {"state": "enabled", "value": {"option": "no_proxy"}}:
                return cls(value=("no_proxy", None))

            case {"state": "enabled", "value": {"option": "url", "url": str() as url}}:
                return cls(value=("url", url))

            case {
                "state": "enabled",
                "value": {
                    "option": "global",
                    "global_proxy_id": str() as global_proxy_id,
                },
            }:
                return cls(value=("global", global_proxy_id))

            case {"state": "enabled", "value": {"option": "environment"}}:
                return cls(value=("environment", "environment"))

            case _:
                return cls()

    def api_response(self) -> HttpProxyAPIValueType:
        state: CheckboxState = "disabled" if self.value is None else "enabled"
        r: HttpProxyAPIValueType = {"state": state}
        if self.value is None:
            return r

        option, value = self.value
        if option == "no_proxy":
            r["value"] = {"option": option}

        if option == "environment":
            r["value"] = {"option": option}

        if option == "url" and value is not None:
            r["value"] = {"option": "url", "url": value}

        if option == "global" and value is not None:
            r["value"] = {"option": "global", "global_proxy_id": value}

        return r

    def to_mk_file_format(self) -> ProxyUrl | None:
        return self.value

    def disable(self) -> None:
        self.value = None


# ----------------------------------------------------------------
class AckStateValue(TypedDict, total=False):
    start_predefined: IncidentStateStr
    start_integer: int


class AckStateAPI(CheckboxStateType, total=False):
    value: AckStateValue


class AckStateMk(TypedDict):
    start: IncidentState


@dataclass
class AckState:
    value: AckStateMk | None = None

    @classmethod
    def from_mk_file_format(cls, data: AckStateMk | None) -> AckState:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: AckStateAPI) -> AckState:
        if data["state"] == "disabled":
            return cls()

        value = data["value"]

        if "start_predefined" in value:
            return cls(value={"start": value["start_predefined"]})
        return cls(value={"start": value["start_integer"]})

    def api_response(self) -> AckStateAPI:
        state: CheckboxState = "disabled" if not self.value else "enabled"
        r: AckStateAPI = {"state": state}
        if self.value is None:
            return r

        if isinstance(self.value["start"], int):
            r["value"] = {"start_integer": self.value["start"]}
            return r

        r["value"] = {"start_predefined": self.value["start"]}
        return r

    def to_mk_file_format(self) -> AckStateMk | None:
        return self.value


# ----------------------------------------------------------------
class RecoveryStateValue(TypedDict, total=False):
    start_predefined: CaseStateStr | IncidentStateStr
    start_integer: int


class RecoveryStateAPI(CheckboxStateType, total=False):
    value: RecoveryStateValue


class RecoveryStateMk(TypedDict):
    start: CaseState | IncidentState


@dataclass
class RecoveryState:
    value: RecoveryStateMk | None = None

    @classmethod
    def from_mk_file_format(cls, data: RecoveryStateMk | None) -> RecoveryState:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: RecoveryStateAPI) -> RecoveryState:
        if data["state"] == "disabled":
            return cls()

        value = data["value"]

        if value.get("start_predefined") is not None:
            return cls(value={"start": value["start_predefined"]})
        return cls(value={"start": value["start_integer"]})

    def api_response(self) -> RecoveryStateAPI:
        state: CheckboxState = "disabled" if not self.value else "enabled"
        r: RecoveryStateAPI = {"state": state}
        if self.value is None:
            return r

        if isinstance(self.value["start"], int):
            r["value"] = {"start_integer": self.value["start"]}
            return r

        r["value"] = {"start_predefined": self.value["start"]}
        return r

    def to_mk_file_format(self) -> RecoveryStateMk | None:
        return self.value


# ----------------------------------------------------------------
class DowntimeStateValue(TypedDict, total=False):
    start_predefined: IncidentStateStr
    end_predefined: IncidentStateStr
    start_integer: int
    end_integer: int


class DowntimeStateAPI(CheckboxStateType, total=False):
    value: DowntimeStateValue


class DowntimeStateMk(TypedDict, total=False):
    start: IncidentState
    end: IncidentState


@dataclass
class DowntimeState:
    value: DowntimeStateMk | None = None

    @classmethod
    def from_mk_file_format(cls, data: DowntimeStateMk | None) -> DowntimeState:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: DowntimeStateAPI) -> DowntimeState:
        if data["state"] == "disabled":
            return cls()

        v = data["value"]
        value: DowntimeStateMk = {}

        if "start_predefined" in v:
            value["start"] = v["start_predefined"]

        if "start_integer" in v:
            value["start"] = v["start_integer"]

        if "end_predefined" in v:
            value["end"] = v["end_predefined"]

        if "end_integer" in v:
            value["end"] = v["end_integer"]

        return cls(value=value)

    def api_response(self) -> DowntimeStateAPI:
        state: CheckboxState = "disabled" if not self.value else "enabled"
        r: DowntimeStateAPI = {"state": state}
        if self.value is None:
            return r

        v: DowntimeStateValue = {}
        if isinstance(self.value["start"], int):
            v["start_integer"] = self.value["start"]
        else:
            v["start_predefined"] = self.value["start"]

        if "end" in self.value:
            if isinstance(self.value["end"], int):
                v["end_integer"] = self.value["end"]
            else:
                v["end_predefined"] = self.value["end"]

        r["value"] = v
        return r

    def to_mk_file_format(self) -> DowntimeStateMk | None:
        return self.value


# ----------------------------------------------------------------
class MgmntPriorityAPIValueType(CheckboxStateType, total=False):
    value: MgmntPriorityType


class MgmntUrgencyAPIValueType(CheckboxStateType, total=False):
    value: MgmntUrgencyType


class MgmtTypeParamsAPI(TypedDict, total=False):
    host_short_description: CheckboxStrAPIType
    service_short_description: CheckboxStrAPIType
    service_description: CheckboxStrAPIType
    host_description: CheckboxStrAPIType
    urgency: MgmntUrgencyAPIValueType
    impact: CheckboxStrAPIType
    caller: str
    state_recovery: RecoveryStateAPI
    state_acknowledgement: AckStateAPI
    state_downtime: DowntimeStateAPI
    priority: MgmntPriorityAPIValueType


class MgmtTypeAPI(TypedDict, total=False):
    option: Literal["case", "incident"]
    params: MgmtTypeParamsAPI


@dataclass
class ManagementTypePriority:
    value: MgmntPriorityType | None = None

    @classmethod
    def from_mk_file_format(cls, data: MgmntPriorityType | None) -> ManagementTypePriority:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: MgmntPriorityAPIValueType) -> ManagementTypePriority:
        if data["state"] == "disabled":
            return cls()
        return cls(value=data["value"])

    def api_response(self) -> MgmntPriorityAPIValueType:
        state: CheckboxState = "disabled" if not self.value else "enabled"
        r: MgmntPriorityAPIValueType = {"state": state}
        if self.value is not None:
            r["value"] = self.value
        return r

    def to_mk_file_format(self) -> MgmntPriorityType | None:
        return self.value


@dataclass
class ManagementTypeUrgency:
    value: MgmntUrgencyType | None = None

    @classmethod
    def from_mk_file_format(cls, data: MgmntUrgencyType | None) -> ManagementTypeUrgency:
        return cls(value=data)

    @classmethod
    def from_api_request(cls, data: MgmntUrgencyAPIValueType) -> ManagementTypeUrgency:
        if data["state"] == "disabled":
            return cls()
        return cls(value=data["value"])

    def api_response(self) -> MgmntUrgencyAPIValueType:
        state: CheckboxState = "disabled" if not self.value else "enabled"
        r: MgmntUrgencyAPIValueType = {"state": state}
        if self.value is not None:
            r["value"] = self.value
        return r

    def to_mk_file_format(self) -> MgmntUrgencyType | None:
        return self.value


@dataclass
class ManagementType:
    mgmt_type: Literal["case", "incident"] = "incident"
    host_short_desc: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    svc_short_desc: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    svc_desc: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    host_desc: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    priority: ManagementTypePriority = field(default_factory=ManagementTypePriority)
    urgency: ManagementTypeUrgency = field(default_factory=ManagementTypeUrgency)
    impact: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    caller: str | None = None
    state_recovery: RecoveryState = field(default_factory=RecoveryState)
    state_acknowledgement: AckState = field(default_factory=AckState)
    state_downtime: DowntimeState = field(default_factory=DowntimeState)

    @classmethod
    def from_mk_file_format(
        cls, config: tuple[Literal["case", "incident"], Mapping] | None
    ) -> ManagementType:
        if config is None:
            return cls()

        mgmt_type, params = config

        if mgmt_type == "case":
            return cls(
                mgmt_type=mgmt_type,
                host_short_desc=CheckboxWithStrValue.from_mk_file_format(
                    params.get("host_short_desc")
                ),
                svc_short_desc=CheckboxWithStrValue.from_mk_file_format(
                    params.get("svc_short_desc")
                ),
                host_desc=CheckboxWithStrValue.from_mk_file_format(params.get("host_desc")),
                svc_desc=CheckboxWithStrValue.from_mk_file_format(params.get("svc_desc")),
                state_recovery=RecoveryState.from_mk_file_format(params.get("recovery_state")),
                priority=ManagementTypePriority.from_mk_file_format(params.get("priority")),
            )

        return cls(
            mgmt_type=mgmt_type,
            host_short_desc=CheckboxWithStrValue.from_mk_file_format(params.get("host_short_desc")),
            svc_short_desc=CheckboxWithStrValue.from_mk_file_format(params.get("svc_short_desc")),
            host_desc=CheckboxWithStrValue.from_mk_file_format(params.get("host_desc")),
            svc_desc=CheckboxWithStrValue.from_mk_file_format(params.get("svc_desc")),
            state_recovery=RecoveryState.from_mk_file_format(params.get("recovery_state")),
            caller=params.get("caller", ""),
            urgency=ManagementTypeUrgency.from_mk_file_format(params.get("urgency")),
            impact=CheckboxWithStrValue.from_mk_file_format(params.get("impact")),
            state_acknowledgement=AckState.from_mk_file_format(params.get("ack_state")),
            state_downtime=DowntimeState.from_mk_file_format(params.get("dt_state")),
        )

    @classmethod
    def from_api_request(cls, data: MgmtTypeAPI) -> ManagementType:
        option = data["option"]
        params = data["params"]

        if option == "incident":
            return cls(
                mgmt_type=option,
                host_short_desc=CheckboxWithStrValue.from_api_request(
                    params["host_short_description"]
                ),
                svc_short_desc=CheckboxWithStrValue.from_api_request(
                    params["service_short_description"]
                ),
                svc_desc=CheckboxWithStrValue.from_api_request(params["service_description"]),
                host_desc=CheckboxWithStrValue.from_api_request(params["host_description"]),
                urgency=ManagementTypeUrgency.from_api_request(params["urgency"]),
                impact=CheckboxWithStrValue.from_api_request(params["impact"]),
                caller=params["caller"],
                state_recovery=RecoveryState.from_api_request(
                    params["state_recovery"],
                ),
                state_acknowledgement=AckState.from_api_request(params["state_acknowledgement"]),
                state_downtime=DowntimeState.from_api_request(params["state_downtime"]),
            )

        return cls(
            mgmt_type=option,
            host_short_desc=CheckboxWithStrValue.from_api_request(params["host_short_description"]),
            svc_short_desc=CheckboxWithStrValue.from_api_request(
                params["service_short_description"]
            ),
            svc_desc=CheckboxWithStrValue.from_api_request(params["service_description"]),
            host_desc=CheckboxWithStrValue.from_api_request(params["host_description"]),
            priority=ManagementTypePriority.from_api_request(params["priority"]),
            state_recovery=RecoveryState.from_api_request(
                params["state_recovery"],
            ),
        )

    def api_response(self) -> MgmtTypeAPI:
        r: MgmtTypeAPI = {"option": self.mgmt_type}
        params: MgmtTypeParamsAPI = {
            "host_description": self.host_desc.api_response(),
            "service_description": self.svc_desc.api_response(),
            "host_short_description": self.host_short_desc.api_response(),
            "service_short_description": self.svc_short_desc.api_response(),
            "state_recovery": self.state_recovery.api_response(),
        }

        if self.mgmt_type == "case":
            params["priority"] = self.priority.api_response()
            r["params"] = params
            return r

        params.update(
            {
                "caller": "" if self.caller is None else self.caller,
                "urgency": self.urgency.api_response(),
                "impact": self.impact.api_response(),
                "state_acknowledgement": self.state_acknowledgement.api_response(),
                "state_downtime": self.state_downtime.api_response(),
            }
        )
        r["params"] = params
        return r

    def to_mk_file_format(self) -> tuple[Literal["case", "incident"], Mapping] | None:
        if self.mgmt_type is None:
            return None

        r = {
            "ack_state": self.state_acknowledgement.to_mk_file_format(),
            "caller": self.caller,
            "dt_state": self.state_downtime.to_mk_file_format(),
            "host_desc": self.host_desc.to_mk_file_format(),
            "host_short_desc": self.host_short_desc.to_mk_file_format(),
            "impact": self.impact.to_mk_file_format(),
            "recovery_state": self.state_recovery.to_mk_file_format(),
            "svc_desc": self.svc_desc.to_mk_file_format(),
            "svc_short_desc": self.svc_short_desc.to_mk_file_format(),
            "urgency": self.urgency.to_mk_file_format(),
            "priority": self.priority.to_mk_file_format(),
        }

        return (self.mgmt_type, {k: v for k, v in r.items() if v is not None})


# ----------------------------------------------------------------
class SysLogFacilityAPIValueType(CheckboxStateType, total=False):
    value: SysLogFacilityStrType


class SysLogPriorityAPIAttrs(TypedDict):
    from_priority: SysLogPriorityStrType
    to_priority: SysLogPriorityStrType


class SysLogPriorityAPIValueType(CheckboxStateType, total=False):
    value: SysLogPriorityAPIAttrs


class EventConsoleValues(TypedDict, total=False):
    match_rule_ids: CheckboxListOfStrAPIType
    match_syslog_priority: SysLogPriorityAPIValueType
    match_syslog_facility: SysLogFacilityAPIValueType
    match_event_comment: CheckboxStrAPIType


class EventConsoleApiAttrs(TypedDict, total=False):
    match_type: EventConsoleOption
    values: EventConsoleValues


class EventConsoleAPIValueType(CheckboxStateType, total=False):
    value: EventConsoleApiAttrs


@dataclass
class EventConsoleAlerts:
    state: CheckboxState = "disabled"
    match_type: EventConsoleOption = "do_not_match_event_console_alerts"
    match_rule_id: CheckboxWithListOfStrValues = field(default_factory=CheckboxWithListOfStrValues)
    match_comment: CheckboxWithStrValue = field(default_factory=CheckboxWithStrValue)
    match_priority: CheckboxSysLogPriority = field(default_factory=CheckboxSysLogPriority)
    match_syslog_facility: CheckboxSysLogFacility = field(default_factory=CheckboxSysLogFacility)

    @classmethod
    def from_mk_file_format(
        cls, data: ConditionEventConsoleAlertsType | Literal[False] | None
    ) -> EventConsoleAlerts:
        if data is None:
            return cls()

        if data is False:
            return cls(state="enabled", match_type="do_not_match_event_console_alerts")

        return cls(
            state="enabled",
            match_type="match_only_event_console_alerts",
            match_rule_id=CheckboxWithListOfStrValues.from_mk_file_format(
                data.get("match_rule_id")
            ),
            match_priority=CheckboxSysLogPriority.from_mk_file_format(data.get("match_priority")),
            match_syslog_facility=CheckboxSysLogFacility.from_mk_file_format(
                data.get("match_facility")
            ),
            match_comment=CheckboxWithStrValue.from_mk_file_format(data.get("match_comment")),
        )

    @classmethod
    def from_api_request(cls, data: EventConsoleAPIValueType) -> EventConsoleAlerts:
        if data["state"] == "disabled":
            return cls()

        value = data["value"]
        if value.get("values") is None:
            return cls(
                state="enabled",
                match_type=value["match_type"],
            )

        values = value["values"]
        return cls(
            state="enabled",
            match_type="match_only_event_console_alerts",
            match_rule_id=CheckboxWithListOfStrValues.from_api_request(values["match_rule_ids"]),
            match_comment=CheckboxWithStrValue.from_api_request(values["match_event_comment"]),
            match_priority=CheckboxSysLogPriority.from_api_request(values["match_syslog_priority"]),
            match_syslog_facility=CheckboxSysLogFacility.from_api_request(
                values["match_syslog_facility"]
            ),
        )

    def api_response(self) -> EventConsoleAPIValueType:
        r: EventConsoleAPIValueType = {"state": self.state}
        if self.state == "disabled":
            return r

        if self.match_type == "do_not_match_event_console_alerts":
            r["value"] = {"match_type": self.match_type}

        else:
            r["value"] = {
                "match_type": self.match_type,
                "values": {
                    "match_rule_ids": self.match_rule_id.api_response(),
                    "match_syslog_priority": self.match_priority.api_response(),
                    "match_syslog_facility": self.match_syslog_facility.api_response(),
                    "match_event_comment": self.match_comment.api_response(),
                },
            }

        return r

    def to_mk_file_format(
        self,
    ) -> ConditionEventConsoleAlertsType | Literal[False] | None:
        if self.state == "disabled":
            return None

        if self.match_type == "do_not_match_event_console_alerts":
            return False

        r = {
            "match_rule_id": self.match_rule_id.to_mk_file_format(),
            "match_priority": self.match_priority.to_mk_file_format(),
            "match_facility": self.match_syslog_facility.to_mk_file_format(),
            "match_comment": self.match_comment.to_mk_file_format(),
        }
        return cast(
            ConditionEventConsoleAlertsType,
            {k: v for k, v in r.items() if v is not None},
        )


# ----------------------------------------------------------------
@dataclass
class NotificationBulkingAlwaysParams:
    subject_for_bulk_notifications: CheckboxWithStrValue
    max_bulk_size: int
    notification_bulks_based_on: list[GroupbyType]
    notification_bulks_based_on_custom_macros: list[str] | None
    time_horizon: int

    def __iter__(self) -> Iterator:
        yield "subject_for_bulk_notifications", self.subject_for_bulk_notifications.api_response()
        yield "max_bulk_size", self.max_bulk_size
        yield "notification_bulks_based_on", self.notification_bulks_based_on
        yield "time_horizon", self.time_horizon
        if self.notification_bulks_based_on_custom_macros is not None:
            yield (
                "notification_bulks_based_on_custom_macros",
                self.notification_bulks_based_on_custom_macros,
            )


@dataclass
class NotificationBulkingTimeoutParams:
    time_period: str
    subject_for_bulk_notifications: CheckboxWithStrValue
    max_bulk_size: int
    notification_bulks_based_on: list[GroupbyType]
    notification_bulks_based_on_custom_macros: list[str] | None
    bulk_outside_timeperiod: BulkOutsideTimePeriod

    def __iter__(self) -> Iterator:
        yield (
            "subject_for_bulk_notifications",
            self.subject_for_bulk_notifications.api_response(),
        )
        yield "bulk_outside_timeperiod", self.bulk_outside_timeperiod.api_response()
        yield "time_period", self.time_period
        yield "max_bulk_size", self.max_bulk_size
        yield "notification_bulks_based_on", self.notification_bulks_based_on

        if self.notification_bulks_based_on_custom_macros is not None:
            yield (
                "notification_bulks_based_on_custom_macros",
                self.notification_bulks_based_on_custom_macros,
            )


@dataclass
class BulkOutsideTimePeriod:
    state: CheckboxState
    subject_for_bulk_notifications: CheckboxWithStrValue
    max_bulk_size: int
    notification_bulks_based_on: list[GroupbyType]
    notification_bulks_based_on_custom_macros: list[str] | None
    time_horizon: int

    @classmethod
    def from_mk_file_format(cls, data: AlwaysBulkParameters | None) -> BulkOutsideTimePeriod:
        if data is None:
            return BulkOutsideTimePeriod.disabled()

        return cls(
            state="enabled",
            subject_for_bulk_notifications=CheckboxWithStrValue.from_mk_file_format(
                data.get("bulk_subject")
            ),
            max_bulk_size=data["count"],
            notification_bulks_based_on=data["groupby"],
            notification_bulks_based_on_custom_macros=data.get("groupby_custom"),
            time_horizon=data["interval"],
        )

    @classmethod
    def from_api_request(cls, data: BulkOutsideAPIValueType) -> BulkOutsideTimePeriod:
        if data["state"] == "disabled":
            return BulkOutsideTimePeriod.disabled()

        value = data["value"]

        return cls(
            state="enabled",
            subject_for_bulk_notifications=CheckboxWithStrValue.from_api_request(
                value["subject_for_bulk_notifications"]
            ),
            max_bulk_size=value["max_bulk_size"],
            notification_bulks_based_on=value["notification_bulks_based_on"],
            notification_bulks_based_on_custom_macros=value.get(
                "notification_bulks_based_on_custom_macros"
            ),
            time_horizon=value["time_horizon"],
        )

    def api_response(self) -> BulkOutsideAPIValueType:
        r: BulkOutsideAPIValueType = {"state": self.state}
        if self.state == "enabled":
            r["value"] = BulkOutsideAPIAttrs(
                subject_for_bulk_notifications=self.subject_for_bulk_notifications.api_response(),
                max_bulk_size=self.max_bulk_size,
                notification_bulks_based_on=self.notification_bulks_based_on,
                time_horizon=self.time_horizon,
            )

            if self.notification_bulks_based_on_custom_macros is not None:
                r["value"]["notification_bulks_based_on_custom_macros"] = (
                    self.notification_bulks_based_on_custom_macros
                )

        return r

    def to_mk_file_format(self) -> AlwaysBulkParameters:
        r = AlwaysBulkParameters(
            count=self.max_bulk_size,
            groupby=self.notification_bulks_based_on,
            interval=self.time_horizon,
        )
        if (bulk_subject := self.subject_for_bulk_notifications.to_mk_file_format()) is not None:
            r["bulk_subject"] = bulk_subject

        if (groupby_custom := self.notification_bulks_based_on_custom_macros) is not None:
            r["groupby_custom"] = groupby_custom

        return r

    @classmethod
    def disabled(cls):
        return cls(
            state="disabled",
            subject_for_bulk_notifications=CheckboxWithStrValue(),
            max_bulk_size=0,
            notification_bulks_based_on=[],
            notification_bulks_based_on_custom_macros=None,
            time_horizon=0,
        )


class BulkOutsideAPIAttrs(TypedDict, total=False):
    time_horizon: int
    notification_bulks_based_on: list[GroupbyType]
    notification_bulks_based_on_custom_macros: list[str]
    max_bulk_size: int
    subject_for_bulk_notifications: CheckboxStrAPIType


class BulkOutsideAPIValueType(CheckboxStateType, total=False):
    value: BulkOutsideAPIAttrs


class NotificationBulkingAPIParams(TypedDict, total=False):
    time_horizon: int
    notification_bulks_based_on: list[GroupbyType]
    notification_bulks_based_on_custom_macros: list[str]
    max_bulk_size: int
    subject_for_bulk_notifications: CheckboxStrAPIType
    time_period: str
    bulk_outside_timeperiod: BulkOutsideAPIValueType


class NotificationBulkingAPIAttrs(TypedDict):
    when_to_bulk: Literal["timeperiod", "always"]
    params: NotificationBulkingAPIParams


class NotificationBulkingAPIValueType(CheckboxStateType, total=False):
    value: NotificationBulkingAPIAttrs


@dataclass
class CheckboxNotificationBulking:
    when_to_bulk: Literal["always", "timeperiod"] = "always"
    bulk: NotificationBulkingAlwaysParams | NotificationBulkingTimeoutParams | None = None

    @classmethod
    def from_mk_file_format(cls, data: NotifyBulkType | None) -> CheckboxNotificationBulking:
        if data is None:
            return cls()

        when_to_bulk, bulk_params = data
        subject_for_bulk_notifications = CheckboxWithStrValue.from_mk_file_format(
            bulk_params.get("bulk_subject")
        )

        bulk: NotificationBulkingAlwaysParams | NotificationBulkingTimeoutParams

        if is_always_bulk(bulk_params):
            bulk = NotificationBulkingAlwaysParams(
                subject_for_bulk_notifications=subject_for_bulk_notifications,
                max_bulk_size=bulk_params["count"],
                notification_bulks_based_on=bulk_params["groupby"],
                notification_bulks_based_on_custom_macros=bulk_params.get("groupby_custom"),
                time_horizon=bulk_params["interval"],
            )
        elif is_timeperiod_bulk(bulk_params):
            bulk = NotificationBulkingTimeoutParams(
                time_period=bulk_params["timeperiod"],
                subject_for_bulk_notifications=subject_for_bulk_notifications,
                max_bulk_size=bulk_params["count"],
                notification_bulks_based_on=bulk_params["groupby"],
                notification_bulks_based_on_custom_macros=bulk_params.get("groupby_custom"),
                bulk_outside_timeperiod=BulkOutsideTimePeriod.from_mk_file_format(
                    bulk_params.get("bulk_outside")
                ),
            )
        return cls(when_to_bulk=when_to_bulk, bulk=bulk)

    @classmethod
    def from_api_request(cls, data: NotificationBulkingAPIValueType) -> CheckboxNotificationBulking:
        if data["state"] == "disabled":
            return cls()

        value = data["value"]
        params = value["params"]
        when_to_bulk = value["when_to_bulk"]
        subject_for_bulk_notifications = CheckboxWithStrValue.from_api_request(
            params["subject_for_bulk_notifications"]
        )

        bulk: NotificationBulkingAlwaysParams | NotificationBulkingTimeoutParams
        if when_to_bulk == "always":
            bulk = NotificationBulkingAlwaysParams(
                subject_for_bulk_notifications=subject_for_bulk_notifications,
                max_bulk_size=params["max_bulk_size"],
                notification_bulks_based_on=params["notification_bulks_based_on"],
                notification_bulks_based_on_custom_macros=params.get(
                    "notification_bulks_based_on_custom_macros"
                ),
                time_horizon=params["time_horizon"],
            )

        elif when_to_bulk == "timeperiod":
            bulk = NotificationBulkingTimeoutParams(
                time_period=params["time_period"],
                subject_for_bulk_notifications=subject_for_bulk_notifications,
                max_bulk_size=params["max_bulk_size"],
                notification_bulks_based_on=params["notification_bulks_based_on"],
                notification_bulks_based_on_custom_macros=params.get(
                    "notification_bulks_based_on_custom_macros"
                ),
                bulk_outside_timeperiod=BulkOutsideTimePeriod.from_api_request(
                    params["bulk_outside_timeperiod"]
                ),
            )

        return cls(when_to_bulk=when_to_bulk, bulk=bulk)

    def api_response(self) -> NotificationBulkingAPIValueType:
        state: CheckboxState = "disabled" if self.bulk is None else "enabled"
        r: NotificationBulkingAPIValueType = {"state": state}
        if self.bulk is not None:
            params = cast(NotificationBulkingAPIParams, dict(self.bulk))
            r["value"] = {"when_to_bulk": self.when_to_bulk, "params": params}
        return r

    def to_mk_file_format(self) -> NotifyBulkType | None:
        if self.bulk is None:
            return None
        r = {
            "count": self.bulk.max_bulk_size,
            "groupby": self.bulk.notification_bulks_based_on,
        }

        if self.bulk.notification_bulks_based_on_custom_macros is not None:
            r["groupby_custom"] = self.bulk.notification_bulks_based_on_custom_macros

        if (
            bulk_subject := self.bulk.subject_for_bulk_notifications.to_mk_file_format()
        ) is not None:
            r["bulk_subject"] = bulk_subject

        if isinstance(self.bulk, NotificationBulkingAlwaysParams):
            r["interval"] = self.bulk.time_horizon
            always_bulk_params = cast(AlwaysBulkParameters, r)
            return ("always", always_bulk_params)

        r.update(
            {
                "timeperiod": self.bulk.time_period,
                "bulk_outside": self.bulk.bulk_outside_timeperiod.to_mk_file_format(),
            }
        )
        timeperiod_bulk_params = cast(TimeperiodBulkParameters, r)
        return ("timeperiod", timeperiod_bulk_params)


# ----------------------------------------------------------------
class API_ExplicitOrStore(TypedDict, total=False):
    option: Literal["explicit", "store"]
    store_id: str


class API_Password(API_ExplicitOrStore, total=False):  # ServiceNowPlugin, SMSAPIPlugin
    password: str


@dataclass
class APIPasswordOption:
    option: Literal["explicit", "store"] | None = None
    store_id: str = ""
    password: str = ""

    @classmethod
    def from_api_request(cls, incoming: API_Password) -> APIPasswordOption:
        if "password" in incoming:
            return cls(option="explicit", password=incoming["password"])
        return cls(option="store", store_id=incoming["store_id"])

    def api_response(self) -> API_Password:
        if self.option is None:
            return {}

        r: API_Password = {"option": self.option}
        if self.option == "explicit":
            r["password"] = self.password
            return r
        r["store_id"] = self.store_id
        return r

    @classmethod
    def from_mk_file_format(cls, data: PasswordType | None) -> APIPasswordOption:
        if data is None:
            return cls()

        if "password" in data:
            return cls(option="explicit", password=data[1])
        return cls(option="store", password=data[1])

    def to_mk_file_format(self) -> PasswordType | None:
        if self.option is None:
            return None

        if self.option == "explicit":
            return "password", self.password
        return "store", self.store_id


# ----------------------------------------------------------------
class APISecret(API_ExplicitOrStore, total=False):
    secret: str


@dataclass
class APISignL4SecretOption:
    option: Literal["explicit", "store"] | None = None
    store_id: str = ""
    secret: str = ""

    @classmethod
    def from_api_request(cls, incoming: APISecret) -> APISignL4SecretOption:
        if "secret" in incoming:
            return cls(option="explicit", secret=incoming["secret"])
        return cls(option="store", store_id=incoming["store_id"])

    def api_response(self) -> APISecret:
        if self.option is None:
            return {}

        r: APISecret = {"option": self.option}
        if self.option == "explicit":
            r["secret"] = self.secret
            return r
        r["store_id"] = self.store_id
        return r

    @classmethod
    def from_mk_file_format(cls, data: PasswordType | None) -> APISignL4SecretOption:
        if data is None:
            return cls()

        if "password" in data:
            return cls(option="explicit", secret=data[1])
        return cls(option="store", secret=data[1])

    def to_mk_file_format(self) -> PasswordType | None:
        if self.option is None:
            return None

        if self.option == "explicit":
            return "password", self.secret
        return "store", self.store_id


# ----------------------------------------------------------------
class APIKey(API_ExplicitOrStore, total=False):
    key: str


@dataclass
class APIIlertKeyOption:
    option: Literal["explicit", "store"] | None = None
    store_id: str = ""
    key: str = ""

    @classmethod
    def from_api_request(cls, incoming: APIKey) -> APIIlertKeyOption:
        if "key" in incoming:
            return cls(option="explicit", key=incoming["key"])
        return cls(option="store", store_id=incoming["store_id"])

    def api_response(self) -> APIKey:
        if self.option is None:
            return {}

        r: APIKey = {"option": self.option}
        if self.option == "explicit":
            r["key"] = self.key
            return r
        r["store_id"] = self.store_id
        return r

    @classmethod
    def from_mk_file_format(cls, data: IlertAPIKey | None) -> APIIlertKeyOption:
        if data is None:
            return cls()

        if "ilert_api_key" in data:
            return cls(option="explicit", key=data[1])
        return cls(option="store", key=data[1])

    def to_mk_file_format(self) -> IlertAPIKey | None:
        if self.option is None:
            return None

        if self.option == "explicit":
            return "ilert_api_key", self.key
        return "store", self.store_id


@dataclass
class APIPagerDutyKeyOption:
    option: Literal["explicit", "store"] | None = None
    store_id: str = ""
    key: str = ""

    @classmethod
    def from_api_request(cls, incoming: APIKey) -> APIPagerDutyKeyOption:
        if "key" in incoming:
            return cls(option="explicit", key=incoming["key"])
        return cls(option="store", store_id=incoming["store_id"])

    def api_response(self) -> APIKey:
        if self.option is None:
            return {}

        r: APIKey = {"option": self.option}
        if self.option == "explicit":
            r["key"] = self.key
            return r
        r["store_id"] = self.store_id
        return r

    @classmethod
    def from_mk_file_format(cls, data: RoutingKeyType | None) -> APIPagerDutyKeyOption:
        if data is None:
            return cls()

        if "routing_key" in data:
            return cls(option="explicit", key=data[1])
        return cls(option="store", key=data[1])

    def to_mk_file_format(self) -> RoutingKeyType | None:
        if self.option is None:
            return None

        if self.option == "explicit":
            return "routing_key", self.key
        return "store", self.store_id


@dataclass
class APIOpenGenieKeyOption:
    option: Literal["explicit", "store"] | None = None
    store_id: str = ""
    key: str = ""

    @classmethod
    def from_api_request(cls, incoming: APIKey) -> APIOpenGenieKeyOption:
        if "key" in incoming:
            return cls(option="explicit", key=incoming["key"])
        return cls(option="store", store_id=incoming["store_id"])

    def api_response(self) -> APIKey:
        if self.option is None:
            return {}

        r: APIKey = {"option": self.option}
        if self.option == "explicit":
            r["key"] = self.key
            return r
        r["store_id"] = self.store_id
        return r

    @classmethod
    def from_mk_file_format(cls, data: PasswordType | None) -> APIOpenGenieKeyOption:
        if data is None:
            return cls()

        if "password" in data:
            return cls(option="explicit", key=data[1])
        return cls(option="store", key=data[1])

    def to_mk_file_format(self) -> PasswordType | None:
        if self.option is None:
            return None

        if self.option == "explicit":
            return "password", self.key
        return "store", self.store_id


# ----------------------------------------------------------------
class API_WebhookURL(API_ExplicitOrStore, total=False):
    url: str


@dataclass
class WebhookURLOption:
    option: Literal["explicit", "store"] | None = None
    store_id: str = ""
    url: str = ""

    @classmethod
    def from_mk_file_format(cls, data: WebHookUrl | None) -> WebhookURLOption:
        if data is None:
            return cls()

        if "webhook_url" in data:
            return cls(option="explicit", url=data[1])
        return cls(option="store", store_id=data[1])

    @classmethod
    def from_api_request(cls, incoming: API_WebhookURL) -> WebhookURLOption:
        if "url" in incoming:
            return cls(option="explicit", url=incoming["url"])
        return cls(option="store", store_id=incoming["store_id"])

    def api_response(self) -> API_WebhookURL:
        if self.option is None:
            return {}

        r: API_WebhookURL = {"option": self.option}
        if self.option == "explicit":
            r["url"] = self.url
            return r
        r["store_id"] = self.store_id
        return r

    def to_mk_file_format(self) -> WebHookUrl | None:
        if self.option is None:
            return None

        if self.option == "explicit":
            return "webhook_url", self.url
        return "store", self.store_id


# ----------------------------------------------------------------


class API_AsciiMailData(TypedDict, total=False):
    plugin_name: Required[AsciiMailPluginName]
    from_details: FromAndToEmailFieldsAPIValueType
    reply_to: FromAndToEmailFieldsAPIValueType
    subject_for_host_notifications: CheckboxStrAPIType
    subject_for_service_notifications: CheckboxStrAPIType
    send_separate_notification_to_every_recipient: CheckboxStateType
    sort_order_for_bulk_notifications: CheckboxSortOrderAPIType
    body_head_for_both_host_and_service_notifications: CheckboxStrAPIType
    body_tail_for_host_notifications: CheckboxStrAPIType
    body_tail_for_service_notifications: CheckboxStrAPIType


class API_HTMLMailData(TypedDict, total=False):
    plugin_name: Required[MailPluginName]
    from_details: FromAndToEmailFieldsAPIValueType
    reply_to: FromAndToEmailFieldsAPIValueType
    subject_for_host_notifications: CheckboxStrAPIType
    subject_for_service_notifications: CheckboxStrAPIType
    info_to_be_displayed_in_the_email_body: CheckboxEmailBodyInfoAPIType
    insert_html_section_between_body_and_table: CheckboxStrAPIType
    url_prefix_for_links_to_checkmk: CheckboxURLPrefixAPIValueType
    sort_order_for_bulk_notifications: CheckboxSortOrderAPIType
    send_separate_notification_to_every_recipient: CheckboxStateType
    enable_sync_smtp: API_EnableSyncViaSMTPValueType
    display_graphs_among_each_other: CheckboxStateType
    graphs_per_notification: CheckboxIntAPIType
    bulk_notifications_with_graphs: CheckboxIntAPIType


class API_CiscoData(TypedDict, total=False):
    plugin_name: Required[CiscoPluginName]
    webhook_url: API_WebhookURL
    http_proxy: HttpProxyAPIValueType
    url_prefix_for_links_to_checkmk: CheckboxURLPrefixAPIValueType
    disable_ssl_cert_verification: CheckboxStateType


class API_MKEventData(TypedDict, total=False):
    plugin_name: Required[MkeventdPluginName]
    syslog_facility_to_use: SysLogFacilityAPIValueType
    ip_address_of_remote_event_console: CheckboxStrAPIType


class API_IlertData(TypedDict, total=False):
    plugin_name: Required[IlertPluginName]
    api_key: APIKey
    disable_ssl_cert_verification: CheckboxStateType
    notification_priority: Literal["HIGH", "LOW"]
    custom_summary_for_host_alerts: str
    custom_summary_for_service_alerts: str
    url_prefix_for_links_to_checkmk: CheckboxURLPrefixAPIValueType
    http_proxy: HttpProxyAPIValueType


class API_JiraData(TypedDict, total=False):
    plugin_name: Required[JiraPluginName]
    jira_url: str
    disable_ssl_cert_verification: CheckboxStateType
    username: str
    password: str
    project_id: str
    issue_type_id: str
    host_custom_id: str
    service_custom_id: str
    monitoring_url: str
    site_custom_id: CheckboxStrAPIType
    priority_id: CheckboxStrAPIType
    host_summary: CheckboxStrAPIType
    service_summary: CheckboxStrAPIType
    label: CheckboxStrAPIType
    resolution_id: CheckboxStrAPIType
    optional_timeout: CheckboxStrAPIType


class API_OpsGenieIssueData(TypedDict, total=False):
    plugin_name: Required[OpsGeniePluginName]
    api_key: APIKey
    domain: CheckboxStrAPIType
    disable_ssl_cert_verification: CheckboxStateType
    http_proxy: HttpProxyAPIValueType
    owner: CheckboxStrAPIType
    source: CheckboxStrAPIType
    priority: OpsGeniePriorityAPIType
    note_while_creating: CheckboxStrAPIType
    note_while_closing: CheckboxStrAPIType
    desc_for_host_alerts: CheckboxStrAPIType
    desc_for_service_alerts: CheckboxStrAPIType
    message_for_host_alerts: CheckboxStrAPIType
    message_for_service_alerts: CheckboxStrAPIType
    responsible_teams: CheckboxListOfStrAPIType
    actions: CheckboxListOfStrAPIType
    tags: CheckboxListOfStrAPIType
    entity: CheckboxStrAPIType


class API_PagerDutyData(TypedDict, total=False):
    plugin_name: Required[PagerdutyPluginName]
    integration_key: APIKey
    disable_ssl_cert_verification: CheckboxStateType
    http_proxy: HttpProxyAPIValueType
    url_prefix_for_links_to_checkmk: CheckboxURLPrefixAPIValueType


class API_PushOverData(TypedDict, total=False):
    plugin_name: Required[PushoverPluginName]
    api_key: str
    user_group_key: str
    url_prefix_for_links_to_checkmk: CheckboxStrAPIType
    http_proxy: HttpProxyAPIValueType
    priority: CheckboxPushoverPriorityAPIType
    sound: CheckboxPushoverSoundAPIType


class API_ServiceNowData(TypedDict, total=False):
    plugin_name: Required[ServiceNowPluginName]
    servicenow_url: str
    http_proxy: HttpProxyAPIValueType
    username: str
    user_password: API_Password
    use_site_id_prefix: CheckboxUseSiteIDPrefixAPIType
    optional_timeout: CheckboxStrAPIType
    management_type: MgmtTypeAPI


class API_SignL4Data(TypedDict, total=False):
    plugin_name: Required[Signl4PluginName]
    team_secret: APISecret
    url_prefix_for_links_to_checkmk: CheckboxURLPrefixAPIValueType
    disable_ssl_cert_verification: CheckboxStateType
    http_proxy: HttpProxyAPIValueType


class API_SlackData(TypedDict, total=False):
    plugin_name: Required[SlackPluginName]
    webhook_url: API_WebhookURL
    url_prefix_for_links_to_checkmk: CheckboxURLPrefixAPIValueType
    disable_ssl_cert_verification: CheckboxStateType
    http_proxy: HttpProxyAPIValueType


class API_SmsAPIData(TypedDict, total=False):
    plugin_name: Required[SmsApiPluginName]
    modem_type: Literal["trb140"]
    modem_url: str
    disable_ssl_cert_verification: CheckboxStateType
    http_proxy: HttpProxyAPIValueType
    username: str
    user_password: API_Password
    timeout: str


class API_SmsData(TypedDict, total=False):
    plugin_name: Required[SmsPluginName]
    params: list[str]


class API_SpectrumData(TypedDict, total=False):
    plugin_name: Required[SpectrumPluginName]
    base_oid: str
    destination_ip: str
    snmp_community: str


class API_VictorOpsData(TypedDict, total=False):
    plugin_name: Required[SplunkPluginName]
    splunk_on_call_rest_endpoint: API_WebhookURL
    url_prefix_for_links_to_checkmk: CheckboxURLPrefixAPIValueType
    disable_ssl_cert_verification: CheckboxStateType
    http_proxy: HttpProxyAPIValueType


class API_MSTeamsData(TypedDict, total=False):
    plugin_name: Required[MSTeamsPluginName]
    webhook_url: API_WebhookURL
    http_proxy: HttpProxyAPIValueType
    host_title: CheckboxStrAPIType
    service_title: CheckboxStrAPIType
    host_summary: CheckboxStrAPIType
    service_summary: CheckboxStrAPIType
    url_prefix_for_links_to_checkmk: CheckboxURLPrefixAPIValueType
    host_details: CheckboxStrAPIType
    service_details: CheckboxStrAPIType
    affected_host_groups: CheckboxStateType


class APIPluginDict(TypedDict, total=False):
    """Users can create their own plugins"""

    plugin_name: CustomPluginName


class APIPluginList(TypedDict, total=False):
    """Users can create their own plugins"""

    plugin_name: CustomPluginName
    params: list[str]


PluginType = (
    API_AsciiMailData
    | API_HTMLMailData
    | API_CiscoData
    | API_MKEventData
    | API_IlertData
    | API_JiraData
    | API_OpsGenieIssueData
    | API_PagerDutyData
    | API_PushOverData
    | API_ServiceNowData
    | API_SignL4Data
    | API_SlackData
    | API_SmsAPIData
    | API_SpectrumData
    | API_VictorOpsData
    | API_MSTeamsData
    | API_SmsData
    | APIPluginDict
    | APIPluginList
)


class APIRuleProperties(TypedDict, total=False):
    description: str
    comment: str
    documentation_url: str
    do_not_apply_this_rule: CheckboxStateType
    allow_users_to_deactivate: CheckboxStateType
    user_id: str | None
    rule_id: str


class APINotifyPlugin(TypedDict):
    option: PluginOptions | str  # str only required for the openapi docs example
    plugin_params: PluginType


class APINotificationMethod(TypedDict, total=False):
    notify_plugin: APINotifyPlugin
    notification_bulking: NotificationBulkingAPIValueType


class APIContactSelection(TypedDict, total=False):
    all_contacts_of_the_notified_object: CheckboxStateType
    all_users: CheckboxStateType
    all_users_with_an_email_address: CheckboxStateType
    the_following_users: CheckboxListOfStrAPIType
    members_of_contact_groups: CheckboxListOfStrAPIType
    explicit_email_addresses: CheckboxListOfStrAPIType
    restrict_by_custom_macros: ContactMatchMacrosAPIValueType
    restrict_by_contact_groups: CheckboxListOfStrAPIType


class APIConditions(TypedDict, total=False):
    match_sites: CheckboxListOfStrAPIType
    match_folder: CheckboxStrAPIType
    match_host_tags: MatchHostTagsAPIValueType
    match_host_labels: MatchLabelsAPIValueType
    match_host_groups: CheckboxListOfStrAPIType
    match_hosts: CheckboxListOfStrAPIType
    match_exclude_hosts: CheckboxListOfStrAPIType
    match_service_labels: MatchLabelsAPIValueType
    match_service_groups: CheckboxListOfStrAPIType
    match_exclude_service_groups: CheckboxListOfStrAPIType
    match_service_groups_regex: MatchServiceGroupsRegexAPIValueType
    match_exclude_service_groups_regex: MatchServiceGroupsRegexAPIValueType
    match_services: CheckboxListOfStrAPIType
    match_exclude_services: CheckboxListOfStrAPIType
    match_check_types: CheckboxListOfStrAPIType
    match_plugin_output: CheckboxStrAPIType
    match_contact_groups: CheckboxListOfStrAPIType
    match_service_levels: MatchServiceLevelsAPIValueType
    match_only_during_time_period: CheckboxStrAPIType
    match_host_event_type: MatchHostEventsAPIValueType
    match_service_event_type: MatchServiceEventsAPIValueType
    restrict_to_notification_numbers: NotificationNumbersAPIValueType
    throttle_periodic_notifications: ThrottlePeriodicNotificationsAPIValueType
    match_notification_comment: CheckboxStrAPIType
    event_console_alerts: EventConsoleAPIValueType


class APINotificationRule(TypedDict, total=False):
    rule_properties: APIRuleProperties
    notification_method: APINotificationMethod
    contact_selection: APIContactSelection
    conditions: APIConditions


class APINotificationRuleConfig(TypedDict, total=False):
    rule_config: APINotificationRule
