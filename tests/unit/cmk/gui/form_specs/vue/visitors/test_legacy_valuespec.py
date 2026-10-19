#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.form_specs.private import LegacyValueSpec
from cmk.gui.form_specs.vue.visitors import DataOrigin, get_visitor, VisitorOptions
from cmk.gui.valuespec import TextInput


@pytest.mark.xfail(strict=True, raises=TypeError, reason="Crash groups 4397, 4107, 4224: TypeError")
@pytest.mark.usefixtures("request_context")
def test_legacy_valuespec_ignores_file_inputs_sent_as_objects() -> None:
    # Crash groups 4397/4107/4224: the frontend sends file inputs as {} in input_context
    visitor = get_visitor(
        LegacyValueSpec.wrap(TextInput()),
        VisitorOptions(data_origin=DataOrigin.FRONTEND),
    )

    assert (
        visitor.to_disk(
            {"varprefix": "posted", "input_context": {"posted": "foo", "posted_upload": {}}}
        )
        == "foo"
    )
