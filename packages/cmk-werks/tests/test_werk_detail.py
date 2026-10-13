#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Container, Sequence

import lxml.html
import pytest

from cmk.web.page_container import PageContainer, PageMenuLink
from cmk.werks.tool import load_werk
from cmk.werks.tool.models import WerkV3
from cmk.werks.web.werk_detail import render_werk_detail

from ._werk_files import werk_text


def _werk(werk_id: int = 1234, *, title: str = "A werk title", compatible: str = "yes") -> WerkV3:
    return load_werk(
        file_content=werk_text(title=title, compatible=compatible), file_name=f"{werk_id}.md"
    )


def _render(
    werk: WerkV3,
    *,
    acknowledged: bool = False,
    acknowledge_url: str | None = None,
    known_checks: Container[str] = frozenset(),
) -> PageContainer:
    return render_werk_detail(
        werk,
        acknowledged=acknowledged,
        acknowledge_url=acknowledge_url,
        known_checks=lambda: known_checks,
        i18n=str,
    )


def _cell(page: PageContainer, caption: str) -> lxml.html.HtmlElement:
    cell = lxml.html.fromstring(page.content).find(f".//tr[th='{caption}']/td")
    if cell is None:
        raise AssertionError(f"the werk page has no {caption} row")
    return cell


def _acknowledge_entries(page: PageContainer) -> Sequence[PageMenuLink]:
    if page.page_menu is None:
        raise AssertionError("the werk page has no page menu")
    return page.page_menu.dropdowns[0].topics[0].entries


def test_the_page_is_titled_with_the_werk_id_and_title() -> None:
    assert _render(_werk()).title == "Werk #1234 - A werk title"


def test_the_class_is_styled_by_the_werk_class() -> None:
    cell = _cell(_render(_werk()), "Class")

    assert (cell.text_content(), cell.get("class")) == ("Bug fix", "werkclass werkclassfix")


@pytest.mark.parametrize(
    "compatible, acknowledged, expected",
    [
        pytest.param("yes", False, ("Compatible", "werkcomp werkcompcompat"), id="compatible"),
        pytest.param(
            "yes",
            True,
            ("Compatible", "werkcomp werkcompcompat"),
            id="compatible-though-acknowledged",
        ),
        pytest.param(
            "no", True, ("Incompatible", "werkcomp werkcompincomp_ack"), id="acknowledged"
        ),
        pytest.param(
            "no",
            False,
            ("Incompatible - TODO", "werkcomp werkcompincomp_unack"),
            id="unacknowledged",
        ),
    ],
)
def test_the_compatibility_tells_whether_an_incompatible_werk_is_acknowledged(
    compatible: str, acknowledged: bool, expected: tuple[str, str]
) -> None:
    cell = _cell(_render(_werk(compatible=compatible), acknowledged=acknowledged), "Compatibility")

    assert (cell.text_content(), cell.get("class")) == expected


def test_the_description_is_rendered_as_html() -> None:
    assert _cell(_render(_werk()), "Description").findtext("p") == "A description."


def test_check_plugins_named_in_the_title_link_to_their_man_pages() -> None:
    title = _cell(_render(_werk(title="df, mem: Fix the unit"), known_checks={"df"}), "Title")

    assert [(link.text, link.get("href")) for link in title.iter("a")] == [
        ("df", "wato.py?mode=check_manpage&check_type=df")
    ]


def test_an_unacknowledged_werk_can_be_acknowledged() -> None:
    page = _render(_werk(compatible="no"), acknowledge_url="change_log.py?_werk_ack=1234")

    assert _acknowledge_entries(page) == [
        PageMenuLink(
            title="Acknowledge",
            icon_name="werk-ack",
            url="change_log.py?_werk_ack=1234",
            is_enabled=True,
            is_shortcut=True,
            is_suggested=True,
        )
    ]


def test_an_acknowledged_werk_cannot_be_acknowledged_again() -> None:
    page = _render(
        _werk(compatible="no"), acknowledged=True, acknowledge_url="change_log.py?_werk_ack=1234"
    )

    assert [entry.is_enabled for entry in _acknowledge_entries(page)] == [False]


def test_acknowledging_is_not_offered_without_the_permission() -> None:
    assert _acknowledge_entries(_render(_werk(compatible="no"))) == []
