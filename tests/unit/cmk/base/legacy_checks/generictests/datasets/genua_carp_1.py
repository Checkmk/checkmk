#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "genua_carp"

info = [[["carp0", "2", "2"], ["carp1", "2", "2"], ["carp2", "1", "0"]], []]

discovery = {"": [("carp0", None), ("carp1", None), ("carp2", None)]}

checks = {
    "": [
        ("carp0", {}, [(0, "Node test: node in carp state master with IfLinkState up", [])]),
        ("carp1", {}, [(0, "Node test: node in carp state master with IfLinkState up", [])]),
        ("carp2", {}, [(1, "Node test: node in carp state init with IfLinkState down", [])]),
    ]
}
