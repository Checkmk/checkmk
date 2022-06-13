#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Type

import cmk.utils.store as store
import cmk.utils.version as cmk_version

import cmk.gui.pages
import cmk.gui.watolib.read_only as read_only
from cmk.gui.breadcrumb import make_main_menu_breadcrumb
from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import FinalizeRequest, MKAuthException, MKGeneralException, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.plugins.wato.utils import mode_registry
from cmk.gui.plugins.wato.utils.base_modes import WatoMode
from cmk.gui.plugins.wato.utils.html_elements import (
    initialize_wato_html_head,
    wato_html_footer,
    wato_html_head,
)
from cmk.gui.utils.flashed_messages import get_flashed_messages
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.wato.pages.not_implemented import ModeNotImplemented
from cmk.gui.watolib.activate_changes import update_config_generation
from cmk.gui.watolib.git import do_git_commit
from cmk.gui.watolib.sidebar_reload import is_sidebar_reload_needed

if cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module
else:
    managed = None  # type: ignore[assignment]

# .
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Der Seitenaufbau besteht aus folgenden Teilen:                       |
#   | 1. Kontextbuttons: wo kann man von hier aus hinspringen, ohne Aktion |
#   | 2. Verarbeiten einer Aktion, falls eine gültige Transaktion da ist   |
#   | 3. Anzeigen von Inhalten                                             |
#   |                                                                      |
#   | Der Trick: welche Inhalte angezeigt werden, hängt vom Ausgang der    |
#   | Aktion ab. Wenn man z.B. bei einem Host bei "Add host" auf           |
#   | [Save] klickt, dann kommt bei Erfolg die Inventurseite, bei Miss-    |
#   | bleibt man auf der Neuanlegen-Seite                                  |
#   |                                                                      |
#   | Dummerweise kann ich aber die Kontextbuttons erst dann anzeigen,     |
#   | wenn ich den Ausgang der Aktion kenne. Daher wird zuerst die Aktion  |
#   | ausgeführt, welche aber keinen HTML-Code ausgeben darf.              |
#   `----------------------------------------------------------------------'


@cmk.gui.pages.register("wato")
def page_handler() -> None:
    initialize_wato_html_head()

    if not active_config.wato_enabled:
        raise MKGeneralException(
            _(
                "Setup is disabled. Please set <tt>wato_enabled = True</tt>"
                " in your <tt>multisite.mk</tt> if you want to use Setup."
            )
        )

    # config.current_customer can not be checked with CRE repos
    if cmk_version.is_managed_edition() and not managed.is_provider(
        active_config.current_customer
    ):  # type: ignore[attr-defined]
        raise MKGeneralException(_("Check_MK can only be configured on the managers central site."))

    current_mode = request.var("mode") or "main"
    mode_class = mode_registry.get(current_mode, ModeNotImplemented)
    _ensure_mode_permissions(mode_class)

    display_options.load_from_html(request, html)

    if display_options.disabled(display_options.N):
        html.add_body_css_class("inline")

    # If we do an action, we aquire an exclusive lock on the complete WATO.
    if transactions.is_transaction():
        with store.lock_checkmk_configuration():
            _wato_page_handler(current_mode, mode_class())
    else:
        _wato_page_handler(current_mode, mode_class())


def _wato_page_handler(current_mode: str, mode: WatoMode) -> None:
    # Do actions (might switch mode)
    if transactions.is_transaction():
        try:
            if read_only.is_enabled() and not read_only.may_override():
                raise MKUserError(None, read_only.message())

            result = mode.action()
            if isinstance(result, (tuple, str, bool)):
                raise MKGeneralException(
                    f'WatoMode "{current_mode}" returns unsupported return value: {result!r}'
                )

            # We assume something has been modified and increase the config generation ID by one.
            update_config_generation()

            if active_config.wato_use_git:
                do_git_commit()

            # Handle two cases:
            # a) Don't render the page content after action
            #    (a confirm dialog is displayed by the action, or a non-HTML content was sent)
            # b) Redirect to another page
            if isinstance(result, FinalizeRequest):
                raise result

        except MKUserError as e:
            user_errors.add(e)

        except MKAuthException as e:
            user_errors.add(MKUserError(None, e.args[0]))

    breadcrumb = make_main_menu_breadcrumb(mode.main_menu()) + mode.breadcrumb()
    page_menu = mode.page_menu(breadcrumb)
    wato_html_head(
        title=mode.title(),
        breadcrumb=breadcrumb,
        page_menu=page_menu,
        show_body_start=display_options.enabled(display_options.H),
        show_top_heading=display_options.enabled(display_options.T),
    )

    if not transactions.is_transaction() or (read_only.is_enabled() and read_only.may_override()):
        _show_read_only_warning()

    # Show outcome of failed action on this page
    html.show_user_errors()

    # Show outcome of previous page (that redirected to this one)
    for message in get_flashed_messages():
        html.show_message(message)

    # Show content
    mode.handle_page()

    if is_sidebar_reload_needed():
        html.reload_whole_page()

    wato_html_footer(show_body_end=display_options.enabled(display_options.H))


def _ensure_mode_permissions(mode_class: Type[WatoMode]) -> None:
    permissions = mode_class.permissions()
    if permissions is None:
        permissions = []
    else:
        user.need_permission("wato.use")
    if transactions.is_transaction():
        user.need_permission("wato.edit")
    elif user.may("wato.seeall"):
        permissions = []
    for pname in permissions:
        user.need_permission(pname if "." in pname else ("wato." + pname))


def _show_read_only_warning() -> None:
    if read_only.is_enabled():
        html.show_warning(read_only.message())
