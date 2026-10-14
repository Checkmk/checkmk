#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from textwrap import dedent

import pytest
from utils.postprocess import postprocess


@pytest.mark.parametrize(
    ["code", "expected"],
    [
        pytest.param(
            """
                class Foo(Enum):
                    count = "count"
                    foo = "bar"
            """,
            """
                class Foo(str, Enum):
                    count = "count"  # type: ignore[assignment]
                    foo = "bar"
            """,
            id="enum-with-shadowing-member",
        ),
        pytest.param(
            """
                class Foo(StrEnum):
                    count = "count"
                    foo = "bar"
            """,
            """
                class Foo(StrEnum):
                    count = "count"  # type: ignore[assignment]
                    foo = "bar"
            """,
            id="strenum-with-shadowing-member",
        ),
        pytest.param(
            """
                class Foo(str, Enum, metaclass=EnumMeta):
                    count = "count"
            """,
            """
                class Foo(str, Enum, metaclass=EnumMeta):
                    count = "count"  # type: ignore[assignment]
            """,
            id="metaclass-keyword-does-not-hide-str-enum",
        ),
        pytest.param(
            """
                class Foo(Enum):
                    foo = "bar"
            """,
            """
                class Foo(str, Enum):
                    foo = "bar"
            """,
            id="no-shadowing-member",
        ),
        pytest.param(
            """
                class Foo(IntEnum):
                    count = 1
            """,
            """
                class Foo(IntEnum):
                    count = 1
            """,
            id="non-str-enum-untouched",
        ),
    ],
)
def test_postprocess_enums(code: str, expected: str) -> None:
    assert postprocess(dedent(code).lstrip()) == dedent(expected).lstrip()


def test_postprocess_strips_optional_from_required_member() -> None:
    code = dedent("""
        class Dictionary:
            elements: Sequence[DictionaryElement] | None = field(default_factory=list)
    """).lstrip()
    expected = dedent("""
        class Dictionary:
            elements: Sequence[DictionaryElement] = field(default_factory=list)
    """).lstrip()
    assert postprocess(code) == expected


def test_postprocess_strips_only_none_from_union_of_required_member() -> None:
    code = dedent("""
        class Dictionary:
            elements: Sequence[DictionaryElement] | Sequence[str] | None = field(default_factory=list)
    """).lstrip()
    expected = dedent("""
        class Dictionary:
            elements: Sequence[DictionaryElement] | Sequence[str] = field(default_factory=list)
    """).lstrip()
    assert postprocess(code) == expected


@pytest.mark.parametrize(
    "annotation",
    [
        pytest.param("Sequence[DictionaryElement]", id="not-optional"),
        pytest.param("Sequence[DictionaryElement] | Sequence[str]", id="union-without-none"),
        pytest.param("Optional[Sequence[DictionaryElement]]", id="optional-subscript"),
        pytest.param("None | Sequence[DictionaryElement]", id="none-first"),
    ],
)
def test_postprocess_rejects_required_member_not_annotated_as_optional(annotation: str) -> None:
    code = dedent(f"""
        class Dictionary:
            elements: {annotation} = field(default_factory=list)
    """).lstrip()

    with pytest.raises(ValueError, match=r"Dictionary\.elements"):
        postprocess(code)


def test_postprocess_keeps_optional_of_other_member() -> None:
    code = dedent("""
        class Dictionary:
            title: str | None = None
    """).lstrip()
    assert postprocess(code) == code


def test_postprocess_keeps_optional_of_same_member_in_other_class() -> None:
    code = dedent("""
        class List:
            elements: list[Element] | None = None
    """).lstrip()
    assert postprocess(code) == code


def test_postprocess_keeps_optional_of_member_after_its_class() -> None:
    code = dedent("""
        class Dictionary:
            title: str


        elements: list[Element] | None = None
    """).lstrip()
    assert postprocess(code) == code
