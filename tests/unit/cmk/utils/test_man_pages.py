#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Mapping, Optional, Set

import pytest

from tests.testlib.utils import cmk_path, cpe_path

from tests.unit.conftest import FixPluginLegacy, FixRegister

import cmk.utils.man_pages as man_pages
from cmk.utils.type_defs import CheckPluginName

ManPages = Mapping[str, Optional[man_pages.ManPage]]


@pytest.fixture(autouse=True)
def patch_man_page_dir_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(
        man_pages,
        "_get_man_page_dirs",
        lambda: [
            tmp_path,
            Path(cpe_path(), "checkman"),
            Path(cmk_path(), "checkman"),
        ],
    )


@pytest.fixture(scope="module", name="all_pages")
def get_all_pages() -> ManPages:
    base_dirs = [
        Path(cpe_path(), "checkman"),
        Path(cmk_path(), "checkman"),
    ]
    return {
        name: man_pages.load_man_page(name, base_dirs)
        for name in man_pages.all_man_pages(base_dirs)
    }


@pytest.fixture(scope="module", name="catalog")
def get_catalog() -> man_pages.ManPageCatalog:
    return man_pages.load_man_page_catalog()


def test_man_page_path_only_shipped() -> None:
    assert man_pages.man_page_path("if64") == Path(cmk_path()) / "checkman" / "if64"
    assert man_pages.man_page_path("not_existant") is None


def test_man_page_path_both_dirs(tmp_path) -> None:
    f1 = tmp_path / "file1"
    f1.write_text("x", encoding="utf-8")

    assert man_pages.man_page_path("file1") == tmp_path / "file1"
    assert man_pages.man_page_path("file2") is None

    f2 = tmp_path / "if"
    f2.write_text("x", encoding="utf-8")

    assert man_pages.man_page_path("if") == tmp_path / "if"


def test_all_manpages_migrated(all_pages: ManPages) -> None:
    for name in all_pages:
        if name in ("check-mk-inventory", "check-mk"):
            continue
        assert CheckPluginName(name)


def test_all_man_pages(tmp_path) -> None:
    (tmp_path / ".asd").write_text("", encoding="utf-8")
    (tmp_path / "asd~").write_text("", encoding="utf-8")
    (tmp_path / "if").write_text("", encoding="utf-8")

    pages = man_pages.all_man_pages()

    assert len(pages) > 1241
    assert ".asd" not in pages
    assert "asd~" not in pages

    assert pages["if"] == str(tmp_path / "if")
    assert pages["if64"] == "%s/checkman/if64" % cmk_path()


def test_load_all_man_pages(all_pages: ManPages) -> None:
    for _name, man_page in all_pages.items():
        assert isinstance(man_page, man_pages.ManPage)


def test_print_man_page_table(capsys) -> None:
    man_pages.print_man_page_table()
    out, err = capsys.readouterr()
    assert err == ""

    lines = out.split("\n")

    assert len(lines) > 1241
    assert "enterasys_powersupply" in out
    assert "IBM Websphere MQ: Channel Message Count" in out


def man_page_catalog_titles():
    assert man_pages.CATALOG_TITLES["hw"]
    assert man_pages.CATALOG_TITLES["os"]


def test_load_man_page_catalog(catalog) -> None:
    assert isinstance(catalog, dict)

    for path, entries in catalog.items():
        assert isinstance(path, tuple)
        assert isinstance(entries, list)

        # TODO: Test for unknown paths?

        # Test for non fallback man pages
        assert not any("Cannot parse man page" in e.title for e in entries)


def test_no_unsorted_man_pages(catalog: man_pages.ManPageCatalog) -> None:
    unsorted_page_names = [m.name for m in catalog.get(("unsorted",), [])]

    assert not unsorted_page_names


def test_manpage_files(all_pages: ManPages) -> None:
    assert len(all_pages) > 1000


def test_find_missing_manpages_passive(fix_register: FixRegister, all_pages: ManPages) -> None:
    for plugin_name in fix_register.check_plugins:
        assert str(plugin_name) in all_pages, "Manpage missing: %s" % plugin_name


def test_find_missing_manpages_active(
    fix_plugin_legacy: FixPluginLegacy, all_pages: ManPages
) -> None:
    for plugin_name in ("check_%s" % n for n in fix_plugin_legacy.active_check_info):
        assert plugin_name in all_pages, "Manpage missing: %s" % plugin_name


def test_find_missing_plugins(
    fix_register: FixRegister,
    fix_plugin_legacy: FixPluginLegacy,
    all_pages: ManPages,
) -> None:
    missing_plugins = (
        set(all_pages)
        - set(str(plugin_name) for plugin_name in fix_register.check_plugins)
        - set(f"check_{name}" for name in fix_plugin_legacy.active_check_info)
        - {
            "check-mk",
            "check-mk-inventory",
        }
    )
    assert (
        not missing_plugins
    ), f"The following manpages have no corresponding plugins: {', '.join(missing_plugins)}"


def test_cluster_check_functions_match_manpages_cluster_sections(
    fix_register: FixRegister,
    all_pages: ManPages,
):
    missing_cluster_description: Set[str] = set()
    unexpected_cluster_description: Set[str] = set()

    for plugin in fix_register.check_plugins.values():
        man_page = all_pages[str(plugin.name)]
        assert man_page
        has_cluster_doc = bool(man_page.cluster)
        has_cluster_func = plugin.cluster_check_function is not None
        if has_cluster_doc is not has_cluster_func:
            (missing_cluster_description, unexpected_cluster_description,)[
                has_cluster_doc
            ].add(str(plugin.name))

    assert not missing_cluster_description
    assert not unexpected_cluster_description


def test_no_subtree_and_entries_on_same_level(catalog) -> None:
    for category, entries in catalog.items():
        has_entries = entries != []
        has_categories = man_pages._manpage_catalog_subtree_names(catalog, category) != []
        assert (
            has_entries != has_categories
        ), "A category must only have entries or categories, not both"


# TODO: print_man_page_browser()


def test_load_man_page_not_existing() -> None:
    assert man_pages.load_man_page("not_existing") is None


def test_print_man_page_nowiki_index(capsys) -> None:
    renderer = man_pages.NowikiManPageRenderer("if64")
    index_entry = renderer.index_entry()
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""

    assert "<tr>" in index_entry
    assert "[check_if64|" in index_entry


def test_print_man_page_nowiki_content(capsys) -> None:
    renderer = man_pages.NowikiManPageRenderer("if64")
    content = renderer.render()
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""

    assert content.startswith("TI:")
    assert "\nSA:" in content
    assert "License:" in content


def test_print_man_page(capsys) -> None:
    man_pages.ConsoleManPageRenderer("if64").paint()
    out, err = capsys.readouterr()
    assert err == ""

    assert out.startswith(" if64    ")
    assert "\n License: " in out


def test_missing_catalog_entries_of_man_pages(all_pages: ManPages) -> None:
    found_catalog_entries_from_man_pages: set[str] = set()
    for name in man_pages.all_man_pages():
        man_page = all_pages[name]
        assert man_page is not None
        found_catalog_entries_from_man_pages.update(man_page.catalog)
    missing_catalog_entries = found_catalog_entries_from_man_pages - set(man_pages.CATALOG_TITLES)
    assert not missing_catalog_entries
