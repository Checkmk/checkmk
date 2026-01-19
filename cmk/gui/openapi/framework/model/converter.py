#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ipaddress
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

from pydantic import PlainValidator

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.regex import regex, REGEX_ID
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui import sites, userdb
from cmk.gui.config import active_config, builtin_role_ids
from cmk.gui.customer import customer_api
from cmk.gui.groups import GroupName, GroupType
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.permissions import load_dynamic_permissions, permission_registry
from cmk.gui.userdb import connection_choices
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib import groups_io, tags
from cmk.gui.watolib.hosts_and_folders import Host, strip_hostname_whitespace_chars
from cmk.gui.watolib.passwords import load_passwords
from cmk.gui.watolib.userroles import role_exists, RoleID
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables import Hostgroups, Servicegroups
from cmk.utils.tags import TagGroupID, TagID


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
class RegistryConverter[T]:
    registry_or_getter: Mapping[str, T] | Callable[[UserPermissions], Mapping[str, T]]
    custom_error_message: str | None = None

    @property
    def _registry(self) -> Mapping[str, T]:
        if not isinstance(self.registry_or_getter, Mapping):
            self.registry_or_getter = self.registry_or_getter(
                UserPermissions.from_config(active_config, permission_registry)
            )

        return self.registry_or_getter

    def validate(self, value: str) -> str:
        """Validates that the given value is in the registry."""
        if value not in self._registry:
            valid_options = sorted(self._registry)
            if len(valid_options) > 20:
                valid_options_string = ", ".join(f"'{x}'" for x in valid_options[:19])
                valid_options_string += ", ... (more options available)"
            else:
                valid_options_string = ", ".join(f"'{x}'" for x in valid_options)
            raise ValueError(
                self.custom_error_message
                or f"Value {value!r} is not allowed, valid options are: {valid_options_string}"
            )

        return value

    def value(self, value: str) -> T:
        """Returns the value from the registry."""
        self.validate(value)
        return self._registry[value]


@dataclass(kw_only=True, slots=True)
class HostConverter:
    type PermissionType = Literal["setup_write", "setup_read", "monitor"]

    permission_type: PermissionType = "monitor"
    should_be_cluster: bool | None = None

    @staticmethod
    def _parse_host_name(value: str) -> HostName:
        if not value:
            raise ValueError("Host name cannot be empty.")
        return HostName(strip_hostname_whitespace_chars(value))

    def host(self, value: str) -> Host:
        if host := Host.host(HostName(self._parse_host_name(value))):
            self._verify(host)
            return host

        raise ValueError(f"Host not found: {value!r}")

    def host_name(self, value: str) -> HostName:
        name = self._parse_host_name(value)
        if host := Host.host(name):
            self._verify(host)
            return name

        raise ValueError(f"Host not found: {value!r}")

    @classmethod
    def not_exists(cls, value: str) -> HostName:
        name = cls._parse_host_name(value)
        if Host.host(name):
            raise ValueError(f"Host {value!r} already exists.")

        return name

    def _verify(self, host: Host) -> None:
        """Run all configured verifications for the host."""
        self._verify_user_permissions(host)
        self._verify_cluster(host)

    def _verify_user_permissions(self, host: Host) -> None:
        if self.permission_type == "monitor":
            return

        host.permissions.need_permission("read")
        if self.permission_type == "setup_write":
            host.permissions.need_permission("write")

    def _verify_cluster(self, host: Host) -> None:
        if self.should_be_cluster is None:
            return
        if self.should_be_cluster and not host.is_cluster():
            raise ValueError(f"Host {host.name!r} is not a cluster host, but should be.")
        if not self.should_be_cluster and host.is_cluster():
            raise ValueError(f"Host {host.name!r} is a cluster host, but should not be.")


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
    def active(raw_user_id: str) -> UserId:
        user_id = UserId.parse(raw_user_id)
        users = userdb.load_users(lock=False)
        if user_id not in users:
            raise ValueError(f"User {raw_user_id!r} does not exist.")
        return user_id

    @staticmethod
    def valid_user_id(raw_user_id: str) -> UserId:
        return UserId.parse(raw_user_id)


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


@dataclass(slots=True)
class UserRoleIdConverter:
    type PermissionType = Literal["wato.users", "wato.edit"]

    permission_type: PermissionType = "wato.users"

    def should_exist(self, user_role: str) -> RoleID:
        self._verify_user_permissions()
        role_id = RoleID(user_role)
        if not role_exists(role_id):
            raise ValueError(f"The role should exist but it doesn't: '{user_role}'")
        return role_id

    def should_be_custom_and_should_exist(self, user_role: str) -> RoleID:
        role_id = self.should_exist(user_role)
        if role_id in builtin_role_ids:
            raise ValueError(f"The role should be a custom role but it's not: '{user_role}'")
        return role_id

    def should_not_exist(self, user_role: str) -> RoleID:
        self._verify_user_permissions()
        role_id = RoleID(user_role)
        if role_exists(role_id):
            raise ValueError(f"The role should not exist but it does: '{user_role}'")
        return role_id

    def should_be_builtin(self, user_role: str) -> RoleID:
        self._verify_user_permissions()
        if user_role not in builtin_role_ids:
            raise ValueError(f"The role should be a built-in role but it's not: '{user_role}'")
        return RoleID(user_role)

    def _verify_user_permissions(self) -> None:
        # TODO: clean this up (CMK-17068)
        load_dynamic_permissions()
        user.need_permission("wato.users")

        if self.permission_type == "wato.edit":
            user.need_permission("wato.edit")


class PermissionsConverter:
    @staticmethod
    def validate(value: dict[str, str]) -> dict[str, str]:
        _validation_errors = []
        for key, val in value.items():
            if key not in permission_registry:
                _validation_errors.append(f"The specified permission name doesn't exist: {key}")
            if val not in ["yes", "no", "default"]:
                _validation_errors.append(
                    f"Invalid permission value: {val}.  Only 'yes', 'no', and 'default' are allowed."
                )

        if _validation_errors:
            raise ValueError("Validation errors found:\n" + "\n".join(_validation_errors))

        return value


class SiteIdConverter:
    @staticmethod
    def should_exist(value: str) -> SiteId:
        site_id = SiteId(value)
        if site_id not in active_config.sites:
            raise ValueError(f"Site {site_id!r} does not exist.")
        return site_id

    @staticmethod
    def should_not_exist(value: str) -> SiteId:
        site_id = SiteId(value)
        if site_id in active_config.sites:
            raise ValueError(f"Site {site_id!r} already exists.")
        return site_id


class PasswordConverter:
    @staticmethod
    def is_valid_id(ident: str) -> str:
        pattern: re.Pattern[str] = regex(REGEX_ID, re.ASCII)
        if pattern.match(ident) is None:
            raise ValueError(
                f"{ident!r} does not match pattern. An identifier must only consist of letters, digits, dash and underscore and it must start with a letter or underscore."
            )
        return ident

    @staticmethod
    def not_exists(ident: str) -> str:
        if ident in load_passwords():
            raise ValueError(f'Password "{ident}" already exists.')
        return ident

    @staticmethod
    def exists(ident: str) -> str:
        if ident not in load_passwords():
            raise ValueError(f'Password "{ident}" is not known.')
        return ident


@dataclass(slots=True)
class RelativeUrlConverter:
    allowed_to_be_empty: bool = False
    must_endwith_one: list[str] | None = None
    must_startwith_one: list[str] | None = None

    def validate(self, value: str) -> str:
        if self.allowed_to_be_empty and not value:
            return value

        if self.must_endwith_one is not None:
            if not any({value.endswith(postfix) for postfix in self.must_endwith_one}):
                raise ValueError(
                    "The URL {value!r} does not end with one of {self.must_endwith_one!r}"
                )

        if self.must_startwith_one is not None:
            if not any({value.startswith(prefix) for prefix in self.must_startwith_one}):
                raise ValueError(
                    "The URL {value!r} does not start with one of {self.must_startwith_one!r}"
                )
        return value


class LDAPConnectionIDConverter:
    @staticmethod
    def should_exist(value: str) -> str:
        ldap_connection_ids = [cnx_id for cnx_id, _ in connection_choices()]
        if value not in ldap_connection_ids:
            raise ValueError(f"The LDAP connection {value!r} should exist but it doesn't.")
        return value

    @staticmethod
    def should_not_exist(value: str) -> str:
        ldap_connection_ids = [cnx_id for cnx_id, _ in connection_choices()]
        if value in ldap_connection_ids:
            raise ValueError(f"The LDAP connection {value!r} should not exist but it does.")
        return value


@dataclass(slots=True)
class CustomerConverter:
    allow_global: bool = True

    def should_exist(self, value: str) -> str:
        if self.allow_global and value == "global":
            return value

        if value not in customer_api().customer_collection():
            raise ValueError(f"Customer '{value}' does not exist.")

        return value
