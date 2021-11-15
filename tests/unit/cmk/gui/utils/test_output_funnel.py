#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List

import pytest

from cmk.gui.http import Response
from cmk.gui.utils.output_funnel import OutputFunnel


def written(funnel) -> bytes:
    return funnel._response_stack[-1].get_data()


def response_texts(funnel: OutputFunnel) -> List[List[str]]:
    return [[e.decode("utf-8") for e in r.iter_encoded()] for r in funnel._response_stack[1:]]


@pytest.fixture(name="funnel")
def fixture_funnel() -> OutputFunnel:
    return OutputFunnel(Response())


def test_output_funnel_not_plugged(funnel: OutputFunnel) -> None:
    funnel.write(b"A")
    assert written(funnel) == b"A"


def test_output_funnel_plugged(funnel: OutputFunnel) -> None:
    with funnel.plugged():
        funnel.write(b"B")
        assert response_texts(funnel) == [["B"]]


def test_output_funnel_2nd_plug(funnel: OutputFunnel) -> None:
    with funnel.plugged():
        funnel.write(b"B")
        assert response_texts(funnel) == [["B"]]
        with funnel.plugged():
            funnel.write(b"C")
            assert response_texts(funnel) == [["B"], ["C"]]
        assert response_texts(funnel) == [["B", "C"]]
    assert written(funnel) == b"BC"


def test_output_funnel_drain(funnel: OutputFunnel) -> None:
    with funnel.plugged():
        funnel.write(b"A")
        text = funnel.drain()
        assert text == "A"

        funnel.write(b"B")
        assert response_texts(funnel) == [["B"]]
    assert written(funnel) == b"B"


def test_output_funnel_context_nesting(funnel: OutputFunnel) -> None:
    funnel.write(b"A")
    assert written(funnel) == b"A"
    with funnel.plugged():
        funnel.write(b"B")
        assert response_texts(funnel) == [["B"]]
        with funnel.plugged():
            funnel.write(b"C")
            assert response_texts(funnel) == [["B"], ["C"]]
        assert response_texts(funnel) == [["B", "C"]]
    assert written(funnel) == b"ABC"


def test_output_funnel_context_drain(funnel: OutputFunnel) -> None:
    funnel.write(b"A")
    assert written(funnel) == b"A"
    with funnel.plugged():
        funnel.write(b"B")
        assert response_texts(funnel) == [["B"]]
        code = funnel.drain()
        assert response_texts(funnel) == [[]]
    assert code == "B"
    assert written(funnel) == b"A"


def test_output_funnel_context_raise(funnel: OutputFunnel) -> None:
    try:
        funnel.write(b"A")
        assert written(funnel) == b"A"
        with funnel.plugged():
            funnel.write(b"B")
            assert response_texts(funnel) == [["B"]]
            raise Exception("Test exception")
    except Exception as e:
        assert "%s" % e == "Test exception"
    finally:
        assert response_texts(funnel) == []


def test_output_funnel_try_finally(funnel: OutputFunnel) -> None:
    try:
        funnel.write(b"try1\n")
        try:
            funnel.write(b"try2\n")
            raise Exception("Error")
        except Exception:
            funnel.write(b"except2\n")
            raise
        finally:
            funnel.write(b"finally2\n")
    except Exception as e:
        funnel.write(b"except1\n")
        funnel.write(str(e).encode("ascii") + b"\n")
    finally:
        funnel.write(b"finally1\n")
    assert written(funnel) == b"try1\ntry2\nexcept2\nfinally2\nexcept1\nError\nfinally1\n"
