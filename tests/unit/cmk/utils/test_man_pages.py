#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.utils import man_pages

_IF64_MAN_PAGE = man_pages.ManPage(
    name="if64",
    path=Path("/this/path/is/irrelevant/for/the/test/if64"),
    title="Monitor Network Interfaces via Standard MIB Using 64-Bit Counters",
    agents=["snmp"],
    catalog=["hw", "network", "generic"],
    license="GPLv2",
    distribution="check_mk",
    description=(
        "This check does the same as {interfaces} but uses 64-bit counters from\nthe {IF-MIB}"
        " {.1.3.6.1.2.1.31.1.1.1}. This allows to correctly\nmonitor switch ports with a traffic"
        " of more then 2GB per check interval.\n\nAlso, this check can use {ifAlias} instead if"
        " ..."  # shortened for this test
    ),
    item=None,
    discovery=None,
    cluster=None,
)


def _make_checkman_dir(family_dir: Path, *names: str) -> Path:
    (checkman := family_dir / "checkman").mkdir(parents=True)
    for name in names:
        (checkman / name).write_text("", encoding="utf-8")
    return checkman


def test_man_page_path_map_is_not_cached(tmp_path: Path) -> None:
    checkman = _make_checkman_dir(tmp_path, "file1")
    families = {"family": [str(tmp_path)]}
    assert "file2" not in man_pages.make_man_page_path_map(families, "checkman")

    (checkman / "file2").touch()

    assert man_pages.make_man_page_path_map(families, "checkman")["file2"] == checkman / "file2"


def test_man_page_path_map_skips_hidden_and_backup_files(tmp_path: Path) -> None:
    checkman = _make_checkman_dir(tmp_path, ".asd", "asd~", "OWNERS", "if")

    assert man_pages.make_man_page_path_map({"family": [str(tmp_path)]}, "checkman") == {
        "if": checkman / "if"
    }


def test_man_page_path_map_first_family_wins(tmp_path: Path) -> None:
    first = _make_checkman_dir(tmp_path / "first", "if")
    _make_checkman_dir(tmp_path / "second", "if")

    path_map = man_pages.make_man_page_path_map(
        {"first": [str(tmp_path / "first")], "second": [str(tmp_path / "second")]}, "checkman"
    )

    assert path_map["if"] == first / "if"


def test_print_man_page_nowiki_content() -> None:
    content = man_pages.NowikiManPageRenderer(_IF64_MAN_PAGE).render_page()
    assert content.startswith("TI:")
    assert "\nSA:" in content
    assert "License:" in content


def test_print_man_page() -> None:
    rendered = man_pages.ConsoleManPageRenderer(_IF64_MAN_PAGE).render_page()
    assert rendered.startswith(" if64    ")
    assert "\n License: " in rendered


def _broken_man_page(tmp_path: Path) -> Path:
    path = tmp_path / "broken"
    path.write_text("agents: linux\ncatalog: os/misc\n")
    return path


def test_a_broken_man_page_falls_back_to_a_placeholder(tmp_path: Path) -> None:
    man_page = man_pages.parse_man_page("broken", _broken_man_page(tmp_path), debug=False)
    assert man_page.title == "broken: Cannot parse manual page: 'title'"


def test_a_broken_man_page_raises_on_request(tmp_path: Path) -> None:
    with pytest.raises(KeyError):
        man_pages.parse_man_page("broken", _broken_man_page(tmp_path), debug=True)
