#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import re
from collections.abc import Mapping
from typing import Any, Literal, override

from marshmallow import ValidationError
from marshmallow.decorators import post_load, pre_dump, validates_schema
from marshmallow_oneofschema import OneOfSchema

from cmk.ccc.user import UserId

from cmk.utils.tags import TagGroupID

from cmk.gui import userdb
from cmk.gui.fields.base import BaseSchema
from cmk.gui.fields.definitions import GroupField, Timestamp
from cmk.gui.fields.mixins import CheckmkTuple, Converter
from cmk.gui.watolib.tags import load_tag_group

from cmk.fields import Boolean, Constant, Integer, List, Nested, String, Time
from cmk.fields.validators import IsValidRegexp, ValidateIPv4, ValidateIPv4Network

from .definitions import CmkOneOfSchema

# TODO: make wrong 'tuple_fields' entries fail at compile not, not at runtime.


class RegexpRewrites(BaseSchema, CheckmkTuple):
    r"""Represents a regexp replacement.

    The replacement string gets validated against the regexp for match group compatibility.

    Examples:

        >>> schema = RegexpRewrites()
        >>> tup = schema.load({'search': '(abc)', 'replace_with': '\\1'})
        >>> tup
        ('(abc)', '\\1')

        >>> schema.dump(tup)
        {'search': '(abc)', 'replace_with': '\\1'}

        >>> schema.load({'search': 'abc', 'replace_with': '\\1, \\22'})  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        m...: {'replace_with': ['regexp only contains 0 match groups, but a match group with index 22 (\\22) was used in the replacement string.']}

        >>> schema.load({'search': '()()()', 'replace_with': '\\1, \\3'})  # doctest: +ELLIPSIS
        ('()()()', '\\1, \\3')

    """

    tuple_fields = ("search", "replace_with")
    cast_to_dict = True

    search = String(
        description=(
            "The search regexp. May contain match-groups, conditional matches, etc. "
            "This follows the Python regular expression syntax.\n\n"
            "For details see:\n\n"
            " * https://docs.python.org/3/library/re.html"
        ),
        maxLength=30,
        validate=IsValidRegexp(),
        required=True,
    )
    replace_with = String(
        description="The replacement string. Match-groups can only be identified by `\\1`, `\\2`, "
        "etc. Highest supported match group is `\\99`. Named lookups are not "
        "supported.",
        maxLength=30,
        required=True,
    )

    @validates_schema
    def validate_replacement(self, data: Mapping[str, str], **kwargs: object) -> None:
        search = re.compile(data["search"])
        replace_groups = list(set(re.findall(r"\\((?:[1-9]|\d\d)+)", data["replace_with"])))
        replace_groups.sort()

        # NOTE
        # We don't need to check for exhaustive use of the replacement groups. We only need
        # to check the highest match-group used in the replacement, as this is the only case
        # where a mismatch may occur.
        if replace_groups:
            highest_replacement_group = int(replace_groups[-1])
            if highest_replacement_group > search.groups:
                raise ValidationError(
                    f"regexp only contains {search.groups} match groups, but a match group with "
                    f"index {highest_replacement_group} (\\{highest_replacement_group}) was used "
                    "in the replacement string.",
                    field_name="replace_with",
                )


class IPAddressRange(BaseSchema, CheckmkTuple):
    """

    >>> schema = IPAddressRange()
    >>> rv = schema.dump(('ip_range', ('127.0.0.1', '127.0.0.2')))
    >>> rv
    {'type': 'ip_range', 'from_address': '127.0.0.1', 'to_address': '127.0.0.2'}

    >>> schema.load(rv)
    ('ip_range', ('127.0.0.1', '127.0.0.2'))

    """

    tuple_fields = ("type", ("from_address", "to_address"))
    cast_to_dict = True

    type = Constant(
        description="A range of addresses.",
        constant="ip_range",
    )
    from_address = String(
        description="The first IPv4 address of this range.",
        validate=ValidateIPv4(),
    )
    to_address = String(
        description="The last IPv4 address of this range.",
        validate=ValidateIPv4(),
    )


class IPNetworkCIDR(String):
    """
    >>> schema = IPNetworkCIDR()
    >>> schema.serialize("d", dict(d=("192.168.178.10", 24)))
    '192.168.178.10/24'
    >>> schema.deserialize("192.168.178.10/24")
    ('192.168.178.10', 24)
    >>> class FooSchema(BaseSchema):
    ...    blah = IPNetworkCIDR()
    >>> schema = FooSchema()
    >>> schema.load({"blah": "broken"})
    Traceback (most recent call last):
    ...
    marshmallow.exceptions.ValidationError: {'blah': ["Expected an IP network in CIDR notation like '192.168.0.0/24'"]}
    >>> schema.dump({"blah": "broken"})
    Traceback (most recent call last):
    ...
    marshmallow.exceptions.ValidationError: Error handling 'broken', expected a tuple of IPv4 address and network size e.g. ('192.168.0.0', 24)
    """

    @override
    def _deserialize(
        self, value: object, attr: str | None, data: Mapping[str, object] | None, **kwargs: object
    ) -> tuple[str, int]:
        try:
            network, mask = tuple(str(value).split("/"))
            return network, int(mask)
        except ValueError:
            raise ValidationError("Expected an IP network in CIDR notation like '192.168.0.0/24'")

    @override
    def _serialize(
        self,
        value: tuple[str, int] | list[str | int],
        attr: str | None,
        obj: object,
        **kwargs: object,
    ) -> str:
        if isinstance(value, list | tuple) and len(value) == 2:
            return f"{value[0]}/{value[1]}"
        raise ValidationError(
            f"Error handling {value!r}, expected a tuple of IPv4 address and network size e.g. ('192.168.0.0', 24)"
        )


class IPNetwork(BaseSchema, CheckmkTuple):
    """
    >>> schema = IPNetwork()
    >>> rv = schema.dump(('ip_network', ('192.168.0.0', 24)))
    >>> rv
    {'type': 'ip_network', 'network': '192.168.0.0/24'}
    >>> schema.load(rv)
    ('ip_network', ('192.168.0.0', 24))
    """

    tuple_fields = ("type", "network")
    cast_to_dict = True

    type = Constant(
        description="A single IPv4 network in CIDR notation.",
        constant="ip_network",
    )
    network = IPNetworkCIDR(
        description=(
            "A IPv4 network in CIDR notation. Minimum prefix length is 8 bit, "
            "maximum prefix length is 30 bit.\n\nValid examples:\n\n"
            " * `192.168.0.0/24`\n"
            " * `192.168.0.0/255.255.255.0`"
        ),
        validate=ValidateIPv4Network(min_prefix=8, max_prefix=30),
    )


class IPAddresses(BaseSchema, CheckmkTuple):
    """Represents a list of IPv4 addresses

    >>> schema = IPAddresses()
    >>> rv = schema.dump(('ip_list', ['127.0.0.1', '127.0.0.2']))
    >>> rv
    {'type': 'ip_list', 'addresses': ['127.0.0.1', '127.0.0.2']}

    >>> schema.load(rv)
    ('ip_list', ['127.0.0.1', '127.0.0.2'])

    """

    tuple_fields = ("type", "addresses")
    cast_to_dict = True

    type = Constant(
        description="A list of single IPv4 addresses.",
        constant="ip_list",
    )
    addresses = List(
        String(
            validate=ValidateIPv4(),
        )
    )


class IPRegexp(BaseSchema, CheckmkTuple):
    """

    >>> schema = IPRegexp()
    >>> rv = schema.dump(('ip_regex_list', ['127.0.[0-9].1', '127.0.[0-9].2']))
    >>> schema.load(rv)
    ('ip_regex_list', ['127.0.[0-9].1', '127.0.[0-9].2'])

    """

    tuple_fields = ("type", "regexp_list")
    cast_to_dict = True

    type = Constant(
        description="IPv4 addresses which match a regexp pattern",
        constant="ip_regex_list",
    )
    regexp_list = List(
        String(validate=IsValidRegexp()),
        description=(
            "A list of regular expressions which are matched against the found "
            "IP addresses. The matches will be excluded from the result."
        ),
    )


class IPRange(OneOfSchema):
    """Represents an IP range (of various types)

    The keys from the store are translated to the OpenAPI ones (note address_range key):

        >>> s = IPRange()
        >>> rv = s.dump(('ip_range', ('127.0.0.1', '127.0.0.2')))
        >>> rv
        {'type': 'address_range', 'from_address': '127.0.0.1', 'to_address': '127.0.0.2'}

    They are also translated forward:

        >>> s.load(rv)
        ('ip_range', ('127.0.0.1', '127.0.0.2'))

    Loading defective values from store is possible...

        >>> rv = s.dump(('ip_network', ('127.0.0.1', '32')))
        >>> rv
        {'type': 'network_range', 'network': '127.0.0.1/32'}

    ... but saving isn't:

        >>> s.load(rv)  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: {'network': ['Prefix of ...

    """

    type_field_remove = False
    type_schemas = {
        "address_range": IPAddressRange,
        "network_range": IPNetwork,
        "explicit_addresses": IPAddresses,
    }

    @override
    def get_obj_type(self, obj: tuple[str, object]) -> str:
        return {
            "ip_range": "address_range",
            "ip_network": "network_range",
            "ip_list": "explicit_addresses",
        }[obj[0]]


class IPRangeWithRegexp(OneOfSchema):
    type_field_remove = False
    type_schemas = {
        "address_range": IPAddressRange,
        "network_range": IPNetwork,
        "explicit_addresses": IPAddresses,
        "exclude_by_regexp": IPRegexp,
    }

    @override
    def get_obj_type(self, obj: tuple[str, object] | dict[str, object]) -> str:
        if isinstance(obj, dict):
            type_key = obj["type"]
            assert isinstance(type_key, str)
            return type_key
        return {
            "ip_range": "address_range",
            "ip_network": "network_range",
            "ip_list": "explicit_addresses",
            "ip_regex_list": "exclude_by_regexp",
        }[obj[0]]


class DateConverter(Converter):
    # NOTE that 24:00 doesn't exist. This would be 00:00 on the next day, but the intended
    # meaning is "the last second/minute of this day", so we replace it with that.

    @override
    def from_checkmk(self, data: tuple[int, int] | list[int]) -> datetime.time:
        """Converts a Checkmk date string to a datetime object

        Examples:
            >>> DateConverter().from_checkmk([24, 0])
            datetime.time(23, 59, 59)

            >>> DateConverter().from_checkmk((0, 0))
            datetime.time(0, 0)
        """
        if data[0] == 24 and data[1] == 0:  # Checkmk format can be [24, 0] e.g. folder network scan
            return datetime.time(23, 59, 59)

        return datetime.time(*data)

    @override
    def to_checkmk(self, data: datetime.time) -> tuple[int, int]:
        return data.hour, data.minute


class TimeAllowedRange(BaseSchema, CheckmkTuple):
    """
    >>> schema = TimeAllowedRange()
    >>> rv = schema.dump(((12, 0), (24, 0)))
    >>> rv
    {'start': '12:00:00', 'end': '23:59:59'}

    >>> schema.load(rv)
    ((12, 0), (23, 59))

    """

    tuple_fields = ("start", "end")
    converter = (DateConverter(), DateConverter())

    start = Time(
        description=("The start time of day. Inclusive. Use ISO8601 format. Seconds are stripped."),
        required=True,
        pattern=r"^\d\d:\d\d(:\d\d)?$",
    )
    end = Time(
        description=("The end time of day. Inclusive. Use ISO8601 format. Seconds are stripped."),
        required=True,
        pattern=r"^\d\d:\d\d(:\d\d)?$",
    )


def _active_users(user: UserId) -> None:
    users = userdb.load_users(lock=False)
    if user not in users:
        raise ValidationError(f"User {user!r} is not known.")


def _enum_options(options: list[tuple[str, str]]) -> str:
    """

    >>> _enum_options([('foo', 'Do the foo, bar times!'), ('bar', 'Barf!')])
    ' * `foo` - Do the foo, bar times!\\n * `bar` - Barf!'

    Args:
        options:

    Returns:

    """
    return "\n".join(f" * `{value}` - {description}" for value, description in options)


class DirectMapping(BaseSchema, CheckmkTuple):
    tuple_fields = ("hostname", "replace_with")

    hostname = String(
        description="The host name to be replaced.",
        required=True,
    )
    replace_with = String(
        description="The replacement string.",
        required=True,
    )


class TranslateNames(BaseSchema):
    case = String(
        data_key="convert_case",
        description="Convert all detected host names to upper- or lower-case.\n\n"
        + _enum_options(
            [
                ("nop", "Do not convert anything"),
                ("lower", "Convert all host names to lowercase."),
                ("upper", "Convert all host names to uppercase."),
            ]
        ),
        enum=["nop", "lower", "upper"],
        load_default="nop",
    )
    drop_domain = Boolean(
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
    )
    regex = List(
        Nested(RegexpRewrites),
        data_key="regexp_rewrites",
        description=(
            "Rewrite discovered host names with multiple regular expressions. The "
            "replacements will be done one after another in the order they appear "
            "in the list. If not anchored at the end by a `$` character, the regexp"
            "will be anchored at the end implicitly by adding a `$` character.\n\n"
            "These will be executed **after**:\n\n"
            " * `convert_case`\n"
            " * `drop_domain`\n"
        ),
    )
    mapping = List(
        Nested(DirectMapping),
        data_key="hostname_replacement",
        description=(
            "Replace one value with another.\n\n"
            "These will be executed **after**:\n\n"
            " * `convert_case`\n"
            " * `drop_domain`\n"
            " * `regexp_rewrites`\n"
        ),
    )


class NetworkScan(BaseSchema):
    """
    >>> from pprint import pprint
    >>> schema = NetworkScan()
    >>> settings = {
    ...     'exclude_ranges': [('ip_list', ['192.168.0.2']),
    ...                        ('ip_regex_list', ['192.168.[02].*'])],
    ...     'ip_ranges': [('ip_range', ('192.168.0.10', '192.168.0.244')),
    ...                   ('ip_network', ('172.10.9.0', 24)),
    ...                   ('ip_regex_list', ['192.168.[01].*']),
    ...                   ('ip_list', ['192.168.0.2'])],
    ...     'max_parallel_pings': 100,
    ... #   This is disabled, due to "running outside app context", duh.
    ... #   'run_as': 'cmkadmin',
    ...     'scan_interval': 86400,
    ...     'set_ipaddress': True,
    ...     'time_allowed': [((12, 0), (23, 59))],
    ...     'translate_names': {
    ...         'case': 'lower',
    ...         'drop_domain': True,
    ...         'mapping': [('example.com', 'www.example.com')],
    ...         'regex': [('.*', 'mehrfacheregulaere')]}}
    >>> pprint(dumped := schema.dump(settings))
    {'addresses': [{'from_address': '192.168.0.10',
                    'to_address': '192.168.0.244',
                    'type': 'address_range'},
                   {'network': '172.10.9.0/24', 'type': 'network_range'},
                   {'regexp_list': ['192.168.[01].*'], 'type': 'exclude_by_regexp'},
                   {'addresses': ['192.168.0.2'], 'type': 'explicit_addresses'}],
     'exclude_addresses': [{'addresses': ['192.168.0.2'],
                            'type': 'explicit_addresses'},
                           {'regexp_list': ['192.168.[02].*'],
                            'type': 'exclude_by_regexp'}],
     'max_parallel_pings': 100,
     'scan_interval': 86400,
     'set_ip_address': True,
     'time_allowed': [{'end': '23:59:00', 'start': '12:00:00'}],
     'translate_names': {'convert_case': 'lower',
                         'drop_domain': True,
                         'hostname_replacement': [{'hostname': 'example.com',
                                                   'replace_with': 'www.example.com'}],
                         'regexp_rewrites': [{'replace_with': 'mehrfacheregulaere',
                                              'search': '.*'}]}}
    >>> settings == schema.load(dumped)
    True
    """

    ip_ranges = List(
        Nested(IPRangeWithRegexp()),
        data_key="addresses",
        required=True,
        description="IPv4 addresses to include.",
    )
    exclude_ranges = List(
        Nested(IPRangeWithRegexp()),
        data_key="exclude_addresses",
        description="IPv4 addresses to exclude.",
    )
    scan_interval = Integer(
        description="Scan interval in seconds. Default is 1 day, minimum is 1 hour.",
        load_default=60 * 60 * 24,
        minimum=3600,
    )
    time_allowed = List(
        Nested(TimeAllowedRange()),
        description="Only execute the discovery during this time range each day..",
        required=True,
    )
    set_ipaddress = Boolean(
        data_key="set_ip_address",
        description="When set, the found IPv4 address is set on the discovered host.",
        load_default=True,
    )
    max_parallel_pings = Integer(
        description="Set the maximum number of concurrent pings sent to target IP addresses.",
        required=False,
        minimum=1,
        maximum=200,
        load_default=100,
    )
    run_as = String(
        description=(
            "Execute the network scan in the Checkmk user context of the chosen user. "
            "This user needs the permission to add new hosts to this folder."
        ),
        required=False,
        validate=_active_users,
    )
    tag_criticality = String(
        description=(
            "Specify which criticality tag to set on the host created by the network scan. "
            "This field is required if the criticality tag group exists, "
            "otherwise it as to be omitted."
        ),
        required=False,
    )
    translate_names = Nested(TranslateNames)

    @validates_schema
    def validate_tag_criticality(self, data: dict[str, Any], **kwargs: Any) -> None:
        tag_criticality = load_tag_group(TagGroupID("criticality"))
        if tag_criticality is None:
            if "tag_criticality" in data:
                raise ValidationError(
                    "Tag group criticality does not exist. tag_criticality must be omitted."
                )
        else:
            if "tag_criticality" not in data:
                raise ValidationError("tag_criticality must be specified")
            if (value := data["tag_criticality"]) not in (t.id for t in tag_criticality.tags):
                raise ValidationError(
                    f"tag_criticality value {value!r} is not defined for criticality tag group"
                )


class NetworkScanResultState(String):
    @override
    def _serialize(
        self, value: object | None, attr: str | None, obj: object, **kwargs: object
    ) -> str:
        if value is None:
            return "running"
        if value is True:
            return "succeeded"
        if value is False:
            return "failed"
        raise AssertionError(f"NetworkScanResult: value {value} not defined")


class NetworkScanResult(BaseSchema):
    start = Timestamp(
        description="When the scan started",
        allow_none=True,
    )
    end = Timestamp(
        description="When the scan finished. Will be Null if not yet run.",
        allow_none=True,
    )
    state = NetworkScanResultState(
        description="Last scan result",
        enum=[
            "running",
            "succeeded",
            "failed",
        ],
    )
    output = String(
        description="Short human readable description of what is happening.",
    )


class LockedBy(BaseSchema, CheckmkTuple):
    """
    >>> schema = LockedBy()
    >>> rv = schema.dump(("site", "dcd", "conn"))
    >>> rv
    {'site_id': 'site', 'program_id': 'dcd', 'instance_id': 'conn'}

    >>> schema.load(rv)
    ('site', 'dcd', 'conn')
    """

    tuple_fields = ("site_id", "program_id", "instance_id")
    cast_to_dict = True
    site_id = String(
        description="Site ID",
        required=True,
    )
    program_id = String(
        description="Program ID",
        required=True,
    )
    instance_id = String(
        description="Instance ID",
        required=True,
    )


AuthProtocolType = Literal["MD5-96", "SHA-1-96", "SHA-2-224", "SHA-2-256", "SHA-2-384", "SHA-2-512"]
PrivacyProtocolType = Literal[
    "CBC-DES",
    "AES-128",
    "3DES-EDE",
    "AES-192",
    "AES-256",
    "AES-192-Blumenthal",
    "AES-256-Blumenthal",
]


AUTH_PROT_MAP: Mapping[AuthProtocolType, str] = {
    "MD5-96": "md5",
    "SHA-1-96": "sha",
    "SHA-2-224": "SHA-224",
    "SHA-2-256": "SHA-256",
    "SHA-2-384": "SHA-384",
    "SHA-2-512": "SHA-512",
}

PRIV_PROT_MAP: Mapping[PrivacyProtocolType, str] = {
    "CBC-DES": "DES",
    "AES-128": "AES",
    "3DES-EDE": "3DES-EDE",
    "AES-192": "AES-192",
    "AES-256": "AES-256",
    "AES-192-Blumenthal": "AES-192-Blumenthal",
    "AES-256-Blumenthal": "AES-256-Blumenthal",
}


class MappingConverter[K, V](Converter):
    """Converts keys according to a mapping

    The direction of the mapping is defined as "INTO Checkmk":

        >>> mapping = {'a': 'b'}

        >>> conv = MappingConverter(mapping)
        >>> conv.to_checkmk('a')
        'b'

        >>> conv.to_checkmk('b')
        Traceback (most recent call last):
        ...
        KeyError: 'b'

    The reverse lookup of the mapping is done by "from_checkmk":

        >>> conv.from_checkmk('b')
        'a'

        >>> conv.from_checkmk('a')
        Traceback (most recent call last):
        ...
        KeyError: 'a'

    """

    __slots__ = ("mapping",)

    def __init__(self, mapping: Mapping[K, V]) -> None:
        self.mapping = mapping

    @override
    def to_checkmk(self, data: K) -> V:
        return self.mapping[data]

    @override
    def from_checkmk(self, data: V) -> K:
        for key, value in self.mapping.items():
            if data == value:
                return key
        raise KeyError(data)


AuthProtocolConverter = MappingConverter(AUTH_PROT_MAP)
PrivacyProtocolConverter = MappingConverter(PRIV_PROT_MAP)


class SNMPCommunity(BaseSchema):
    cast_to_dict = True

    type = Constant(constant="v1_v2_community")
    community = String(
        description="SNMP community (SNMP Versions 1 and 2c)",
        required=True,
    )

    @post_load
    def to_checkmk_str(self, data: dict[str, str], **kwargs: object) -> str:
        return data["community"]

    @pre_dump
    def from_tuple(self, data: object, **kwargs: object) -> dict[str, str] | None:
        """

        v1 'community'
        v3 ('noAuthNoPriv', 'sicherheitsname')
        v3 ('authNoPriv', 'SHA-512', 'sicherheitsname', 'passwort')
        v3 ('authPriv', 'SHA-512', 'sicherheitsname', 'passwort', 'DES', 'privacypasswort')

           Args:
               data:
               **kwargs:

           Returns:

        """
        if isinstance(data, str):
            return {
                "type": "v1_v2_community",
                "community": data,
            }
        return None


class SNMPv3NoAuthNoPrivacy(BaseSchema, CheckmkTuple):
    tuple_fields = ("type", "security_name")
    cast_to_dict = True

    type = Constant(
        description="The type of credentials to use.",
        constant="noAuthNoPriv",
    )
    security_name = String(
        description="Security name",
        required=True,
    )


class SNMPv3AuthNoPrivacy(BaseSchema, CheckmkTuple):
    tuple_fields = ("type", "auth_protocol", "security_name", "auth_password")
    converter = (None, AuthProtocolConverter, None, None)
    cast_to_dict = True

    type = Constant(
        description="The type of credentials to use.",
        constant="authNoPriv",
    )
    auth_protocol = String(
        description="Authentication protocol.",
        enum=list(AUTH_PROT_MAP.keys()),
        required=True,
    )
    security_name = String(
        description="Security name",
        required=True,
    )
    auth_password = String(
        description="Authentication pass phrase.",
        minLength=8,
        required=True,
    )


class SNMPv3AuthPrivacy(BaseSchema, CheckmkTuple):
    tuple_fields = (
        "type",
        "auth_protocol",
        "security_name",
        "auth_password",
        "privacy_protocol",
        "privacy_password",
    )
    converter = (
        None,
        AuthProtocolConverter,
        None,
        None,
        PrivacyProtocolConverter,
        None,
    )
    cast_to_dict = True

    type = Constant(
        description="SNMPv3 with authentication and privacy.",
        constant="authPriv",
    )
    auth_protocol = String(
        description="Authentication protocol.",
        enum=list(AUTH_PROT_MAP.keys()),
        required=True,
    )
    security_name = String(
        description="Security name",
        required=True,
    )
    auth_password = String(
        description="Authentication pass phrase.",
        minLength=8,
        required=True,
    )
    privacy_protocol = String(
        description=(
            "The privacy protocol. "
            "The only supported values in the Raw Edition are CBC-DES and AES-128. "
            "If selected, privacy_password needs to be supplied as well."
        ),
        required=True,
        enum=list(PRIV_PROT_MAP.keys()),
    )
    privacy_password = String(
        description=(
            "Privacy pass phrase. If filled, privacy_protocol needs to be selected as well."
        ),
        required=True,
        minLength=8,
    )


class SNMPCredentials(CmkOneOfSchema):
    """Validate and convert from/to Checkmk internal format for SNMP credentials.

    Here are the various possible values in the attribute

    For v1, v2:

        'community'

    For v3:
        ('noAuthNoPriv', 'sicherheitsname')
        ('authNoPriv', <auth_prot>, 'sicherheitsname', 'passwort')
        ('authPriv', <auth_prot>, 'sicherheitsname', 'passwort', <priv_prot>, 'privacypasswort')

    Examples:

        >>> schema = SNMPCredentials()
        >>> dumped = schema.dump("bar")
        >>> dumped
        {'type': 'v1_v2_community', 'community': 'bar'}

        >>> schema.load(dumped)
        'bar'

        >>> dumped = schema.dump(('authNoPriv', 'sha', 'foo', 'barbarbar'))
        >>> dumped
        {'type': 'v3_auth_no_privacy', 'auth_protocol': 'SHA-1-96', 'security_name': 'foo', 'auth_password': 'barbarbar'}

        >>> schema.load(dumped)
        ('authNoPriv', 'sha', 'foo', 'barbarbar')

        >>> auth_priv = {
        ...     'type': 'v3_auth_privacy',
        ...     'security_name': 'foo',
        ...     'auth_password': 'barbarbar',
        ...     'auth_protocol': 'MD5-96',
        ...     'privacy_protocol': 'CBC-DES',
        ...     'privacy_password': 'barbarbar',
        ... }
        >>> schema.load(auth_priv)
        ('authPriv', 'md5', 'foo', 'barbarbar', 'DES', 'barbarbar')

        >>> rv = schema.dump(('authPriv', 'md5', 'foo', 'barbarbar', 'DES', 'barbaric'))
        >>>
        {'type': 'v3_auth_privacy', 'security_name': 'foo', 'auth_password': 'barbarbar', \
'auth_protocol': 'MD5-96', 'privacy_protocol': 'CBC-DES', 'privacy_password': 'barbaric'}

        >>> schema.load(rv)
        ('authPriv', 'md5', 'foo', 'barbarbar', 'DES', 'barbaric')

        >>> rv = schema.dump(('noAuthNoPriv', 'barbarbar'))
        >>> rv
        {'type': 'v3_no_auth_no_privacy', 'security_name': 'barbarbar'}

        >>> schema.load(rv)
        ('noAuthNoPriv', 'barbarbar')

    """

    type_schemas = {
        "v1_v2_community": SNMPCommunity,
        "v3_no_auth_no_privacy": SNMPv3NoAuthNoPrivacy,
        "v3_auth_no_privacy": SNMPv3AuthNoPrivacy,
        "v3_auth_privacy": SNMPv3AuthPrivacy,
    }

    @override
    def get_obj_type(self, obj: str | tuple[str, ...]) -> str:
        if isinstance(obj, str):
            return "v1_v2_community"
        return {
            "noAuthNoPriv": "v3_no_auth_no_privacy",
            "authNoPriv": "v3_auth_no_privacy",
            "authPriv": "v3_auth_privacy",
        }[obj[0]]


class IPMIParameters(BaseSchema):
    cast_to_dict = True

    username = String(required=True)
    password = String(required=True)


class MetaData(BaseSchema):
    cast_to_dict = True

    created_at = Timestamp(
        description="When has this object been created.",
        allow_none=True,
    )
    updated_at = Timestamp(
        description="When this object was last changed.",
        allow_none=True,
    )
    created_by = String(
        description="The user id under which this object has been created.",
        allow_none=True,
    )


class HostAttributeManagementBoardField(String):
    def __init__(self) -> None:
        super().__init__(
            description=(
                "The protocol used to connect to the management board.\n\n"
                "Valid options are:\n\n"
                " * `none` - No management board\n"
                " * `snmp` - Connect using SNMP\n"
                " * `ipmi` - Connect using IPMI\n"
            ),
            enum=["none", "snmp", "ipmi"],
        )

    @override
    def _deserialize(
        self, value: object, attr: str | None, data: Mapping[str, object] | None, **kwargs: Any
    ) -> object:
        # get value from api, convert it to cmk/python
        deserialized = super()._deserialize(value, attr, data, **kwargs)
        if deserialized == "none":
            return None
        return deserialized

    @override
    def _serialize(self, value: str | None, attr: str | None, obj: object, **kwargs: Any) -> str:
        # get value from cmk/python, convert it to api side
        serialized = super()._serialize(value, attr, obj, **kwargs)
        if serialized is None:
            return "none"
        return serialized


class HostContactGroup(BaseSchema):
    cast_to_dict = True

    groups = List(
        GroupField(
            group_type="contact",
            example="all",
            required=True,
        ),
        required=True,
        description="A list of contact groups.",
    )
    use = Boolean(
        description="Add these contact groups to the host.",
        load_default=False,
    )
    use_for_services = Boolean(
        description=(
            "<p>Always add host contact groups also to its services.</p>"
            "With this option contact groups that are added to hosts are always being added to "
            "services, as well. This only makes a difference if you have assigned other contact "
            "groups to services via rules in <i>Host & Service Parameters</i>. As long as you do "
            "not have any such rule a service always inherits all contact groups from its host."
        ),
        load_default=False,
    )
    recurse_use = Boolean(
        description="Add these groups as contacts to all hosts in all sub-folders of this folder.",
        load_default=False,
    )
    recurse_perms = Boolean(
        description="Give these groups also permission on all sub-folders.",
        load_default=False,
    )
