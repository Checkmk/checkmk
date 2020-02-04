#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import time
import random
from typing import List, Optional  # pylint: disable=unused-import

import cmk.gui.config as config
from cmk.gui.http import Request  # pylint: disable=unused-import


class TransactionManager(object):
    """Manages the handling of transaction IDs used by the GUI to prevent against
    performing the same action multiple times."""
    def __init__(self, request):
        # type: (Request) -> None
        super(TransactionManager, self).__init__()
        self._request = request

        self._new_transids = []  # type: List[str]
        self._ignore_transids = False
        self._current_transid = None  # type: Optional[str]

    def ignore(self):
        # type: () -> None
        """Makes the GUI skip all transaction validation steps"""
        self._ignore_transids = True

    def get(self):
        # type: () -> str
        """Returns a transaction ID that can be used during a subsequent action"""
        if not self._current_transid:
            self._current_transid = self.fresh_transid()
        return self._current_transid

    def fresh_transid(self):
        # type: () -> str
        """Compute a (hopefully) unique transaction id.

        This is generated during rendering of a form or an action link, stored
        in a user specific file for later validation, sent to the users browser
        via HTML code, then submitted by the user together with the action
        (link / form) and then validated if it is a known transid. When it is a
        known transid, it will be used and invalidated. If the id is not known,
        the action will not be processed."""
        transid = "%d/%d" % (int(time.time()), random.getrandbits(32))
        self._new_transids.append(transid)
        return transid

    def store_new(self):
        # type: () -> None
        """All generated transids are saved per user.

        They are stored in the transids.mk.  Per user only up to 20 transids of
        the already existing ones are kept. The transids generated on the
        current page are all kept. IDs older than one day are deleted."""
        if not self._new_transids:
            return

        valid_ids = config.user.transids(lock=True)
        cleared_ids = []
        now = time.time()
        for valid_id in valid_ids:
            timestamp = valid_id.split("/")[0]
            if now - int(timestamp) < 86400:  # one day
                cleared_ids.append(valid_id)
        config.user.save_transids((cleared_ids[-20:] + self._new_transids))

    def transaction_valid(self):
        # type: () -> bool
        """Checks if the current transaction is valid

        i.e. in case of browser reload a browser reload, the form submit should
        not be handled  a second time.. The HTML variable _transid must be
        present.

        In case of automation users (authed by _secret in URL): If it is empty
        or -1, then it's always valid (this is used for webservice calls).
        This was also possible for normal users, but has been removed to preven
        security related issues."""
        if not self._request.has_var("_transid"):
            return False

        transid = self._request.var("_transid")
        if self._ignore_transids and (not transid or transid == '-1'):
            return True  # automation

        if '/' not in transid:
            return False

        # Normal user/password auth user handling
        timestamp = transid.split("/", 1)[0]

        # If age is too old (one week), it is always
        # invalid:
        now = time.time()
        if now - int(timestamp) >= 604800:  # 7 * 24 hours
            return False

        # Now check, if this transid is a valid one
        return transid in config.user.transids(lock=False)

    def is_transaction(self):
        # type: () -> bool
        """Checks, if the current page is a transation, i.e. something that is secured by
        a transid (such as a submitted form)"""
        return self._request.has_var("_transid")

    def check_transaction(self):
        # type: () -> bool
        """called by page functions in order to check, if this was a reload or the original form submission.

        Increases the transid of the user, if the latter was the case.

        There are three return codes:

        True:  -> positive confirmation by the user
        False: -> not yet confirmed, question is being shown
        None:  -> a browser reload or a negative confirmation
        """
        if self.transaction_valid():
            transid = self._request.var("_transid")
            if transid and transid != "-1":
                self._invalidate(transid)
            return True
        return False

    def _invalidate(self, used_id):
        # type: (str) -> None
        """Remove the used transid from the list of valid ones"""
        valid_ids = config.user.transids(lock=True)
        try:
            valid_ids.remove(used_id)
        except ValueError:
            return
        config.user.save_transids(valid_ids)
