#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated, get_args

import pytest
from pydantic import AfterValidator
from pytest_mock import MockerFixture

from tests.unit.cmk.gui.users import create_and_destroy_user

from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.utils.tags import TagGroup, TagGroupID, TagID

from cmk.automations.results import DeleteHostsResult

from cmk.gui.exceptions import MKAuthException
from cmk.gui.groups import GroupType
from cmk.gui.openapi.framework.model import ApiOmitted, json_dump_without_omitted
from cmk.gui.openapi.framework.model.converter import (
    GroupConverter,
    HostAddressConverter,
    HostConverter,
    TagConverter,
    UserConverter,
)
from cmk.gui.session import SuperUserContext, UserContext
from cmk.gui.watolib.groups import HostAttributeContactGroups
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import folder_tree


def test_validators_dont_run_on_json_dump() -> None:
    def validator(_: str) -> str:
        raise ValueError("Should not run")

    @dataclass(slots=True)
    class Model:
        field: Annotated[str, AfterValidator(validator)]

    instance = Model(field="test")
    json_dump_without_omitted(Model, instance)


class TestHostAddressConverter:
    def test_allow_empty(self) -> None:
        validator = HostAddressConverter(allow_empty=True)
        assert validator("") == ""

    def test_forbid_empty(self) -> None:
        validator = HostAddressConverter(allow_empty=False)
        with pytest.raises(ValueError, match="Empty host address is not allowed"):
            validator("")

    @pytest.mark.parametrize("value", ["192.168.0.1"])
    def test_allow_ipv4(self, value: str) -> None:
        validator = HostAddressConverter(allow_ipv4=True)
        assert validator(value) == value

    @pytest.mark.parametrize("value", ["192.168.0.1"])
    def test_forbid_ipv4(self, value: str) -> None:
        validator = HostAddressConverter(allow_ipv4=False)
        with pytest.raises(ValueError, match="IPv4 address.* not allowed"):
            validator(value)

    @pytest.mark.parametrize("value", ["2001:db8::1"])
    def test_allow_ipv6(self, value: str) -> None:
        validator = HostAddressConverter(allow_ipv6=True)
        assert validator(value) == value

    @pytest.mark.parametrize("value", ["2001:db8::1"])
    def test_forbid_ipv6(self, value: str) -> None:
        validator = HostAddressConverter(allow_ipv6=False)
        with pytest.raises(ValueError, match="IPv6 address.* not allowed"):
            validator(value)

    @pytest.mark.parametrize("value", ["example.com"])
    def test_allow_hostname(self, value: str) -> None:
        validator = HostAddressConverter(allow_ipv4=False, allow_ipv6=False, allow_empty=False)
        assert validator(value) == value


class TestTagConverterCriticality:
    @pytest.fixture(name="tag_is_present")
    def fixture_tag_is_present(self, mocker: MockerFixture) -> Iterator[TagID]:
        tag_id = TagID("test_tag")
        group = TagGroup.from_config(
            {
                "id": TagGroupID("test"),
                "title": "Test Tag Group",
                "tags": [
                    {
                        "id": tag_id,
                        "title": "Test Tag",
                        "aux_tags": [],
                    }
                ],
            }
        )
        mocker.patch(
            "cmk.gui.watolib.tags.load_tag_group",
            return_value=group,
        )
        yield tag_id

    @pytest.fixture(name="tag_is_not_present")
    def fixture_tag_is_not_present(self, mocker: MockerFixture) -> Iterator[None]:
        mocker.patch("cmk.gui.watolib.tags.load_tag_group", return_value=None)
        yield None

    def test_present_and_valid_value(self, tag_is_present: TagID) -> None:
        assert tag_is_present == TagConverter.tag_criticality_presence(tag_is_present)

    def test_present_and_invalid_value(self, tag_is_present: TagID) -> None:
        with pytest.raises(ValueError, match="is not defined for criticality group"):
            TagConverter.tag_criticality_presence(TagID("invalid_tag"))

    def test_present_and_omitted(self, tag_is_present: TagID) -> None:
        with pytest.raises(ValueError, match="tag_criticality must be specified"):
            TagConverter.tag_criticality_presence(ApiOmitted())

    def test_not_present_and_value(self, tag_is_not_present: None) -> None:
        with pytest.raises(ValueError, match="tag_criticality must be omitted"):
            TagConverter.tag_criticality_presence(TagID("test_tag"))

    def test_not_present_and_omitted(self, tag_is_not_present: None) -> None:
        omitted = ApiOmitted()
        assert omitted == TagConverter.tag_criticality_presence(omitted)


class TestUserConverter:
    @pytest.fixture(name="user_is_present")
    def fixture_user_is_present(self, mocker: MockerFixture) -> Iterator[str]:
        user = "test_user"
        mocker.patch("cmk.gui.userdb.load_users", return_value={user: {"name": user}})
        yield user

    @pytest.fixture(name="user_is_not_present")
    def fixture_user_is_not_present(self, mocker: MockerFixture) -> Iterator[None]:
        mocker.patch("cmk.gui.userdb.load_users", return_value={})
        yield None

    def test_present(self, user_is_present: str) -> None:
        assert user_is_present == UserConverter.active(user_is_present)

    def test_not_present(self, user_is_not_present: None) -> None:
        with pytest.raises(ValueError, match="User .* does not exist"):
            UserConverter.active("non_existent_user")


class TestGroupConverter:
    @pytest.fixture(name="group_is_present")
    def fixture_group_is_present(
        self, mocker: MockerFixture, group_type: GroupType
    ) -> Iterator[str]:
        group_name = "test_group"
        mocker.patch(
            "cmk.gui.watolib.groups_io.load_group_information",
            return_value={group_type: {group_name: {}}},
        )
        yield group_name

    @pytest.fixture(name="group_is_not_present")
    def fixture_group_is_not_present(
        self, mocker: MockerFixture, group_type: GroupType
    ) -> Iterator[None]:
        mocker.patch(
            "cmk.gui.watolib.groups_io.load_group_information", return_value={group_type: {}}
        )
        yield None

    @pytest.mark.parametrize("group_type", get_args(GroupType))
    def test_exists(self, group_type: GroupType, group_is_present: str) -> None:
        assert group_is_present == GroupConverter(group_type).exists(group_is_present)

    @pytest.mark.parametrize("group_type", get_args(GroupType))
    def test_exists_fails(self, group_type: GroupType, group_is_not_present: None) -> None:
        with pytest.raises(ValueError, match="Group missing"):
            GroupConverter(group_type).exists("non_existent_group")

    @pytest.mark.parametrize("group_type", get_args(GroupType))
    def test_not_exists(self, group_type: GroupType, group_is_not_present: None) -> None:
        group_name = "non_existent_group"
        assert group_name == GroupConverter(group_type).not_exists(group_name)

    @pytest.mark.parametrize("group_type", get_args(GroupType))
    def test_not_exists_fails(self, group_type: GroupType, group_is_present: str) -> None:
        with pytest.raises(ValueError, match="Group .* exists"):
            GroupConverter(group_type).not_exists(group_is_present)

    @staticmethod
    def _groups_except_contact() -> list[GroupType]:
        """Get all group types except 'contact'.

        The monitored checks don't support contact groups.
        """
        return [group for group in get_args(GroupType) if group != "contact"]

    @pytest.fixture(name="group_is_monitored")
    def fixture_group_is_monitored(
        self,
        group_type: GroupType,
        mock_livestatus: MockLiveStatusConnection,
        group_is_not_monitored: str,
    ) -> Iterator[str]:
        """Set up the livestatus mock for testing monitored groups. Yields the group name."""
        mock_livestatus.add_table(f"{group_type}groups", [{"name": group_is_not_monitored}])
        yield group_is_not_monitored

    @pytest.fixture(name="group_is_not_monitored")
    def fixture_group_is_not_monitored(
        self, group_type: GroupType, mock_livestatus: MockLiveStatusConnection
    ) -> Iterator[str]:
        """Set up the livestatus mock for testing unmonitored groups. Yields the group name."""
        group_name = "test_group"
        table = f"{group_type}groups"
        mock_livestatus.expect_query(f"GET {table}\nColumns: name\nFilter: name = {group_name}")
        yield group_name

    @pytest.mark.parametrize("group_type", _groups_except_contact())
    @pytest.mark.usefixtures("request_context")
    def test_monitored(
        self,
        group_type: GroupType,
        mock_livestatus: MockLiveStatusConnection,
        group_is_monitored: str,
    ) -> None:
        with mock_livestatus:
            assert group_is_monitored == GroupConverter(group_type).monitored(group_is_monitored)

    @pytest.mark.parametrize("group_type", _groups_except_contact())
    @pytest.mark.usefixtures("request_context")
    def test_monitored_fails(
        self,
        group_type: GroupType,
        mock_livestatus: MockLiveStatusConnection,
        group_is_not_monitored: str,
    ) -> None:
        with mock_livestatus, pytest.raises(ValueError, match="is not monitored"):
            GroupConverter(group_type).monitored(group_is_not_monitored)

    @pytest.mark.parametrize("group_type", _groups_except_contact())
    @pytest.mark.usefixtures("request_context")
    def test_not_monitored(
        self,
        group_type: GroupType,
        mock_livestatus: MockLiveStatusConnection,
        group_is_not_monitored: str,
    ) -> None:
        with mock_livestatus:
            assert group_is_not_monitored == GroupConverter(group_type).not_monitored(
                group_is_not_monitored
            )

    @pytest.mark.parametrize("group_type", _groups_except_contact())
    @pytest.mark.usefixtures("request_context")
    def test_not_monitored_fails(
        self,
        group_type: GroupType,
        mock_livestatus: MockLiveStatusConnection,
        group_is_monitored: str,
    ) -> None:
        with mock_livestatus, pytest.raises(ValueError, match="should not be monitored"):
            GroupConverter(group_type).not_monitored(group_is_monitored)

    def test_monitored_fails_contact(self) -> None:
        with pytest.raises(ValueError, match="Unsupported group type"):
            GroupConverter("contact").monitored("some_group")

    def test_not_monitored_fails_contact(self) -> None:
        with pytest.raises(ValueError, match="Unsupported group type"):
            GroupConverter("contact").not_monitored("some_group")


class TestHostConverter:
    @staticmethod
    def _permission_types(*, except_monitor: bool = False) -> list[HostConverter.PermissionType]:
        permission_types: list[HostConverter.PermissionType] = [
            "monitor",
            "setup_read",
            "setup_write",
        ]
        if except_monitor:
            return [perm for perm in permission_types if perm != "monitor"]

        return permission_types

    @pytest.fixture(name="sample_host")
    def fixture_sample_host(self, request_context: None) -> Iterator[str]:
        host_name = "test_host"
        root_folder = folder_tree().root_folder()

        # for test_exists_setup_write_edit_hosts
        contact_groups = HostAttributeContactGroups().default_value()
        contact_groups["groups"] = ["all"]

        with SuperUserContext():
            root_folder.create_hosts(
                [(HostName(host_name), HostAttributes(contactgroups=contact_groups), None)],
                pprint_value=False,
            )
        try:
            yield host_name
        finally:
            with SuperUserContext():
                root_folder.delete_hosts(
                    [HostName(host_name)],
                    automation=lambda _automation_config, _hosts, _debug: DeleteHostsResult(),
                    pprint_value=False,
                    debug=False,
                )

    @pytest.mark.parametrize("permission_type", _permission_types())
    def test_exists_fails_not_found(
        self,
        with_admin_login: UserId,
        permission_type: HostConverter.PermissionType,
    ) -> None:
        with pytest.raises(ValueError, match="Host not found"):
            HostConverter(permission_type=permission_type).host_name("non_existent_host")

    def test_exists_monitor_without_permissions(self, sample_host: str) -> None:
        with UserContext(UserId("made-up")):
            assert sample_host == HostConverter(permission_type="monitor").host_name(sample_host)

    @pytest.mark.parametrize("permission_type", _permission_types(except_monitor=True))
    def test_exists_fails_no_permission(
        self, sample_host: str, permission_type: HostConverter.PermissionType
    ) -> None:
        with UserContext(UserId("made-up")), pytest.raises(MKAuthException):
            HostConverter(permission_type=permission_type).host_name(sample_host)

    def test_exists_setup_read_all_folders(self, sample_host: str) -> None:
        with UserContext(UserId("made-up"), explicit_permissions={"wato.see_all_folders"}):
            assert sample_host == HostConverter(permission_type="setup_read").host_name(sample_host)

    def test_exists_setup_write_all_folders(self, sample_host: str) -> None:
        # write also requires read permissions, could be changed in the future
        with UserContext(
            UserId("made-up"), explicit_permissions={"wato.see_all_folders", "wato.all_folders"}
        ):
            assert sample_host == HostConverter(permission_type="setup_write").host_name(
                sample_host
            )

    def test_exists_setup_write_edit_hosts(self, sample_host: str) -> None:
        # write also requires read permissions, could be changed in the future
        with create_and_destroy_user() as (user_id, _password):
            with UserContext(
                user_id, explicit_permissions={"wato.see_all_folders", "wato.edit_hosts"}
            ):
                assert sample_host == HostConverter(permission_type="setup_write").host_name(
                    sample_host
                )
