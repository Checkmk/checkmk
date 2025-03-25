#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.private import Labels, World
from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor
from cmk.gui.form_specs.vue.visitors._type_defs import VisitorOptions

labels = {"cmk/check_mk_server": "yes"}


def test_labels_can_serialize_to_disk() -> None:
    frontend_visitor = get_visitor(
        Labels(world=World.CORE),
        VisitorOptions(data_origin=DataOrigin.FRONTEND),
    )
    disk_visitor = get_visitor(
        Labels(world=World.CORE),
        VisitorOptions(data_origin=DataOrigin.DISK),
    )

    disk_visitor.to_disk(labels)
    frontend_visitor.to_disk(labels)


def test_labels_pass_validation() -> None:
    frontend_visitor = get_visitor(
        Labels(world=World.CORE),
        VisitorOptions(data_origin=DataOrigin.FRONTEND),
    )
    disk_visitor = get_visitor(
        Labels(world=World.CORE),
        VisitorOptions(data_origin=DataOrigin.DISK),
    )

    assert not disk_visitor.validate(labels)
    assert not frontend_visitor.validate(labels)
