#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.gui.valuespec as vs
from cmk.gui.i18n import _

from .utils import expect_validate_failure, expect_validate_success, request_var

Sentinel = object()


def get_transform_1() -> vs.Transform:
    """
    Use case: the valuespec of a form has changed.
    Normally this means that also the dataschema has changed.
    But of course the user should not loose their existing configuration.
    So we define only a forth function to transform the old dataschema into the
    new one.
    We imagine some form was like:
      valuespec = vs.TextInput(title="address")
    But now we want also support proxies for the connection:
    """
    valuespec = vs.CascadingDropdown(
        title=_("address"),
        choices=[
            (
                "direct",
                _("Direct URL"),
                vs.TextInput(
                    allow_empty=False,
                    size=45,
                ),
            ),
            (
                "proxy",
                _("address via proxy"),
                vs.Dictionary(
                    elements=[
                        (
                            "address",
                            vs.TextInput(
                                title=_("address"),
                                size=45,
                            ),
                        ),
                        (
                            "proxy",
                            vs.TextInput(
                                title=_("proxy"),
                                size=45,
                            ),
                        ),
                    ],
                ),
            ),
        ],
    )

    # so we now have to transform a bare string as a direct connection:
    def _forth(value):
        if isinstance(value, str):
            # this is the old format, so we transform it to the new format
            return ("direct", value)
        # we assume otherwise it has to be the new format and return as is
        return value

    return vs.Transform(valuespec, forth=_forth)


def get_transform_2() -> vs.Transform:
    """
    The other use case where you need both back and forth can be useful for
    multiple things:
    * When the value of the valuespec is used by some external tool, and that
      tool expects a different value format: You already know that a vs.Age will
      be consumed by a tool that expects minutes instead of Seconds. Then you
      can use a Transform to transparently transform this value so it can be
      consumed without additional calculations.
    * When you can not decide if you already transformed the value or not:
      Imagine a vs.Integer that contained minutes, but was then replaced by a
      vs.Age (for better UI) which stores the duration in seconds:
      We only got an integer value and can not know if it's seconds or minutes.
      So we make sure it is saved as minutes on the disc, and transform it back
      and forth each time we load or save the value.
    """
    return vs.Transform(
        valuespec=vs.Age(minvalue=1, default_value=60),
        forth=lambda v: int(v * 60),
        back=lambda v: float(v) / 60.0,
        title=_("Normal check interval for service checks"),
    )


class TestValueSpecTransform:
    def test_allow_empty_is_passed_throught(self) -> None:
        assert vs.Transform(vs.TextInput(allow_empty=False)).allow_empty() is False
        assert vs.Transform(vs.TextInput(allow_empty=True)).allow_empty() is True

    def test_missing_forth_is_passthough(self) -> None:
        assert vs.Transform(vs.TextInput()).forth(Sentinel) is Sentinel

    def test_title(self) -> None:
        assert vs.Transform(vs.TextInput(title="text_input_title")).title() == "text_input_title"
        assert (
            vs.Transform(vs.TextInput(title="text_input_title"), title="transform_title").title()
            == "transform_title"
        )

    def test_help(self) -> None:
        assert vs.Transform(vs.TextInput(help="text_input_help")).help() == "text_input_help"
        assert (
            vs.Transform(vs.TextInput(help="text_input_help"), help="transform_help").help()
            == "transform_help"
        )

    # TODO: render_input and render_input_as_form

    def test_canonical_value(self) -> None:
        assert vs.Transform(vs.TextInput()).canonical_value() == ""
        # min_value is used for canonical value:
        assert get_transform_2().canonical_value() == 1 / 60

    def test_default_value(self) -> None:
        assert vs.Transform(vs.TextInput(default_value="smth")).default_value() == "smth"
        # we transform the value back
        assert get_transform_2().default_value() == 60 / 60

    def test_mask(self) -> None:
        assert get_transform_2().mask(60) == 60
        assert get_transform_1().mask("ut_url") == ("direct", "ut_url")
        assert get_transform_1().mask(("direct", "ut_url")) == ("direct", "ut_url")

    def test_value_to_html(self) -> None:
        assert get_transform_2().value_to_html(60) == "1 hours"
        assert get_transform_1().value_to_html("ut_url") == "Direct URL, ut_url"

    def test_from_html_vars(self) -> None:
        with request_var(age_minutes="1"):
            # normal age field (without transfrom) would return 60 as it saves
            # the age in seconds.
            assert get_transform_2().from_html_vars("age") == 1

    def test_validate(self) -> None:
        expect_validate_success(get_transform_1(), "ut_address")
        expect_validate_success(get_transform_1(), ("direct", "ut_address"))
        expect_validate_failure(get_transform_1(), ("not_existing", "ut_address"))


def test_transform_value_with_transform_vs() -> None:
    valuespec = vs.Transform(
        valuespec=vs.TextInput(),
        forth=lambda x: x if x == "lala" else x.upper(),
        back=lambda x: x + "aaa",
    )

    assert valuespec.transform_value("lala") == "lalaaaa"
    assert valuespec.transform_value("AAA") == "AAAaaa"


def test_transform_value_dict() -> None:
    valuespec = vs.Dictionary(
        elements=[
            ("a", vs.TextInput()),
        ]
    )
    assert valuespec.transform_value({"a": "lala"}) == {"a": "lala"}


def test_transform_value_in_dict() -> None:
    valuespec = vs.Dictionary(
        elements=[
            (
                "a",
                vs.Transform(
                    valuespec=vs.TextInput(),
                    forth=lambda x: x if x == "lala" else x.upper(),
                    back=lambda x: x + "aaa",
                ),
            ),
        ]
    )

    assert valuespec.transform_value({"a": "lala"}) == {"a": "lalaaaa"}
    assert valuespec.transform_value({"a": "AAA"}) == {"a": "AAAaaa"}


def test_transform_value_in_tuple() -> None:
    valuespec: vs.Tuple[tuple[str, str]] = vs.Tuple(
        elements=[
            vs.Transform(
                valuespec=vs.TextInput(),
                forth=lambda x: x if x == "lala" else x.upper(),
                back=lambda x: x + "aaa",
            ),
            vs.Transform(
                valuespec=vs.TextInput(),
                forth=lambda x: x if x == "lala" else x.upper(),
                back=lambda x: x + "aaa",
            ),
        ]
    )

    assert valuespec.transform_value(("lala", "AAA")) == ("lalaaaa", "AAAaaa")


def test_transform_value_in_cascading_dropdown() -> None:
    valuespec = vs.CascadingDropdown(
        choices=[
            ("a", "Title a", vs.TextInput()),
            (
                "b",
                "Title b",
                vs.Transform(
                    valuespec=vs.TextInput(),
                    forth=lambda x: x if x == "lala" else x.upper(),
                    back=lambda x: x + "aaa",
                ),
            ),
        ]
    )

    assert valuespec.transform_value(("a", "abc")) == ("a", "abc")
    assert valuespec.transform_value(("b", "lala")) == ("b", "lalaaaa")
    assert valuespec.transform_value(("b", "AAA")) == ("b", "AAAaaa")


def test_transform_value_and_json() -> None:
    # before all keys where upper case, then we decided to move to lower case,
    # but want to keep compatibility with old values saved in the config
    valuespec = vs.Transform(
        valuespec=vs.Dictionary(
            elements=[
                ("key1", vs.TextInput()),
            ]
        ),
        forth=lambda x: {k.lower(): v for k, v in x.items()},
    )
    assert valuespec.transform_value({"KEY1": "value1"}) == {"key1": "value1"}

    assert valuespec.value_to_json({"KEY1": "value1"}) == {"key1": "value1"}
    assert valuespec.value_from_json({"key1": "value1"}) == {"key1": "value1"}


def test_transform_value_no_transform_vs() -> None:
    valuespec = vs.TextInput()
    assert valuespec.transform_value("lala") == "lala"
    assert valuespec.transform_value("AAA") == "AAA"
