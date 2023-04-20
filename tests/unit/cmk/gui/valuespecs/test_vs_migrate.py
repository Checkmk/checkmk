#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.valuespec as vs

from .utils import (
    expect_validate_failure_migrate_or_transform,
    expect_validate_success_migrate_or_transform,
)


@pytest.fixture(name="migrate")
def fixture_migrate() -> vs.Migrate[vs.CascadingDropdownChoiceValue]:
    return vs.Migrate(
        vs.CascadingDropdown(
            title="address",
            choices=[
                (
                    "direct",
                    "Direct URL",
                    vs.TextInput(
                        allow_empty=False,
                        size=45,
                    ),
                ),
                (
                    "proxy",
                    "address via proxy",
                    vs.Dictionary(
                        elements=[
                            (
                                "address",
                                vs.TextInput(
                                    title="address",
                                    size=45,
                                ),
                            ),
                            (
                                "proxy",
                                vs.TextInput(
                                    title="proxy",
                                    size=45,
                                ),
                            ),
                        ],
                    ),
                ),
            ],
        ),
        migrate=lambda v: ("direct", v) if isinstance(v, str) else v,
    )


class TestMigrate:
    def test_mask(self, migrate: vs.Migrate[vs.CascadingDropdownChoiceValue]) -> None:
        assert migrate.mask(("direct", "some_url")) == ("direct", "some_url")
        assert migrate.mask("some_url") == ("direct", "some_url")

    def test_value_to_html(self, migrate: vs.Migrate[vs.CascadingDropdownChoiceValue]) -> None:
        assert migrate.value_to_html(("proxy", {})) == "address via proxy, (no parameters)"
        assert migrate.value_to_html("some_url") == "Direct URL, some_url"

    def test_validate(self, migrate: vs.Migrate[vs.CascadingDropdownChoiceValue]) -> None:
        expect_validate_success_migrate_or_transform(migrate, ("direct", "some_url"))
        expect_validate_success_migrate_or_transform(migrate, "some_url")
        expect_validate_failure_migrate_or_transform(migrate, {1, 2, 3})


def test_transform_value_with_migrate_vs() -> None:
    valuespec = vs.Migrate(
        vs.TextInput(),
        migrate=lambda x: x if x == "lala" else x.upper(),
    )

    assert valuespec.transform_value("lala") == "lala"
    assert valuespec.transform_value("aaa") == "AAA"


def test_transform_value_in_dict() -> None:
    valuespec = vs.Dictionary(
        elements=[
            (
                "a",
                vs.Migrate(
                    vs.TextInput(),
                    migrate=lambda x: x if x == "lala" else x.upper(),
                ),
            ),
        ]
    )

    assert valuespec.transform_value({"a": "lala"}) == {"a": "lala"}
    assert valuespec.transform_value({"a": "aaa"}) == {"a": "AAA"}


def test_transform_value_in_tuple() -> None:
    assert vs.Tuple[tuple[str, str]](
        elements=[
            vs.Migrate(
                vs.TextInput(),
                migrate=lambda x: x if x == "lala" else x.upper(),
            ),
            vs.Migrate(
                vs.TextInput(),
                migrate=lambda x: x if x == "lala" else x.upper(),
            ),
        ]
    ).transform_value(("lala", "aaa")) == ("lala", "AAA")


def test_transform_value_in_cascading_dropdown() -> None:
    valuespec = vs.CascadingDropdown(
        choices=[
            ("a", "Title a", vs.TextInput()),
            (
                "b",
                "Title b",
                vs.Migrate(
                    vs.TextInput(),
                    migrate=lambda x: x if x == "lala" else x.upper(),
                ),
            ),
        ]
    )

    assert valuespec.transform_value(("a", "abc")) == ("a", "abc")
    assert valuespec.transform_value(("b", "lala")) == ("b", "lala")
    assert valuespec.transform_value(("b", "AAA")) == ("b", "AAA")


def test_transform_value_and_json() -> None:
    # before all keys where upper case, then we decided to move to lower case,
    # but want to keep compatibility with old values saved in the config
    valuespec = vs.Migrate(
        vs.Dictionary(
            elements=[
                ("key1", vs.TextInput()),
            ]
        ),
        migrate=lambda x: {k.lower(): v for k, v in x.items()},
    )
    assert valuespec.transform_value({"KEY1": "value1"}) == {"key1": "value1"}

    assert valuespec.value_to_json({"KEY1": "value1"}) == {"key1": "value1"}
    assert valuespec.value_from_json({"key1": "value1"}) == {"key1": "value1"}
