import pytest
import os

from testlib import cmk_path

# Make the cmk.paths point to the git directory so the unit tests can be
# done without setting up a site
@pytest.fixture(autouse=True)
def patch_cmk_paths(monkeypatch, tmpdir):
    monkeypatch.setattr("cmk.paths.check_manpages_dir", "%s/checkman" % cmk_path())
    monkeypatch.setattr("cmk.paths.local_check_manpages_dir", "%s" % tmpdir)

import cmk.man_pages as man_pages

# TODO: Add tests for module internal functions

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


def test_no_subtree_and_entries_on_same_level():
    catalog = man_pages.load_man_page_catalog()
    for category, entries in catalog.items():
        has_entries    = entries != []
        has_categories = man_pages._manpage_catalog_subtree_names(catalog, category) != []
        assert has_entries != has_categories, "A category must only have entries or categories, not both"


# TODO: print_man_page_browser()


def test_load_man_page_not_existing():
    assert man_pages.load_man_page("not_existing") == None


def test_load_man_page_format():
    page = man_pages.load_man_page("if64")
    assert type(page) == dict

    for key in [ "header", "configuration", "parameters" ]:
        assert key in page

    for key in [ 'description', 'license', 'title', 'perfdata',
                 'item', 'catalog', 'agents', 'inventory',
                 'distribution', 'examples']:
        assert key in page["header"]

    for entry in page["configuration"]:
        assert type(entry) == tuple
        assert len(entry) == 2

    for entry in page["parameters"]:
        assert type(entry) == tuple
        assert len(entry) == 2


def test_print_man_page_nowiki(capsys):
    man_pages.print_man_page_nowiki("if64")
    out, err = capsys.readouterr()

    # Entry for index page
    assert "<tr>" in err
    assert "[check_if64|" in err

    assert out.startswith("TI:")
    assert "\nH1:" in out


def test_print_man_page(capsys):
    man_pages.print_man_page("if64")
    out, err = capsys.readouterr()
    assert err == ""

    assert out.startswith(" if64    ")
    assert "\n License: " in out
