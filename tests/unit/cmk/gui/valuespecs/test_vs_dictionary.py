#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

import cmk.gui.valuespec as vs
from cmk.gui.utils.html import HTML

from .utils import expect_validate_failure, expect_validate_success, request_var


def _test_elements() -> list[tuple[str, vs.ValueSpec]]:
    return [
        ("a", vs.TextInput(title="A")),
        ("b", vs.Integer()),
        ("c", vs.Password(title="C", default_value="z")),
        ("d", vs.Integer(minvalue=1)),
    ]


class TestValueSpecDictionary:
    def test_init(self) -> None:
        vs.Dictionary(elements=_test_elements(), optional_keys=set())
        vs.Dictionary(elements=_test_elements(), optional_keys=[])
        vs.Dictionary(elements=_test_elements(), optional_keys=False)
        vs.Dictionary(elements=_test_elements(), optional_keys=True)

        with pytest.raises(
            TypeError, match="optional_keys and required_keys can not be set at the same time."
        ):
            vs.Dictionary(elements=_test_elements(), optional_keys={"a"}, required_keys=["b"])

        with pytest.raises(
            TypeError,
            match="optional_keys = False enforces all keys to be required, so required_keys has no effect.",
        ):
            vs.Dictionary(elements=_test_elements(), optional_keys=False, required_keys=["b"])

    def test_validate(self) -> None:
        empty_dict: dict[str, object] = {}

        expect_validate_success(vs.Dictionary(elements=_test_elements()), empty_dict)
        expect_validate_success(
            vs.Dictionary(elements=_test_elements()), {"a": "", "b": 0, "c": "", "d": 4}
        )
        expect_validate_failure(vs.Dictionary(elements=_test_elements()), {"z": "z"})
        expect_validate_success(
            vs.Dictionary(elements=_test_elements(), ignored_keys=["z"]), {"z": "z"}
        )

        expect_validate_failure(vs.Dictionary(elements=_test_elements()), ["a", "b"])  # type: ignore[misc]

        # required_keys do what you would expect
        expect_validate_success(
            vs.Dictionary(elements=_test_elements(), required_keys=("a",)), {"a": "a"}
        )
        expect_validate_failure(
            vs.Dictionary(elements=_test_elements(), required_keys=("a",)), empty_dict
        )

        # optional_keys invert required_keys internally:
        # optional_keys=[a,b,c] == required_keys=[d]
        expect_validate_success(
            vs.Dictionary(elements=_test_elements(), optional_keys=["a", "b", "c"]), {"d": 1}
        )
        expect_validate_failure(
            vs.Dictionary(elements=_test_elements(), optional_keys=["a", "b", "c"]), empty_dict
        )

        # child valuespec failure:
        expect_validate_failure(vs.Dictionary(elements=_test_elements()), {"d": 0})
        # child valuespec datatype failure:
        expect_validate_failure(vs.Dictionary(elements=_test_elements()), {"d": "asd"})

    def test_default_value(self) -> None:
        assert vs.Dictionary(elements=_test_elements()).default_value() == {}
        assert vs.Dictionary(
            elements=_test_elements(), required_keys=["a", "c"]
        ).default_value() == {"a": "", "c": "z"}
        assert vs.Dictionary(
            elements=_test_elements(), default_keys=["b", "d"]
        ).default_value() == {
            "b": 0,
            "d": 1,
        }
        assert vs.Dictionary(
            elements=_test_elements(), optional_keys=["a", "b", "c"]
        ).default_value() == {"d": 1}
        assert vs.Dictionary(elements=_test_elements(), optional_keys=False).default_value() == {
            "a": "",
            "b": 0,
            "c": "z",
            "d": 1,
        }

        with pytest.raises(TypeError, match="got an unexpected keyword argument 'default_value'"):
            # default_value was intentionally removed from
            # Dictionary, because it does not have any effect.
            d = vs.Dictionary(  # type: ignore[call-arg]
                elements=_test_elements(), default_value=None
            )
            _ = d.default_value() == {}

    def test_canonical_value(self) -> None:
        assert vs.Dictionary(elements=_test_elements()).canonical_value() == {}
        assert vs.Dictionary(
            elements=_test_elements(), required_keys=["a", "c"]
        ).canonical_value() == {"a": "", "c": ""}
        assert (
            vs.Dictionary(elements=_test_elements(), default_keys=["b", "d"]).canonical_value()
            == {}
        )
        assert vs.Dictionary(
            elements=_test_elements(), optional_keys=["a", "b", "c"]
        ).canonical_value() == {"d": 1}
        assert vs.Dictionary(elements=_test_elements(), optional_keys=False).canonical_value() == {
            "a": "",
            "b": 0,
            "c": "",
            "d": 1,
        }

    def test_from_html_vars(self, request_context: None) -> None:
        with request_var(v_p_a="a", v_p_b="2", v_p_c="c", v_p_d="4"):
            assert vs.Dictionary(elements=_test_elements()).from_html_vars("v") == {}
            assert vs.Dictionary(elements=_test_elements(), optional_keys=False).from_html_vars(
                "v"
            ) == {
                "a": "a",
                "b": 2,
                "c": "c",
                "d": 4,
            }

        with request_var(v_p_a="a", v_p_a_USE="1"):
            assert vs.Dictionary(elements=_test_elements()).from_html_vars("v") == {"a": "a"}

    def test_value_to_html(self) -> None:
        assert vs.Dictionary(elements=_test_elements()).value_to_html({}) == "(no parameters)"
        assert (
            vs.Dictionary(elements=_test_elements(), empty_text="empty").value_to_html({})
            == "empty"
        )
        assert (
            vs.Dictionary(
                elements=_test_elements(), required_keys=["a", "c"], default_text="default"
            ).value_to_html({"a": "", "c": "z"})
            == "default"
        )
        assert vs.Dictionary(elements=_test_elements(), required_keys=["a", "c"]).value_to_html(
            {"a": "", "c": "z"}
        ) == HTML.without_escaping(
            "<table>"
            "<tr>"
            '<td class="title">A:&nbsp;</td><td></td>'
            "</tr><tr>"
            '<td class="title">C:&nbsp;</td><td>******</td>'
            "</tr>"
            "</table>"
        )

    @pytest.mark.parametrize(
        "elements,value,expected",
        [
            ([], {}, {}),
            ([], {"a": 1}, {}),
            ([("a", vs.Integer())], {"a": 1}, {"a": 1}),
            ([("a", vs.Tuple(elements=[]))], {"a": tuple()}, {"a": []}),
        ],
    )
    def test_value_to_json(
        self,
        elements: vs.DictionaryElementsRaw,
        value: dict[str, int | tuple],
        expected: dict[str, tuple | list | int],
    ) -> None:
        assert vs.Dictionary(elements=elements).value_to_json(value) == expected

    def test_value_from_json(self) -> None:
        assert vs.Dictionary(elements=_test_elements()).value_from_json({}) == {}
        assert vs.Dictionary(elements=_test_elements()).value_from_json({"a": "a"}) == {"a": "a"}

    def test_mask(self) -> None:
        assert vs.Dictionary(elements=[("the answer", vs.Password())]).mask(
            {"the answer": "42"}
        ) == {"the answer": "******"}

    def test_transform_value(self) -> None:
        assert vs.Dictionary(
            elements=[
                ("a", vs.TextInput()),
            ]
        ).transform_value({"a": "lala"}) == {"a": "lala"}
