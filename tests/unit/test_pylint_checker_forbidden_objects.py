#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, Tuple

import astroid  # type: ignore[import]
import pytest

from tests.testlib.pylint_checker_forbidden_objects import (
    ABCMetaChecker,
    ForbiddenFunctionChecker,
    SixEnsureStrBinChecker,
    TypingNamedTupleChecker,
)


@pytest.fixture(name="abcmeta_checker")
def abcmeta_checker_fixture() -> ABCMetaChecker:
    return ABCMetaChecker(None)


@pytest.fixture(name="namedtuple_checker")
def namedtuple_checker_fixture() -> TypingNamedTupleChecker:
    return TypingNamedTupleChecker(None)


class _TestChecker(ForbiddenFunctionChecker):
    name = "test_checker"
    target_lib = "testlib"
    target_objects = frozenset(["test1", "test2"])
    mgs = {"E9210": ("Checker for test purposes", "test_checker", "Checker only for test purposes")}


@pytest.fixture(name="test_checker")
def test_checker_fixture() -> _TestChecker:
    return _TestChecker(None)


@pytest.fixture(name="six_checker")
def six_checker_fixture() -> SixEnsureStrBinChecker:
    return SixEnsureStrBinChecker(None)


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


@pytest.mark.parametrize(
    ["import_code", "call_code", "ref_value"],
    [
        ("from testlib import test1 #@", """s =test1() #@ """, True),
        ("from testlib import test2  #@", """ s=test2() #@""", True),
        ("from testlib import test1 #@", """ test2() #@""", False),
        ("from testlib import test1, test2 #@", "test1() #@", True),
        ("from testlib import test1, test2 #@", "test2() #@", True),
    ],
)
def test_multiple_fcts(
    import_code: str, call_code: str, ref_value: bool, test_checker: _TestChecker
) -> None:
    node = astroid.extract_node(import_code)
    test_checker.visit_importfrom(node)
    node = astroid.extract_node(call_code)
    val = test_checker._visit_call(
        node.value if isinstance(node, astroid.node_classes.Assign) else node
    )

    assert val is ref_value


@pytest.mark.parametrize(
    ["import_code", "call_code", "ref_value"],
    [
        ("import typing #@", """ map(typing.NamedTuple, something) #@ """, True),
        ("import something #@", "map(something.NamedTuple, smth) #@", False),
    ],
)
def test_function_as_argument_attribute(
    import_code: str, call_code: str, ref_value: bool, namedtuple_checker: TypingNamedTupleChecker
) -> None:
    node = astroid.extract_node(import_code)
    namedtuple_checker.visit_import(node)
    node = astroid.extract_node(call_code)
    value = False
    for arg in node.args:
        if namedtuple_checker._called_with_library(arg) or namedtuple_checker._called_directly(arg):
            value = True
    assert value is ref_value


@pytest.mark.parametrize(
    ["import_code", "call_code", "ref_value"],
    [
        ("from typing import NamedTuple #@", """ map(NamedTuple, something) #@ """, True),
        ("from something import NamedTuple #@", "map(NamedTuple, smth) #@", False),
    ],
)
def test_function_as_argument_name(
    import_code: str, call_code: str, ref_value: bool, namedtuple_checker: TypingNamedTupleChecker
) -> None:
    node = astroid.extract_node(import_code)
    namedtuple_checker.visit_importfrom(node)
    node = astroid.extract_node(call_code)
    value = False
    for arg in node.args:
        if namedtuple_checker._called_with_library(arg) or namedtuple_checker._called_directly(arg):
            value = True
    assert value is ref_value


@pytest.mark.parametrize(
    "modules",
    [
        [
            ("from six import ensure_str #@", """s =ensure_str("s") #@ """, True),
            ("from six import ensure_str #@", """s =ensure_str("s") #@ """, True),
            ("from six import ensure_binary  #@", """ s=ensure_binary("s") #@""", True),
            ("from six import ensure_str #@", """ ensure_binary("s") #@""", False),
            ("from six import ensure_str, ensure_binary #@", "ensure_binary(1) #@", True),
            ("from six import ensure_str, ensure_binary #@", "ensure_str(1) #@", True),
        ]
    ],
)
def test_multiple_modules_multiple_functions(
    six_checker: SixEnsureStrBinChecker, modules: Iterable[Tuple[str, str, bool]]
) -> None:
    for import_code, call_code, ref_value in modules:
        node = astroid.extract_node(import_code)
        node.parent = astroid.Module("module ", None)
        six_checker.visit_module(node.parent)
        six_checker.visit_importfrom(node)
        node = astroid.extract_node(call_code)
        assert (
            six_checker._visit_call(
                node.value if isinstance(node, astroid.node_classes.Assign) else node
            )
            is ref_value
        )


@pytest.mark.parametrize(
    ["call_code", "ref_value"],
    [
        (
            """
from abc import ABCMeta
class b(metaclass=ABCMeta): #@
    pass
""",
            True,
        ),
        (
            """
from abc import ABCMeta as k
class b(metaclass=k): #@
    pass
""",
            True,
        ),
        (
            """
ABCMeta=type
class b(metaclass=ABCMeta): #@
    pass
""",
            False,
        ),
        (
            """
class b(ABC): #@
    pass
""",
            False,
        ),
        (
            """
from abc import ABCMeta
k=ABCMeta
class a(metaclass=k): #@
    pass
""",
            True,
        ),
        (
            """
from abc import smth
class a(metaclass=smth): #@
    pass
""",
            False,
        ),
    ],
)
def test_abcmeta_usage(call_code: str, ref_value: bool, abcmeta_checker: ABCMetaChecker) -> None:
    node = astroid.extract_node(call_code)
    assert abcmeta_checker._visit_classdef(node) is ref_value
