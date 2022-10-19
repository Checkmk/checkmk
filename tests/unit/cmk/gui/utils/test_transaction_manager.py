#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

from cmk.gui.http import request
from cmk.gui.utils.transaction_manager import TransactionManager, transactions


@pytest.fixture(name="transaction_ids")
def fixture_transaction_ids() -> list[str]:
    return []


@pytest.fixture(name="tm")
@pytest.mark.usefixtures("request_context")
def fixture_tm(transaction_ids: list[str]) -> TransactionManager:
    def transids(lock=False):
        return transaction_ids

    def save_transids(transids: list[str]) -> None:
        pass

    return TransactionManager(transids, save_transids)


@pytest.mark.usefixtures("request_context")
def test_request_context_integration() -> None:
    assert callable(transactions.transaction_valid)
    assert callable(transactions.is_transaction)
    assert callable(transactions.check_transaction)


def test_transaction_new_id(tm) -> None:  # type:ignore[no-untyped-def]
    assert tm._new_transids == []
    trans_id = tm.get()
    assert isinstance(trans_id, str)
    assert tm._new_transids == [trans_id]


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
def test_transaction_valid(  # type:ignore[no-untyped-def]
    transaction_ids, tm, transid, ignore_transids, result, mocker, is_existing
) -> None:
    assert tm._ignore_transids is False
    if ignore_transids:
        tm.ignore()
        assert tm._ignore_transids is True

    if transid is not None:
        request.set_var("_transid", transid)
        assert request.has_var("_transid")
        assert request.var("_transid") == transid

    if is_existing:
        transaction_ids.append(transid)

    assert tm.transaction_valid() == result


def test_is_transaction(tm) -> None:  # type:ignore[no-untyped-def]
    assert not tm.is_transaction()
    request.set_var("_transid", "123")
    assert tm.is_transaction()


def test_check_transaction_invalid(tm, monkeypatch) -> None:  # type:ignore[no-untyped-def]
    assert tm.check_transaction() is False


def test_check_transaction_valid(  # type:ignore[no-untyped-def]
    transaction_ids, tm, monkeypatch, mocker
) -> None:
    valid_transid = "%d/abc" % time.time()
    request.set_var("_transid", valid_transid)
    transaction_ids.append(valid_transid)

    invalidate = mocker.patch.object(tm, "_invalidate")
    assert tm.check_transaction() is True
    invalidate.assert_called_once_with(valid_transid)


def test_check_transaction_automation(  # type:ignore[no-untyped-def]
    tm, monkeypatch, mocker
) -> None:
    tm.ignore()
    request.set_var("_transid", "-1")

    invalidate = mocker.patch.object(tm, "_invalidate")
    assert tm.check_transaction() is True
    invalidate.assert_not_called()
