#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime
import re
import typing

from marshmallow import ValidationError
from marshmallow.decorators import post_load, pre_dump, validates_schema
from marshmallow_oneofschema import OneOfSchema  # type: ignore[import]

from cmk.gui import userdb
from cmk.gui.fields.base import BaseSchema
from cmk.gui.fields.definitions import GroupField, List, Nested, Timestamp
from cmk.gui.fields.mixins import CheckmkTuple, Converter
from cmk.gui.fields.validators import IsValidRegexp, ValidateIPv4, ValidateIPv4Network

from cmk.fields import Boolean, Constant, DateTime, Integer, String, Time

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
    def validate_replacement(self, data, **kwargs):
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


class IPNetwork(BaseSchema, CheckmkTuple):
    tuple_fields = ("type", "network")
    cast_to_dict = True

    type = Constant(
        description="A single IPv4 network in CIDR notation.",
        constant="ip_network",
    )
    network = String(
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

        >>> rv = s.dump(('ip_network', '127.0.0.1/32'))
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

    def get_obj_type(self, obj):
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

    def get_obj_type(self, obj):
        if isinstance(obj, dict):
            return obj["type"]
        return {
            "ip_range": "address_range",
            "ip_network": "network_range",
            "ip_list": "explicit_addresses",
            "ip_regex_list": "exclude_by_regexp",
        }[obj[0]]


class DateConverter(Converter):
    # NOTE that 24:00 doesn't exist. This would be 00:00 on the next day, but the intended
    # meaning is "the last second/minute of this day", so we replace it with that.

    def from_checkmk(self, data):
        if data == (24, 0):
            data = (23, 59, 59)
        return datetime.time(*data)

    def to_checkmk(self, data):
        return data.hour, data.minute


class TimeAllowedRange(BaseSchema, CheckmkTuple):
    """
    >>> schema = TimeAllowedRange()
    >>> rv = schema.dump(((12, 0), (24, 0)))
    >>> rv
    OrderedDict([('start', '12:00:00'), ('end', '23:59:59')])

    >>> schema.load(rv)
    ((12, 0), (23, 59))

    """

    tuple_fields = ("start", "end")
    converter = (DateConverter(), DateConverter())

    start = Time(
        description=(
            "The start time of day. Inclusive. " "Use ISO8601 format. Seconds are stripped."
        )
    )
    end = Time(
        description=("The end time of day. Inclusive. " "Use ISO8601 format. Seconds are stripped.")
    )


def _active_users(user):
    users = userdb.load_users(lock=False)
    if user not in users:
        raise ValidationError(f"User {user!r} is not known.")


def _enum_options(options: typing.List[typing.Tuple[str, str]]) -> str:
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
        description="The hostname to be replaced.",
        required=True,
    )
    replace_with = String(
        description="The replacement string.",
        required=True,
    )


class TranslateNames(BaseSchema):
    case = String(
        data_key="convert_case",
        description="Convert all detected hostnames to upper- or lower-case.\n\n"
        + _enum_options(
            [
                ("nop", "Do not convert anything"),
                ("lower", "Convert all hostnames to lowercase."),
                ("upper", "Convert all hostnames to uppercase."),
            ]
        ),
        enum=["nop", "lower", "upper"],
        load_default="nop",
    )
    drop_domain = Boolean(
        description=(
            "Drop the rest of the domain, only keep the hostname. Will not affect "
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
            "Rewrite discovered hostnames with multiple regular expressions. The "
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

    >>> schema = NetworkScan()
    >>> settings = {
    ...     'exclude_ranges': [('ip_list', ['192.168.0.2']),
    ...                        ('ip_regex_list', ['192.168.[02].*'])],
    ...     'ip_ranges': [('ip_range', ('192.168.0.10', '192.168.0.244')),
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
    >>> result = schema.dump(settings)
    >>> assert len(result['addresses']) == 3
    >>> assert len(result['exclude_addresses']) == 2
    >>> assert len(result['time_allowed'][0]) == 2
    >>> assert len(result['translate_names']) == 4

    >>> import unittest
    >>> test_case = unittest.TestCase()
    >>> test_case.maxDiff = None
    >>> test_case.assertDictEqual(settings, schema.load(result))

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
    translate_names = Nested(TranslateNames)


class NetworkScanResult(BaseSchema):
    start = DateTime(description="When the scan started")
    end = DateTime(
        description="When the scan finished. Will be Null if not yet run.",
        allow_none=True,
    )
    state = String(
        description="Last scan result",
        enum=[
            "not_started",
            "running",
            "succeeded",
            "failed",
        ],
    )


AUTH_PROT_MAP = {
    "MD5-96": "md5",
    "SHA-1-96": "sha",
    "SHA-2-224": "SHA-224",
    "SHA-2-256": "SHA-256",
    "SHA-2-384": "SHA-384",
    "SHA-2-512": "SHA-512",
}

PRIV_PROT_MAP = {
    "CBC-DES": "DES",
    "AES-128": "AES",
    "3DES-EDE": "3DES-EDE",
    "AES-192": "AES-192",
    "AES-256": "AES-256",
    "AES-192-Blumenthal": "AES-192-Blumenthal",
    "AES-256-Blumenthal": "AES-256-Blumenthal",
}


class MappingConverter(Converter):
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

    def __init__(self, mapping):
        self.mapping = mapping

    def to_checkmk(self, data):
        return self.mapping[data]

    def from_checkmk(self, data):
        for key, value in self.mapping.items():
            if data == value:
                return key
        raise KeyError(data)


class SNMPCommunity(BaseSchema):
    cast_to_dict = True

    type = Constant(constant="v1_v2_community")
    community = String(
        description="SNMP community (SNMP Versions 1 and 2c)",
    )

    @post_load
    def to_checkmk_str(self, data, **kwargs):
        return data["community"]

    @pre_dump
    def from_tuple(self, data, **kwargs):
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
    converter = (None, MappingConverter(AUTH_PROT_MAP), None, None)
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
        MappingConverter(AUTH_PROT_MAP),
        None,
        None,
        MappingConverter(PRIV_PROT_MAP),
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
            "Privacy pass phrase. " "If filled, privacy_protocol needs to be selected as well."
        ),
        required=True,
        minLength=8,
    )


class SNMPCredentials(OneOfSchema):
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

    def get_obj_type(self, obj):
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
    )
    updated_at = Timestamp(
        description="When this object was last changed.",
    )
    created_by = String(
        description="The user id under which this object has been created.",
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

    def _deserialize(self, value, attr, data, **kwargs) -> typing.Any:
        # get value from api, convert it to cmk/python
        deserialized = super()._deserialize(value, attr, data, **kwargs)
        if deserialized == "none":
            return None
        return deserialized

    def _serialize(self, value, attr, obj, **kwargs) -> typing.Optional[str]:
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
