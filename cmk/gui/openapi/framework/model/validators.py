#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ipaddress
from dataclasses import dataclass
from typing import Literal

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables import Hostgroups, Servicegroups
from cmk.utils.tags import TagGroupID, TagID

from cmk.gui import sites, userdb
from cmk.gui.groups import GroupName, GroupType
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.watolib import tags
from cmk.gui.watolib.groups_io import load_group_information
from cmk.gui.watolib.hosts_and_folders import Host


@dataclass(slots=True)
class HostValidator:
    # TODO: skip_validation_on_view?
    permission_type: Literal["setup_write", "setup_read", "monitor"] = "monitor"

    def exists(self, value: str) -> str:
        host = Host.host(HostName(value))
        self._verify_user_permissions(host)

        if host is None:
            raise ValueError(f"Host not found: {value!r}")
        return value

    def _verify_user_permissions(self, host: Host | None) -> None:
        if self.permission_type == "monitor":
            return

        if not host:
            return

        host._user_needs_permission("read")
        if self.permission_type == "setup_write":
            host._user_needs_permission("write")


@dataclass(slots=True)
class GroupValidator:
    group_type: GroupType

    def exists(
        self,
        group: GroupName,
    ) -> None:
        if not GroupValidator._verify_group_exists(self.group_type, group):
            raise ValueError(f"Group missing: {group!r}")

    def not_exists(
        self,
        group: GroupName,
    ) -> None:
        if GroupValidator._verify_group_exists(self.group_type, group):
            raise ValueError(f"Group {group!r} already exists.")

    def monitored(
        self,
        group: GroupName,
    ) -> None:
        if not GroupValidator._group_is_monitored(self.group_type, group):
            raise ValueError(
                f"Group {group!r} exists, but is not monitored. Activate the configuration?"
            )

    def not_monitored(
        self,
        group: GroupName,
    ) -> None:
        if GroupValidator._group_is_monitored(self.group_type, group):
            raise ValueError(
                f"Group {group!r} exists, but should not be monitored. Activate the configuration?"
            )

    @staticmethod
    def _verify_group_exists(group_type: GroupType, name: GroupName) -> bool:
        specific_existing_groups = load_group_information()[group_type]
        return name in specific_existing_groups

    @staticmethod
    def _group_is_monitored(group_type: GroupType, group_name: GroupName) -> bool:
        # Danke mypy
        rv: bool
        if group_type == "service":
            rv = bool(
                Query([Servicegroups.name], Servicegroups.name == group_name).first_value(
                    sites.live()
                )
            )
        elif group_type == "host":
            rv = bool(
                Query([Hostgroups.name], Hostgroups.name == group_name).first_value(sites.live())
            )
        else:
            raise ValueError("Unknown group type.")
        return rv


class UserValidator:
    @staticmethod
    def active(user: str) -> str:
        users = userdb.load_users(lock=False)
        if user not in users:
            raise ValueError(f"User {user!r} does not exist.")
        return user


class TagValidator:
    @staticmethod
    def tag_criticality_presence(value: TagID | ApiOmitted) -> str | ApiOmitted:
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
class HostAddressValidator:
    allow_ipv4: bool = True
    allow_ipv6: bool = True
    allow_empty: bool = False

    @staticmethod
    def _try_parse_ip_address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
        try:
            return ipaddress.ip_address(value)
        except ValueError:
            return None

    def __call__(self, value: str) -> str:
        if not self.allow_empty and not value:
            raise ValueError("Empty host address is not allowed.")

        HostAddress(value)  # this allows hostnames and ip addresses
        if not self.allow_ipv4 or not self.allow_ipv6:
            if ip := self._try_parse_ip_address(value):
                if not self.allow_ipv4 and isinstance(ip, ipaddress.IPv4Address):
                    raise ValueError(f"IPv4 address '{value}' is not allowed.")
                if not self.allow_ipv6 and isinstance(ip, ipaddress.IPv6Address):
                    raise ValueError(f"IPv6 address '{value}' is not allowed.")

        return value
