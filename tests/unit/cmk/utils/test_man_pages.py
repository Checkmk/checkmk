#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest  # type: ignore[import]

from testlib.utils import cmk_path

import cmk.utils.debug
import cmk.utils.man_pages as man_pages
from cmk.utils.type_defs import CheckPluginName

import cmk.base.api.agent_based.register as agent_based_register

# TODO: Add tests for module internal functions


@pytest.fixture(autouse=True)
def patch_cmk_paths(monkeypatch, tmp_path):
    monkeypatch.setattr("cmk.utils.paths.local_check_manpages_dir", tmp_path)


@pytest.fixture(scope="module", name="all_pages")
def _get_all_pages():
    return {name: man_pages.load_man_page(name) for name in man_pages.all_man_pages()}


@pytest.fixture(scope="module", name="catalog")
def _get_catalog():
    return man_pages.load_man_page_catalog()


def test_man_page_exists_only_shipped():
    assert man_pages.man_page_exists("if64") is True
    assert man_pages.man_page_exists("not_existant") is False


def test_man_page_exists_both_dirs(tmp_path):
    f1 = tmp_path / "file1"
    f1.write_text(u"x", encoding="utf-8")

    assert man_pages.man_page_exists("file1") is True
    assert man_pages.man_page_exists("file2") is False

    f2 = tmp_path / "if"
    f2.write_text(u"x", encoding="utf-8")

    assert man_pages.man_page_exists("if") is True


def test_man_page_path_only_shipped():
    assert man_pages.man_page_path("if64") == Path(cmk_path()) / "checkman" / "if64"
    assert man_pages.man_page_path("not_existant") is None


def test_man_page_path_both_dirs(tmp_path):
    f1 = tmp_path / "file1"
    f1.write_text(u"x", encoding="utf-8")

    assert man_pages.man_page_path("file1") == tmp_path / "file1"
    assert man_pages.man_page_path("file2") is None

    f2 = tmp_path / "if"
    f2.write_text(u"x", encoding="utf-8")

    assert man_pages.man_page_path("if") == tmp_path / "if"


def test_all_manpages_migrated(all_pages):
    for name in all_pages:
        if name in ("check-mk-inventory", "check-mk"):
            continue
        assert CheckPluginName(name)


def test_all_man_pages(tmp_path):
    (tmp_path / ".asd").write_text(u"", encoding="utf-8")
    (tmp_path / "asd~").write_text(u"", encoding="utf-8")
    (tmp_path / "if").write_text(u"", encoding="utf-8")

    pages = man_pages.all_man_pages()

    assert len(pages) > 1241
    assert ".asd" not in pages
    assert "asd~" not in pages

    assert pages["if"] == str(tmp_path / "if")
    assert pages["if64"] == "%s/checkman/if64" % cmk_path()


def test_load_all_man_pages(all_pages):
    for name, man_page in all_pages.items():
        assert man_page is not None, name
        assert isinstance(man_page, dict)
        _check_man_page_structure(man_page)


def test_print_man_page_table(capsys):
    man_pages.print_man_page_table()
    out, err = capsys.readouterr()
    assert err == ""

    lines = out.split("\n")

    assert len(lines) > 1241
    assert "enterasys_powersupply" in out
    assert "IBM Websphere MQ: Channel Message Count" in out


def man_page_catalog_titles():
    titles = man_pages.man_page_catalog_titles()
    assert isinstance(titles, dict)
    assert "hw" in titles
    assert "os" in titles


def test_load_man_page_catalog():
    catalog = man_pages.load_man_page_catalog()
    assert isinstance(catalog, dict)

    for path, entries in catalog.items():
        assert isinstance(path, tuple)
        assert isinstance(entries, list)

        # TODO: Test for unknown paths?

        for entry in entries:
            assert isinstance(entry, dict)

            # Test for non fallback man pages
            assert "Cannot parse man page" not in entry["title"]


def test_no_unsorted_man_pages():
    catalog = man_pages.load_man_page_catalog()
    unsorted_page_names = [m["name"] for m in catalog.get(("unsorted",), [])]

    assert not unsorted_page_names, "Found unsorted man pages: %s" % ", ".join(unsorted_page_names)


def test_manpage_files(all_pages):
    assert len(all_pages) > 1000


def _is_pure_section_declaration(check):
    '''return true if and only if the check never generates a service'''
    return check.get('inventory_function') is None and check.get('check_function') is None


def test_find_missing_manpages_passive(registered_check_plugins, all_pages):
    for plugin_name in registered_check_plugins:
        assert str(plugin_name) in all_pages, "Manpage missing: %s" % plugin_name


def test_find_missing_manpages_active(config_active_check_info, all_pages):
    for plugin_name in ("check_%s" % n for n in config_active_check_info):
        assert plugin_name in all_pages, "Manpage missing: %s" % plugin_name


def test_find_missing_manpages_cluster_section(registered_check_plugins, all_pages):
    missing_cluster_description = set()
    for plugin in registered_check_plugins.values():
        if plugin.cluster_check_function.__name__ in (
                "unfit_for_clustering",
                "cluster_legacy_mode_from_hell",
        ):
            continue
        man_page = all_pages[str(plugin.name)]
        assert man_page
        if "cluster" not in man_page["header"]:
            missing_cluster_description.add(str(plugin.name))

    assert not missing_cluster_description


def test_no_subtree_and_entries_on_same_level(catalog):
    for category, entries in catalog.items():
        has_entries = entries != []
        has_categories = man_pages._manpage_catalog_subtree_names(catalog, category) != []
        assert has_entries != has_categories, "A category must only have entries or categories, not both"


# TODO: print_man_page_browser()


def test_load_man_page_not_existing():
    assert man_pages.load_man_page("not_existing") is None


def _check_man_page_structure(page):
    for key in ["header"]:
        assert key in page

    for key in ['description', 'license', 'title', 'catalog', 'agents', 'distribution']:
        assert key in page["header"]

    if "configuration" in page:
        assert isinstance(page["configuration"], list)

    if "parameters" in page:
        assert isinstance(page["parameters"], list)

    if "inventory" in page:
        assert isinstance(page["inventory"], list)

    assert isinstance(page["header"]["agents"], list)


def test_load_man_page_format(all_pages):
    page = all_pages["if64"]
    assert isinstance(page, dict)

    _check_man_page_structure(page)

    # Check optional keys
    for key in ['item', 'inventory']:
        assert key in page["header"]


def test_print_man_page_nowiki_index(capsys):
    renderer = man_pages.NowikiManPageRenderer("if64")
    index_entry = renderer.index_entry()
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""

    assert "<tr>" in index_entry
    assert "[check_if64|" in index_entry


def test_print_man_page_nowiki_content(capsys):
    renderer = man_pages.NowikiManPageRenderer("if64")
    content = renderer.render()
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""

    assert content.startswith("TI:")
    assert "\nSA:" in content
    assert "License:" in content


def test_print_man_page(capsys):
    man_pages.ConsoleManPageRenderer("if64").paint()
    out, err = capsys.readouterr()
    assert err == ""

    assert out.startswith(" if64    ")
    assert "\n License: " in out


def test_missing_catalog_entries_of_man_pages(all_pages) -> None:
    catalog_titles = set(man_pages.catalog_titles.keys())
    found_catalog_entries_from_man_pages = set()
    for name in man_pages.all_man_pages():
        man_page = all_pages[name]
        assert man_page is not None
        found_catalog_entries_from_man_pages |= set(man_page['header']['catalog'].split("/"))
    missing_catalog_entries = found_catalog_entries_from_man_pages - catalog_titles
    assert missing_catalog_entries == set(), "Found missing catalog entries: %s" % ", ".join(
        sorted(missing_catalog_entries))
