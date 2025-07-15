#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ipaddress
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from pydantic import PlainValidator

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.user import UserId

from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables import Hostgroups, Servicegroups
from cmk.utils.tags import TagGroupID, TagID

from cmk.gui import sites, userdb
from cmk.gui.groups import GroupName, GroupType
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.watolib import groups_io, tags
from cmk.gui.watolib.hosts_and_folders import Host


def TypedPlainValidator[T](input_type: type[T], validator: Callable[[T], object]) -> PlainValidator:
    """
    Creates a pydantic validator that replaces the normal validation with the given `validator`.

    This is similar to a normal `PlainValidator`, except that it also validates the input type,
    before calling the `validator` function. It should most likely be used instead of
    `PlainValidator` in all cases. If the input type is the same as the validator result, an
    `AfterValidator` is the better choice. This validator will first check if the input matches the
    specified `input_type`, then will execute the given `validator` function. The result of this
    function should be used as an annotation on the field/type via `Annotated`.

    Args:
        input_type: Allowed input type, will be used for the schema and actual validation.
        validator: A function which validates the input value and converts it to the output type.
    """

    def _with_type_check(value: T) -> object:
        if not isinstance(value, input_type):
            raise TypeError(f"Expected {input_type}, got {value!r}")

        return validator(value)

    return PlainValidator(
        func=_with_type_check,
        json_schema_input_type=input_type,
    )


@dataclass(slots=True)
class HostConverter:
    type PermissionType = Literal["setup_write", "setup_read", "monitor"]

    permission_type: PermissionType = "monitor"

    def host(self, value: str) -> Host:
        if host := Host.host(HostName(value)):
            self._verify_user_permissions(host)
            return host

        raise ValueError(f"Host not found: {value!r}")

    def host_name(self, value: str) -> HostName:
        name = HostName(value)
        if host := Host.host(name):
            self._verify_user_permissions(host)
            return name

        raise ValueError(f"Host not found: {value!r}")

    @staticmethod
    def not_exists(value: str) -> HostName:
        name = HostName(value)
        if Host.host(name):
            raise ValueError(f"Host {value!r} already exists.")

        return name

    def _verify_user_permissions(self, host: Host) -> None:
        if self.permission_type == "monitor":
            return

        host.permissions.need_permission("read")
        if self.permission_type == "setup_write":
            host.permissions.need_permission("write")


@dataclass(slots=True)
class GroupConverter:
    group_type: GroupType

    def exists(
        self,
        group: GroupName,
    ) -> GroupName:
        if not GroupConverter._verify_group_exists(self.group_type, group):
            raise ValueError(f"Group missing: {group!r}")
        return group

    def not_exists(
        self,
        group: GroupName,
    ) -> GroupName:
        if GroupConverter._verify_group_exists(self.group_type, group):
            raise ValueError(f"Group {group!r} already exists.")
        return group

    def monitored(
        self,
        group: GroupName,
    ) -> GroupName:
        if not GroupConverter._group_is_monitored(self.group_type, group):
            raise ValueError(
                f"Group {group!r} exists, but is not monitored. Activate the configuration?"
            )
        return group

    def not_monitored(
        self,
        group: GroupName,
    ) -> GroupName:
        if GroupConverter._group_is_monitored(self.group_type, group):
            raise ValueError(
                f"Group {group!r} exists, but should not be monitored. Activate the configuration?"
            )
        return group

    @staticmethod
    def _verify_group_exists(group_type: GroupType, name: GroupName) -> bool:
        specific_existing_groups = groups_io.load_group_information()[group_type]
        return name in specific_existing_groups

    @staticmethod
    def _group_is_monitored(group_type: GroupType, group_name: GroupName) -> bool:
        if group_type == "service":
            return bool(
                Query([Servicegroups.name], Servicegroups.name == group_name).first_value(
                    sites.live()
                )
            )
        if group_type == "host":
            return bool(
                Query([Hostgroups.name], Hostgroups.name == group_name).first_value(sites.live())
            )

        raise ValueError("Unsupported group type.")


class UserConverter:
    @staticmethod
    def active(user: str) -> UserId:
        user_id = UserId.parse(user)
        users = userdb.load_users(lock=False)
        if user_id not in users:
            raise ValueError(f"User {user!r} does not exist.")
        return user_id


class TagConverter:
    @staticmethod
    def tag_criticality_presence(value: TagID | ApiOmitted) -> TagID | ApiOmitted:
        tag_criticality = tags.load_tag_group(TagGroupID("criticality"))
        if tag_criticality is None:
            if not isinstance(value, ApiOmitted):
                raise ValueError(
                    "Tag group criticality does not exist. tag_criticality must be omitted."
                )
        else:
            if isinstance(value, ApiOmitted):
                raise ValueError("tag_criticality must be specified")
            if value not in (t.id for t in tag_criticality.tags):
                raise ValueError(
                    f"tag_criticality value '{value!r}' is not defined for criticality group"
                )
        return value


@dataclass(slots=True)
class HostAddressConverter:
    allow_ipv4: bool = True
    allow_ipv6: bool = True
    allow_empty: bool = False

    @staticmethod
    def _try_parse_ip_address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
        try:
            return ipaddress.ip_address(value)
        except ValueError:
            return None

    def __call__(self, value: str) -> HostAddress:
        if not self.allow_empty and not value:
            raise ValueError("Empty host address is not allowed.")

        address = HostAddress(value)  # this allows hostnames and ip addresses
        if not self.allow_ipv4 or not self.allow_ipv6:
            if ip := self._try_parse_ip_address(value):
                if not self.allow_ipv4 and isinstance(ip, ipaddress.IPv4Address):
                    raise ValueError(f"IPv4 address '{value}' is not allowed.")
                if not self.allow_ipv6 and isinstance(ip, ipaddress.IPv6Address):
                    raise ValueError(f"IPv6 address '{value}' is not allowed.")

        return address
