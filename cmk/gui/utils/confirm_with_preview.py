#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Union, Optional
from cmk.gui.utils.html import HTML
from cmk.gui.globals import html
from cmk.gui.i18n import _


def confirm_with_preview(msg: Union[str, HTML], method: str = "POST") -> Optional[bool]:
    """Show a confirm dialog to the user

    BE AWARE: In case you just want to have some action confirmed by the user, you
    should use the javascript powere confirm dialg (make_confirm, add_confirm_on_submit, ...).

    This method is used only in places where we explicitly need to show important information to the
    user before he can decide whether or not to confirm the action.

    The confirm dialog is normally not a dialog which need to be protected by a transid itselfs. It
    is only a intermediate step to the real action But there are use cases where the confirm dialog
    is used during rendering a normal page, for example when deleting a dashlet from a dashboard. In
    such cases, the transid must be added by the confirm dialog.
    """
    if html.request.var("_do_actions") == _("No"):
        # User has pressed "No", now invalidate the unused transid
        html.check_transaction()
        return None  # None --> "No"

    if not html.request.has_var("_do_confirm"):
        if html.mobile:
            html.open_center()
        html.open_div(class_="really")
        html.write_text(msg)
        html.begin_form("confirm", method=method, add_transid=False)
        html.hidden_fields(add_action_vars=True)
        html.button("_do_confirm", _("Yes!"), "really")
        html.button("_do_actions", _("No"), "")
        html.end_form()
        html.close_div()
        if html.mobile:
            html.close_center()

        return False  # False --> "Dialog shown, no answer yet"

    # Now check the transaction. True: "Yes", None --> Browser reload of "yes" page
    return True if html.check_transaction() else None
