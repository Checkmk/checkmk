#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import time
from typing import List, Optional

import pytest

from cmk.utils.type_defs import UserId

import cmk.gui.http as http
from cmk.gui.globals import transactions
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.utils.transaction_manager import TransactionManager


@pytest.fixture()
def tm():
    request = http.Request({"wsgi.input": "", "SCRIPT_NAME": ""})
    return TransactionManager(request, MockLoggedInUser())


def test_request_context_integration(request_context):
    assert callable(transactions.transaction_valid)
    assert callable(transactions.is_transaction)
    assert callable(transactions.check_transaction)


def test_transaction_new_id(tm):
    assert tm._new_transids == []
    trans_id = tm.get()
    assert isinstance(trans_id, str)
    assert tm._new_transids == [trans_id]


class MockLoggedInUser(LoggedInUser):
    def __init__(self):
        super().__init__(None)
        self._ids = []

    def transids(self, lock=False):
        return self._ids

    def save_transids(self, transids: List[str]) -> None:
        pass

    def _gather_roles(self, _user_id: Optional[UserId]) -> List[str]:
        return []


@pytest.mark.parametrize(
    "transid,ignore_transids,result,is_existing",
    [
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
    ],
)
def test_transaction_valid(tm, transid, ignore_transids, result, mocker, is_existing):
    assert tm._ignore_transids is False
    if ignore_transids:
        tm.ignore()
        # NOTE: This seems to be a mypy 0.780 bug.
        assert tm._ignore_transids is True  # type: ignore[comparison-overlap]

    if transid is not None:
        tm._request.set_var("_transid", transid)
        assert tm._request.has_var("_transid")
        assert tm._request.var("_transid") == transid

    if is_existing:
        tm._user._ids = [transid]

    assert tm.transaction_valid() == result


def test_is_transaction(tm):
    assert not tm.is_transaction()
    tm._request.set_var("_transid", "123")
    assert tm.is_transaction()


def test_check_transaction_invalid(tm, monkeypatch):
    assert tm.check_transaction() is False


def test_check_transaction_valid(tm, monkeypatch, mocker):
    valid_transid = "%d/abc" % time.time()
    tm._request.set_var("_transid", valid_transid)
    tm._user._ids = [valid_transid]

    invalidate = mocker.patch.object(tm, "_invalidate")
    assert tm.check_transaction() is True
    invalidate.assert_called_once_with(valid_transid)


def test_check_transaction_automation(tm, monkeypatch, mocker):
    tm.ignore()
    tm._request.set_var("_transid", "-1")

    invalidate = mocker.patch.object(tm, "_invalidate")
    assert tm.check_transaction() is True
    invalidate.assert_not_called()
