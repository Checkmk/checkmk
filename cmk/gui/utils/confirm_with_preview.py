#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from typing import Literal

from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _, _l
from cmk.gui.type_defs import CSSSpec
from cmk.gui.utils.html import HTML
from cmk.gui.utils.mobile import is_mobile
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeuri


def confirm_with_preview(
    msg: str | HTML,
    confirm_options: list[tuple[str, str]],
    method: str = "POST",
    class_: CSSSpec | None = None,
) -> bool | None:
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
        html.open_div(class_="really " + (" ".join(class_) if class_ is not None else ""))
        html.write_text_permissive(msg)
        with html.form_context("confirm", method=method, add_transid=False):
            html.hidden_fields(add_action_vars=True)
            for title, varname in confirm_options:
                html.button(varname, title, "really")
            html.button("_do_actions", _("Cancel"))
        html.close_div()
        if mobile:
            html.close_center()

        return False  # False --> "Dialog shown, no answer yet"

    # Now check the transaction. True: "Yes", None --> Browser reload of "yes" page
    return True if transactions.check_transaction() else None


# TODO Try to replace all call sites of confirm_with_preview() with command_confirm_dialog()
def command_confirm_dialog(
    confirm_options: list[tuple[str, str]],
    command_title: str,
    command_html: HTML,
    icon_class: Literal["question", "warning"],
    confirm_button: LazyString = _l("Confirm"),
    cancel_button: LazyString = _l("Cancel"),
    deny_button: LazyString | None = None,
    deny_js_function: str | None = None,
) -> bool | None:
    if any(request.has_var(varname) for _title, varname in confirm_options):
        return True if transactions.check_transaction() else None
    mobile = is_mobile(request, response)

    if mobile:
        html.open_center()

    with html.form_context("confirm", method="POST", add_transid=False):
        html.hidden_fields(add_action_vars=True)
        for title, varname in confirm_options:
            html.hidden_field(varname, title)

    # return to commands page on mobile
    cancel_url = (
        makeuri(
            request,
            addvars=[("page", "commands")],
            delvars=["filled_in", "_transid", "_do_actions", "actions"],
        )
        if mobile
        else makeuri(
            request=request,
            addvars=[("_do_actions", "no")],
            delvars=["filled_in", "_transid"],
        )
    )
    deny_button_config = (
        {}
        if deny_button is None and deny_js_function is None
        else {
            "denyButtonText": str(deny_button or _l("Deny")),
            "showDenyButton": True,
        }
    )
    html.javascript(
        "cmk.forms.confirm_dialog(%s, function() {const form = document.getElementById('form_confirm');form.submit()}, %s, %s)"
        % (
            json.dumps(
                {
                    "title": command_title,
                    "html": str(command_html),
                    "confirmButtonText": str(confirm_button),
                    "cancelButtonText": str(cancel_button),
                    "icon": icon_class,
                    "customClass": {
                        "confirmButton": "confirm_%s" % icon_class,
                        "icon": "confirm_icon confirm_%s" % icon_class,
                    },
                    **deny_button_config,
                }
            ),
            f"function() {{location.href = {json.dumps(cancel_url)}}}",
            deny_js_function if deny_js_function is not None else "null",
        )
    )

    if mobile:
        html.close_center()

    return False  # False --> "Dialog shown, no answer yet"
