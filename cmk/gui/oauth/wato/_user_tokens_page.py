#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import override

from cmk.ccc.version import Edition
from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.oauth.token.token_store import get_token_store
from cmk.gui.oauth.wato._token_table import (
    bulk_revoke_page_menu_topics,
    load_clients_by_id,
    render_selection_checkbox_cell,
    render_token_summary_cells,
    revoke_tokens_from_request,
)
from cmk.gui.page_menu import PageMenu, PageMenuDropdown
from cmk.gui.pages import Page, PageContext, PageEndpoint, PageRegistry
from cmk.gui.permissions import permission_registry
from cmk.gui.table import table_element
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.verify_requirements import verify_requirements
from cmk.gui.wato.pages.user_profile.page_menu import page_menu_dropdown_user_related
from cmk.web.utils.confirm_links import make_confirm_delete_link
from cmk.web.utils.csrf_token import check_csrf_token
from cmk.web.utils.flashed_messages import get_flashed_messages
from cmk.web.utils.icons import IconNames, StaticIcon
from cmk.web.utils.urls import makeactionuri

_SELECTION_KEY = "user_oauth_tokens"


def register(edition: Edition, page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("user_oauth_tokens", UserOAuthTokensOverview(edition)))


class UserOAuthTokensOverview(Page):
    def __init__(self, edition: Edition) -> None:
        self._edition = edition

    def _page_title(self) -> str:
        return _("OAuth access tokens")

    def _action(self, request: Request) -> None:
        assert user.id is not None
        check_csrf_token(session, request, i18n=_)
        revoke_tokens_from_request(request, user_id=user.id)

    def _page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        topics = bulk_revoke_page_menu_topics(
            _SELECTION_KEY,
            _(
                "Any application using the selected tokens will no longer be able to"
                " access the API with them."
            ),
        )
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(name="tokens", title=_("Tokens"), topics=topics),
                page_menu_dropdown_user_related(
                    self._edition,
                    config.sites,
                    page_name="user_oauth_tokens",
                    show_shortcuts=False,
                ),
            ],
            breadcrumb=breadcrumb,
        )

    @override
    def page(self, ctx: PageContext) -> None:
        verify_requirements(
            UserPermissions.from_config(ctx.config, permission_registry),
            "general.edit_profile",
            ctx.config.wato_enabled,
        )
        title = self._page_title()
        breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_user(), title)
        make_header(
            html,
            title=title,
            breadcrumb=breadcrumb,
            page_menu=self._page_menu(ctx.config, breadcrumb),
            debug=ctx.config.debug,
            lang=user.language,
            inject_js_profiling_code=ctx.config.inject_js_profiling_code,
            load_frontend_vue=ctx.config.load_frontend_vue,
            custom_style_sheet=ctx.config.custom_style_sheet,
            screenshotmode=ctx.config.screenshotmode,
            inline_help_as_text=user.inline_help_as_text,
            hide_suggestions=not user.get_tree_state("suggestions", "all", True),
            user_role_ids=user.role_ids,
        )

        if transactions.check_transaction(ctx.request):
            try:
                self._action(ctx.request)
            except MKUserError as e:
                user_errors.add(e)

        for message in get_flashed_messages():
            html.show_message(message.msg)

        html.show_user_errors()

        self._show_form(ctx.request, ctx.config)

    def _show_form(self, request: Request, config: Config) -> None:
        assert user.id is not None

        # Read before emitting any HTML, so an unusable store shows as an error
        # message instead of a half-rendered table.
        with get_token_store() as store:
            tokens = store.list_by_user(user.id)
        clients = load_clients_by_id()

        html.open_div(class_="wato")
        with html.form_context("bulk_revoke_form", method="POST"):
            with table_element("user_oauth_tokens", limit=config.table_row_limit) as table:
                for token in tokens:
                    table.row()
                    render_selection_checkbox_cell(table, token.token_hash)

                    table.cell(_("Actions"), css=["buttons"])
                    delete_url = make_confirm_delete_link(
                        i18n=_,
                        url=makeactionuri(
                            request, transactions.get(), [("_delete", token.token_hash)]
                        ),
                        title=_("Revoke this access token"),
                        message=_(
                            "Any application using this token will no longer be able to "
                            "access the API with it."
                        ),
                    )
                    html.icon_button(
                        delete_url, _("Revoke this access token"), StaticIcon(IconNames.delete)
                    )

                    render_token_summary_cells(table, token, clients)
            html.hidden_fields()
        html.close_div()
        html.footer()
