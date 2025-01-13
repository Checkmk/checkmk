#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.tags import TagConfig, TagGroupID, TagID

from cmk.gui.config import active_config
from cmk.gui.painter.v0 import base
from cmk.gui.views import host_tag_plugins


@pytest.mark.usefixtures("load_config")
def test_host_tag_painter_registration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        host_tag_plugins, "painter_registry", painter_registry := base.PainterRegistry()
    )
    monkeypatch.setattr(base, "painter_registry", painter_registry)

    with monkeypatch.context() as m:
        m.setattr(
            active_config,
            "tags",
            TagConfig.from_config(
                {
                    "aux_tags": [],
                    "tag_groups": [
                        {
                            "id": TagGroupID("whoot"),
                            "topic": "Blubberei",
                            "tags": [
                                {
                                    "aux_tags": [],
                                    "id": TagID("bla"),
                                    "title": "Bla",
                                },
                            ],
                            "title": "Whoot",
                        },
                    ],
                }
            ),
        )
        host_tag_plugins.register_tag_plugins()
        assert "host_tag_whoot" in list(base.painter_registry.keys())
