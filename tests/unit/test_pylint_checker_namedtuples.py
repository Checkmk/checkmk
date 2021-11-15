#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, Tuple

import astroid  # type: ignore[import]
import pytest

from tests.testlib.pylint_checker_forbidden_functions import (
    TypingNamedTupleChecker,  # type: ignore[import]
)


@pytest.fixture(name="namedtuple_checker")
def namedtuple_checker_fixture() -> TypingNamedTupleChecker:
    return TypingNamedTupleChecker(None)


@pytest.mark.parametrize(
    ["import_code", "call_code", "ref_value"],
    [
        ("from typing import NamedTuple #@", """s =NamedTuple("s",[]) #@ """, True),
        ("from typing import NamedTuple as nt #@", """ s=nt("s", []) #@""", True),
        ("from typing import NamedTuple #@", """NamedTuple("s", []) #@""", True),
        ("from somelibrary import NamedTuple #@", """NamedTuple("s", []) #@""", False),
        (
            "from typing import NamedTuple #@",
            """ class Employee(NamedTuple): i:int #@ """,
            False,
        ),
        ("from somelib.typing import NamedTuple #@", """ NamedTuple("s", []) #@ """, True),
        ("from something import somefct as NamedTuple #@", """NamedTuple("s", []) #@""", False),
        ("from typing import NamedTuple as nt #@", """ class Employee(nt): i:int #@ """, False),
    ],
)
def test_import_from_typing(
    import_code: str, call_code: str, ref_value: bool, namedtuple_checker: TypingNamedTupleChecker
) -> None:
    node = astroid.extract_node(import_code)
    namedtuple_checker.visit_importfrom(node)
    node = astroid.extract_node(call_code)
    assert (
        namedtuple_checker._visit_call(
            node.value if isinstance(node, astroid.node_classes.Assign) else node
        )
        is ref_value
    )


@pytest.mark.parametrize(
    ["import_code", "call_code", "ref_value"],
    [
        ("import typing #@", """ s=typing.NamedTuple("s",[]) #@ """, True),
        ("import typing as tp #@", """s=tp.NamedTuple("s",[]) #@""", True),
        ("import something #@", """ s=something.NamedTuple("s", []) #@""", False),
        ("import typing #@", """ typing.NamedTuple("s", []) #@""", True),
        ("import something #@", """ something.NamedTuple("s", []) #@""", False),
        ("import typing #@", """ class Employee(typing.NamedTuple): i:int #@ """, False),
        ("import something #@", """ class Employee(something.NamedTuple): i:int #@ """, False),
        (
            "import something.typing #@",
            """ class Employee(something.typing.NamedTuple): i:int #@ """,
            False,
        ),
        (
            "import typing as something #@",
            """ class Employee(something.NamedTuple): i:int #@ """,
            False,
        ),
    ],
)
def test_import_typing(
    import_code: str, call_code: str, ref_value: bool, namedtuple_checker: TypingNamedTupleChecker
) -> None:
    node = astroid.extract_node(import_code)
    namedtuple_checker.visit_import(node)
    node = astroid.extract_node(call_code)
    assert (
        namedtuple_checker._visit_call(
            node.value if isinstance(node, astroid.node_classes.Assign) else node
        )
        is ref_value
    )


@pytest.mark.parametrize(
    "modules",
    [
        [
            ("import typing #@", """ s=typing.NamedTuple("s",[]) #@ """, True),
            ("import typing as tp #@", """s=tp.NamedTuple("s",[]) #@""", True),
            ("import something #@", """ s=something.NamedTuple("s", []) #@""", False),
            ("import typing #@", """ typing.NamedTuple("s", []) #@""", True),
            ("import something #@", """ something.NamedTuple("s", []) #@""", False),
            ("import typing #@", """ class Employee(typing.NamedTuple): i:int #@ """, False),
            ("import something #@", """ class Employee(something.NamedTuple): i:int #@ """, False),
            (
                "import something.typing #@",
                """ class Employee(something.typing.NamedTuple): i:int #@ """,
                False,
            ),
            (
                "import typing as something #@",
                """ class Employee(something.NamedTuple): i:int #@ """,
                False,
            ),
        ]
    ],
)
def test_multiple_modules_typing(
    namedtuple_checker: TypingNamedTupleChecker, modules: Iterable[Tuple[str, str, bool]]
) -> None:
    for import_code, call_code, ref_value in modules:
        node = astroid.extract_node(import_code)
        node.parent = astroid.Module("module ", None)
        namedtuple_checker.visit_module(node.parent)
        namedtuple_checker.visit_import(node)
        node = astroid.extract_node(call_code)
        assert (
            namedtuple_checker._visit_call(
                node.value if isinstance(node, astroid.node_classes.Assign) else node
            )
            is ref_value
        )
