#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.gui.wato.pages.sites import StatusHostFormSpecAdapter

ADAPTER = StatusHostFormSpecAdapter(SiteConfigurations({}))


@pytest.mark.parametrize(
    "model",
    [
        None,
        (SiteId("central"), "myhost"),
    ],
)
def test_status_host_round_trip(model: tuple[SiteId, str] | None) -> None:
    assert ADAPTER.from_form_spec(ADAPTER.to_form_spec(model)) == model


def test_status_host_to_form_spec() -> None:
    assert ADAPTER.to_form_spec(None) == ("disabled", None)
    assert ADAPTER.to_form_spec((SiteId("central"), "myhost")) == (
        "enabled",
        (SiteId("central"), "myhost"),
    )


def test_status_host_from_form_spec_accepts_list_payload() -> None:
    # Parsed frontend data may carry the inner pair as a list
    assert ADAPTER.from_form_spec(("enabled", ["central", "myhost"])) == (
        SiteId("central"),
        "myhost",
    )


def test_status_host_from_form_spec_rejects_unknown_shape() -> None:
    with pytest.raises(ValueError):
        ADAPTER.from_form_spec(("central", "myhost"))
