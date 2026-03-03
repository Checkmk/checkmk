#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.figures import create_figures_response


@pytest.mark.parametrize(
    "title_url,expected_title_url",
    [
        pytest.param("javascript:alert(1)", None, id="javascript scheme blocked"),
        pytest.param("data:text/html,<script>alert(1)</script>", None, id="data scheme blocked"),
        pytest.param("vbscript:msgbox(1)", None, id="vbscript scheme blocked"),
        pytest.param("http://example.com", "http://example.com", id="http allowed"),
        pytest.param("https://example.com", "https://example.com", id="https allowed"),
        pytest.param(
            "view.py?view_name=allhosts", "view.py?view_name=allhosts", id="relative URL allowed"
        ),
        pytest.param(None, None, id="None passthrough"),
    ],
)
def test_create_figures_response_sanitizes_title_url(
    title_url: str | None, expected_title_url: str | None
) -> None:
    data = {"title": "Test", "title_url": title_url}
    response = create_figures_response(data)
    assert response["figure_response"]["title_url"] == expected_title_url


def test_create_figures_response_without_title_url() -> None:
    data = {"title": "Test"}
    response = create_figures_response(data)
    assert "title_url" not in response["figure_response"]


def test_create_figures_response_non_dict_data() -> None:
    data = [1, 2, 3]
    response = create_figures_response(data)
    assert response["figure_response"] == [1, 2, 3]
