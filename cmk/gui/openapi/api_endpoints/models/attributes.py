#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime as dt
import re
from collections.abc import Sequence
from dataclasses import dataclass
from ipaddress import IPv4Network
from typing import Annotated, Literal, Self

from annotated_types import Ge, Interval, MaxLen, MinLen
from pydantic import AfterValidator, model_validator, WithJsonSchema

from cmk.ccc.hostaddress import HostAddress
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId

from cmk.utils.translations import TranslationOptionsSpec

from cmk.gui.fields.attributes import (
    AuthProtocolConverter,
    AuthProtocolType,
    PrivacyProtocolConverter,
    PrivacyProtocolType,
)
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework.model import api_field, ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import IPv4String, RegexString
from cmk.gui.openapi.framework.model.converter import (
    GroupConverter,
    TagConverter,
    TypedPlainValidator,
    UserConverter,
)
from cmk.gui.openapi.framework.model.dynamic_fields import WithDynamicFields
from cmk.gui.watolib.host_attributes import (
    ExcludeIPRange,
    HostContactGroupSpec,
    IPMICredentials,
    IPRange,
    MetaData,
    NetworkScanResult,
    NetworkScanSpec,
)


@dataclass(kw_only=True, slots=True)
class HostContactGroupModel:
    groups: list[Annotated[str, AfterValidator(GroupConverter(group_type="host").exists)]] = (
        api_field(description="A list of contact groups.", example="all")
    )
    use: bool = api_field(description="Add these contact groups to the host.")
    use_for_services: bool = api_field(
        description="<p>Always add host contact groups also to its services.</p>With this option contact groups that are added to hosts are always being added to services, as well. This only makes a difference if you have assigned other contact groups to services via rules in <i>Host & Service Parameters</i>. As long as you do not have any such rule a service always inherits all contact groups from its host.",
    )
    recurse_use: bool = api_field(
        description="Add these groups as contacts to all hosts in all sub-folders of this folder.",
    )
    recurse_perms: bool = api_field(
        description="Give these groups also permission on all sub-folders."
    )

    @classmethod
    def from_internal(cls, value: HostContactGroupSpec) -> "HostContactGroupModel":
        return cls(
            groups=value["groups"],
            use=value["use"],
            use_for_services=value["use_for_services"],
            recurse_use=value["recurse_use"],
            recurse_perms=value["recurse_perms"],
        )

    def to_internal(self) -> HostContactGroupSpec:
        return {
            "groups": self.groups,
            "use": self.use,
            "use_for_services": self.use_for_services,
            "recurse_use": self.recurse_use,
            "recurse_perms": self.recurse_perms,
        }


@dataclass(kw_only=True, slots=True)
class SNMPCommunityModel:
    type: Literal["v1_v2_community"] = api_field(description="SNMP v1 or v2 with community")
    community: str = api_field(description="SNMP community (SNMP Versions 1 and 2c)")


@dataclass(kw_only=True, slots=True)
class SNMPv3NoAuthNoPrivacyModel:
    type: Literal["noAuthNoPriv"] = api_field(
        description="SNMPv3 without authentication or privacy"
    )
    security_name: str = api_field(description="Security name")

    @classmethod
    def from_internal(cls, value: tuple[Literal["noAuthNoPriv"], str]) -> Self:
        return cls(
            type=value[0],
            security_name=value[1],
        )

    def to_internal(self) -> tuple[Literal["noAuthNoPriv"], str]:
        return self.type, self.security_name


@dataclass(kw_only=True, slots=True)
class SNMPv3AuthNoPrivacyModel:
    type: Literal["authNoPriv"] = api_field(
        description="SNMPv3 with authentication, but without privacy"
    )
    auth_protocol: AuthProtocolType = api_field(description="Authentication protocol.")
    security_name: str = api_field(description="Security name")
    auth_password: Annotated[str, MinLen(8)] = api_field(
        description="Authentication pass phrase.",
    )

    @classmethod
    def from_internal(cls, value: tuple[Literal["authNoPriv"], str, str, str]) -> Self:
        return cls(
            type=value[0],
            auth_protocol=AuthProtocolConverter.from_checkmk(value[1]),
            security_name=value[2],
            auth_password=value[3],
        )

    def to_internal(self) -> tuple[Literal["authNoPriv"], str, str, str]:
        return (
            self.type,
            AuthProtocolConverter.to_checkmk(self.auth_protocol),
            self.security_name,
            self.auth_password,
        )


@dataclass(kw_only=True, slots=True)
class SNMPv3AuthPrivacyModel:
    type: Literal["authPriv"] = api_field(description="SNMPv3 with authentication and privacy")
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
    def from_internal(cls, value: tuple[Literal["authPriv"], str, str, str, str, str]) -> Self:
        return cls(
            type=value[0],
            auth_protocol=AuthProtocolConverter.from_checkmk(value[1]),
            security_name=value[2],
            auth_password=value[3],
            privacy_protocol=PrivacyProtocolConverter.from_checkmk(value[4]),
            privacy_password=value[5],
        )

    def to_internal(self) -> tuple[Literal["authPriv"], str, str, str, str, str]:
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


class SNMPCredentialsConverter:
    @staticmethod
    def from_internal(value: str | tuple) -> SNMPCredentialsModel:
        if isinstance(value, str):
            return SNMPCommunityModel(
                type="v1_v2_community",
                community=value,
            )

        match value[0]:
            case "noAuthNoPriv":
                return SNMPv3NoAuthNoPrivacyModel.from_internal(value)
            case "authPriv":
                return SNMPv3AuthNoPrivacyModel.from_internal(value)
            case "authPriv":
                return SNMPv3AuthPrivacyModel.from_internal(value)
            case _:
                raise ValueError(f"Unknown SNMP credentials type: {value[0]!r}")

    @staticmethod
    def to_internal(field: SNMPCredentialsModel) -> str | tuple:
        match field:
            case SNMPCommunityModel():
                return field.community
            case SNMPv3NoAuthNoPrivacyModel():
                return field.to_internal()
            case SNMPv3AuthNoPrivacyModel():
                return field.to_internal()
            case SNMPv3AuthPrivacyModel():
                return field.to_internal()
            case _:
                raise ValueError(f"Unknown SNMP credentials type: {field.type!r}")


@dataclass(kw_only=True, slots=True)
class IPAddressRangeModel:
    type: Literal["ip_range"] = api_field(description="Select a range of IP addresses")
    from_address: IPv4String = api_field(description="The first IPv4 address of this range.")
    to_address: IPv4String = api_field(description="The last IPv4 address of this range.")

    @classmethod
    def from_internal(cls, value: tuple[Literal["ip_range"], tuple[str, str]]) -> Self:
        return cls(
            type=value[0],
            from_address=IPv4String(value[1][0]),
            to_address=IPv4String(value[1][1]),
        )

    def to_internal(self) -> tuple[Literal["ip_range"], tuple[str, str]]:
        return self.type, (str(self.from_address), str(self.to_address))


@dataclass(kw_only=True, slots=True)
class IPNetworkModel:
    type: Literal["ip_network"] = api_field(description="Select an entire network")
    network: IPv4Network = api_field(
        description="A IPv4 network in CIDR notation. Minimum prefix length is 8 bit, maximum prefix length is 30 bit.\n\nValid examples:\n\n * `192.168.0.0/24`\n * `192.168.0.0/255.255.255.0`"
    )

    @classmethod
    def from_internal(cls, value: tuple[Literal["ip_network"], tuple[str, int]]) -> Self:
        network, mask = value[1]
        return cls(
            type=value[0],
            network=IPv4Network(f"{network}/{mask}"),
        )

    def to_internal(self) -> tuple[Literal["ip_network"], tuple[str, int]]:
        return self.type, (str(self.network.network_address), self.network.prefixlen)


@dataclass(kw_only=True, slots=True)
class IPAddressesModel:
    type: Literal["ip_list"] = api_field(description="Select multiple explicit IP addresses")
    addresses: list[IPv4String] = api_field(description="List of IPv4 addresses")

    @classmethod
    def from_internal(cls, value: tuple[Literal["ip_list"], Sequence[HostAddress]]) -> Self:
        return cls(
            type=value[0],
            addresses=[IPv4String(x) for x in value[1]],
        )

    def to_internal(self) -> tuple[Literal["ip_list"], Sequence[HostAddress]]:
        return self.type, [HostAddress(x) for x in self.addresses]


@dataclass(kw_only=True, slots=True)
class IPRegexpModel:
    type: Literal["ip_regex_list"] = api_field(description="Deselect IP addresses with regexes")
    regexp_list: list[RegexString] = api_field(
        description="A list of regular expressions which are matched against the found IP addresses. The matches will be excluded from the result."
    )

    @classmethod
    def from_internal(cls, value: tuple[Literal["ip_regex_list"], Sequence[str]]) -> Self:
        return cls(
            type=value[0],
            regexp_list=[RegexString(x) for x in value[1]],
        )

    def to_internal(self) -> tuple[Literal["ip_regex_list"], Sequence[str]]:
        return self.type, [str(x) for x in self.regexp_list]


IPRangeModel = IPAddressRangeModel | IPNetworkModel | IPAddressesModel
IPRangeWithRegexpModel = IPRangeModel | IPRegexpModel
_CheckmkTime = tuple[int, int]


class IPRangeConverter:
    @staticmethod
    def from_internal(value: IPRange) -> IPRangeModel:
        if value[0] == "ip_range":
            return IPAddressRangeModel.from_internal(value)
        if value[0] == "ip_network":
            return IPNetworkModel.from_internal(value)
        if value[0] == "ip_list":
            return IPAddressesModel.from_internal(value)
        raise ValueError(f"Unknown IP range type: {value[0]!r}")

    @staticmethod
    def from_internal_exclude(value: ExcludeIPRange) -> IPRangeWithRegexpModel:
        if value[0] == "ip_regex_list":
            return IPRegexpModel.from_internal(value)

        return IPRangeConverter.from_internal(value)


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
    def from_internal(cls, value: tuple[_CheckmkTime, _CheckmkTime]) -> Self:
        return cls(
            start=cls._from_checkmk_time(value[0]),
            end=cls._from_checkmk_time(value[1]),
        )

    def to_internal(self) -> tuple[_CheckmkTime, _CheckmkTime]:
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
    def from_internal(cls, value: tuple[str, str]) -> Self:
        return cls(
            search=RegexString(value[0]),
            replace_with=value[1],
        )

    def to_internal(self) -> tuple[str, str]:
        return str(self.search), self.replace_with


@dataclass(kw_only=True, slots=True)
class DirectMappingModel:
    hostname: str = api_field(description="The host name to be replaced.")
    replace_with: str = api_field(description="The replacement string.")

    @classmethod
    def from_internal(cls, value: tuple[str, str]) -> Self:
        return cls(
            hostname=value[0],
            replace_with=value[1],
        )

    def to_internal(self) -> tuple[str, str]:
        return self.hostname, self.replace_with


@dataclass(kw_only=True, slots=True)
class TranslateNamesModel:
    case: Literal["nop", "lower", "upper"] = api_field(
        alias="convert_case",
        description="Convert all detected host names to upper- or lower-case.\n\n * `nop` - Do not convert anything\n * `lower` - Convert all host names to lowercase.\n * `upper` - Convert all host names to uppercase.",
        # default="nop",
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

    @staticmethod
    def case_from_internal(
        value: Literal["lower", "upper"] | None,
    ) -> Literal["nop", "lower", "upper"]:
        if value is None:
            return "nop"
        return value

    @staticmethod
    def case_to_internal(
        value: Literal["nop", "lower", "upper"],
    ) -> Literal["lower", "upper"] | None:
        if value == "nop":
            return None
        return value

    @classmethod
    def from_internal(cls, value: TranslationOptionsSpec) -> "TranslateNamesModel":
        return cls(
            case=TranslateNamesModel.case_from_internal(value.get("case")),
            drop_domain=value["drop_domain"] if "drop_domain" in value else ApiOmitted(),
            regex=[RegexpRewritesModel.from_internal(entry) for entry in value["regex"]],
            mapping=[DirectMappingModel.from_internal(entry) for entry in value["mapping"]],
        )

    def to_internal(self) -> TranslationOptionsSpec:
        if not isinstance(self.regex, ApiOmitted):
            regex = [entry.to_internal() for entry in self.regex]
        else:
            regex = []
        if not isinstance(self.mapping, ApiOmitted):
            mapping = [entry.to_internal() for entry in self.mapping]
        else:
            mapping = []
        spec = TranslationOptionsSpec(
            case=TranslateNamesModel.case_to_internal(self.case),
            regex=regex,
            mapping=mapping,
        )
        if not isinstance(self.drop_domain, ApiOmitted):
            spec["drop_domain"] = self.drop_domain

        return spec


@dataclass(kw_only=True, slots=True)
class NetworkScanModel:
    ip_ranges: list[IPRangeModel] = api_field(
        alias="addresses", description="IPv4 addresses to include."
    )
    exclude_ranges: list[IPRangeWithRegexpModel] | ApiOmitted = api_field(
        alias="exclude_addresses",
        description="IPv4 addresses to exclude.",
        default_factory=ApiOmitted,
    )
    scan_interval: Annotated[int, Ge(3600)] | ApiOmitted = api_field(
        description="Scan interval in seconds. Default is 1 day, minimum is 1 hour.",
        default_factory=ApiOmitted,
        # default=60 * 60 * 24,
    )
    time_allowed: list[TimeAllowedRangeModel] = api_field(
        description="Only execute the discovery during this time range each day."
    )
    set_ipaddress: bool = api_field(
        description="When set, the found IPv4 address is set on the discovered host.",
        # default=True
    )
    max_parallel_pings: Annotated[int, Interval(ge=1, le=200)] = api_field(
        description="Set the maximum number of concurrent pings sent to target IP addresses.",
        # default=100,
    )
    run_as: (
        Annotated[
            UserId,
            TypedPlainValidator(str, UserConverter.active),
            WithJsonSchema({"type": "string"}, mode="serialization"),
        ]
        | ApiOmitted
    ) = api_field(
        description="Execute the network scan in the Checkmk user context of the chosen user. This user needs the permission to add new hosts to this folder.",
        default_factory=ApiOmitted,
    )
    tag_criticality: Annotated[
        str | ApiOmitted, AfterValidator(TagConverter.tag_criticality_presence)
    ] = api_field(
        description="Specify which criticality tag to set on the host created by the network scan. This field is required if the criticality tag group exists, otherwise it as to be omitted.",
        default_factory=ApiOmitted,
    )
    translate_names: TranslateNamesModel | ApiOmitted = api_field(
        description="Name translation settings",
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_internal(cls, value: NetworkScanSpec) -> "NetworkScanModel":
        return cls(
            ip_ranges=[IPRangeConverter.from_internal(entry) for entry in value["ip_ranges"]],
            exclude_ranges=[
                IPRangeConverter.from_internal_exclude(entry) for entry in value["exclude_ranges"]
            ]
            if "exclude_ranges" in value
            else ApiOmitted(),
            scan_interval=value["scan_interval"],
            time_allowed=[
                TimeAllowedRangeModel.from_internal(entry) for entry in value["time_allowed"]
            ],
            set_ipaddress=value["set_ipaddress"],
            max_parallel_pings=value["max_parallel_pings"],
            run_as=value["run_as"],
            tag_criticality=value["tag_criticality"]
            if "tag_criticality" in value
            else ApiOmitted(),
            translate_names=TranslateNamesModel.from_internal(value["translate_names"])
            if "translate_names" in value
            else ApiOmitted(),
        )

    def to_internal(self) -> NetworkScanSpec:
        if not isinstance(self.exclude_ranges, ApiOmitted):
            exclude_ranges = [entry.to_internal() for entry in self.exclude_ranges]
        else:
            exclude_ranges = []
        if not isinstance(self.run_as, ApiOmitted):
            run_as = self.run_as
        elif user.id is not None:
            run_as = user.id
        else:
            # TODO: adjust typing? maybe this can never happen?
            raise ValueError("No run_as specified, no logged in user id?")
        spec = NetworkScanSpec(
            ip_ranges=[entry.to_internal() for entry in self.ip_ranges],
            exclude_ranges=exclude_ranges,
            scan_interval=(60 * 60 * 24)
            if isinstance(self.scan_interval, ApiOmitted)
            else self.scan_interval,
            time_allowed=[entry.to_internal() for entry in self.time_allowed],
            set_ipaddress=self.set_ipaddress,
            run_as=run_as,
        )
        if not isinstance(self.tag_criticality, ApiOmitted):
            spec["tag_criticality"] = self.tag_criticality
        if not isinstance(self.max_parallel_pings, ApiOmitted):
            spec["max_parallel_pings"] = self.max_parallel_pings
        if not isinstance(self.translate_names, ApiOmitted):
            spec["translate_names"] = self.translate_names.to_internal()

        return spec


@dataclass(kw_only=True, slots=True)
class IPMIParametersModel:  # TODO: this is dumb (or at least the IPMICredentials are)
    username: str | ApiOmitted = api_field(description="IPMI username", default_factory=ApiOmitted)
    password: str | ApiOmitted = api_field(description="IPMI password", default_factory=ApiOmitted)

    @classmethod
    def from_internal(cls, value: IPMICredentials) -> "IPMIParametersModel":
        return cls(
            username=value.get("username", ApiOmitted()),
            password=value.get("password", ApiOmitted()),
        )

    def to_internal(self) -> IPMICredentials:
        spec = IPMICredentials()
        if not isinstance(self.username, ApiOmitted):
            spec["username"] = self.username
        if not isinstance(self.password, ApiOmitted):
            spec["password"] = self.password
        return spec


@dataclass(kw_only=True, slots=True)
class NetworkScanResultModel:
    start: dt.datetime | None = api_field(
        description="When the scan started",
    )
    end: dt.datetime | None | ApiOmitted = api_field(
        description="When the scan finished. Will be Null if not yet run.",
        default_factory=ApiOmitted,
    )
    state: Literal["running", "succeeded", "failed"] = api_field(description="Last scan result")
    output: str = api_field(description="Short human readable description of what is happening.")

    @staticmethod
    def state_from_internal(value: bool | None) -> Literal["running", "succeeded", "failed"]:
        if value is None:
            return "running"
        return "succeeded" if value else "failed"

    @classmethod
    def from_internal(cls, value: NetworkScanResult) -> "NetworkScanResultModel":
        end_time: dt.datetime | None | ApiOmitted
        if (end_time_internal := value.get("end")) is True:
            end_time = ApiOmitted()
        elif end_time_internal is not None:
            end_time = dt.datetime.fromtimestamp(end_time_internal)
        else:
            end_time = None
        return cls(
            start=dt.datetime.fromtimestamp(start) if (start := value.get("start")) else None,
            end=end_time,
            state=NetworkScanResultModel.state_from_internal(value.get("state")),
            output=value.get("output", ""),
        )


@dataclass(kw_only=True, slots=True)
class MetaDataModel:
    created_at: dt.datetime | ApiOmitted = api_field(
        description="When has this object been created.",
        default_factory=ApiOmitted,
    )
    updated_at: dt.datetime | ApiOmitted = api_field(
        description="When this object was last changed.",
        default_factory=ApiOmitted,
    )
    created_by: str | None | ApiOmitted = api_field(
        description="The user id under which this object has been created.",
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_internal(cls, value: MetaData) -> Self:
        return cls(
            created_at=dt.datetime.fromtimestamp(value["created_at"])
            if "created_at" in value
            else ApiOmitted(),
            updated_at=dt.datetime.fromtimestamp(value["updated_at"])
            if "updated_at" in value
            else ApiOmitted(),
            created_by=value["created_by"] if "created_by" in value else ApiOmitted(),
        )


@dataclass(kw_only=True, slots=True)
class LockedByModel:
    site_id: str = api_field(description="Site ID")
    program_id: str = api_field(description="Program ID")
    instance_id: str = api_field(description="Instance ID")

    @classmethod
    def from_internal(cls, value: tuple[SiteId, str, str] | Sequence[str]) -> Self:
        # see `to_internal` - we allow tuples and lists...
        assert len(value) == 3, f"Expected 3 values, got {len(value)}"
        return cls(
            site_id=value[0],
            program_id=value[1],
            instance_id=value[2],
        )

    def to_internal(self) -> Sequence[str]:
        # for some godforsaken reason, the locked_by attribute is a list and not a tuple
        return [self.site_id, self.program_id, self.instance_id]


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
    )


@dataclass(slots=True)
class _LabelValidator:
    kind: Literal["key", "value"]

    def __call__(self, value: str) -> str:
        """Validate a label key or value.

        Examples:
            >>> _LabelValidator(kind="key")("my_label")
            'my_label'
            >>> _LabelValidator(kind="value")("my_value")
            'my_value'
            >>> _LabelValidator(kind="key")("error:")
            Traceback (most recent call last):
                ...
            ValueError: Invalid label key: 'error:'
            >>> _LabelValidator(kind="value")("error:")
            Traceback (most recent call last):
                ...
            ValueError: Invalid label value: 'error:'
        """
        if ":" in value:
            raise ValueError(f"Invalid label {self.kind}: {value!r}")

        return value


HostLabels = dict[
    Annotated[str, AfterValidator(_LabelValidator(kind="key"))],
    Annotated[
        str,
        AfterValidator(_LabelValidator(kind="value")),
        WithJsonSchema({"type": "string", "description": "The host label value"}),
    ],
]
