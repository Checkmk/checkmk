#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Iterator

import pytest
from pytest_mock import MockerFixture

from cmk.utils.tags import TagGroup, TagGroupID, TagID

from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.validators import (
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

    def test_not_present(self, user_is_not_present: str) -> None:
        with pytest.raises(ValueError, match="User .* does not exist"):
            UserValidator.active(user_is_not_present)
