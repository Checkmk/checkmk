#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Optional, Tuple, Union

from cmk.gui.htmllib.context import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.utils.html import HTML
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.transaction_manager import transactions


def confirm_with_preview(
    msg: Union[str, HTML], confirm_options: List[Tuple[str, str]], method: str = "POST"
) -> Optional[bool]:
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
    if request.var("_do_actions") == _("Cancel"):
        # User has pressed "Cancel", now invalidate the unused transid
        transactions.check_transaction()
        return None  # None --> "Cancel"

    if not any(request.has_var(varname) for _title, varname in confirm_options):
        mobile = is_mobile(request, response)
        if mobile:
            html.open_center()
        html.open_div(class_="really")
        html.write_text(msg)
        html.begin_form("confirm", method=method, add_transid=False)
        html.hidden_fields(add_action_vars=True)
        for title, varname in confirm_options:
            html.button(varname, title, "really")
        html.button("_do_actions", _("Cancel"))
        html.end_form()
        html.close_div()
        if mobile:
            html.close_center()

        return False  # False --> "Dialog shown, no answer yet"

    # Now check the transaction. True: "Yes", None --> Browser reload of "yes" page
    return True if transactions.check_transaction() else None
