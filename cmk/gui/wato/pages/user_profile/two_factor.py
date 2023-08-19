#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The user can change own 2FA related settings on this page"""

import abc
import datetime
import http.client as http_client
import time
from base64 import b32decode, b32encode
from collections.abc import Sequence
from typing import Any
from urllib import parse
from uuid import uuid4

from fido2 import cbor  # type: ignore[import]
from fido2.client import ClientData  # type: ignore[import]
from fido2.ctap2 import (  # type: ignore[import]
    AttestationObject,
    AttestedCredentialData,
    AuthenticatorData,
)
from fido2.server import Fido2Server  # type: ignore[import]
from fido2.webauthn import PublicKeyCredentialRpEntity  # type: ignore[import]

from cmk.utils.crypto.password import Password
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.site import omd_site
from cmk.utils.totp import TOTP, TotpVersion

from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_simple_page_breadcrumb
from cmk.gui.crash_handler import handle_exception_as_gui_crash_report
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.page_menu import (
    make_form_submit_link,
    make_javascript_link,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import Page, PageRegistry
from cmk.gui.session import session
from cmk.gui.table import table_element
from cmk.gui.type_defs import TotpCredential, WebAuthnCredential
from cmk.gui.userdb import (
    is_two_factor_backup_code_valid,
    is_two_factor_login_enabled,
    load_two_factor_credentials,
    make_two_factor_backup_codes,
)
from cmk.gui.userdb.store import save_two_factor_credentials
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.theme import theme
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    make_confirm_delete_link,
    makeactionuri,
    makeuri_contextless,
)
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import Dictionary, FixedValue, TextInput
from cmk.gui.watolib.mode import redirect

from .abstract_page import ABCUserProfilePage
from .page_menu import page_menu_dropdown_user_related


def make_fido2_server() -> Fido2Server:
    rp_id = request.host
    logger.debug("Using %r as relaying party ID", rp_id)
    return Fido2Server(PublicKeyCredentialRpEntity(rp_id, "Checkmk"))


overview_page_name: str = "user_two_factor_overview"


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page(overview_page_name)(UserTwoFactorOverview)
    page_registry.register_page("user_two_factor_edit_credential")(EditCredentialAlias)
    page_registry.register_page("user_webauthn_register_begin")(UserWebAuthnRegisterBegin)
    page_registry.register_page("user_webauthn_register_complete")(UserWebAuthnRegisterComplete)
    page_registry.register_page("user_login_two_factor")(UserLoginTwoFactor)
    page_registry.register_page("user_webauthn_login_begin")(UserWebAuthnLoginBegin)
    page_registry.register_page("user_webauthn_login_complete")(UserWebAuthnLoginComplete)
    page_registry.register_page("user_totp_register")(RegisterTotpSecret)


class UserTwoFactorOverview(ABCUserProfilePage):
    def _page_title(self) -> str:
        return _("Two-factor authentication")

    def __init__(self) -> None:
        super().__init__("general.manage_2fa")

    def _action(self) -> None:
        assert user.id is not None
        credentials = load_two_factor_credentials(user.id)

        if credential_id := request.get_ascii_input("_delete_credential"):
            if credential_id in credentials["webauthn_credentials"]:
                del credentials["webauthn_credentials"][credential_id]
            elif credential_id in credentials["totp_credentials"]:
                del credentials["totp_credentials"][credential_id]
            else:
                return
            save_two_factor_credentials(user.id, credentials)
            flash(_("Selected credential has been deleted"))

        if request.has_var("_backup_codes"):
            codes = make_two_factor_backup_codes()
            credentials["backup_codes"] = [pwhashed for _password, pwhashed in codes]
            save_two_factor_credentials(user.id, credentials)
            flash(
                _(
                    "The following backup codes have been generated: <ul>%s</ul> These codes are "
                    "displayed only now. Save them securely."
                )
                % "".join(f"<li><tt>{password.raw}</tt></li>" for password, _pwhashed in codes)
            )

    def _page_menu(self, breadcrumb) -> PageMenu:  # type: ignore[no-untyped-def]
        page_menu: PageMenu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="actions",
                    title=_("Actions"),
                    topics=[
                        PageMenuTopic(
                            title=_("Actions"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add Security Token"),
                                    icon_name="2fa",
                                    item=make_javascript_link("cmk.webauthn.register()"),
                                    is_shortcut=True,
                                    is_suggested=True,
                                    description=_(
                                        "Make use of Web Authentication also known as WebAuthn to register cryptographic keys generated by authentication devices such as YubiKey."
                                    ),
                                ),
                                PageMenuEntry(
                                    title=_("Add Authenticator App"),
                                    icon_name="2fa",
                                    item=make_simple_link("user_totp_register.py"),
                                    is_shortcut=True,
                                    is_suggested=True,
                                    description=_(
                                        "Make use of an Authenicatior App to generate time-based one-time validation codes."
                                    ),
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
                page_menu_dropdown_user_related(page_name=overview_page_name, show_shortcuts=False),
            ],
            breadcrumb=breadcrumb,
        )
        page_menu.add_doc_reference(title=self._page_title(), doc_ref=DocReference.WATO_USER_2FA)
        return page_menu

    def _show_form(self) -> None:
        assert user.id is not None

        credentials = load_two_factor_credentials(user.id)
        webauthn_credentials = credentials["webauthn_credentials"]
        backup_codes = credentials["backup_codes"]
        totp_credentials = credentials["totp_credentials"]

        html.begin_form("two_factor", method="POST")
        html.div("", id_="webauthn_message")
        forms.header(_("Credentials"))

        forms.section(_("Security Tokens"), simple=True)
        if webauthn_credentials:
            self._show_registered_credentials(webauthn_credentials)
        else:
            html.i(_("Not registered"))

        forms.section(_("Authenticaton Applications"), simple=True)
        if totp_credentials:
            self._show_registered_credentials(totp_credentials)
        else:
            html.i(_("Not registered"))

        forms.section(_("Backup codes"), simple=True)
        if backup_codes:
            html.p(
                _(
                    "You have %d unused backup codes left. You can use them as one-time password "
                    "if your key is not available."
                )
                % len(backup_codes)
            )
            html.i(
                _(
                    "If you regenerate backup codes, you automatically invalidate the existing codes."
                )
            )
        else:
            html.i(_("No backup codes created yet."))

        forms.end()

        html.hidden_fields()
        html.end_form()
        html.footer()

    @classmethod
    def _show_registered_credentials(
        cls, two_factor_credentials: dict[str, TotpCredential] | dict[str, WebAuthnCredential]
    ) -> None:
        with table_element(title=None, searchable=False, sortable=False) as table:
            for credential in two_factor_credentials.values():
                table.row()
                table.cell(_("Actions"), css=["buttons"])
                delete_url = make_confirm_delete_link(
                    url=makeactionuri(
                        request, transactions, [("_delete_credential", credential["credential_id"])]
                    ),
                    title=_("Delete two-factor credential"),
                )
                html.icon_button(delete_url, _("Delete two-factor credential"), "delete")

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


class RegisterTotpSecret(ABCUserProfilePage):
    def _page_title(self) -> str:
        return _("Register Authenticatior App")

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
            _("Profile"), breadcrumb, form_name="profile", button_name="_save", add_cancel_link=True
        )
        return menu

    def _action(self) -> None:
        assert user.id is not None
        credentials = load_two_factor_credentials(user.id, lock=True)

        secret = b32decode(request.get_ascii_input_mandatory("_otp"))
        otp = TOTP(secret, TotpVersion.one)

        vs = self._valuespec()
        provided_otp = vs.from_html_vars("profile")
        now_time = otp.calculate_generation(datetime.datetime.now())
        if otp.check_totp(provided_otp["Validate OTP"], now_time):
            totp_uuid = str(uuid4())
            credentials["totp_credentials"][totp_uuid] = {
                "credential_id": totp_uuid,
                "secret": secret,
                "version": 1,
                "registered_at": int(time.time()),
                "alias": "",
            }
            save_two_factor_credentials(user.id, credentials)
            flash(_("Registration successful"))
            origtarget = "user_two_factor_overview.py"
            raise redirect(origtarget)

        flash(_("Failed"))

    def _show_form(self) -> None:
        assert user.id is not None

        if not request.is_ssl_request:
            origtarget = "user_two_factor_overview.py"
            raise redirect(origtarget)
        secret = TOTP.generate_secret()
        base32_secret = b32encode(secret).decode()

        html.begin_form("profile", method="POST")
        html.prevent_password_auto_completion()
        html.open_div(class_="wato")

        html.p(
            "otpauth://totp/%s?secret=%s&issuer=%s"
            % (
                parse.quote(user.alias, safe=""),
                base32_secret,
                parse.quote("checkmk " + omd_site(), safe=""),
            )
        )

        self._valuespec().render_input(
            "profile",
            {
                "Validate OTP": "",
            },
        )

        forms.end()
        html.close_div()
        html.hidden_field("_otp", base32_secret)
        html.hidden_fields()
        html.end_form()
        html.footer()

    def _valuespec(self) -> Dictionary:
        return Dictionary(
            title=_("Edit credential"),
            optional_keys=False,
            render="form",
            elements=[
                (
                    "Validate OTP",
                    TextInput(title=_("Validate OTP")),
                ),
            ],
        )


class EditCredentialAlias(ABCUserProfilePage):
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
            _("Profile"), breadcrumb, form_name="profile", button_name="_save", add_cancel_link=True
        )
        return menu

    def _action(self) -> None:
        assert user.id is not None
        credentials = load_two_factor_credentials(user.id, lock=True)

        credential_id = request.get_ascii_input_mandatory("_edit")
        if credential_id in credentials["webauthn_credentials"]:
            credential: TotpCredential | WebAuthnCredential = credentials["webauthn_credentials"][
                credential_id
            ]
        elif credential_id in credentials["totp_credentials"]:
            credential = credentials["totp_credentials"][credential_id]
        else:
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
        if credential_id in credentials["webauthn_credentials"]:
            credential: TotpCredential | WebAuthnCredential = credentials["webauthn_credentials"][
                credential_id
            ]
        elif credential_id in credentials["totp_credentials"]:
            credential = credentials["totp_credentials"][credential_id]
        else:
            raise MKUserError("_edit", _("The credential does not exist"))

        html.begin_form("profile", method="POST")
        html.prevent_password_auto_completion()
        html.open_div(class_="wato")

        self._valuespec(credential).render_input(
            "profile",
            {
                "registered_at": self._display_time(credential["registered_at"]),
                "alias": credential["alias"],
            },
        )

        forms.end()
        html.close_div()
        html.hidden_field("_edit", credential_id)
        html.hidden_fields()
        html.end_form()
        html.footer()

    def _display_time(self, epoch_time: int) -> str:
        return time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(epoch_time)
        )  # In future consider UTC aligned time.

    def _valuespec(self, credential: TotpCredential | WebAuthnCredential) -> Dictionary:
        return Dictionary(
            title=_("Edit credential"),
            optional_keys=False,
            render="form",
            elements=[
                (
                    "registered_at",
                    FixedValue(
                        value=self._display_time(credential["registered_at"]),
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
        except MKGeneralException as e:
            response.status_code = http_client.BAD_REQUEST
            response.set_data(str(e))
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

        try:
            auth_data = make_fido2_server().register_complete(
                session.session_info.webauthn_action_state, client_data, att_obj
            )
        except ValueError as e:
            if "Invalid origin in ClientData" in str(e):
                raise MKGeneralException(
                    "The origin %r is not valid. You need to access the UI via HTTPS "
                    "and you need to use a valid host or domain name. See werk #13325 for "
                    "further information" % client_data.get("origin")
                ) from e
            raise

        ident = auth_data.credential_data.credential_id.hex()
        credentials = load_two_factor_credentials(user.id, lock=True)

        if ident in credentials["webauthn_credentials"]:
            raise MKGeneralException(_("Your WebAuthn credential is already in use"))

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


class UserLoginTwoFactor(Page):
    def page(self) -> None:
        assert user.id is not None

        html.render_headfoot = False
        html.add_body_css_class("login")
        html.add_body_css_class("two_factor")
        make_header(html, _("Two-factor authentication"), Breadcrumb(), javascripts=[])

        html.open_div(id_="login")

        html.open_div(id_="login_window")

        html.open_a(href="https://checkmk.com", class_="login_window_logo_link")
        html.img(
            src=theme.detect_icon_path(
                icon_name="login_logo" if theme.has_custom_logo("login_logo") else "checkmk_logo",
                prefix="",
            ),
            id_="logo",
        )
        html.close_a()

        if not is_two_factor_login_enabled(user.id):
            raise MKGeneralException(_("Two-factor authentication not enabled"))

        credentials = load_two_factor_credentials(user.id)
        totp_style = {
            "label": "label_pass",
            "input": "input_pass",
            "button": "_use_totp_code",
            "div": "",
        }
        backup_style = totp_style

        html.label(
            _("Two-factor authentication"),
            for_="webauthn_message",
            id_="label_webauthn",
            class_="legend",
        )

        # WebAuthn
        if credentials["webauthn_credentials"]:
            html.begin_form(
                "webauthn_login",
                method="POST",
                add_transid=False,
                action="user_login_two_factor.py",
            )
            html.prevent_password_auto_completion()
            html.hidden_field(
                "_origtarget", origtarget := request.get_url_input("_origtarget", "index.py")
            )

            html.div("", id_="webauthn_message")
            html.javascript("cmk.webauthn.login()")

            html.hidden_fields()
            html.end_form()

        # TOTP
        if credentials["totp_credentials"]:
            html.begin_form(
                "totp_login", method="POST", add_transid=False, action="user_login_two_factor.py"
            )
            html.prevent_password_auto_completion()
            html.hidden_field(
                "_origtarget", origtarget := request.get_url_input("_origtarget", "index.py")
            )

            if totp_code := request.get_validated_type_input(Password, "_totp_code"):
                totp_credential = credentials["totp_credentials"]
                for credential in totp_credential:
                    otp = TOTP(totp_credential[credential]["secret"], TotpVersion.one)
                    if otp.check_totp(
                        totp_code.raw_bytes.decode(),
                        otp.calculate_generation(datetime.datetime.now()),
                    ):
                        session.session_info.two_factor_completed = True
                        raise HTTPRedirect(origtarget)

            with foldable_container(
                treename="authenticator_app",
                id_="backup_container",
                isopen=False,
                title=_("Use Authenticator App"),
                indent=False,
                save_state=False,
            ):
                html.label(
                    "%s:" % _("OTP code"),
                    id_=totp_style["label"],
                    class_=["legend"],
                    for_="_totp_code",
                )
                html.br()
                html.password_input("_totp_code", id_=totp_style["input"], size=None)

                html.open_div(id_="button_text")
                html.button(totp_style["button"], _("Use authenticator code"), cssclass="hot")
                html.close_div()

            if user_errors:
                html.open_div(id_="login_error")
                html.show_user_errors()
                html.close_div()

            html.hidden_fields()
            html.end_form()

        # Backup
        if credentials["backup_codes"]:
            if credentials["totp_credentials"]:
                backup_style = {
                    "label": "label_backup",
                    "input": "input_backup",
                    "button": "_use_backup_code",
                    "div": "backup_foldable",
                }
            html.begin_form(
                "backup_code_login",
                method="POST",
                add_transid=False,
                action="user_login_two_factor.py",
            )
            html.prevent_password_auto_completion()
            html.hidden_field(
                "_origtarget", origtarget := request.get_url_input("_origtarget", "index.py")
            )

            if backup_code := request.get_validated_type_input(Password, "_backup_code"):
                if is_two_factor_backup_code_valid(user.id, backup_code):
                    session.session_info.two_factor_completed = True
                    raise HTTPRedirect(origtarget)

            html.open_div(class_=backup_style["div"])
            with foldable_container(
                treename="backup_codes",
                id_="backup_container",
                isopen=False,
                title=_("Use backup code"),
                indent=False,
                save_state=False,
            ):
                html.label(
                    "%s:" % _("Backup code"),
                    id_=backup_style["label"],
                    class_=["legend", ""],
                    for_="_backup_code",
                )
                html.br()
                html.password_input("_backup_code", id_=backup_style["input"], size=None)

                html.open_div(id_="button_text")
                html.button(backup_style["button"], _("Use backup code"), cssclass="hot")
                html.close_div()
            html.close_div()

            if user_errors:
                html.open_div(id_="login_error")
                html.show_user_errors()
                html.close_div()

            html.close_div()
            html.hidden_fields()
            html.end_form()

        html.close_div()
        html.footer()


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
        session.session_info.two_factor_completed = True
        return {"status": "OK"}
