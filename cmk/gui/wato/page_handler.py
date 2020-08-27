#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import inspect
from typing import List, Tuple, Type, Optional

import cmk.utils.version as cmk_version
import cmk.utils.store as store

import cmk.gui.pages
import cmk.gui.config as config
from cmk.gui.type_defs import PermissionName
from cmk.gui.display_options import display_options
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKGeneralException, MKAuthException, MKUserError
from cmk.gui.plugins.wato.utils.html_elements import (
    wato_html_head,
    wato_html_footer,
    initialize_wato_html_head,
)
from cmk.gui.plugins.wato.utils import mode_registry
from cmk.gui.wato.pages.not_implemented import ModeNotImplemented
from cmk.gui.plugins.wato.utils.base_modes import WatoMode
from cmk.gui.watolib.git import do_git_commit
from cmk.gui.watolib.sidebar_reload import is_sidebar_reload_needed
from cmk.gui.watolib.activate_changes import update_config_generation
from cmk.gui.watolib import init_wato_datastructures
from cmk.gui.breadcrumb import make_main_menu_breadcrumb

if cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module
else:
    managed = None  # type: ignore[assignment]

#.
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
#   | Aktion ab. Wenn man z.B. bei einem Host bei "Create new host" auf    |
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

    if not config.wato_enabled:
        raise MKGeneralException(
            _("WATO is disabled. Please set <tt>wato_enabled = True</tt>"
              " in your <tt>multisite.mk</tt> if you want to use WATO."))

    # config.current_customer can not be checked with CRE repos
    if cmk_version.is_managed_edition() and not managed.is_provider(
            config.current_customer):  # type: ignore[attr-defined]
        raise MKGeneralException(
            _("Check_MK can only be configured on "
              "the managers central site."))

    current_mode = html.request.var("mode") or "main"
    mode_permissions, mode_class = _get_mode_permission_and_class(current_mode)

    display_options.load_from_html()

    if display_options.disabled(display_options.N):
        html.add_body_css_class("inline")

    # If we do an action, we aquire an exclusive lock on the complete WATO.
    if html.is_transaction():
        with store.lock_checkmk_configuration():
            _wato_page_handler(current_mode, mode_permissions, mode_class)
    else:
        _wato_page_handler(current_mode, mode_permissions, mode_class)


def _wato_page_handler(current_mode: str, mode_permissions: List[PermissionName],
                       mode_class: Type[WatoMode]) -> None:
    try:
        init_wato_datastructures(with_wato_lock=not html.is_transaction())
    except Exception:
        # Snapshot must work in any case
        if current_mode == 'snapshot':
            pass
        else:
            raise

    # Check general permission for this mode
    if mode_permissions is not None and not config.user.may("wato.seeall"):
        _ensure_mode_permissions(mode_permissions)

    mode = mode_class()

    # Do actions (might switch mode)
    action_message: Optional[str] = None
    if html.is_transaction():
        try:
            config.user.need_permission("wato.edit")

            # Even if the user has seen this mode because auf "seeall",
            # he needs an explicit access permission for doing changes:
            if config.user.may("wato.seeall"):
                if mode_permissions:
                    _ensure_mode_permissions(mode_permissions)

            if cmk.gui.watolib.read_only.is_enabled(
            ) and not cmk.gui.watolib.read_only.may_override():
                raise MKUserError(None, cmk.gui.watolib.read_only.message())

            result = mode.action()
            if isinstance(result, tuple):
                newmode, action_message = result
            else:
                newmode = result

            # We assume something has been modified and increase the config generation ID by one.
            update_config_generation()

            # If newmode is False, then we shall immediately abort.
            # This is e.g. the case, if the page outputted non-HTML
            # data, such as a tarball (in the export function). We must
            # be sure not to output *any* further data in that case.
            if newmode is False:
                return

            # if newmode is not None, then the mode has been changed
            if newmode is not None:
                assert not isinstance(newmode, bool)
                if newmode == "":  # no further information: configuration dialog, etc.
                    if action_message:
                        html.show_message(action_message)
                        wato_html_footer()
                    return
                mode_permissions, mode_class = _get_mode_permission_and_class(newmode)
                current_mode = newmode
                mode = mode_class()
                html.request.set_var("mode", newmode)  # will be used by makeuri

                # Check general permissions for the new mode
                if mode_permissions is not None and not config.user.may("wato.seeall"):
                    for pname in mode_permissions:
                        if '.' not in pname:
                            pname = "wato." + pname
                        config.user.need_permission(pname)

        except MKUserError as e:
            action_message = "%s" % e
            html.add_user_error(e.varname, action_message)

        except MKAuthException as e:
            reason = e.args[0]
            action_message = reason
            html.add_user_error(None, reason)

    breadcrumb = make_main_menu_breadcrumb(mode.main_menu()) + mode.breadcrumb()
    page_menu = mode.page_menu(breadcrumb)
    wato_html_head(title=mode.title(),
                   breadcrumb=breadcrumb,
                   page_menu=page_menu,
                   show_body_start=display_options.enabled(display_options.H),
                   show_top_heading=display_options.enabled(display_options.T))

    if not html.is_transaction() or (cmk.gui.watolib.read_only.is_enabled() and
                                     cmk.gui.watolib.read_only.may_override()):
        _show_read_only_warning()

    # Show outcome of action
    if html.has_user_errors():
        html.show_user_errors()
    elif action_message:
        html.show_message(action_message)

    # Show content
    mode.handle_page()

    if is_sidebar_reload_needed():
        html.reload_sidebar()

    if config.wato_use_git and html.is_transaction():
        do_git_commit()

    wato_html_footer(show_footer=display_options.enabled(display_options.Z),
                     show_body_end=display_options.enabled(display_options.H))


def _get_mode_permission_and_class(mode_name: str) -> Tuple[List[PermissionName], Type[WatoMode]]:
    mode_class = mode_registry.get(mode_name, ModeNotImplemented)
    mode_permissions = mode_class.permissions()

    if mode_class is None:
        raise MKGeneralException(_("No such WATO module '<tt>%s</tt>'") % mode_name)

    if inspect.isfunction(mode_class):
        raise MKGeneralException(
            _("Deprecated WATO module: Implemented as function. "
              "This needs to be refactored as WatoMode child class."))

    if mode_permissions is not None and not config.user.may("wato.use"):
        raise MKAuthException(_("You are not allowed to use WATO."))

    return mode_permissions, mode_class


def _ensure_mode_permissions(mode_permissions: List[PermissionName]) -> None:
    for pname in mode_permissions:
        if '.' not in pname:
            pname = "wato." + pname
        config.user.need_permission(pname)


def _show_read_only_warning() -> None:
    if cmk.gui.watolib.read_only.is_enabled():
        html.show_warning(cmk.gui.watolib.read_only.message())
