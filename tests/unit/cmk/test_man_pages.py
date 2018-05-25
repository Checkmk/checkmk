import pytest
import os

from testlib import cmk_path

import cmk.man_pages as man_pages
import cmk_base.checks as checks

# TODO: Add tests for module internal functions

@pytest.fixture(autouse=True)
def patch_cmk_paths(monkeypatch, tmpdir):
    monkeypatch.setattr("cmk.paths.local_check_manpages_dir", "%s" % tmpdir)

def test_man_page_exists_only_shipped():
    assert man_pages.man_page_exists("if64") == True
    assert man_pages.man_page_exists("not_existant") == False


def test_man_page_exists_both_dirs(tmpdir):
    f1 = tmpdir.join("file1")
    f1.write("x")

    assert man_pages.man_page_exists("file1") == True
    assert man_pages.man_page_exists("file2") == False

    f2 = tmpdir.join("if")
    f2.write("x")

    assert man_pages.man_page_exists("if") == True


def test_man_page_path_only_shipped():
    assert man_pages.man_page_path("if64") == "%s/checkman/if64" % cmk_path()
    assert man_pages.man_page_path("not_existant") == None


def test_man_page_path_both_dirs(tmpdir):
    f1 = tmpdir.join("file1")
    f1.write("x")

    assert man_pages.man_page_path("file1") == "%s/file1" % tmpdir
    assert man_pages.man_page_path("file2") == None

    f2 = tmpdir.join("if")
    f2.write("x")

    assert man_pages.man_page_path("if") == "%s/if" % tmpdir


def test_all_man_pages(tmpdir):
    f1 = tmpdir.join(".asd").write("")
    f2 = tmpdir.join("asd~").write("")
    f3 = tmpdir.join("if").write("")

    pages = man_pages.all_man_pages()

    assert len(pages) > 1241
    assert ".asd" not in pages
    assert "asd~" not in pages

    assert pages["if"] == "%s/if" % tmpdir
    assert pages["if64"] == "%s/checkman/if64" % cmk_path()


def test_load_all_man_pages():
    for name in man_pages.all_man_pages().keys():
        man_page = man_pages.load_man_page(name)
        assert type(man_page) == dict
        _check_man_page_structure(man_page)


def test_print_man_page_table(capsys):
    man_pages.print_man_page_table()
    out, err = capsys.readouterr()
    assert err == ""

    lines = out.split("\n")

    assert len(lines) > 1241
    assert "enterasys_powersupply" in out
    assert "IBM Websphere MQ Channel Message count" in out


def man_page_catalog_titles():
    titles = man_pages.man_page_catalog_titles()
    assert type(titles) == dict
    assert "hw" in titles
    assert "os" in titles


def test_load_man_page_catalog():
    catalog = man_pages.load_man_page_catalog()
    assert type(catalog) == dict

    for path, entries in catalog.items():
        assert type(path) == tuple
        assert type(entries) == list

        # TODO: Test for unknown paths?

        for entry in entries:
            type(entry) == dict

            # Test for non fallback man pages
            assert "Cannot parse man page" not in entry["title"]


def test_no_unsorted_man_pages():
    catalog = man_pages.load_man_page_catalog()
    unsorted_page_names = [ m["name"] for m in catalog.get(("unsorted", ), []) ]

    assert not unsorted_page_names, "Found unsorted man pages: %s" % ", ".join(unsorted_page_names)


def test_manpage_catalog_headers():
    for name, path in man_pages.all_man_pages().items():
        try:
            parsed = man_pages._parse_man_page_header(name, path)
        except Exception, e:
            if cmk.debug.enabled():
                raise
            parsed = man_pages._create_fallback_man_page(name, path, e)

        assert parsed.get("catalog"), "Did not find \"catalog:\" header in man page \"%s\"" % name


def test_manpage_files():
    manuals = man_pages.all_man_pages()
    assert len(manuals) > 1000


def _is_pure_section_declaration(check):
    '''return true if and only if the check never generates a service'''
    return (check.get('inventory_function') is None and
            check.get('check_function') is None)


def test_find_missing_manpages():
    all_check_manuals = man_pages.all_man_pages()

    checks.load()
    checks_sorted = [ (name, entry) for (name, entry) in checks.check_info.items()
                      if not _is_pure_section_declaration(entry) ] + \
       [ ("check_" + name, entry) for (name, entry) in checks.active_check_info.items() ]
    checks_sorted.sort()
    assert len(checks_sorted) > 1000

    for check_plugin_name, check in checks_sorted:
        assert check_plugin_name in all_check_manuals, "Manpage missing: %s" % check_plugin_name


def test_no_subtree_and_entries_on_same_level():
    catalog = man_pages.load_man_page_catalog()
    for category, entries in catalog.items():
        has_entries    = entries != []
        has_categories = man_pages._manpage_catalog_subtree_names(catalog, category) != []
        assert has_entries != has_categories, "A category must only have entries or categories, not both"


# TODO: print_man_page_browser()


def test_load_man_page_not_existing():
    assert man_pages.load_man_page("not_existing") == None


def _check_man_page_structure(page):
    for key in [ "header" ]:
        assert key in page

    for key in [ 'description', 'license', 'title',
                 'catalog', 'agents',
                 'distribution']:
        assert key in page["header"]

    if "configuration" in page:
       assert type(page["configuration"]) == list

    if "parameters" in page:
        assert type(page["parameters"]) == list

    if "inventory" in page:
        assert type(page["inventory"]) == list

    assert type(page["header"]["agents"]) == list


def test_load_man_page_format():
    page = man_pages.load_man_page("if64")
    assert type(page) == dict

    _check_man_page_structure(page)

    # Check optional keys
    for key in [ 'item', 'inventory']:
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
    man_pages.print_man_page("if64")
    out, err = capsys.readouterr()
    assert err == ""

    assert out.startswith(" if64    ")
    assert "\n License: " in out
