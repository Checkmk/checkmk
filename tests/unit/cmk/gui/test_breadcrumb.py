#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem


def test_breadcrumb_item_creation() -> None:
    i1 = BreadcrumbItem("Title", "index.py", None)
    assert i1.title == "Title"
    assert i1.url == "index.py"


def test_breadcrumb_creation() -> None:
    i1 = BreadcrumbItem("Title1", "index.py", None)

    b = Breadcrumb([i1])
    assert len(b) == 1
    assert b[0].title == "Title1"

    b.append(BreadcrumbItem("Title2", "index.py", None))
    assert len(b) == 2
    assert b[1].title == "Title2"

    b += [
        BreadcrumbItem("Title3", "index.py", None),
        BreadcrumbItem("Title4", "index.py", None),
    ]
    assert isinstance(b, Breadcrumb)
    assert len(b) == 4
    assert b[2].title == "Title3"
    assert b[3].title == "Title4"


def test_breadcrumb_add() -> None:
    i1 = BreadcrumbItem("Title1", "index.py", None)
    b1 = Breadcrumb([i1])

    i2 = BreadcrumbItem("Title2", "index.py", None)
    b2 = Breadcrumb([i2])

    b3 = b1 + b2
    assert len(b1) == 1
    assert len(b2) == 1
    assert len(b3) == 2
