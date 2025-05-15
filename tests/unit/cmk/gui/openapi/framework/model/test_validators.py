#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator
from typing import get_args

import pytest
from pytest_mock import MockerFixture

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.utils.tags import TagGroup, TagGroupID, TagID

from cmk.gui.groups import GroupType
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.validators import (
    GroupValidator,
    HostAddressValidator,
    TagValidator,
    UserValidator,
)


class TestHostAddressValidator:
    def test_allow_empty(self) -> None:
        validator = HostAddressValidator(allow_empty=True)
        assert validator("") == ""

    def test_forbid_empty(self) -> None:
        validator = HostAddressValidator(allow_empty=False)
        with pytest.raises(ValueError, match="Empty host address is not allowed"):
            validator("")

    @pytest.mark.parametrize("value", ["192.168.0.1"])
    def test_allow_ipv4(self, value: str) -> None:
        validator = HostAddressValidator(allow_ipv4=True)
        assert validator(value) == value

    @pytest.mark.parametrize("value", ["192.168.0.1"])
    def test_forbid_ipv4(self, value: str) -> None:
        validator = HostAddressValidator(allow_ipv4=False)
        with pytest.raises(ValueError, match="IPv4 address.* not allowed"):
            validator(value)

    @pytest.mark.parametrize("value", ["2001:db8::1"])
    def test_allow_ipv6(self, value: str) -> None:
        validator = HostAddressValidator(allow_ipv6=True)
        assert validator(value) == value

    @pytest.mark.parametrize("value", ["2001:db8::1"])
    def test_forbid_ipv6(self, value: str) -> None:
        validator = HostAddressValidator(allow_ipv6=False)
        with pytest.raises(ValueError, match="IPv6 address.* not allowed"):
            validator(value)

    @pytest.mark.parametrize("value", ["example.com"])
    def test_allow_hostname(self, value: str) -> None:
        validator = HostAddressValidator(allow_ipv4=False, allow_ipv6=False, allow_empty=False)
        assert validator(value) == value


class TestTagValidatorCriticality:
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
        assert tag_is_present == TagValidator.tag_criticality_presence(tag_is_present)

    def test_present_and_invalid_value(self, tag_is_present: TagID) -> None:
        with pytest.raises(ValueError, match="is not defined for criticality group"):
            TagValidator.tag_criticality_presence(TagID("invalid_tag"))

    def test_present_and_omitted(self, tag_is_present: TagID) -> None:
        with pytest.raises(ValueError, match="tag_criticality must be specified"):
            TagValidator.tag_criticality_presence(ApiOmitted())

    def test_not_present_and_value(self, tag_is_not_present: None) -> None:
        with pytest.raises(ValueError, match="tag_criticality must be omitted"):
            TagValidator.tag_criticality_presence(TagID("test_tag"))

    def test_not_present_and_omitted(self, tag_is_not_present: None) -> None:
        omitted = ApiOmitted()
        assert omitted == TagValidator.tag_criticality_presence(omitted)


class TestUserValidator:
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
        assert user_is_present == UserValidator.active(user_is_present)

    def test_not_present(self, user_is_not_present: None) -> None:
        with pytest.raises(ValueError, match="User .* does not exist"):
            UserValidator.active("non_existent_user")


class TestGroupValidator:
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
        assert group_is_present == GroupValidator(group_type).exists(group_is_present)

    @pytest.mark.parametrize("group_type", get_args(GroupType))
    def test_exists_fails(self, group_type: GroupType, group_is_not_present: None) -> None:
        with pytest.raises(ValueError, match="Group missing"):
            GroupValidator(group_type).exists("non_existent_group")

    @pytest.mark.parametrize("group_type", get_args(GroupType))
    def test_not_exists(self, group_type: GroupType, group_is_not_present: None) -> None:
        group_name = "non_existent_group"
        assert group_name == GroupValidator(group_type).not_exists(group_name)

    @pytest.mark.parametrize("group_type", get_args(GroupType))
    def test_not_exists_fails(self, group_type: GroupType, group_is_present: str) -> None:
        with pytest.raises(ValueError, match="Group .* exists"):
            GroupValidator(group_type).not_exists(group_is_present)

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
            assert group_is_monitored == GroupValidator(group_type).monitored(group_is_monitored)

    @pytest.mark.parametrize("group_type", _groups_except_contact())
    @pytest.mark.usefixtures("request_context")
    def test_monitored_fails(
        self,
        group_type: GroupType,
        mock_livestatus: MockLiveStatusConnection,
        group_is_not_monitored: str,
    ) -> None:
        with mock_livestatus, pytest.raises(ValueError, match="is not monitored"):
            GroupValidator(group_type).monitored(group_is_not_monitored)

    @pytest.mark.parametrize("group_type", _groups_except_contact())
    @pytest.mark.usefixtures("request_context")
    def test_not_monitored(
        self,
        group_type: GroupType,
        mock_livestatus: MockLiveStatusConnection,
        group_is_not_monitored: str,
    ) -> None:
        with mock_livestatus:
            assert group_is_not_monitored == GroupValidator(group_type).not_monitored(
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
            GroupValidator(group_type).not_monitored(group_is_monitored)

    def test_monitored_fails_contact(self) -> None:
        with pytest.raises(ValueError, match="Unsupported group type"):
            GroupValidator("contact").monitored("some_group")

    def test_not_monitored_fails_contact(self) -> None:
        with pytest.raises(ValueError, match="Unsupported group type"):
            GroupValidator("contact").not_monitored("some_group")
