#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.session import session


def verify_requirements(permission: str, wato_enabled: bool) -> None:
    if not user.id:
        raise MKUserError(None, _("Not logged in."))

    # If the user is obligated to change his password, or 2FA is
    # enforced, he should be allowed to do so.
    if (
        request.get_ascii_input("reason") not in ("expired", "enforced")
        and not session.two_factor_enforced()
    ):
        if not user.may(permission):
            raise MKAuthException(_("You are not allowed to edit your user profile."))

    if not wato_enabled:
        raise MKAuthException(_("User profiles can not be edited (Setup is disabled)."))
