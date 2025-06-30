#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.ccc.version as cmk_version
from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException

from cmk.utils import paths
from cmk.utils.paths import configuration_lockfile

from cmk.gui.breadcrumb import make_main_menu_breadcrumb
from cmk.gui.config import Config
from cmk.gui.customer import customer_api
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import FinalizeRequest, MKAuthException, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.utils.flashed_messages import get_flashed_messages_with_categories
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.watolib import read_only
from cmk.gui.watolib.activate_changes import update_config_generation
from cmk.gui.watolib.git import do_git_commit
from cmk.gui.watolib.mode import mode_registry, WatoMode
from cmk.gui.watolib.sidebar_reload import is_sidebar_reload_needed

from .pages._html_elements import initialize_wato_html_head, wato_html_footer, wato_html_head
from .pages.not_implemented import ModeNotImplemented

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


def page_handler(config: Config) -> None:
    initialize_wato_html_head()

    if not config.wato_enabled:
        raise MKGeneralException(
            _(
                "Setup is disabled. Please set <tt>wato_enabled = True</tt>"
                " in your <tt>multisite.mk</tt> if you want to use Setup."
            )
        )

    current_mode = request.get_str_input_mandatory("mode")
    # Backup has to be accessible for remote sites, otherwise the user has no
    # chance to configure a backup for remote sites.
    # config.current_customer can not be checked with CRE repos
    if (
        cmk_version.edition(paths.omd_root) is cmk_version.Edition.CME
        and not customer_api().is_provider(config.current_customer)
        and not current_mode.startswith(("backup", "edit_backup"))
    ):
        raise MKGeneralException(_("Checkmk can only be configured on the managers central site."))

    mode_instance = mode_registry.get(current_mode, ModeNotImplemented)()
    mode_instance.ensure_permissions()

    display_options.load_from_html(request, html)

    if display_options.disabled(display_options.N):
        html.add_body_css_class("inline")

    # If we do an action, we acquire an exclusive lock on the complete Setup.
    if transactions.is_transaction():
        with store.lock_checkmk_configuration(configuration_lockfile):
            _wato_page_handler(config, current_mode, mode_instance)
    else:
        _wato_page_handler(config, current_mode, mode_instance)


def _wato_page_handler(config: Config, current_mode: str, mode: WatoMode) -> None:
    # Do actions (might switch mode)
    if transactions.is_transaction():
        try:
            if read_only.is_enabled() and not read_only.may_override():
                raise MKUserError(None, read_only.message())

            result = mode.action()
            if isinstance(result, tuple | str | bool):
                raise MKGeneralException(
                    f'WatoMode "{current_mode}" returns unsupported return value: {result!r}'
                )

            # We assume something has been modified and increase the config generation ID by one.
            update_config_generation()

            if config.wato_use_git:
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

    if read_only.is_enabled() and (not transactions.is_transaction() or read_only.may_override()):
        html.show_warning(read_only.message())

    # Show outcome of failed action on this page
    html.show_user_errors()

    # Show outcome of previous page (that redirected to this one)
    for message in get_flashed_messages_with_categories():
        html.show_message_by_msg_type(
            msg=message.msg,
            msg_type=message.msg_type,
            flashed=True,
        )

    # Show content
    mode.handle_page(config)

    if is_sidebar_reload_needed():
        html.reload_whole_page()

    wato_html_footer(show_body_end=display_options.enabled(display_options.H))
