import os

import omdlib.main

def test_root_context():
    site = omdlib.main.RootContext()
    assert site.name == None
    assert site.dir == "/"


def test_site_context(monkeypatch):
    site = omdlib.main.SiteContext("dingeling")
    assert site.name == "dingeling"
    assert site.dir == "/omd/sites/dingeling"
    assert site.tmp_dir == "/omd/sites/dingeling/tmp"


def test_site_context_version(monkeypatch):
    site = omdlib.main.SiteContext("dingeling")
    monkeypatch.setattr(os, "readlink", lambda x: "../2018.08.11.cee")
    assert site.version == "2018.08.11.cee"


def test_site_context_exists(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: p == "/omd/sites/dingeling")

    site = omdlib.main.SiteContext("dingeling")
    assert site.exists()

    site = omdlib.main.SiteContext("dingelang")
    assert not site.exists()


def test_site_context_is_empty(monkeypatch):
    monkeypatch.setattr(os, "listdir", lambda p:
        [] if p == "/omd/sites/dingeling" else ["abc", "version"])

    site = omdlib.main.SiteContext("dingeling")
    assert site.is_empty()

    site = omdlib.main.SiteContext("dingelang")
    assert not site.is_empty()
