#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The user can change own 2FA related settings on this page"""

import abc
import http.client as http_client
import time
from typing import Any, Sequence

from fido2 import cbor  # type: ignore[import]
from fido2.client import ClientData  # type: ignore[import]
from fido2.ctap2 import (  # type: ignore[import]
    AttestationObject,
    AttestedCredentialData,
    AuthenticatorData,
)
from fido2.server import Fido2Server  # type: ignore[import]
from fido2.webauthn import PublicKeyCredentialRpEntity  # type: ignore[import]

from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_simple_page_breadcrumb
from cmk.gui.crash_reporting import handle_exception_as_gui_crash_report
from cmk.gui.exceptions import HTTPRedirect, MKGeneralException, MKUserError
from cmk.gui.globals import (
    g,
    html,
    request,
    response,
    session,
    theme,
    transactions,
    user,
    user_errors,
)
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.page_menu import (
    make_form_submit_link,
    make_javascript_link,
    make_simple_form_page_menu,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import Page, page_registry
from cmk.gui.plugins.wato.utils.base_modes import redirect
from cmk.gui.table import table_element
from cmk.gui.type_defs import WebAuthnCredential
from cmk.gui.userdb import (
    is_two_factor_backup_code_valid,
    is_two_factor_login_enabled,
    load_two_factor_credentials,
    make_two_factor_backup_codes,
    save_two_factor_credentials,
    set_two_factor_completed,
)
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.urls import make_confirm_link, makeactionuri, makeuri_contextless
from cmk.gui.valuespec import Dictionary, FixedValue, TextInput

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

        if request.has_var("_backup_codes"):
            display_codes, credentials["backup_codes"] = make_two_factor_backup_codes()
            save_two_factor_credentials(user.id, credentials)
            flash(
                _(
                    "Backup codes have been generated: <ul>%s</ul> Save them now. "
                    "If you loose them, you will have to generate new ones."
                )
                % "".join(f"<li><tt>{c}</tt></li>" for c in display_codes)
            )

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
                                PageMenuEntry(
                                    title=_("Regenerate backup codes"),
                                    icon_name="2fa_backup_codes",
                                    item=make_form_submit_link("two_factor", "_backup_codes"),
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
        self._show_backup_codes(credentials["backup_codes"])

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

                html.icon_button(
                    makeuri_contextless(
                        request,
                        [("_edit", credential["credential_id"])],
                        filename="user_two_factor_edit_credential.py",
                    ),
                    _("Edit this credential"),
                    "edit",
                )
                table.cell(_("Alias"), credential["alias"])
                table.cell(
                    _("Registered at"),
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(credential["registered_at"])),
                )

    def _show_backup_codes(self, backup_codes: Sequence[str]) -> None:
        forms.header(_("Backup codes"))
        forms.section(_("Backup codes"), simple=True)
        if backup_codes:
            html.p(_("You have %d unused backup codes left.") % len(backup_codes))
            html.i(_("If you regenerate backup codes, you automatically invalidate old codes."))
        else:
            html.i(_("No backup codes created yet."))

        forms.end()


@page_registry.register_page("user_two_factor_edit_credential")
class UserChangePasswordPage(ABCUserProfilePage):
    def _page_title(self) -> str:
        return _("Edit credential")

    def __init__(self) -> None:
        super().__init__("general.manage_2fa")

    def _breadcrumb(self) -> Breadcrumb:
        breadcrumb = make_simple_page_breadcrumb(mega_menu_registry.menu_user(), self._page_title())
        breadcrumb.insert(
            -1,
            BreadcrumbItem(
                title=_("Two-factor authentication"),
                url="user_two_factor_overview.py",
            ),
        )
        return breadcrumb

    def _page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Profile"), breadcrumb, form_name="profile", button_name="_save", add_abort_link=True
        )
        return menu

    def _action(self) -> None:
        assert user.id is not None
        credentials = load_two_factor_credentials(user.id, lock=True)

        credential_id = request.get_ascii_input_mandatory("_edit")
        credential = credentials["webauthn_credentials"].get(credential_id)
        if credential is None:
            raise MKUserError("_edit", _("The credential does not exist"))

        vs = self._valuespec(credential)
        settings = vs.from_html_vars("profile")
        vs.validate_value(settings, "profile")

        credential["alias"] = settings["alias"]

        save_two_factor_credentials(user.id, credentials)

        flash(_("Successfully changed the credential."))

        # In distributed setups with remote sites where the user can login, start the
        # user profile replication now which will redirect the user to the destination
        # page after completion. Otherwise directly open up the destination page.
        origtarget = "user_two_factor_overview.py"
        if user.authorized_login_sites():
            raise redirect(
                makeuri_contextless(
                    request, [("back", origtarget)], filename="user_profile_replicate.py"
                )
            )
        raise redirect(origtarget)

    def _show_form(self) -> None:
        assert user.id is not None
        credentials = load_two_factor_credentials(user.id)

        credential_id = request.get_ascii_input_mandatory("_edit")
        credential = credentials["webauthn_credentials"].get(credential_id)
        if credential is None:
            raise MKUserError("_edit", _("The credential does not exist"))

        html.begin_form("profile", method="POST")
        html.prevent_password_auto_completion()
        html.open_div(class_="wato")

        self._valuespec(credential).render_input(
            "profile",
            {
                "registered_at": credential["registered_at"],
                "alias": credential["alias"],
            },
        )

        forms.end()
        html.close_div()
        html.hidden_field("_edit", credential_id)
        html.hidden_fields()
        html.end_form()
        html.footer()

    def _valuespec(self, credential: WebAuthnCredential) -> Dictionary:
        return Dictionary(
            title=_("Edit credential"),
            optional_keys=False,
            render="form",
            elements=[
                (
                    "registered_at",
                    FixedValue(
                        value=time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime(credential["registered_at"])
                        ),
                        title=_("Registered at"),
                    ),
                ),
                (
                    "alias",
                    TextInput(title=_("Alias")),
                ),
            ],
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
                "alias": "",
                "credential_data": bytes(auth_data.credential_data),
            }
        )
        save_two_factor_credentials(user.id, credentials)

        flash(_("Registration successful"))
        return {"status": "OK"}


@page_registry.register_page("user_login_two_factor")
class UserLoginTwoFactor(Page):
    def page(self) -> None:
        assert user.id is not None

        html.set_render_headfoot(False)
        html.add_body_css_class("login")
        html.add_body_css_class("two_factor")
        html.header(_("Two-factor authentication"), Breadcrumb(), javascripts=[])

        html.open_div(id_="login")

        html.open_div(id_="login_window")

        html.open_a(href="https://checkmk.com")
        html.img(
            src=theme.detect_icon_path(icon_name="logo", prefix="mk-"),
            id_="logo",
            class_="custom" if theme.has_custom_logo() else None,
        )
        html.close_a()

        if not is_two_factor_login_enabled(user.id):
            raise MKGeneralException(_("Two-factor authentication not enabled"))

        html.begin_form(
            "two_factor_login", method="POST", add_transid=False, action="user_login_two_factor.py"
        )
        html.prevent_password_auto_completion()
        html.hidden_field(
            "_origtarget", origtarget := request.get_url_input("_origtarget", "index.py")
        )

        if backup_code := request.get_ascii_input("_backup_code"):
            if is_two_factor_backup_code_valid(user.id, backup_code):
                set_two_factor_completed()
                raise HTTPRedirect(origtarget)

        html.label(
            _("Two-factor authentication"),
            for_="webauthn_message",
            id_="label_2fa",
            class_="legend",
        )
        html.div("", id_="webauthn_message")

        with foldable_container(
            treename="webauthn_backup_codes",
            id_="backup_container",
            isopen=False,
            title=_("Use backup code"),
            indent=False,
            save_state=False,
        ):
            html.label(
                "%s:" % _("Backup code"),
                id_="label_pass",
                class_=["legend"],
                for_="_backup_code",
            )
            html.br()
            html.password_input("_backup_code", id_="input_pass", size=None)

            html.open_div(id_="button_text")
            html.button("_use_backup_code", _("Use backup code"), cssclass="hot")
            html.close_div()
            html.close_div()

        if user_errors:
            html.open_div(id_="login_error")
            html.show_user_errors()
            html.close_div()

        html.javascript("cmk.webauthn.login()")

        html.hidden_fields()
        html.end_form()
        html.close_div()
        html.footer()


@page_registry.register_page("user_webauthn_login_begin")
class UserWebAuthnLoginBegin(CBORPage):
    def page(self) -> CBORPageResult:
        assert user.id is not None

        if not is_two_factor_login_enabled(user.id):
            raise MKGeneralException(_("Two-factor authentication not enabled"))

        auth_data, state = make_fido2_server().authenticate_begin(
            [
                AttestedCredentialData.unpack_from(v["credential_data"])[0]
                for v in load_two_factor_credentials(user.id)["webauthn_credentials"].values()
            ],
            user_verification="discouraged",
        )

        session.session_info.webauthn_action_state = state
        logger.debug("Authentication data: %r", auth_data)
        return auth_data


@page_registry.register_page("user_webauthn_login_complete")
class UserWebAuthnLoginComplete(CBORPage):
    def page(self) -> CBORPageResult:
        assert user.id is not None

        if not is_two_factor_login_enabled(user.id):
            raise MKGeneralException(_("Two-factor authentication not enabled"))

        data: dict[str, object] = cbor.decode(request.get_data())
        credential_id = data["credentialId"]
        client_data = ClientData(data["clientDataJSON"])
        auth_data = AuthenticatorData(data["authenticatorData"])
        signature = data["signature"]
        logger.debug("ClientData: %r", client_data)
        logger.debug("AuthenticatorData: %r", auth_data)

        make_fido2_server().authenticate_complete(
            session.session_info.webauthn_action_state,
            [
                AttestedCredentialData.unpack_from(v["credential_data"])[0]
                for v in load_two_factor_credentials(user.id)["webauthn_credentials"].values()
            ],
            credential_id,
            client_data,
            auth_data,
            signature,
        )
        session.session_info.webauthn_action_state = None
        set_two_factor_completed()
        return {"status": "OK"}
