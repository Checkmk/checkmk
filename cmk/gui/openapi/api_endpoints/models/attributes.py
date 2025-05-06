#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime as dt
import re
from dataclasses import dataclass
from typing import Annotated, Literal, Self

from annotated_types import Ge, Interval, MaxLen, MinLen
from pydantic import AfterValidator, model_validator

from cmk.gui.fields.attributes import (
    AuthProtocolConverter,
    AuthProtocolType,
    PrivacyProtocolConverter,
    PrivacyProtocolType,
)
from cmk.gui.openapi.framework.model import api_field, ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import IPv4NetworkString, IPv4String, RegexString
from cmk.gui.openapi.framework.model.dynamic_fields import WithDynamicFields
from cmk.gui.openapi.framework.model_validators import GroupValidator, TagValidator, UserValidator


@dataclass(kw_only=True, slots=True)
class HostContactGroupModel:
    groups: list[Annotated[str, AfterValidator(GroupValidator(group_type="host").exists)]] = (
        api_field(description="A list of contact groups.", example="all")
    )
    use: bool = api_field(description="Add these contact groups to the host.", default=False)
    use_for_services: bool = api_field(
        description="<p>Always add host contact groups also to its services.</p>With this option contact groups that are added to hosts are always being added to services, as well. This only makes a difference if you have assigned other contact groups to services via rules in <i>Host & Service Parameters</i>. As long as you do not have any such rule a service always inherits all contact groups from its host.",
        default=False,
    )
    recurse_use: bool = api_field(
        description="Add these groups as contacts to all hosts in all sub-folders of this folder.",
        default=False,
    )
    recurse_perms: bool = api_field(
        description="Give these groups also permission on all sub-folders.", default=False
    )


@dataclass(kw_only=True, slots=True)
class SNMPCommunityModel:
    type: Literal["v1_v2_community"] = "v1_v2_community"
    community: str = api_field(description="SNMP community (SNMP Versions 1 and 2c)")


@dataclass(kw_only=True, slots=True)
class SNMPv3NoAuthNoPrivacyModel:
    type: Literal["noAuthNoPriv"] = "noAuthNoPriv"
    security_name: str = api_field(description="Security name")

    @classmethod
    def from_checkmk_tuple(cls, value: tuple[Literal["noAuthNoPriv"], str]) -> Self:
        return cls(
            type=value[0],
            security_name=value[1],
        )

    def to_checkmk_tuple(self) -> tuple[Literal["noAuthNoPriv"], str]:
        return self.type, self.security_name


@dataclass(kw_only=True, slots=True)
class SNMPv3AuthNoPrivacyModel:
    type: Literal["authNoPriv"] = "authNoPriv"
    auth_protocol: AuthProtocolType = api_field(description="Authentication protocol.")
    security_name: str = api_field(description="Security name")
    auth_password: Annotated[str, MinLen(8)] = api_field(
        description="Authentication pass phrase.",
    )

    @classmethod
    def from_checkmk_tuple(cls, value: tuple[Literal["authNoPriv"], str, str, str]) -> Self:
        return cls(
            type=value[0],
            auth_protocol=AuthProtocolConverter.from_checkmk(value[1]),
            security_name=value[2],
            auth_password=value[3],
        )

    def to_checkmk_tuple(self) -> tuple[Literal["authNoPriv"], str, str, str]:
        return (
            self.type,
            AuthProtocolConverter.to_checkmk(self.auth_protocol),
            self.security_name,
            self.auth_password,
        )


@dataclass(kw_only=True, slots=True)
class SNMPv3AuthPrivacyModel:
    type: Literal["authPriv"] = "authPriv"
    auth_protocol: AuthProtocolType = api_field(description="Authentication protocol.")
    security_name: str = api_field(description="Security name")
    auth_password: Annotated[str, MinLen(8)] = api_field(
        description="Authentication pass phrase.",
    )
    privacy_protocol: PrivacyProtocolType = api_field(
        description="The privacy protocol. The only supported values in the Raw Edition are CBC-DES and AES-128. If selected, privacy_password needs to be supplied as well."
    )
    privacy_password: Annotated[str, MinLen(8)] = api_field(
        description="Privacy pass phrase. If filled, privacy_protocol needs to be selected as well.",
    )

    @classmethod
    def from_checkmk_tuple(cls, value: tuple[Literal["authPriv"], str, str, str, str, str]) -> Self:
        return cls(
            type=value[0],
            auth_protocol=AuthProtocolConverter.from_checkmk(value[1]),
            security_name=value[2],
            auth_password=value[3],
            privacy_protocol=PrivacyProtocolConverter.from_checkmk(value[4]),
            privacy_password=value[5],
        )

    def to_checkmk_tuple(self) -> tuple[Literal["authPriv"], str, str, str, str, str]:
        return (
            self.type,
            AuthProtocolConverter.to_checkmk(self.auth_protocol),
            self.security_name,
            self.auth_password,
            PrivacyProtocolConverter.to_checkmk(self.privacy_protocol),
            self.privacy_password,
        )


SNMPCredentialsModel = (
    SNMPCommunityModel
    | SNMPv3NoAuthNoPrivacyModel
    | SNMPv3AuthNoPrivacyModel
    | SNMPv3AuthPrivacyModel
)


@dataclass(kw_only=True, slots=True)
class IPAddressRangeModel:
    type: Literal["ip_range"] = "ip_range"
    from_address: IPv4String = api_field(description="The first IPv4 address of this range.")
    to_address: IPv4String = api_field(description="The last IPv4 address of this range.")

    @classmethod
    def from_checkmk_tuple(cls, value: tuple[Literal["ip_range"], tuple[str, str]]) -> Self:
        return cls(
            type=value[0],
            from_address=IPv4String(value[1][0]),
            to_address=IPv4String(value[1][1]),
        )

    def to_checkmk_tuple(self) -> tuple[Literal["ip_range"], tuple[str, str]]:
        return self.type, (str(self.from_address), str(self.to_address))


@dataclass(kw_only=True, slots=True)
class IPNetworkModel:
    type: Literal["ip_network"] = "ip_network"
    network: IPv4NetworkString = api_field(
        description="A IPv4 network in CIDR notation. Minimum prefix length is 8 bit, maximum prefix length is 30 bit.\n\nValid examples:\n\n * `192.168.0.0/24`\n * `192.168.0.0/255.255.255.0`"
    )

    @classmethod
    def from_checkmk_tuple(cls, value: tuple[Literal["ip_network"], str]) -> Self:
        return cls(
            type=value[0],
            network=value[1],
        )

    def to_checkmk_tuple(self) -> tuple[Literal["ip_network"], str]:
        return self.type, self.network


@dataclass(kw_only=True, slots=True)
class IPAddressesModel:
    type: Literal["ip_list"] = "ip_list"
    addresses: list[IPv4String] = api_field(description="List of IPv4 addresses")

    @classmethod
    def from_checkmk_tuple(cls, value: tuple[Literal["ip_list"], list[str]]) -> Self:
        return cls(
            type=value[0],
            addresses=[IPv4String(x) for x in value[1]],
        )

    def to_checkmk_tuple(self) -> tuple[Literal["ip_list"], list[str]]:
        return self.type, [str(x) for x in self.addresses]


@dataclass(kw_only=True, slots=True)
class IPRegexpModel:
    type: Literal["ip_regex_list"] = "ip_regex_list"
    regexp_list: list[RegexString] = api_field(
        description="A list of regular expressions which are matched against the found IP addresses. The matches will be excluded from the result."
    )

    @classmethod
    def from_checkmk_tuple(cls, value: tuple[Literal["ip_regex_list"], list[str]]) -> Self:
        return cls(
            type=value[0],
            regexp_list=[RegexString(x) for x in value[1]],
        )

    def to_checkmk_tuple(self) -> tuple[Literal["ip_regex_list"], list[str]]:
        return self.type, [str(x) for x in self.regexp_list]


IPRangeWithRegexpModel = IPAddressRangeModel | IPNetworkModel | IPAddressesModel | IPRegexpModel
_CheckmkTime = tuple[int, int]


@dataclass(kw_only=True, slots=True)
class TimeAllowedRangeModel:
    start: dt.time = api_field(
        description="The start time of day. Inclusive. Use ISO8601 format. Seconds are stripped."
    )
    end: dt.time = api_field(
        description="The end time of day. Inclusive. Use ISO8601 format. Seconds are stripped."
    )

    @staticmethod
    def _from_checkmk_time(value: _CheckmkTime) -> dt.time:
        if value[0] == 24 and value[1] == 0:
            # special case for 24:00
            return dt.time(23, 59, 59)

        return dt.time(value[0], value[1])

    @classmethod
    def from_checkmk_tuple(cls, value: tuple[_CheckmkTime, _CheckmkTime]) -> Self:
        return cls(
            start=cls._from_checkmk_time(value[0]),
            end=cls._from_checkmk_time(value[1]),
        )

    def to_checkmk_tuple(self) -> tuple[_CheckmkTime, _CheckmkTime]:
        return (self.start.hour, self.start.minute), (self.end.hour, self.end.minute)


@dataclass(kw_only=True, slots=True)
class RegexpRewritesModel:
    search: Annotated[RegexString, MaxLen(30)] = api_field(
        description="The search regexp. May contain match-groups, conditional matches, etc. This follows the Python regular expression syntax.\n\nFor details see:\n\n * https://docs.python.org/3/library/re.html"
    )
    replace_with: Annotated[str, MaxLen(30)] = api_field(
        description="The replacement string. Match-groups can only be identified by `\\1`, `\\2`, etc. Highest supported match group is `\\99`. Named lookups are not supported."
    )

    @model_validator(mode="after")
    def _validate(self) -> Self:
        search = re.compile(self.search)
        replace_groups = list(set(re.findall(r"\\([1-9]\d+|\d(?!\d))", self.replace_with)))
        replace_groups.sort()

        # NOTE
        # We don't need to check for exhaustive use of the replacement groups. We only need
        # to check the highest match-group used in the replacement, as this is the only case
        # where a mismatch may occur.
        if replace_groups:
            highest_replacement_group = int(replace_groups[-1])
            if highest_replacement_group > search.groups:
                raise ValueError(
                    "The replacement string contains a match group that is not defined in the regexp."
                )

        return self

    @classmethod
    def from_checkmk_tuple(cls, value: tuple[str, str]) -> Self:
        return cls(
            search=RegexString(value[0]),
            replace_with=value[1],
        )

    def to_checkmk_tuple(self) -> tuple[str, str]:
        return str(self.search), self.replace_with


@dataclass(kw_only=True, slots=True)
class DirectMappingModel:
    # TODO: CheckmkTuple
    hostname: str = api_field(description="The host name to be replaced.")
    replace_with: str = api_field(description="The replacement string.")

    @classmethod
    def from_checkmk_tuple(cls, value: tuple[str, str]) -> Self:
        return cls(
            hostname=value[0],
            replace_with=value[1],
        )

    def to_checkmk_tuple(self) -> tuple[str, str]:
        return self.hostname, self.replace_with


@dataclass(kw_only=True, slots=True)
class TranslateNamesModel:
    case: Literal["nop", "lower", "upper"] = api_field(
        alias="convert_case",
        description="Convert all detected host names to upper- or lower-case.\n\n * `nop` - Do not convert anything\n * `lower` - Convert all host names to lowercase.\n * `upper` - Convert all host names to uppercase.",
        default="nop",
    )
    drop_domain: bool | ApiOmitted = api_field(
        description=(
            "Drop the rest of the domain, only keep the host name. Will not affect "
            "IP addresses.\n\n"
            "Examples:\n\n"
            " * `192.168.0.1` -> `192.168.0.1`\n"
            " * `foobar.example.com` -> `foobar`\n"
            " * `example.com` -> `example`\n"
            " * `example` -> `example`\n\n"
            "This will be executed **after**:\n\n"
            " * `convert_case`\n"
        ),
        default_factory=ApiOmitted,
    )
    regex: list[RegexpRewritesModel] | ApiOmitted = api_field(
        alias="regexp_rewrites",
        description=(
            "Rewrite discovered host names with multiple regular expressions. The "
            "replacements will be done one after another in the order they appear "
            "in the list. If not anchored at the end by a `$` character, the regexp"
            "will be anchored at the end implicitly by adding a `$` character.\n\n"
            "These will be executed **after**:\n\n"
            " * `convert_case`\n"
            " * `drop_domain`\n"
        ),
        default_factory=ApiOmitted,
    )
    mapping: list[DirectMappingModel] | ApiOmitted = api_field(
        alias="hostname_replacement",
        description=(
            "Replace one value with another.\n\n"
            "These will be executed **after**:\n\n"
            " * `convert_case`\n"
            " * `drop_domain`\n"
            " * `regexp_rewrites`\n"
        ),
        default_factory=ApiOmitted,
    )


@dataclass(kw_only=True, slots=True)
class NetworkScanModel:
    ip_ranges: list[IPRangeWithRegexpModel] = api_field(
        alias="addresses", description="IPv4 addresses to include."
    )
    exclude_ranges: list[IPRangeWithRegexpModel] | ApiOmitted = api_field(
        alias="exclude_addresses",
        description="IPv4 addresses to exclude.",
        default_factory=ApiOmitted,
    )
    scan_interval: Annotated[int, Ge(3600)] | ApiOmitted = api_field(
        description="Scan interval in seconds. Default is 1 day, minimum is 1 hour.",
        default=60 * 60 * 24,
    )
    time_allowed: list[TimeAllowedRangeModel] = api_field(
        description="Only execute the discovery during this time range each day."
    )
    set_ipaddress: bool = api_field(
        description="When set, the found IPv4 address is set on the discovered host.", default=True
    )
    max_parallel_pings: Annotated[int, Interval(ge=1, le=200)] = api_field(
        description="Set the maximum number of concurrent pings sent to target IP addresses.",
        default=100,
    )
    run_as: Annotated[str, AfterValidator(UserValidator.active)] | ApiOmitted = api_field(
        description="Execute the network scan in the Checkmk user context of the chosen user. This user needs the permission to add new hosts to this folder.",
    )
    tag_criticality: Annotated[
        str | ApiOmitted, AfterValidator(TagValidator.tag_criticality_presence)
    ] = api_field(
        description="Specify which criticality tag to set on the host created by the network scan. This field is required if the criticality tag group exists, otherwise it as to be omitted.",
        default_factory=ApiOmitted,
    )
    translate_names: TranslateNamesModel | ApiOmitted = api_field(
        description="Name translation settings",
        default_factory=ApiOmitted,
    )


@dataclass(kw_only=True, slots=True)
class IPMIParametersModel:
    username: str = api_field(description="IPMI username")
    password: str = api_field(description="IPMI password")


@dataclass(kw_only=True, slots=True)
class NetworkScanResultModel:
    start: dt.datetime | ApiOmitted = api_field(
        description="When the scan started", default_factory=ApiOmitted
    )
    end: dt.datetime | ApiOmitted = api_field(
        description="When the scan finished. Will be Null if not yet run.",
        default_factory=ApiOmitted,
    )
    state: Literal["running", "succeeded", "failed"] = api_field(description="Last scan result")
    output: str = api_field(description="Short human readable description of what is happening.")


@dataclass(kw_only=True, slots=True)
class MetaDataModel:
    created_at: dt.datetime | None | ApiOmitted = api_field(
        description="When has this object been created.",
        default_factory=ApiOmitted,
    )
    updated_at: dt.datetime | None | ApiOmitted = api_field(
        description="When this object was last changed.",
        default_factory=ApiOmitted,
    )
    created_by: str | None | ApiOmitted = api_field(
        description="The user id under which this object has been created.",
        default_factory=ApiOmitted,
    )


@dataclass(kw_only=True, slots=True)
class LockedByModel:
    # TODO: CheckmkTuple?
    site_id: str = api_field(description="Site ID")
    program_id: str = api_field(description="Program ID")
    instance_id: str = api_field(description="Instance ID")


@dataclass(kw_only=True)
class FolderCustomHostAttributesAndTagGroupsModel(WithDynamicFields):
    """Class for custom host attributes and tag groups."""

    # TODO: validate the attribute key as well as value possibly with Annotated?
    dynamic_fields: dict[str, str] = api_field(
        description=(
            "The property name must be\n\n"
            " * A custom host attribute\n"
            " * A custom tag group starting with `tag_`\n"
        ),
        default_factory=dict,
    )
