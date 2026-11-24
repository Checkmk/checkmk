#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc import tty


@pytest.fixture(name="uncolored_capsys")
def fixture_uncolored_capsys(capsys: pytest.CaptureFixture[str]) -> pytest.CaptureFixture[str]:
    """capsys without colors, even when stdout was a terminal when importing tty (`pytest -s`)

    The colors stay off afterwards: capsys still captures during the teardown of fixtures.
    """
    tty.reinit()
    return capsys


def test_print_table(uncolored_capsys: pytest.CaptureFixture[str]) -> None:
    tty.print_table(["foo", "bar"], ["", ""], [["Guildo", "Horn"], ["Dieter Thomas", "Kuhn"]])
    captured = uncolored_capsys.readouterr()
    assert captured.out == (
        "foo           bar \n------------- ----\nGuildo        Horn\nDieter Thomas Kuhn\n"
    )
    assert captured.err == ""


def test_print_colored_table(uncolored_capsys: pytest.CaptureFixture[str]) -> None:
    tty.print_table(["foo", "bar"], ["XX", "YY"], [["Angus", "Young"], ["Estas", "Tonne"]])
    captured = uncolored_capsys.readouterr()
    assert captured.out == ("XXfoo  YY bar  \nXX-----YY -----\nXXAngusYY Young\nXXEstasYY Tonne\n")
    assert captured.err == ""


def test_print_indented_colored_table(uncolored_capsys: pytest.CaptureFixture[str]) -> None:
    tty.print_table(
        ["foo", "bar"], ["XX", "YY"], [["Dieter", "Bohlen"], ["Thomas", "Anders"]], indent="===="
    )
    captured = uncolored_capsys.readouterr()
    assert captured.out == (
        "====XXfoo   YY bar   \n"
        "====XX------YY ------\n"
        "====XXDieterYY Bohlen\n"
        "====XXThomasYY Anders\n"
    )
    assert captured.err == ""


def test_print_table_prints_the_rows_of_a_generator(
    uncolored_capsys: pytest.CaptureFixture[str],
) -> None:
    tty.print_table(["foo"], [""], (row for row in [["bar"]]))

    assert uncolored_capsys.readouterr().out == "foo\n---\nbar\n"
