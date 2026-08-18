#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

import datetime as dt
import re
from collections.abc import Mapping, Sequence
from ipaddress import IPv4Network
from typing import Annotated, Literal, override, Self

from annotated_types import Ge, Interval, MaxLen, MinLen
from pydantic import (
    AfterValidator,
    Discriminator,
    model_validator,
    PlainSerializer,
    TypeAdapter,
    WithJsonSchema,
)

from cmk.ccc.hostaddress import HostAddress
from cmk.ccc.site import SiteId
from cmk.ccc.translations import TranslationOptions
from cmk.ccc.user import UserId
from cmk.gui.config import active_config
from cmk.gui.fields.attributes import (
    AuthProtocolConverter,
    AuthProtocolType,
    PrivacyProtocolConverter,
    PrivacyProtocolType,
)
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.common_fields import IPv4String, RegexString
from cmk.gui.openapi.framework.model.converter import (
    GroupConverter,
    TagConverter,
    TypedPlainValidator,
    UserConverter,
)
from cmk.gui.openapi.framework.model.dynamic_fields import WithDynamicFields
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.watolib.host_attributes import (
    ABCHostAttribute,
    all_host_attributes,
    ExcludeIPRange,
    HostContactGroupSpec,
    IPMICredentials,
    IPRange,
    MetaData,
    MetricsAssociationAttributeFilter,
    MetricsAssociationEnabled,
    MetricsAssociationHostNameLookupRule,
    NetworkScanResult,
    NetworkScanSpec,
)
from cmk.gui.watolib.tags import load_tag_config_read_only
from cmk.ruleset_matcher.tags import TagGroupID
from cmk.shared_typing.attribute_filter import (
    AttributeFilter,
    AttributeFilterAnd,
    AttributeFilterEquals,
    AttributeKind,
)

# Shared between the lenient input model (flags optional) and the read-only view model
# (flags always rendered), so extracted to module level to avoid duplication.
_CONTACT_GROUP_USE_DESC = "Add these contact groups to the host."
_CONTACT_GROUP_USE_FOR_SERVICES_DESC = "<p>Always add host contact groups also to its services.</p>With this option contact groups that are added to hosts are always being added to services, as well. This only makes a difference if you have assigned other contact groups to services via rules in <i>Host & Service Parameters</i>. As long as you do not have any such rule a service always inherits all contact groups from its host."
_CONTACT_GROUP_RECURSE_USE_DESC = (
    "Add these groups as contacts to all hosts in all sub-folders of this folder."
)
_CONTACT_GROUP_RECURSE_PERMS_DESC = "Give these groups also permission on all sub-folders."


@api_model
class HostContactGroupRequestModel:
    groups: list[Annotated[str, AfterValidator(GroupConverter(group_type="contact").exists)]] = (
        api_field(description="A list of contact groups.", example="all")
    )
    use: bool = api_field(description=_CONTACT_GROUP_USE_DESC, default=False)
    use_for_services: bool = api_field(
        description=_CONTACT_GROUP_USE_FOR_SERVICES_DESC,
        default=False,
    )
    recurse_use: bool = api_field(
        description=_CONTACT_GROUP_RECURSE_USE_DESC,
        default=False,
    )
    recurse_perms: bool = api_field(
        description=_CONTACT_GROUP_RECURSE_PERMS_DESC,
        default=False,
    )

    @classmethod
    def from_internal(cls, value: HostContactGroupSpec) -> HostContactGroupRequestModel:
        return cls(
            groups=value["groups"],
            use=value.get("use", False),
            use_for_services=value.get("use_for_services", False),
            recurse_use=value.get("recurse_use", False),
            recurse_perms=value.get("recurse_perms", False),
        )

    def to_internal(self) -> HostContactGroupSpec:
        return {
            "groups": self.groups,
            "use": self.use,
            "use_for_services": self.use_for_services,
            "recurse_use": self.recurse_use,
            "recurse_perms": self.recurse_perms,
        }


@api_model
class HostContactGroupResponseModel(HostContactGroupRequestModel):
    """Read-only variant used in (effective) attributes responses.

    The flags are declared without a default so that they are always rendered, even when
    ``False`` - the response serializer strips fields equal to their default, which would
    otherwise drop them (the previous implementation always included them)."""

    use: bool = api_field(description=_CONTACT_GROUP_USE_DESC)
    use_for_services: bool = api_field(description=_CONTACT_GROUP_USE_FOR_SERVICES_DESC)
    recurse_use: bool = api_field(description=_CONTACT_GROUP_RECURSE_USE_DESC)
    recurse_perms: bool = api_field(description=_CONTACT_GROUP_RECURSE_PERMS_DESC)

    @classmethod
    @override
    def from_internal(cls, value: HostContactGroupSpec) -> HostContactGroupResponseModel:
        return cls(
            groups=value["groups"],
            use=value.get("use", False),
            use_for_services=value.get("use_for_services", False),
            recurse_use=value.get("recurse_use", False),
            recurse_perms=value.get("recurse_perms", False),
        )


@api_model
class SNMPCommunityModel:
    type: Literal["v1_v2_community"] = api_field(description="SNMP v1 or v2 with community")
    community: str | ApiOmitted = api_field(
        description="SNMP community (SNMP Versions 1 and 2c)",
        default_factory=ApiOmitted,
    )


@api_model
class SNMPv3NoAuthNoPrivacyModel:
    type: Literal["v3_no_auth_no_privacy"] = api_field(
        description="SNMPv3 without authentication or privacy"
    )
    security_name: str = api_field(description="Security name")

    @classmethod
    def from_internal(cls, value: tuple[Literal["noAuthNoPriv"], str]) -> Self:
        return cls(
            type="v3_no_auth_no_privacy",
            security_name=value[1],
        )

    def to_internal(self) -> tuple[Literal["noAuthNoPriv"], str]:
        return "noAuthNoPriv", self.security_name


@api_model
class SNMPv3AuthNoPrivacyModel:
    type: Literal["v3_auth_no_privacy"] = api_field(
        description="SNMPv3 with authentication, but without privacy"
    )
    auth_protocol: AuthProtocolType = api_field(description="Authentication protocol.")
    security_name: str = api_field(description="Security name")
    auth_password: Annotated[str, MinLen(8)] | ApiOmitted = api_field(
        description="Authentication pass phrase.",
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_internal(cls, value: tuple[Literal["authNoPriv"], str, str, str]) -> Self:
        return cls(
            type="v3_auth_no_privacy",
            auth_protocol=AuthProtocolConverter.from_checkmk(value[1]),
            security_name=value[2],
            auth_password=ApiOmitted(),
        )

    def to_internal(self) -> tuple[Literal["authNoPriv"], str, str, str]:
        if isinstance(self.auth_password, ApiOmitted):
            raise ProblemException(
                status=400,
                title="Missing SNMPv3 authentication pass phrase.",
                detail="The 'auth_password' field is required for SNMPv3 authNoPriv credentials.",
            )
        return (
            "authNoPriv",
            AuthProtocolConverter.to_checkmk(self.auth_protocol),
            self.security_name,
            self.auth_password,
        )


@api_model
class SNMPv3AuthPrivacyModel:
    type: Literal["v3_auth_privacy"] = api_field(
        description="SNMPv3 with authentication and privacy"
    )
    auth_protocol: AuthProtocolType = api_field(description="Authentication protocol.")
    security_name: str = api_field(description="Security name")
    auth_password: Annotated[str, MinLen(8)] | ApiOmitted = api_field(
        description="Authentication pass phrase.",
        default_factory=ApiOmitted,
    )
    privacy_protocol: PrivacyProtocolType = api_field(
        description="The privacy protocol. The only supported values in the Community Edition are CBC-DES and AES-128. If selected, privacy_password needs to be supplied as well."
    )
    privacy_password: Annotated[str, MinLen(8)] | ApiOmitted = api_field(
        description="Privacy pass phrase. If filled, privacy_protocol needs to be selected as well.",
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_internal(cls, value: tuple[Literal["authPriv"], str, str, str, str, str]) -> Self:
        return cls(
            type="v3_auth_privacy",
            auth_protocol=AuthProtocolConverter.from_checkmk(value[1]),
            security_name=value[2],
            auth_password=ApiOmitted(),
            privacy_protocol=PrivacyProtocolConverter.from_checkmk(value[4]),
            privacy_password=ApiOmitted(),
        )

    def to_internal(self) -> tuple[Literal["authPriv"], str, str, str, str, str]:
        if isinstance(self.auth_password, ApiOmitted) or isinstance(
            self.privacy_password, ApiOmitted
        ):
            missing = [
                name
                for name, value in (
                    ("auth_password", self.auth_password),
                    ("privacy_password", self.privacy_password),
                )
                if isinstance(value, ApiOmitted)
            ]
            raise ProblemException(
                status=400,
                title="Missing SNMPv3 pass phrase(s).",
                detail=f"The following field(s) are required for SNMPv3 authPriv credentials: {', '.join(missing)}.",
            )
        return (
            "authPriv",
            AuthProtocolConverter.to_checkmk(self.auth_protocol),
            self.security_name,
            self.auth_password,
            PrivacyProtocolConverter.to_checkmk(self.privacy_protocol),
            self.privacy_password,
        )


type SNMPCredentialsModel = (
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
                community=ApiOmitted(),
            )

        match value[0]:
            case "noAuthNoPriv":
                return SNMPv3NoAuthNoPrivacyModel.from_internal(value)
            case "authNoPriv":
                return SNMPv3AuthNoPrivacyModel.from_internal(value)
            case "authPriv":
                return SNMPv3AuthPrivacyModel.from_internal(value)
            case _:
                raise ValueError(f"Unknown SNMP credentials type: {value[0]!r}")

    @staticmethod
    def to_internal(field: SNMPCredentialsModel) -> str | tuple:
        match field:
            case SNMPCommunityModel():
                if isinstance(field.community, ApiOmitted):
                    raise ProblemException(
                        status=400,
                        title="Missing SNMP community.",
                        detail="The 'community' field is required for SNMP v1/v2 credentials.",
                    )
                return field.community
            case SNMPv3NoAuthNoPrivacyModel():
                return field.to_internal()
            case SNMPv3AuthNoPrivacyModel():
                return field.to_internal()
            case SNMPv3AuthPrivacyModel():
                return field.to_internal()
            case _:
                raise ValueError(f"Unknown SNMP credentials type: {field.type!r}")


@api_model
class IPAddressRangeModel:
    type: Literal["address_range"] = api_field(description="Select a range of IP addresses")
    from_address: IPv4String = api_field(description="The first IPv4 address of this range.")
    to_address: IPv4String = api_field(description="The last IPv4 address of this range.")

    @classmethod
    def from_internal(cls, value: tuple[Literal["ip_range"], tuple[str, str]]) -> Self:
        return cls(
            type="address_range",
            from_address=IPv4String(value[1][0]),
            to_address=IPv4String(value[1][1]),
        )

    def to_internal(self) -> tuple[Literal["ip_range"], tuple[str, str]]:
        return "ip_range", (str(self.from_address), str(self.to_address))


@api_model
class IPNetworkModel:
    type: Literal["network_range"] = api_field(description="Select an entire network")
    network: IPv4Network = api_field(
        description="A IPv4 network in CIDR notation. Minimum prefix length is 8 bit, maximum prefix length is 30 bit.\n\nValid examples:\n\n * `192.168.0.0/24`\n * `192.168.0.0/255.255.255.0`"
    )

    @classmethod
    def from_internal(cls, value: tuple[Literal["ip_network"], tuple[str, int]]) -> Self:
        network, mask = value[1]
        return cls(
            type="network_range",
            network=IPv4Network(f"{network}/{mask}"),
        )

    def to_internal(self) -> tuple[Literal["ip_network"], tuple[str, int]]:
        return "ip_network", (str(self.network.network_address), self.network.prefixlen)


@api_model
class IPAddressesModel:
    type: Literal["explicit_addresses"] = api_field(
        description="Select multiple explicit IP addresses"
    )
    addresses: list[IPv4String] = api_field(description="List of IPv4 addresses")

    @classmethod
    def from_internal(cls, value: tuple[Literal["ip_list"], Sequence[HostAddress]]) -> Self:
        return cls(
            type="explicit_addresses",
            addresses=[IPv4String(x) for x in value[1]],
        )

    def to_internal(self) -> tuple[Literal["ip_list"], Sequence[HostAddress]]:
        return "ip_list", [HostAddress(x) for x in self.addresses]


@api_model
class IPRegexpModel:
    type: Literal["exclude_by_regexp"] = api_field(description="Deselect IP addresses with regexes")
    regexp_list: list[RegexString] = api_field(
        description="A list of regular expressions which are matched against the found IP addresses. The matches will be excluded from the result."
    )

    @classmethod
    def from_internal(cls, value: tuple[Literal["ip_regex_list"], Sequence[str]]) -> Self:
        return cls(
            type="exclude_by_regexp",
            regexp_list=[RegexString(x) for x in value[1]],
        )

    def to_internal(self) -> tuple[Literal["ip_regex_list"], Sequence[str]]:
        return "ip_regex_list", [str(x) for x in self.regexp_list]


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


@api_model
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


@api_model
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


@api_model
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


@api_model
class TranslateNamesModel:
    case: Literal["nop", "lower", "upper"] = api_field(
        serialization_alias="convert_case",
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
        serialization_alias="regexp_rewrites",
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
        serialization_alias="hostname_replacement",
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
    def from_internal(cls, value: TranslationOptions) -> TranslateNamesModel:
        return cls(
            case=TranslateNamesModel.case_from_internal(value.get("case")),
            drop_domain=value["drop_domain"] if "drop_domain" in value else ApiOmitted(),
            regex=[RegexpRewritesModel.from_internal(entry) for entry in value["regex"]]
            if "regex" in value
            else ApiOmitted(),
            mapping=[DirectMappingModel.from_internal(entry) for entry in value["mapping"]]
            if "mapping" in value
            else ApiOmitted(),
        )

    def to_internal(self) -> TranslationOptions:
        spec = TranslationOptions(case=TranslateNamesModel.case_to_internal(self.case))
        if not isinstance(self.regex, ApiOmitted) and (
            regex := [entry.to_internal() for entry in self.regex]
        ):
            spec["regex"] = regex
        if not isinstance(self.mapping, ApiOmitted) and (
            mapping := [entry.to_internal() for entry in self.mapping]
        ):
            spec["mapping"] = mapping
        if not isinstance(self.drop_domain, ApiOmitted):
            spec["drop_domain"] = self.drop_domain

        return spec


@api_model
class NetworkScanModel:
    ip_ranges: list[IPRangeModel] = api_field(
        serialization_alias="addresses", description="IPv4 addresses to include."
    )
    exclude_ranges: list[IPRangeWithRegexpModel] | ApiOmitted = api_field(
        serialization_alias="exclude_addresses",
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
        serialization_alias="set_ip_address",
        description="When set, the found IPv4 address is set on the discovered host.",
        # default=True
    )
    max_parallel_pings: Annotated[int, Interval(ge=1, le=200)] | ApiOmitted = api_field(
        description="Set the maximum number of concurrent pings sent to target IP addresses.",
        default_factory=ApiOmitted,
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
    def from_internal(cls, value: NetworkScanSpec) -> NetworkScanModel:
        return cls(
            ip_ranges=[IPRangeConverter.from_internal(entry) for entry in value["ip_ranges"]],
            exclude_ranges=[
                IPRangeConverter.from_internal_exclude(entry) for entry in value["exclude_ranges"]
            ]
            if "exclude_ranges" in value  # type: ignore[redundant-expr]
            else ApiOmitted(),
            scan_interval=value.get("scan_interval", ApiOmitted()),
            time_allowed=[
                TimeAllowedRangeModel.from_internal(entry) for entry in value["time_allowed"]
            ],
            set_ipaddress=value["set_ipaddress"],
            max_parallel_pings=value.get("max_parallel_pings", ApiOmitted()),
            run_as=value.get("run_as", ApiOmitted()),
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
        spec["max_parallel_pings"] = (
            100 if isinstance(self.max_parallel_pings, ApiOmitted) else self.max_parallel_pings
        )
        if not isinstance(self.translate_names, ApiOmitted):
            spec["translate_names"] = self.translate_names.to_internal()

        return spec


@api_model
class IPMIParametersModel:  # TODO: this is dumb (or at least the IPMICredentials are)
    username: str | ApiOmitted = api_field(description="IPMI username", default_factory=ApiOmitted)
    password: str | ApiOmitted = api_field(description="IPMI password", default_factory=ApiOmitted)

    @classmethod
    def from_internal(cls, value: IPMICredentials) -> IPMIParametersModel:
        return cls(
            username=value.get("username", ApiOmitted()),
            password=ApiOmitted(),
        )

    def to_internal(self) -> IPMICredentials:
        spec = IPMICredentials()
        if not isinstance(self.username, ApiOmitted):
            spec["username"] = self.username
        if not isinstance(self.password, ApiOmitted):
            spec["password"] = self.password
        return spec


# Render UTC timestamps as "...+00:00" (via isoformat) rather than pydantic's default "...Z",
# matching the previous implementation's output.
_IsoDateTime = Annotated[dt.datetime, PlainSerializer(lambda v: v.isoformat(), return_type=str)]


@api_model
class NetworkScanResultModel:
    start: _IsoDateTime | None = api_field(
        description="When the scan started",
    )
    end: _IsoDateTime | None | ApiOmitted = api_field(
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
    def from_internal(cls, value: NetworkScanResult) -> NetworkScanResultModel:
        end_time: dt.datetime | None | ApiOmitted
        if (end_time_internal := value.get("end")) is True:
            end_time = ApiOmitted()
        elif end_time_internal is not None:
            end_time = dt.datetime.fromtimestamp(end_time_internal, tz=dt.UTC)
        else:
            end_time = None
        return cls(
            start=dt.datetime.fromtimestamp(start, tz=dt.UTC)
            if (start := value.get("start"))
            else None,
            end=end_time,
            state=NetworkScanResultModel.state_from_internal(value.get("state")),
            output=value.get("output", ""),
        )


@api_model
class MetaDataModel:
    created_at: _IsoDateTime | ApiOmitted = api_field(
        description="When has this object been created.",
        default_factory=ApiOmitted,
    )
    updated_at: _IsoDateTime | ApiOmitted = api_field(
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
            created_at=(
                dt.datetime.fromtimestamp(value["created_at"], tz=dt.UTC)
                if value.get("created_at") is not None
                else ApiOmitted()
            ),
            updated_at=(
                dt.datetime.fromtimestamp(value["updated_at"], tz=dt.UTC)
                if value.get("updated_at") is not None
                else ApiOmitted()
            ),
            created_by=(
                value["created_by"] if value.get("created_by") is not None else ApiOmitted()
            ),
        )


@api_model
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

    def to_internal(self) -> tuple[str, str, str]:
        # The internal hosts.mk representation of locked_by is a tuple (site_id, program, instance).
        return (self.site_id, self.program_id, self.instance_id)


@api_model
class FolderCustomHostAttributesAndTagGroupsModel(WithDynamicFields):
    """Class for custom host attributes and tag groups."""

    # ``None`` is allowed so a custom tag group can be unset (matching the previous
    # implementation, which used ``allow_none=True``). The keys/values are validated against the
    # configured custom attributes and tag groups by `validate_custom_attributes_and_tag_groups`,
    # which is called from the input models only (the read-only view must keep rendering
    # attributes of since-deleted custom attributes).
    dynamic_fields: dict[str, str | None] = api_field(
        description=(
            "The property name must be\n\n"
            " * A custom host attribute\n"
            " * A custom tag group starting with `tag_`\n"
        ),
    )


def validate_custom_attributes_and_tag_groups(dynamic_fields: Mapping[str, str | None]) -> None:
    """Validate custom host attributes and tag groups passed as dynamic fields.

    Mirrors the behaviour of the previous marshmallow implementation: each key must be either a
    host attribute that is editable through the REST API (a configured custom attribute or a
    built-in/edition-specific attribute such as ``relay``) or a custom tag group (``tag_<id>``);
    the value of a tag group must be one of its tags. Unknown keys - including internal,
    non-editable attributes such as ``meta_data`` - are rejected. Raises ``ValueError`` (reported
    as a 400) on the first problem."""
    if not dynamic_fields:
        return

    host_attributes = all_host_attributes(
        active_config.wato_host_attrs, active_config.tags.get_tag_groups_by_topic()
    )
    tag_group_config = load_tag_config_read_only()

    for name, value in dynamic_fields.items():
        if (tag_group := tag_group_config.get_tag_group(TagGroupID(name[4:]))) is not None:
            if value not in tag_group.get_tag_ids():
                raise ValueError(f"Invalid value for tag-group {tag_group.title!r}: {value!r}")
        elif (host_attribute := _custom_host_attribute(host_attributes, name)) is not None:
            # Validate the attribute is settable; the value itself is validated when the host is
            # saved. We deliberately do not call ``validate_input`` here: some attributes (e.g.
            # ``relay``) read request form/query vars in their validation, which are not populated
            # for JSON request bodies in this framework.
            if not isinstance(value, str):
                raise ValueError(f"Attribute {host_attribute.name()!r} must be a string.")
        else:
            raise ValueError(f"Unknown Attribute: {name!r}: {value!r}")


def _custom_host_attribute(
    attributes: dict[str, ABCHostAttribute], name: str
) -> ABCHostAttribute | None:
    # ``openapi_editable`` covers both user-defined custom attributes and built-in/edition-specific
    # attributes that are settable via the REST API but have no dedicated model field (e.g.
    # ``relay``). Internal, read-only attributes (e.g. ``meta_data``) return ``False`` and are
    # therefore rejected.
    attribute = attributes.get(name)
    if attribute is None or not attribute.openapi_editable():
        return None
    return attribute


def _validate_label_key(value: str) -> str:
    """Validate a label key.

    Label keys may not contain ``:`` since the character is used as the
    separator between key and value. Label values, on the other hand, may
    contain ``:`` (for example ``net:ip:v4``).

    Examples:
        >>> _validate_label_key("my_label")
        'my_label'
        >>> _validate_label_key("error:")
        Traceback (most recent call last):
            ...
        ValueError: Invalid label key: 'error:'
    """
    if ":" in value:
        raise ValueError(f"Invalid label key: {value!r}")

    return value


HostLabels = dict[
    Annotated[str, AfterValidator(_validate_label_key)],
    Annotated[
        str,
        WithJsonSchema({"type": "string", "description": "The host label value"}),
    ],
]


@api_model
class MetricsAssociationAttributeFilterModel:
    key: str = api_field(description="Target attribute key to filter on.")
    value: str = api_field(description="Target attribute value to match.")


@api_model
class MetricsAssociationFilterGroupModel:
    resource_attributes: Sequence[MetricsAssociationAttributeFilterModel] = api_field(
        description="A list of resource attribute filters."
    )
    scope_attributes: Sequence[MetricsAssociationAttributeFilterModel] = api_field(
        description="A list of scope attribute filters."
    )
    data_point_attributes: Sequence[MetricsAssociationAttributeFilterModel] = api_field(
        description="A list of data point attribute filters."
    )
    host_name_template: str | ApiOmitted = api_field(
        description="Optional. The host name template of this host name lookup rule (macros "
        "$RESOURCE_ATTR.<key>$, $SCOPE_ATTR.<key>$, $DATA_POINT_ATTR.<key>$), resolved at query "
        "time to select this rule's series.",
        default_factory=ApiOmitted,
    )
    attribute_filter: Mapping[str, object] | ApiOmitted = api_field(
        description="Optional. The recursive attribute filter the Setup GUI persists for a rule. "
        "When present it takes precedence over the three attribute lists: its 'equals' conditions "
        "are projected into them. Only an AND of 'equals' conditions is supported.",
        default_factory=ApiOmitted,
    )


@api_model
class MetricsAssociationEnabledModel:
    host_name_lookup_rules: Annotated[Sequence[MetricsAssociationFilterGroupModel], MinLen(1)] = (
        api_field(
            description="One entry per host name lookup rule that produced this host. The host's "
            "series are the union of all rules (logical OR across rules, logical AND within each "
            "rule)."
        )
    )


# Mirrors the internal representation (and the previous marshmallow tuple): the status and the
# config are correlated, so "enabled" always carries the config and "disabled" always carries None.
MetricsAssociationModel = (
    tuple[Literal["enabled"], MetricsAssociationEnabledModel] | tuple[Literal["disabled"], None]
)


def render_view_site(value: str) -> str:
    """Render a site for read-only responses.

    Unknown sites (e.g. an object configured for a site that no longer exists) are rendered as
    ``Unknown Site: <id>`` rather than failing, matching the previous implementation."""
    if value not in active_config.sites:
        return f"Unknown Site: {value}"
    return value


def snmp_community_or_none(value: str | tuple | None) -> SNMPCredentialsModel | None:
    """Convert an internal SNMP credential to its model, preserving an explicit ``None``.

    The ``HostAttributes`` TypedDict types the value as non-optional, but at runtime it can be
    ``None`` (e.g. effective attributes of an object without SNMP configured)."""
    if value is None:
        return None
    return SNMPCredentialsConverter.from_internal(value)


def ipmi_credentials_or_none(value: IPMICredentials | None) -> IPMIParametersModel | None:
    if value is None:
        return None
    return IPMIParametersModel.from_internal(value)


_WIRE_FILTER_ADAPTER: TypeAdapter[AttributeFilter] = TypeAdapter(
    Annotated[AttributeFilter, Discriminator("type")]
)


def _wire_equals_by_kind(
    attribute_filter: Mapping[str, object],
) -> dict[AttributeKind, list[MetricsAssociationAttributeFilterModel]]:
    """Project the wire filter's ``equals`` conjuncts into the three per-kind lists."""
    root = _WIRE_FILTER_ADAPTER.validate_python(attribute_filter)
    if not isinstance(root, AttributeFilterAnd):
        raise ValueError(f"Expected a top-level 'and' attribute filter, got {root!r}")
    by_kind: dict[AttributeKind, list[MetricsAssociationAttributeFilterModel]] = {
        "resource": [],
        "scope": [],
        "data_point": [],
    }
    for conjunct in root.conjuncts:
        if not isinstance(conjunct, AttributeFilterEquals):
            raise ValueError(f"Expected an 'equals' attribute filter condition, got {conjunct!r}")
        by_kind[conjunct.key.kind].append(
            MetricsAssociationAttributeFilterModel(key=conjunct.key.name, value=conjunct.value)
        )
    return by_kind


def _lookup_rule_to_internal(
    rule: MetricsAssociationFilterGroupModel,
) -> MetricsAssociationHostNameLookupRule:
    """Build one internal host name lookup rule from an API rule."""
    if isinstance(rule.attribute_filter, ApiOmitted):
        resource_attributes = rule.resource_attributes
        scope_attributes = rule.scope_attributes
        data_point_attributes = rule.data_point_attributes
    else:
        by_kind = _wire_equals_by_kind(rule.attribute_filter)
        resource_attributes = by_kind["resource"]
        scope_attributes = by_kind["scope"]
        data_point_attributes = by_kind["data_point"]
    internal = MetricsAssociationHostNameLookupRule(
        resource_attributes=[
            MetricsAssociationAttributeFilter(key=f.key, value=f.value) for f in resource_attributes
        ],
        scope_attributes=[
            MetricsAssociationAttributeFilter(key=f.key, value=f.value) for f in scope_attributes
        ],
        data_point_attributes=[
            MetricsAssociationAttributeFilter(key=f.key, value=f.value)
            for f in data_point_attributes
        ],
    )
    if not isinstance(rule.host_name_template, ApiOmitted):
        internal["host_name_template"] = rule.host_name_template
    return internal


def metrics_association_to_internal(
    model: MetricsAssociationModel,
) -> tuple[Literal["disabled"], None] | tuple[Literal["enabled"], MetricsAssociationEnabled]:
    _status, config = model
    if config is None:
        return ("disabled", None)
    return (
        "enabled",
        MetricsAssociationEnabled(
            host_name_lookup_rules=[
                _lookup_rule_to_internal(rule) for rule in config.host_name_lookup_rules
            ]
        ),
    )


def _lookup_rule_from_internal(
    rule: MetricsAssociationHostNameLookupRule,
) -> MetricsAssociationFilterGroupModel:
    return MetricsAssociationFilterGroupModel(
        resource_attributes=[
            MetricsAssociationAttributeFilterModel(key=f["key"], value=f["value"])
            for f in rule["resource_attributes"]
        ],
        scope_attributes=[
            MetricsAssociationAttributeFilterModel(key=f["key"], value=f["value"])
            for f in rule["scope_attributes"]
        ],
        data_point_attributes=[
            MetricsAssociationAttributeFilterModel(key=f["key"], value=f["value"])
            for f in rule["data_point_attributes"]
        ],
        host_name_template=rule.get("host_name_template", ApiOmitted()),
    )


def metrics_association_from_internal(
    value: tuple[Literal["enabled"], MetricsAssociationEnabled] | tuple[Literal["disabled"], None],
) -> MetricsAssociationModel:
    _status, config = value
    if config is None:
        return ("disabled", None)
    return (
        "enabled",
        MetricsAssociationEnabledModel(
            host_name_lookup_rules=[
                _lookup_rule_from_internal(rule) for rule in config["host_name_lookup_rules"]
            ]
        ),
    )
