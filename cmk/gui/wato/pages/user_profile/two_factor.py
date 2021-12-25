#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The user can change own 2FA related settings on this page"""

import abc
import http.client as http_client
import time
from typing import Any

from fido2 import cbor  # type: ignore[import]
from fido2.client import ClientData  # type: ignore[import]
from fido2.ctap2 import AttestationObject  # type: ignore[import]
from fido2.ctap2 import AttestedCredentialData  # type: ignore[import]
from fido2.server import Fido2Server  # type: ignore[import]
from fido2.webauthn import PublicKeyCredentialRpEntity  # type: ignore[import]

from cmk.gui import forms
from cmk.gui.crash_reporting import handle_exception_as_gui_crash_report
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.globals import g, html, request, response, session, transactions, user
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.page_menu import (
    make_javascript_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import Page, page_registry
from cmk.gui.table import table_element
from cmk.gui.userdb import (
    load_two_factor_credentials,
    save_two_factor_credentials,
    WebAuthnCredential,
)
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.urls import make_confirm_link, makeactionuri

from .abstract_page import ABCUserProfilePage
from .page_menu import page_menu_dropdown_user_related


def make_fido2_server() -> Fido2Server:
    rp_id = request.host
    logger.debug("Using %r as relaying party ID", rp_id)
    return Fido2Server(PublicKeyCredentialRpEntity(rp_id, "Checkmk"))


@page_registry.register_page("user_two_factor_overview")
class UserTwoFactorOverview(ABCUserProfilePage):
    def _page_title(self) -> str:
        return _("Two-factor authentication")

    def __init__(self) -> None:
        super().__init__("general.manage_2fa")

    def _action(self) -> None:
        assert user.id is not None
        credentials = load_two_factor_credentials(user.id)
        if credential_id := request.get_ascii_input("_delete"):
            if credential_id not in credentials["webauthn_credentials"]:
                return
            del credentials["webauthn_credentials"][credential_id]
            save_two_factor_credentials(user.id, credentials)
            flash(_("Credential has been deleted"))

    def _page_menu(self, breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="actions",
                    title=_("Actions"),
                    topics=[
                        PageMenuTopic(
                            title=_("Actions"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add credential"),
                                    icon_name="2fa",
                                    item=make_javascript_link("cmk.webauthn.register()"),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
                page_menu_dropdown_user_related("user_two_factor_overview"),
            ],
            breadcrumb=breadcrumb,
        )

    def _show_form(self) -> None:
        assert user.id is not None
        credentials = load_two_factor_credentials(user.id)

        html.begin_form("two_factor", method="POST")

        self._show_webauthn_credentials(credentials["webauthn_credentials"])

        html.hidden_fields()
        html.end_form()
        html.footer()

    def _show_webauthn_credentials(
        self, webauthn_credentials: dict[str, WebAuthnCredential]
    ) -> None:
        html.div("", id_="webauthn_message")
        forms.header(_("WebAuthn credentials"))

        forms.section(_("Registered credentials"), simple=True)
        if webauthn_credentials:
            self._show_credentials(webauthn_credentials)
        else:
            html.i(_("No credentials registered"))

        forms.end()

    @classmethod
    def _show_credentials(cls, webauthn_credentials: dict[str, WebAuthnCredential]) -> None:
        with table_element(title=None, searchable=False, sortable=False) as table:
            for credential in webauthn_credentials.values():
                table.row()
                table.cell(_("Actions"), css="buttons")
                delete_url = make_confirm_link(
                    url=makeactionuri(
                        request, transactions, [("_delete", credential["credential_id"])]
                    ),
                    message=_("Do you really want to delete this credential"),
                )
                html.icon_button(delete_url, _("Delete this credential"), "delete")
                table.cell(
                    _("Registered at"),
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(credential["registered_at"])),
                )


CBORPageResult = dict[str, Any]


class CBORPage(Page, abc.ABC):
    def handle_page(self) -> None:
        try:
            response.set_content_type("application/cbor")
            response.set_data(cbor.encode(self.page()))
        except Exception as e:
            response.status_code = http_client.INTERNAL_SERVER_ERROR
            handle_exception_as_gui_crash_report(
                plain_error=True,
                show_crash_link=getattr(g, "may_see_crash_reports", False),
            )
            response.set_data(str(e))

    @abc.abstractmethod
    def page(self) -> CBORPageResult:
        """Override this to implement the page functionality"""
        raise NotImplementedError()


@page_registry.register_page("user_webauthn_register_begin")
class UserWebAuthnRegisterBegin(CBORPage):
    def page(self) -> CBORPageResult:
        assert user.id is not None
        user.need_permission("general.manage_2fa")

        registration_data, state = make_fido2_server().register_begin(
            {
                "id": user.id.encode("utf-8"),
                "name": user.id,
                "displayName": user.alias,
                "icon": "",
            },
            [
                AttestedCredentialData.unpack_from(v["credential_data"])[0]
                for v in load_two_factor_credentials(user.id)["webauthn_credentials"].values()
            ],
            user_verification="discouraged",
            authenticator_attachment="cross-platform",
        )

        session.session_info.webauthn_action_state = state
        logger.debug("Registration data: %r", registration_data)
        return registration_data


@page_registry.register_page("user_webauthn_register_complete")
class UserWebAuthnRegisterComplete(CBORPage):
    def page(self) -> CBORPageResult:
        assert user.id is not None
        user.need_permission("general.manage_2fa")

        raw_data = request.get_data()
        logger.debug("Raw request: %r", raw_data)
        data: dict[str, object] = cbor.decode(raw_data)
        client_data = ClientData(data["clientDataJSON"])
        att_obj = AttestationObject(data["attestationObject"])
        logger.debug("Client data: %r", client_data)
        logger.debug("Attestation object: %r", att_obj)

        auth_data = make_fido2_server().register_complete(
            session.session_info.webauthn_action_state, client_data, att_obj
        )

        ident = auth_data.credential_data.credential_id.hex()
        credentials = load_two_factor_credentials(user.id, lock=True)

        if ident in credentials["webauthn_credentials"]:
            raise MKGeneralException(_("Your WebAuthn credetial is already in use"))

        credentials["webauthn_credentials"][ident] = WebAuthnCredential(
            {
                "credential_id": ident,
                "registered_at": int(time.time()),
                "credential_data": bytes(auth_data.credential_data),
            }
        )
        save_two_factor_credentials(user.id, credentials)

        flash(_("Registration successful"))
        return {"status": "OK"}
