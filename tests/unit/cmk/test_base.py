import pytest
import os

import cmk


def test_version():
    assert isinstance(cmk.__version__, str)


def test_is_enterprise_edition(monkeypatch):
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cre")
    assert cmk.is_enterprise_edition() == False
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cee")
    assert cmk.is_enterprise_edition() == True
    monkeypatch.setattr(cmk, "omd_version", lambda: "2016.09.22.cee")
    assert cmk.is_enterprise_edition() == True
    monkeypatch.setattr(cmk, "omd_version", lambda: "2016.09.22.cee.demo")
    assert cmk.is_enterprise_edition() == True


def test_is_raw_edition(monkeypatch):
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cre")
    assert cmk.is_raw_edition() == True
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cee")
    assert cmk.is_raw_edition() == False
    monkeypatch.setattr(cmk, "omd_version", lambda: "2016.09.22.cee")
    assert cmk.is_raw_edition() == False
    monkeypatch.setattr(cmk, "omd_version", lambda: "2016.09.22.cee.demo")
    assert cmk.is_raw_edition() == False


def test_is_demo(monkeypatch):
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cre")
    assert cmk.is_demo() == False
    monkeypatch.setattr(cmk, "omd_version", lambda: "1.4.0i1.cee")
    assert cmk.is_demo() == False
    monkeypatch.setattr(cmk, "omd_version", lambda: "2016.09.22.cee")
    assert cmk.is_demo() == False
    monkeypatch.setattr(cmk, "omd_version", lambda: "2016.09.22.cee.demo")
    assert cmk.is_demo() == True
