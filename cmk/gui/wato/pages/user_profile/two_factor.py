#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The user can change own 2FA related settings on this page"""

import abc
import datetime
import http.client as http_client
import json
import time
from base64 import b32decode, b32encode
from http import HTTPStatus
from typing import assert_never, Literal
from urllib import parse
from uuid import uuid4

import fido2
import fido2.features
from fido2.server import Fido2Server
from fido2.webauthn import (
    AttestedCredentialData,
    AuthenticatorAssertionResponse,
    AuthenticatorAttachment,
    AuthenticatorAttestationResponse,
    PublicKeyCredentialRpEntity,
    PublicKeyCredentialUserEntity,
    UserVerificationRequirement,
)

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site
from cmk.ccc.user import UserId

from cmk.utils.jsontype import JsonSerializable
from cmk.utils.log.security_event import log_security_event

from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem, make_simple_page_breadcrumb
from cmk.gui.config import Config
from cmk.gui.crash_handler import handle_exception_as_gui_crash_report
from cmk.gui.ctx_stack import g
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import (
    make_javascript_link,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import Page, PageEndpoint, PageRegistry
from cmk.gui.session import session
from cmk.gui.site_config import has_wato_slave_sites, is_wato_slave_site
from cmk.gui.table import Table, table_element
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import (
    TotpCredential,
    TwoFactorCredentials,
    WebAuthnActionState,
    WebAuthnCredential,
)
from cmk.gui.userdb import (
    is_two_factor_backup_code_valid,
    is_two_factor_login_enabled,
    load_two_factor_credentials,
    make_two_factor_backup_codes,
    on_failed_login,
    user_locked,
)
from cmk.gui.userdb.store import save_custom_attr, save_two_factor_credentials
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
from cmk.gui.utils.security_log_events import TwoFactorEvent, TwoFactorEventType, TwoFAFailureEvent
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    make_confirm_delete_link,
    makeactionuri,
    makeuri,
    makeuri_contextless,
)
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.utils.user_security_message import SecurityNotificationEvent, send_security_message
from cmk.gui.valuespec import Dictionary, FixedValue, TextInput
from cmk.gui.watolib.mode import redirect

from cmk.crypto.password import Password
from cmk.crypto.password_hashing import PasswordHash
from cmk.crypto.totp import TOTP

from .abstract_page import ABCUserProfilePage
from .page_menu import page_menu_dropdown_user_related

# NOTE: In fido2 >= 2.0.0, this feature has been removed and is enabled per default, see
# https://github.com/Yubico/python-fido2/blob/main/doc/Migration_1-2.adoc#removal-of-featureswebauthn_json_mapping
# TODO: Remove this when we upgraded to fido2 2.0.0.
if _webauthn_json_mapping := getattr(fido2.features, "webauthn_json_mapping", None):
    _webauthn_json_mapping.enabled = True


def make_fido2_server() -> Fido2Server:
    rp_id = request.host
    logger.debug("Using %r as relaying party ID", rp_id)
    # apparently the browsers allow localhost as a secure domain, but the
    # Fido2Server does not. We do not really care if the rp_id is also the
    # origin sent from the browser. We feel the browser is supposed to check
    # for that. So the verify_origin function should always return True...
    return Fido2Server(
        PublicKeyCredentialRpEntity(name="Checkmk", id=rp_id),
        verify_origin=lambda _o: True,
    )


def _log_event_usermanagement(event: TwoFactorEventType) -> None:
    assert user.id is not None
    log_security_event(
        TwoFactorEvent(
            event=event,
            username=user.id,
        )
    )


def _log_event_auth(two_factor_method: str) -> None:
    log_security_event(
        TwoFAFailureEvent(
            user_error="Failed two factor authentication",
            two_fa_method=two_factor_method,
            username=user.id,
            remote_ip=request.remote_ip,
        )
    )


def _handle_failed_auth(user_id: UserId) -> None:
    on_failed_login(user_id, datetime.datetime.now())
    if user_locked(user_id):
        session.invalidate()
        session.persist()
        raise MKUserError(None, _("User is locked"), HTTPStatus.UNAUTHORIZED)


def _handle_success_auth(user_id: UserId) -> None:
    session.session_info.two_factor_completed = True
    save_custom_attr(user_id, "num_failed_logins", 0)


def _sec_notification_event_from_2fa_event(
    event: TwoFactorEventType,
) -> SecurityNotificationEvent:
    match event:
        case TwoFactorEventType.totp_add:
            return SecurityNotificationEvent.totp_added
        case TwoFactorEventType.totp_remove:
            return SecurityNotificationEvent.totp_removed
        case TwoFactorEventType.webauthn_add_:
            return SecurityNotificationEvent.webauthn_added
        case TwoFactorEventType.webauthn_remove:
            return SecurityNotificationEvent.webauthn_removed
        case TwoFactorEventType.backup_add:
            return SecurityNotificationEvent.backup_reset
        case TwoFactorEventType.backup_remove:
            return SecurityNotificationEvent.backup_revoked
        case TwoFactorEventType.backup_used:
            return SecurityNotificationEvent.backup_used
        case _:
            assert_never()


def _handle_revoke_all_backup_codes(user: LoggedInUser, credentials: TwoFactorCredentials) -> None:
    credentials["backup_codes"] = []
    flash(_("All backup codes have been deleted"))
    _save_credentials_all_sites(
        user,
        "user_two_factor_overview.py",
        credentials,
        TwoFactorEventType.backup_remove,
    )


def _save_credentials_all_sites(
    user: LoggedInUser,
    origtarget: str,
    credentials: TwoFactorCredentials,
    log_event: TwoFactorEventType | Literal["alias_changed"],
) -> None:
    if (user_id := user.id) is None:
        return

    save_two_factor_credentials(user_id, credentials)
    if log_event != "alias_changed":
        _log_event_usermanagement(log_event)
        send_security_message(user_id, _sec_notification_event_from_2fa_event(log_event))
    if has_wato_slave_sites():
        raise redirect(
            makeuri_contextless(
                request, [("back", origtarget)], filename="user_profile_replicate.py"
            )
        )


overview_page_name: str = "user_two_factor_overview"


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint(overview_page_name, UserTwoFactorOverview))
    page_registry.register(PageEndpoint("user_two_factor_enforce", UserTwoFactorEnforce))
    page_registry.register(PageEndpoint("user_two_factor_edit_credential", EditCredentialAlias))
    page_registry.register(PageEndpoint("user_webauthn_register_begin", UserWebAuthnRegisterBegin))
    page_registry.register(
        PageEndpoint("user_webauthn_register_complete", UserWebAuthnRegisterComplete)
    )
    page_registry.register(PageEndpoint("user_login_two_factor", UserLoginTwoFactor))
    page_registry.register(PageEndpoint("user_webauthn_login_begin", UserWebAuthnLoginBegin))
    page_registry.register(PageEndpoint("user_webauthn_login_complete", UserWebAuthnLoginComplete))
    page_registry.register(PageEndpoint("user_totp_register", RegisterTotpSecret))


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
                flash(_("Selected credential has been deleted"))
                _save_credentials_all_sites(
                    user,
                    "user_two_factor_overview.py",
                    credentials,
                    TwoFactorEventType.webauthn_remove,
                )
            elif credential_id in credentials["totp_credentials"]:
                del credentials["totp_credentials"][credential_id]
                flash(_("Selected credential has been deleted"))
                _save_credentials_all_sites(
                    user,
                    "user_two_factor_overview.py",
                    credentials,
                    TwoFactorEventType.totp_remove,
                )
            else:
                return
            if not is_two_factor_login_enabled(user.id):
                session.session_info.two_factor_completed = False
                if credentials["backup_codes"]:
                    _handle_revoke_all_backup_codes(user, credentials)

        if request.has_var("_delete_codes"):
            _handle_revoke_all_backup_codes(user, credentials)

        if request.has_var("_backup_codes"):
            codes = make_two_factor_backup_codes()
            credentials["backup_codes"] = [pwhashed for _password, pwhashed in codes]
            flash(self.flash_new_backup_codes(codes))
            _save_credentials_all_sites(
                user,
                "user_two_factor_overview.py",
                credentials,
                TwoFactorEventType.backup_add,
            )

    def flash_new_backup_codes(self, codes: list[tuple[Password, PasswordHash]]) -> HTML:
        backup_codes = "\n".join(pw.raw for pw, _hash in codes)
        success_message = _("Codes copied")
        header_msg = html.render_h3(html.render_b("Successfully generated 10 backup codes"))
        message1 = html.render_p(
            _(
                "Each code may be used only once. Store these backup codes in a safe place. "
                "If you lose access to your authentication device and backup codes, you'll have to "
                "contact your Checkmk admin to recover your account."
            )
        )
        codesdiv = html.render_div(
            HTML.empty().join(
                [html.render_div(code.raw, class_="codelistelement") for code, _v in codes]
            ),
            class_="codelist",
        )
        message2 = html.render_p(_("These codes are only displayed now."))
        copy_button = html.render_input(
            "copy codes",
            type_="button",
            onclick=f"cmk.utils.copy_to_clipboard({json.dumps(backup_codes)}, {json.dumps(success_message)})",
            value=_("Copy codes to clipboard"),
            class_=["button buttonlink"],
        )
        return HTML.empty().join([header_msg, message1, codesdiv, message2, copy_button])

    def _page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        assert user.id is not None
        credentials = load_two_factor_credentials(user.id)
        registered_credentials = list(credentials["webauthn_credentials"].keys()) + list(
            credentials["totp_credentials"].keys()
        )
        # Take possible page actions into account before they are executed
        backup_codes_given = (
            bool(credentials["backup_codes"])
            or request.has_var("_backup_codes")
            and not request.has_var("_delete_codes")
        )
        enable_backup_codes = any(credentials.values()) and (
            [request.get_ascii_input("_delete_credential")] != registered_credentials
        )

        if backup_codes_given:
            backup_codes_item = make_simple_link(
                make_confirm_delete_link(
                    url=makeactionuri(request, transactions, [("_backup_codes", "SET")]),
                    title=_("Regenerate backup codes"),
                    confirm_button=_("Regenerate codes"),
                    message="Generating backup codes automatically invalidates existing codes",
                ),
            )
        else:
            backup_codes_item = make_simple_link(
                makeactionuri(request, transactions, [("_backup_codes", "SET")]),
            )

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
                                    title=_("Register authenticator app"),
                                    icon_name="2fa",
                                    item=make_simple_link("user_totp_register.py"),
                                    is_shortcut=True,
                                    is_suggested=True,
                                    description=_(
                                        "Make use of an authenicator app to generate time-based one-time validation codes."
                                    ),
                                ),
                                PageMenuEntry(
                                    title=_("Register security token"),
                                    icon_name="2fa",
                                    item=make_javascript_link("cmk.webauthn.register()"),
                                    is_shortcut=True,
                                    is_suggested=True,
                                    description=_(
                                        "Make use of Web Authentication also known as WebAuthn to "
                                        "register cryptographic keys generated by authentication "
                                        "devices such as YubiKey."
                                    ),
                                ),
                                PageMenuEntry(
                                    title=(
                                        _("Regenerate backup codes")
                                        if backup_codes_given
                                        else _("Generate backup codes")
                                    ),
                                    icon_name="2fa_backup_codes",
                                    item=backup_codes_item,
                                    is_enabled=enable_backup_codes,
                                    is_shortcut=True,
                                    is_suggested=True,
                                    disabled_tooltip=_(
                                        "Register an authentication device before generating "
                                        "backup codes."
                                    ),
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

    def _render_credentials_table_rows(
        self,
        credentials: dict[str, TotpCredential] | dict[str, WebAuthnCredential],
        what: Literal["totp", "webauthn"],
        table: Table,
    ) -> None:
        name = _("authenticator app") if what == "totp" else _("security token")
        title = _("Authenticator apps") if what == "totp" else _("Security tokens")

        table.groupheader(title + (f" ({len(credentials)})" if credentials else ""))
        if credentials:
            self._show_registered_credentials(credentials, what, table)
        else:
            table.row()
            table.cell(
                "",
                html.render_i(
                    _("Click on 'Register %s' to enable two-factor authentication via %s.")
                    % (name, name)
                ),
                colspan=2,
            )

    def _render_backup_codes_table_rows(
        self, backup_codes: list[PasswordHash], table: Table
    ) -> None:
        table.groupheader(
            _("Backup codes") + (f" ({len(backup_codes)}/10)" if backup_codes else "")
        )
        table.row()
        if backup_codes:
            backup_codes_content = html.render_div(
                html.render_div(
                    _("Backup codes left:") + html.render_span("." * 200, class_=["dots"]),
                    class_="legend",
                )
                + html.render_div(f" {len(backup_codes)}/10", class_="inline"),
                class_="backup_codes",
            )
            backup_codes_info = html.render_div(
                _(
                    "If you lose access to your authentication app / security token, you can use "
                    "any of these codes to login. Generating backup codes automatically "
                    "invalidates existing codes."
                ),
            )

            invalidate_codes_url = make_confirm_delete_link(
                url=makeactionuri(request, transactions, [("_delete_codes", "")]),
                title=_("Invalidate all backup codes"),
                confirm_button=_("Invalidate all"),
            )
            invalidate_codes_button = html.render_div(
                html.render_input(
                    "invalidate_codes",
                    type_="button",
                    onclick="location.href=%s" % json.dumps(invalidate_codes_url),
                    value=_("Invalidate all codes"),
                    class_=["button buttonlink"],
                ),
            )
        else:
            backup_codes_content = html.render_i(_("No backup codes generated yet."))
            backup_codes_info = html.render_div(
                _(
                    "If you lose access to your authentication device, you can use any of the "
                    "generated backup codes to login."
                )
            )

        table.cell(
            "",
            backup_codes_content
            + backup_codes_info
            + (invalidate_codes_button if backup_codes else ""),
        )

    def _show_form(self) -> None:
        assert user.id is not None

        if is_wato_slave_site():
            html.user_error(
                MKUserError(
                    None,
                    _(
                        "Changes to a user's two-factor settings within remote sites will "
                        "be overritten by changes to the user's settings in the central site."
                    ),
                ),
                True,
            )

        credentials = load_two_factor_credentials(user.id)
        webauthn_credentials = credentials["webauthn_credentials"]
        backup_codes = credentials["backup_codes"]
        totp_credentials = credentials["totp_credentials"]

        html.div("", id_="webauthn_message")
        html.open_div(class_="two_factor_overview")

        with table_element(sortable=False, omit_headers=not bool(totp_credentials)) as table:
            self._render_credentials_table_rows(totp_credentials, "totp", table)
            if totp_credentials and webauthn_credentials:  # render both in one table
                self._render_credentials_table_rows(webauthn_credentials, "webauthn", table)

        if not (totp_credentials and webauthn_credentials):
            with table_element(
                sortable=False, omit_headers=(not bool(webauthn_credentials))
            ) as table:
                self._render_credentials_table_rows(webauthn_credentials, "webauthn", table)

        with table_element(sortable=False, omit_headers=True) as table:
            self._render_backup_codes_table_rows(backup_codes, table)

        html.close_div()
        html.footer()

    @classmethod
    def _show_registered_credentials(
        cls,
        two_factor_credentials: (dict[str, TotpCredential] | dict[str, WebAuthnCredential]),
        what: Literal["totp", "webauthn"],
        table: Table,
    ) -> None:
        name = _("authenticator app") if what == "totp" else _("security token")
        for credential in two_factor_credentials.values():
            table.row()
            table.cell(_("Actions"), css=["buttons"])

            html.icon_button(
                makeuri_contextless(
                    request,
                    [("_edit", credential["credential_id"])],
                    filename="user_two_factor_edit_credential.py",
                ),
                _("Edit this credential"),
                "edit",
            )

            delete_title = (
                _("Delete authentication via ")
                + name
                + (f" '{alias}'" if (alias := credential["alias"]) else "")
            )
            delete_url = make_confirm_delete_link(
                url=makeactionuri(
                    request,
                    transactions,
                    [("_delete_credential", credential["credential_id"])],
                ),
                title=delete_title,
                message=_("Registered at ")
                + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(credential["registered_at"])),
            )
            html.icon_button(delete_url, delete_title, "delete")

            table.cell(_("Alias"), credential["alias"])
            table.cell(
                _("Registered at"),
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(credential["registered_at"])),
            )


class UserTwoFactorEnforce(ABCUserProfilePage):
    def _page_title(self) -> str:
        return _("Two-factor authentication")

    def __init__(self) -> None:
        super().__init__("general.manage_2fa")

    def _action(self) -> None:
        assert user.id is not None

    def _page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        assert user.id is not None

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
                                    title=_("Register authenticator app"),
                                    icon_name="2fa",
                                    item=make_simple_link("user_totp_register.py"),
                                    is_shortcut=True,
                                    is_suggested=True,
                                    description=_(
                                        "Make use of an authenicator app to generate time-based one-time validation codes."
                                    ),
                                ),
                                PageMenuEntry(
                                    title=_("Register security token"),
                                    icon_name="2fa",
                                    item=make_javascript_link("cmk.webauthn.register()"),
                                    is_shortcut=True,
                                    is_suggested=True,
                                    description=_(
                                        "Make use of Web Authentication also known as WebAuthn to "
                                        "register cryptographic keys generated by authentication "
                                        "devices such as YubiKey."
                                    ),
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

    def _render_credentials_table_rows(
        self,
        credentials: dict[str, TotpCredential] | dict[str, WebAuthnCredential],
        what: Literal["totp", "webauthn"],
        table: Table,
    ) -> None:
        name = _("authenticator app") if what == "totp" else _("security token")
        title = _("Authenticator apps") if what == "totp" else _("Security tokens")

        table.groupheader(title + (f" ({len(credentials)})" if credentials else ""))
        table.row()
        table.cell(
            "",
            html.render_i(
                _("Click on 'Register %s' to enable two-factor authentication via %s.")
                % (name, name)
            ),
            colspan=2,
        )

    def _show_form(self) -> None:
        assert user.id is not None

        if is_wato_slave_site():
            html.user_error(
                MKUserError(
                    None,
                    _(
                        "Changes to a user's two-factor settings within remote sites will "
                        "be overritten by changes to the user's settings in the central site."
                    ),
                ),
                True,
            )

        credentials = load_two_factor_credentials(user.id)
        webauthn_credentials = credentials["webauthn_credentials"]
        totp_credentials = credentials["totp_credentials"]

        html.div("", id_="webauthn_message")
        html.show_warning(
            _(
                "Your administrator has enforced two-factor authentication for your account. Kindly register one of the following two-factor mechanisms:"
            )
        )
        html.open_div(class_="two_factor_overview")

        with table_element(sortable=False, omit_headers=not bool(totp_credentials)) as table:
            self._render_credentials_table_rows(totp_credentials, "totp", table)
            self._render_credentials_table_rows(webauthn_credentials, "webauthn", table)

        html.close_div()
        html.footer()


class RegisterTotpSecret(ABCUserProfilePage):
    def _page_title(self) -> str:
        return _("Register authenticator app")

    def __init__(self, secret: bytes | None = None) -> None:
        super().__init__("general.manage_2fa")
        self.secret = secret

    def _breadcrumb(self) -> Breadcrumb:
        breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_user(), self._page_title())
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
            _("Profile"),
            breadcrumb,
            form_name="register_totp",
            button_name="_save",
            add_cancel_link=True,
        )
        return menu

    def _action(self) -> None:
        auth_code_vs = TextInput(allow_empty=False)
        auth_code = auth_code_vs.from_html_vars("auth_code")
        auth_code_vs.validate_value(auth_code, "auth_code")

        assert user.id is not None
        credentials = load_two_factor_credentials(user.id, lock=True)

        self.secret = b32decode(request.get_ascii_input_mandatory("_otp"))
        otp = TOTP(self.secret)

        alias = TextInput().from_html_vars("alias")
        now_time = otp.calculate_generation(datetime.datetime.now())
        if otp.check_totp(auth_code, now_time):
            totp_uuid = str(uuid4())
            credentials["totp_credentials"][totp_uuid] = {
                "credential_id": totp_uuid,
                "secret": self.secret,
                "version": 1,
                "registered_at": int(time.time()),
                "alias": alias or "",
            }
            if not session.session_info.two_factor_required:
                # This will trigger when a user is adding a new TOTP secret from the overview page.
                # We redirect the user back as TOTP is added through a seperate page they are sent to.
                origtarget = "user_two_factor_overview.py"
            else:
                # When a user has added TOTP as part of Two Factor Enforcement the user will have
                # been forwarded to a enforcement page based on the below session boolean being
                # set at login. We want them to then enter the main site after a successful TOTP add.
                session.session_info.two_factor_required = False
                origtarget = "index.py"
            session.session_info.two_factor_completed = True
            flash(_("Registration successful"))
            _save_credentials_all_sites(
                user,
                origtarget,
                credentials,
                TwoFactorEventType.totp_add,
            )

            raise redirect(origtarget)
        flash(_("Failed"))

    def _show_form(self) -> None:
        assert user.id is not None
        assert user.alias is not None

        if not self.secret:
            self.secret = TOTP.generate_secret()
        base32_secret = b32encode(self.secret).decode()

        with html.form_context("register_totp", method="POST"):
            html.prevent_password_auto_completion()
            html.open_div(class_="wato")

            forms.header("1. %s" % _("Scan QR-Code or enter secret manually"), foldable=False)
            forms.section(legend=False)

            html.call_ts_function(
                container="div",
                function_name="render_qr_code",
                arguments={
                    "qrcode": "otpauth://totp/%s?secret=%s&issuer=%s"
                    % (
                        parse.quote(user.alias, safe=""),
                        base32_secret,
                        parse.quote("checkmk " + omd_site(), safe=""),
                    ),
                },
            )

            html.open_div()
            html.span("Secret: ")
            html.a(
                html.render_span(base32_secret) + html.render_icon("insert"),
                href="javascript:void(0)",
                onclick="cmk.utils.copy_to_clipboard(%s, %s);"
                % (
                    json.dumps(base32_secret),
                    json.dumps(_("Successfully copied to clipboard")),
                ),
                title=_("Copy secret to clipboard"),
                class_="copy_to_clipboard",
            )
            html.close_div()

            forms.header("2. %s" % _("Enter authentication code"), foldable=False, css="wide")
            forms.section(legend=False)
            html.span(
                _(
                    "Open the two-factor authenticator app on your device and enter the shown "
                    "authentication code below."
                )
            )
            forms.section(_("Authentication code (OTP / TOTP)"), is_required=True)
            TextInput().render_input("auth_code", "")

            forms.header("3. %s" % _("Enter alias (optional)"), foldable=False, css="wide")
            forms.section("Alias")
            TextInput().render_input("alias", "")
            forms.section(legend=False)
            html.span(_("Click ‘Save’ to enable the two-factor authentication."))

            forms.end()
            html.close_div()
            html.hidden_field("_otp", base32_secret)
            html.hidden_fields()
        html.footer()


class EditCredentialAlias(ABCUserProfilePage):
    def _page_title(self) -> str:
        return _("Edit credential")

    def __init__(self) -> None:
        super().__init__("general.manage_2fa")

    def _breadcrumb(self) -> Breadcrumb:
        breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_user(), self._page_title())
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
            _("Profile"),
            breadcrumb,
            form_name="profile",
            button_name="_save",
            add_cancel_link=True,
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

        flash(_("Successfully changed the credential."))
        _save_credentials_all_sites(
            user, "user_two_factor_overview.py", credentials, "alias_changed"
        )

        raise redirect("user_two_factor_overview.py")

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

        with html.form_context("profile", method="POST"):
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


class JsonPage(Page, abc.ABC):
    def handle_page(self, config: Config) -> None:
        try:
            response.set_content_type("application/json")
            response.set_data(json.dumps(self.page(config)))
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
    def page(self, config: Config) -> JsonSerializable:
        """Override this to implement the page functionality"""
        raise NotImplementedError()


def _serialize_webauthn_state(state: dict) -> WebAuthnActionState:
    """the fido2 lib used to use native types and we use literal_eval. Now the
    fido2 lib uses enums and dataclasses, so we need to convert between the
    literal_eval world and the fido2 world..."""

    if "challenge" in state and "user_verification" in state:
        return WebAuthnActionState(
            challenge=state["challenge"],
            user_verification=state["user_verification"].value,
        )
    raise NotImplementedError


class UserWebAuthnRegisterBegin(JsonPage):
    def page(self, config: Config) -> JsonSerializable:
        assert user.id is not None

        if not session.two_factor_enforced():
            user.need_permission("general.manage_2fa")

        registration_data, state = make_fido2_server().register_begin(
            PublicKeyCredentialUserEntity(
                name=user.id,
                id=user.id.encode("utf-8"),
                display_name=user.alias,
            ),
            [
                AttestedCredentialData.unpack_from(v["credential_data"])[0]
                for v in load_two_factor_credentials(user.id)["webauthn_credentials"].values()
            ],
            user_verification=UserVerificationRequirement.DISCOURAGED,
            authenticator_attachment=AuthenticatorAttachment.CROSS_PLATFORM,
        )

        session.session_info.webauthn_action_state = _serialize_webauthn_state(state)
        logger.debug("Registration data: %r", registration_data)
        return dict(registration_data)


class UserWebAuthnRegisterComplete(JsonPage):
    def page(self, config: Config) -> JsonSerializable:
        assert user.id is not None

        if not session.two_factor_enforced():
            user.need_permission("general.manage_2fa")

        raw_data = request.get_data()
        logger.debug("Raw request: %r", raw_data)
        data = AuthenticatorAttestationResponse.from_dict(json.loads(raw_data))
        logger.debug("Client data: %r", data.client_data)
        logger.debug("Attestation object: %r", data.attestation_object)

        try:
            auth_data = make_fido2_server().register_complete(
                state=session.session_info.webauthn_action_state,
                response={  # TODO: Passing a RegistrationResponse would be nicer here.
                    "client_data": data.client_data,
                    "attestation_object": data.attestation_object,
                },
            )
        except ValueError as e:
            if "Invalid origin in ClientData" in str(e):
                raise MKGeneralException(
                    "The origin %r is not valid. You need to access the UI via HTTPS "
                    "and you need to use a valid host or domain name. See werk #13325 for "
                    "further information" % data.client_data.origin
                ) from e
            raise

        assert auth_data.credential_data is not None
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
        _log_event_usermanagement(TwoFactorEventType.webauthn_add_)
        send_security_message(user.id, SecurityNotificationEvent.webauthn_added)
        session.session_info.two_factor_completed = True
        flash(_("Registration successful"))
        navigation_json = {"status": "OK", "redirect": False, "replicate": False}
        if has_wato_slave_sites():
            navigation_json["replicate"] = True
        if session.session_info.two_factor_required:
            session.session_info.two_factor_required = False
            navigation_json["redirect"] = True
        return navigation_json  # type: ignore[return-value]


class UserLoginTwoFactor(Page):
    @classmethod
    def _render_backup_link(cls, origtarget: str) -> None:
        html.open_div(class_="button_text")
        html.a(
            _("Use backup code"),
            href=makeuri(request, [("_mode", "backup"), ("_origtarget", origtarget)]),
        )
        html.close_div()

    @classmethod
    def _render_totp_link(cls, origtarget: str) -> None:
        html.open_div(class_="button_text")
        html.a(
            _("Use authenticator app"),
            href=makeuri(request, [("_mode", "totp"), ("_origtarget", origtarget)]),
        )
        html.close_div()

    @classmethod
    def _render_totp(cls, available_methods: set[str]) -> None:
        html.p(_("Enter the six-digit code from your authenticator app to log in."))
        with html.form_context(
            "totp_login",
            method="POST",
            add_transid=False,
            action="user_login_two_factor.py",
        ):
            html.prevent_password_auto_completion()
            html.hidden_field(
                "_origtarget",
                origtarget := request.get_url_input("_origtarget", "index.py"),
            )

            html.open_div(id_="code_input")
            html.label("%s:" % _("Two-factor code"), for_="_totp_code")
            html.password_input("_totp_code", size=None)
            html.close_div()

            html.open_div(class_="button_text")
            html.button("_use_totp_code", _("Submit"), cssclass="hot")
            html.close_div()

            if "backup_codes" in available_methods:
                cls._render_backup_link(origtarget)

            html.hidden_fields()

    @classmethod
    def _render_backup(cls, available_methods: set[str]) -> None:
        html.p(_("Use one of your backup codes to sign in."))
        with html.form_context(
            "backup_code_login",
            method="POST",
            add_transid=False,
            action="user_login_two_factor.py",
        ):
            html.prevent_password_auto_completion()
            html.hidden_field(
                "_origtarget",
                origtarget := request.get_url_input("_origtarget", "index.py"),
            )

            html.open_div(id_="code_input")
            html.label("%s:" % _("Backup code"), for_="_backup_code")
            html.password_input("_backup_code", size=None)
            html.close_div()

            html.open_div(class_="button_text")
            html.button("_use_backup_code", _("Use backup code"), cssclass="hot")
            html.close_div()

            if "totp_credentials" in available_methods:
                cls._render_totp_link(origtarget)

            html.hidden_fields()

    @classmethod
    def _render_webauthn(cls, available_methods: set[str]) -> None:
        html.p(_("Please follow your browser's instructions for authentication."))
        html.prevent_password_auto_completion()
        html.hidden_field(
            "_origtarget",
            origtarget := request.get_url_input("_origtarget", "index.py"),
        )
        html.div("", id_="webauthn_message")
        html.javascript("cmk.webauthn.login()")

        if "backup_codes" in available_methods:
            html.open_div(class_="button_text")
            html.buttonlink(
                text=_("Use backup code"),
                href=makeuri(request, [("_mode", "backup"), ("_origtarget", origtarget)]),
                class_=["mode_button"],
            )
            html.close_div()
        if "totp_credentials" in available_methods:
            cls._render_totp_link(origtarget)

        html.hidden_fields()

    @classmethod
    def _render_multiple_methods(cls, available_methods: set[str]) -> None:
        html.p(
            _(
                "You have multiple methods enabled. Please select the security method you want "
                "to use to log in."
            )
        )
        html.hidden_field(
            "_origtarget",
            origtarget := request.get_url_input("_origtarget", "index.py"),
        )
        if "totp_credentials" in available_methods:
            html.open_div(class_="button_text")
            html.buttonlink(
                text=_("Authenticator app"),
                href=makeuri(request, [("_mode", "totp"), ("_origtarget", origtarget)]),
                class_=["mode_button"],
            )
            html.close_div()
        if "webauthn_credentials" in available_methods:
            html.open_div(class_="button_text")
            html.buttonlink(
                text=_("Security token"),
                href=makeuri(request, [("_mode", "webauthn"), ("_origtarget", origtarget)]),
                class_=["mode_button"],
            )
            html.close_div()
        if "backup_codes" in available_methods:
            cls._render_backup_link(origtarget)

        html.hidden_fields()

    @classmethod
    def _check_totp_and_backup(
        cls, available_methods: set[str], credentials: TwoFactorCredentials
    ) -> None:
        assert user.id is not None
        if "totp_credentials" in available_methods:
            if totp_code := request.get_validated_type_input(Password, "_totp_code"):
                totp_credential = credentials["totp_credentials"]
                for credential in totp_credential:
                    otp = TOTP(totp_credential[credential]["secret"])
                    if otp.check_totp(
                        totp_code.raw_bytes.decode(),
                        otp.calculate_generation(datetime.datetime.now()),
                    ):
                        _handle_success_auth(user.id)
                        raise redirect(request.get_url_input("_origtarget", "index.py"))
                _log_event_auth("Authenticator application (TOTP)")
                _handle_failed_auth(user.id)
                raise MKUserError(None, _("Invalid code provided"), HTTPStatus.UNAUTHORIZED)

        if "backup_codes" in available_methods:
            if backup_code := request.get_validated_type_input(Password, "_backup_code"):
                if is_two_factor_backup_code_valid(user.id, backup_code):
                    _log_event_usermanagement(TwoFactorEventType.backup_used)
                    send_security_message(user.id, SecurityNotificationEvent.backup_used)
                    _handle_success_auth(user.id)
                    if has_wato_slave_sites():
                        raise redirect(
                            makeuri_contextless(
                                request,
                                [("back", "dashboard.py")],
                                filename="user_profile_replicate.py",
                            )
                        )
                    raise redirect(request.get_url_input("_origtarget", "index.py"))
                _log_event_auth("Backup code")
                _handle_failed_auth(user.id)
                raise MKUserError(None, _("Invalid code provided"), HTTPStatus.UNAUTHORIZED)

    def page(self, config: Config) -> None:
        assert user.id is not None

        html.render_headfoot = False
        html.add_body_css_class("login")
        html.add_body_css_class("two_factor")
        make_header(html, _("Two-factor authentication"), Breadcrumb())
        mode = request.get_url_input("_mode", "")

        html.open_div(id_="login")

        html.open_div(id_="login_window")

        html.open_a(href="https://checkmk.com", class_="login_window_logo_link")
        html.img(
            src=theme.detect_icon_path(
                icon_name=("login_logo" if theme.has_custom_logo("login_logo") else "checkmk_logo"),
                prefix="",
            ),
            id_="logo",
        )
        html.close_a()

        if not is_two_factor_login_enabled(user.id):
            raise MKGeneralException(_("Two-factor authentication not enabled"))

        credentials = load_two_factor_credentials(user.id)
        available_methods = {method_name for method_name, m in credentials.items() if m}
        html.h1(_("Two-factor authentication"))
        if (
            "webauthn_credentials" in available_methods
            and "totp_credentials" in available_methods
            and not mode
        ):
            self._render_multiple_methods(available_methods)
        # TOTP
        elif "totp_credentials" in available_methods and (mode == "totp" or not mode):
            self._render_totp(available_methods)
        # WebAuthn
        elif "webauthn_credentials" in available_methods and (mode == "webauthn" or not mode):
            self._render_webauthn(available_methods)
        # Backup
        elif "backup_codes" in available_methods and (mode == "backup" or not mode):
            self._render_backup(available_methods)

        self._check_totp_and_backup(available_methods, credentials)

        if user_errors:
            html.open_div(id_="login_error")
            html.show_user_errors()
            html.close_div()

        html.close_div()
        html.close_div()
        html.footer()


class UserWebAuthnLoginBegin(JsonPage):
    def page(self, config: Config) -> JsonSerializable:
        assert user.id is not None

        if not is_two_factor_login_enabled(user.id):
            raise MKGeneralException(_("Two-factor authentication not enabled"))
        auth_data, state = make_fido2_server().authenticate_begin(
            [
                AttestedCredentialData.unpack_from(v["credential_data"])[0]
                for v in load_two_factor_credentials(user.id)["webauthn_credentials"].values()
            ],
            user_verification=UserVerificationRequirement.DISCOURAGED,
        )

        session.session_info.webauthn_action_state = _serialize_webauthn_state(state)
        logger.debug("Authentication data: %r", auth_data)
        return dict(auth_data)


class UserWebAuthnLoginComplete(JsonPage):
    def page(self, config: Config) -> JsonSerializable:
        assert user.id is not None

        if not is_two_factor_login_enabled(user.id):
            raise MKGeneralException(_("Two-factor authentication not enabled"))

        data = AuthenticatorAssertionResponse.from_dict(json.loads(request.get_data()))
        logger.debug("ClientData: %r", data.client_data)
        logger.debug("AuthenticatorData: %r", data.authenticator_data)

        try:
            make_fido2_server().authenticate_complete(
                state=session.session_info.webauthn_action_state,
                credentials=[
                    AttestedCredentialData.unpack_from(v["credential_data"])[0]
                    for v in load_two_factor_credentials(user.id)["webauthn_credentials"].values()
                ],
                response={  # TODO: Passing an AuthenticationResponse would be nicer here.
                    "credential_id": data.credential_id,
                    "client_data": data.client_data,
                    "auth_data": data.authenticator_data,
                    "signature": data.signature,
                },
            )
        except BaseException:
            _log_event_auth("Webauthn")
            _handle_failed_auth(user.id)
            raise

        session.session_info.webauthn_action_state = None
        session.session_info.two_factor_completed = True
        save_custom_attr(user.id, "num_failed_logins", 0)
        return {"status": "OK"}
