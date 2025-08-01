#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.private import Labels, World
from cmk.gui.form_specs.vue import get_visitor, RawDiskData, RawFrontendData, VisitorOptions

labels = {"cmk/check_mk_server": "yes"}


def test_labels_can_serialize_to_disk() -> None:
    visitor = get_visitor(
        Labels(world=World.CORE), VisitorOptions(migrate_values=True, mask_values=False)
    )
    visitor.to_disk(RawDiskData(labels))
    visitor.to_disk(RawFrontendData(labels))


def test_labels_pass_validation() -> None:
    visitor = get_visitor(
        Labels(world=World.CORE), VisitorOptions(migrate_values=True, mask_values=False)
    )
    assert not visitor.validate(RawDiskData(labels))
    assert not visitor.validate(RawFrontendData(labels))
