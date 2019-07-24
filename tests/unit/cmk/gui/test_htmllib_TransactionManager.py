#!/usr/bin/env python

import pytest
import time

import cmk.gui.http as http
from cmk.gui.globals import html
import cmk.gui.htmllib as htmllib


@pytest.fixture()
def tm():
    request = http.Request({"wsgi.input": "", "SCRIPT_NAME": ""})
    return htmllib.TransactionManager(request)


def test_htmllib_integration(register_builtin_html):
    assert html.transaction_manager

    getattr(html, "transaction_valid")
    getattr(html, "is_transaction")
    getattr(html, "check_transaction")


def test_transaction_new_id(tm):
    assert tm._new_transids == []
    trans_id = tm.get()
    assert isinstance(trans_id, str)
    assert tm._new_transids == [trans_id]


@pytest.mark.parametrize("transid,ignore_transids,result,is_existing", [
    (None, False, False, False),
    (None, True, False, False),
    ("", False, False, False),
    ("", True, True, False),
    ("abc", False, False, False),
    ("abc", True, False, False),
    ("-1", False, False, False),
    ("-1", True, True, False),
    ("123/abc", False, False, False),
    ("123/abc", True, False, False),
    ("%d/abc" % time.time(), False, False, False),
    ("%d/abc" % time.time(), False, True, True),
])
def test_transaction_valid(tm, transid, ignore_transids, result, monkeypatch, is_existing):
    assert tm._ignore_transids == False
    if ignore_transids:
        tm.ignore()
        assert tm._ignore_transids == True

    if transid is not None:
        tm._request.set_var("_transid", transid)
        assert tm._request.has_var("_transid")
        assert tm._request.var("_transid") == transid

    if is_existing:
        monkeypatch.setattr(tm, "_load_transids", lambda: [transid])
    else:
        monkeypatch.setattr(tm, "_load_transids", lambda: [])

    assert tm.transaction_valid() == result


def test_is_transaction(tm):
    assert not tm.is_transaction()
    tm._request.set_var("_transid", "123")
    assert tm.is_transaction()


def test_check_transaction_invalid(tm, monkeypatch):
    assert tm.check_transaction() == False


def test_check_transaction_valid(tm, monkeypatch, mocker):
    valid_transid = "%d/abc" % time.time()
    tm._request.set_var("_transid", valid_transid)

    monkeypatch.setattr(tm, "_load_transids", lambda: [valid_transid])

    invalidate = mocker.patch.object(tm, "_invalidate")
    assert tm.check_transaction() == True
    invalidate.assert_called_once_with(valid_transid)


def test_check_transaction_automation(tm, monkeypatch, mocker):
    tm.ignore()
    tm._request.set_var("_transid", "-1")

    invalidate = mocker.patch.object(tm, "_invalidate")
    assert tm.check_transaction() == True
    invalidate.assert_not_called()
