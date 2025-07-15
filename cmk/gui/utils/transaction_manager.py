#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from cmk.ccc.user import UserId

from cmk.utils.log.security_event import log_security_event, SecurityEvent

from cmk.gui.ctx_stack import session_attr
from cmk.gui.http import request


class _TransactionIdInvalid(ValueError):
    """Exception for transaction id validation"""


@dataclass
class TransactionIDValidationFailureEvent(SecurityEvent):
    """Indicates failed transaction id validation"""

    def __init__(self, *, username: UserId | None, remote_ip: str | None) -> None:
        super().__init__(
            "Transaction ID validation failed",
            {
                "user": str(username or "Unknown user"),
                "remote_ip": remote_ip,
            },
            SecurityEvent.Domain.application_errors,
        )


class ReaderProtocol(Protocol):
    def __call__(self, *, lock: bool) -> list[str]: ...


class TransactionManager:
    """Manages the handling of transaction IDs used by the GUI to prevent against
    performing the same action multiple times."""

    def __init__(
        self,
        user: UserId | None,
        reader: ReaderProtocol,
        writer: Callable[[list[str]], None],
    ) -> None:
        self._user = user

        self._reader = reader
        self._writer = writer

        self._new_transids: list[str] = []
        self._ignore_transids = False
        self._current_transid: str | None = None

    def ignore(self) -> None:
        """Makes the GUI skip all transaction validation steps"""
        self._ignore_transids = True

    def unignore(self) -> None:
        # Not sure what this is all about, but some test apparently requires it to be false after
        # the request is over, so we make it false after the request is over.
        self._ignore_transids = False

    def get(self) -> str:
        """Returns a transaction ID that can be used during a subsequent action"""
        if not self._current_transid:
            self._current_transid = self.fresh_transid()
        return self._current_transid

    def fresh_transid(self) -> str:
        """Compute a unique transaction id.

        This is generated during rendering of a form or an action link, stored
        in a user specific file for later validation, sent to the users browser
        via HTML code, then submitted by the user together with the action
        (link / form) and then validated if it is a known transid. When it is a
        known transid, it will be used and invalidated. If the id is not known,
        the action will not be processed."""
        transid = "%d/%s" % (int(time.time()), secrets.token_urlsafe(8))
        self._new_transids.append(transid)
        return transid

    def store_new(self) -> None:
        """All generated transids are saved per user.

        They are stored in the transids.mk. Per user only up to 30 transids of
        the already existing ones are kept. The transids generated on the
        current page are all kept. IDs older than one day are deleted."""
        if not self._new_transids:
            return

        valid_ids = self._reader(lock=True)
        cleared_ids = []
        now = time.time()
        for valid_id in valid_ids:
            timestamp = valid_id.split("/")[0]
            if now - int(timestamp) < 86400:  # one day
                cleared_ids.append(valid_id)
        self._writer(cleared_ids[-30:] + self._new_transids)

    def _validate_transaction_id(self, transid: str) -> Literal[True]:
        if "/" not in transid:
            raise _TransactionIdInvalid("No '/' in transid")

        try:
            timestamp = int(transid.split("/", 1)[0])
        except ValueError:
            raise _TransactionIdInvalid("Timestamp invalid")

        # If age is too old (one week), it is always
        # invalid:
        if time.time() - timestamp >= 604800:  # 7 * 24 hours
            raise _TransactionIdInvalid("Timestamp expired")

        # Now check, if this transid is a valid one
        if transid not in self._reader(lock=False):
            raise _TransactionIdInvalid("Transid not found")

        return True

    def transaction_valid(self) -> bool:
        """Checks if the current transaction is valid

        i.e. in case of browser reload a browser reload, the form submit should
        not be handled  a second time.. The HTML variable _transid must be
        present.

        In case of automation users (authed by _secret in URL): If it is empty
        or -1, then it's always valid (this is used for webservice calls).
        This was also possible for normal users, but has been removed to preven
        security related issues."""
        if not request.has_var("_transid"):
            return False

        transid = request.get_str_input_mandatory("_transid", "")
        if self._ignore_transids and (not transid or transid == "-1"):
            return True  # automation

        try:
            return self._validate_transaction_id(transid)
        except _TransactionIdInvalid:
            log_security_event(
                TransactionIDValidationFailureEvent(
                    username=self._user,
                    remote_ip=request.remote_ip,
                )
            )
            return False

    def is_transaction(self) -> bool:
        """Checks, if the current page is a transation, i.e. something that is secured by
        a transid (such as a submitted form)"""
        return request.has_var("_transid")

    def check_transaction(self) -> bool:
        """called by page functions in order to check, if this was a reload or the original form submission.

        Increases the transid of the user, if the latter was the case.

        There are three return codes:

        True:  -> positive confirmation by the user
        False: -> not yet confirmed, question is being shown
        None:  -> a browser reload or a negative confirmation
        """
        if self.transaction_valid():
            transid = request.var("_transid")
            if transid and transid != "-1":
                self._invalidate(transid)
            return True
        return False

    def _invalidate(self, used_id: str) -> None:
        """Remove the used transid from the list of valid ones"""
        valid_ids = self._reader(lock=True)
        try:
            valid_ids.remove(used_id)
        except ValueError:
            return
        self._writer(valid_ids)


transactions: TransactionManager = session_attr(("user", "transactions"), TransactionManager)
