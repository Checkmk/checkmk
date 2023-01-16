#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Collection, Iterator
from pathlib import Path

from cmk.utils.paths import (
    saml2_custom_signature_private_keyfile,
    saml2_custom_signature_public_keyfile,
)

import cmk.gui.forms as forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import (
    make_form_submit_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.plugins.userdb.utils import (
    active_connections_by_type,
    load_connection_config,
    load_roles,
    save_connection_config,
)
from cmk.gui.plugins.wato.utils import mode_url, redirect, WatoMode
from cmk.gui.plugins.wato.utils.base_modes import ModeRegistry
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.userdb.saml2.config import CertificateType, determine_certificate_type
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import (
    CascadingDropdown,
    CertificateWithPrivateKey,
    Dictionary,
    DictionaryEntry,
    DictionaryModel,
    FixedValue,
    HTTPSUrl,
    Integer,
    ListOf,
    rule_option_elements,
    TextInput,
    Tuple,
    UUID,
)
from cmk.gui.wato.pages.userdb_common import (
    add_connections_page_menu,
    connection_actions,
    render_connections_page,
)


def _general_properties() -> list[DictionaryEntry]:
    return [
        (
            "id",
            UUID(
                title=_("Connection ID"),
                help=_(
                    "Internal ID that Checkmk uses to uniquely identify each connection to an Identity Provider."
                ),
            ),
        ),
        (
            "name",
            TextInput(
                title=_("Name"),
                help=_(
                    "A user-friendly name to identify this connection. This will be used for the "
                    "log-in button that is shown on the log-in page once the connection has been set "
                    "up."
                ),
                allow_empty=False,
                size=80,
            ),
        ),
        (
            "type",
            FixedValue(value="saml2"),
        ),
        (
            "version",
            FixedValue(value="1.0.0"),
        ),
    ] + rule_option_elements()


def _connection_properties() -> list[DictionaryEntry]:
    return [
        (
            "idp_metadata_endpoint",
            HTTPSUrl(
                title=_("Metadata endpoint URL"),
                help=_(
                    "The full URL to the metadata endpoint of your organisation's Identity "
                    "Provider. This endpoint is used to automatically discover the correct "
                    "Single Sign-On endpoint and bindings for a successful SAML communication "
                    "with the Identity Provider. Note that we only support HTTPS for this endpoint, "
                    "because it specifies certificate which should be trusted."
                ),
                allow_empty=False,
            ),
        ),
        (
            "checkmk_server_url",
            HTTPSUrl(
                title=_("Checkmk server URL"),
                help=_(
                    "The URL of the server that hosts Checkmk. This is the URL your monitoring users "
                    "use. It does not need to be accessible to your Identity Provider. For example: "
                    "https://mycheckmkserver.com. "
                    "Note that we only support HTTPS for this endpoint, because it specifies "
                    "certificate which should be trusted."
                ),
                allow_empty=False,
            ),
        ),
        (
            "connection_timeout",
            Tuple(
                title=_("Identity Provider connection timeout"),
                help=_(
                    "The timeout applied to HTTP connections with the Identity Provider. Checkmk "
                    "sends requests to and receives responses from it regarding the authentication "
                    "process of a user."
                ),
                elements=[
                    Integer(
                        title=_("Connection timeout (seconds)"),
                        help=_("Time to wait in seconds for a connection."),
                        minvalue=0,
                        default_value=12,
                    ),
                    Integer(
                        title=_("Read timeout (seconds)"),
                        help=_("Time to wait in seconds for a response."),
                        minvalue=0,
                        default_value=12,
                    ),
                ],
            ),
        ),
    ]


def _user_properties() -> list[DictionaryEntry]:
    return [
        (
            "user_id",
            TextInput(
                title=_("User ID attribute"),
                help=_(
                    "The attribute used to identify an individual user. This attribute must be unique."
                ),
                default_value="user_id",
                allow_empty=False,
                size=80,
            ),
        ),
        (
            "alias",
            TextInput(
                title=_("Full name attribute"),
                help=_(
                    "The attribute used as the full name of the user. If this is not specified, the "
                    "user ID is used."
                ),
                allow_empty=True,
                size=80,
            ),
        ),
        (
            "email",
            TextInput(
                title=_("E-mail address attribute"),
                help=_("The attribute used as the e-mail of the user."),
                allow_empty=True,
                size=80,
            ),
        ),
        (
            "contactgroups",
            TextInput(
                title=_("Contact groups attribute"),
                help=_(
                    "The attribute used to map contact groups between your Identity Provider and "
                    "Checkmk. Note that contact groups must exist in Checkmk so that a mapping can be "
                    "done."
                ),
                allow_empty=True,
                size=80,
            ),
        ),
        (
            "role_membership_mapping",
            CascadingDropdown(
                title=_("Roles"),
                help=_(
                    "Choose whether roles should be mapped. Specify the attribute name, and the "
                    "corresponding mappings for each role."
                ),
                choices=[
                    (
                        True,
                        _("Map roles"),
                        Tuple(
                            elements=[
                                TextInput(title=_("Role attribute"), allow_empty=False, size=80),
                                Dictionary(
                                    elements=[
                                        (r, ListOf(title=re["alias"], valuespec=TextInput()))
                                        for r, re in load_roles().items()
                                    ],
                                ),
                            ],
                            orientation="horizontal",
                        ),
                    ),
                    (False, _("Do not map roles"), None),
                ],
                default_value=False,
            ),
        ),
    ]


def _security_properties() -> list[DictionaryEntry]:
    return [
        (
            "signature_certificate",
            CascadingDropdown(
                title=_("Certificate to sign requests (PEM)"),
                help=_(
                    "Checkmk signs its SAML 2.0 requests to your Identity Provider. You can use the "
                    "certificate that is shipped with Checkmk. Alternatively, if your organisation "
                    "manages its own certificates, you can also add a custom certificate. Note that "
                    "the public certificate needs to be a single certificate (not a certificate "
                    "chain)."
                ),
                choices=[
                    ("default", "Use Checkmk certificate", None),
                    ("custom", "Use custom certificate", CertificateWithPrivateKey()),
                ],
                default_value="default",
            ),
        ),
    ]


def saml2_connection_valuespec() -> Dictionary:
    general_properties = _general_properties()
    connection_properties = _connection_properties()
    user_properties = _user_properties()
    security_properties = _security_properties()
    return Dictionary(
        title=_("SAML Authentication"),
        elements=general_properties + connection_properties + user_properties + security_properties,
        headers=[
            (_("General Properties"), [k for k, _v in general_properties]),
            (_("Connection"), [k for k, _v in connection_properties]),
            (_("Security"), [k for k, _v in security_properties]),
            (_("Users"), [k for k, _v in user_properties]),
        ],
        render="form",
        form_narrow=True,
        optional_keys=[],
        hidden_keys=["type", "version"],
    )


class ModeSAML2Config(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "saml_config"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["global"]

    @property
    def type(self) -> str:
        return "saml2"

    def title(self) -> str:
        return _("SAML connections")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return add_connections_page_menu(
            title=self.title(),
            edit_mode_path="edit_saml_config",
            breadcrumb=breadcrumb,
        )

    def action(self) -> ActionResult:
        return connection_actions(config_mode_url=self.mode_url(), connection_type=self.type)

    def page(self) -> None:
        render_connections_page(
            connection_type=self.type,
            edit_mode_path="edit_saml_config",
            config_mode_path="saml_config",
        )


class ModeEditSAML2Config(WatoMode):
    def _from_vars(self) -> None:
        self._valuespec = saml2_connection_valuespec()
        self._html_valuespec_param_prefix = "vs"

    @classmethod
    def name(cls) -> str:
        return "edit_saml_config"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["global"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode]:
        return ModeSAML2Config

    @property
    def type(self) -> str:
        return "saml2"

    @property
    def version(self) -> str:
        return "1.0.0"

    def title(self) -> str:
        title = self._valuespec.title()
        assert title is not None
        return title

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="actions",
                    title=_("Connection"),
                    topics=[
                        PageMenuTopic(
                            title=_("Actions"),
                            entries=list(self._page_menu_entries()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )

    def _page_menu_entries(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Save"),
            icon_name="save",
            item=make_form_submit_link("value_editor", "_save"),
            is_shortcut=True,
            is_suggested=True,
            is_enabled=True,
            css_classes=["submit"],
        )

    def page(self) -> None:
        html.begin_form("value_editor", method="POST")

        if clone_id := request.var("clone"):
            render_values = self._action_clone(clone_id=clone_id)
        else:
            render_values = self._from_config_file(connection_id=request.get_ascii_input("id"))

        if signature_certificate := render_values.get("signature_certificate"):
            render_values["signature_certificate"] = _read_certificate_files(signature_certificate)

        self._valuespec.render_input_as_form(self._html_valuespec_param_prefix, render_values)

        forms.end()
        html.hidden_fields()
        html.end_form()

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(self.mode_url())

        if request.has_var("_save"):
            self._action_save()

        return redirect(mode_url("saml_config"))

    def _from_config_file(self, *, connection_id: str | None = None) -> DictionaryModel:
        if not connection_id:
            return {}

        for connection in active_connections_by_type(self.type):
            if connection["id"] == connection_id:
                return connection

        raise MKUserError(None, _("The requested connection does not exist."))

    def _validate_user_input(self, user_input: DictionaryModel) -> None:
        self._valuespec.validate_value(user_input, self._html_valuespec_param_prefix)
        self._valuespec.validate_datatype(user_input, self._html_valuespec_param_prefix)

    def _action_save(self) -> None:
        user_input = self._valuespec.from_html_vars(self._html_valuespec_param_prefix)
        self._validate_user_input(user_input)

        # The pysaml2 client needs these in separate files.
        user_input["signature_certificate"] = _write_certificate_files(
            user_input["signature_certificate"]
        )

        connections = load_connection_config(lock=True)
        updated_connections = [c for c in connections if c["id"] != user_input["id"]]
        updated_connections.append(user_input)
        save_connection_config(updated_connections)

    def _action_clone(self, clone_id: str) -> DictionaryModel:
        for connection in load_connection_config(lock=False):
            if connection["id"] == clone_id:
                connection["id"] = UUID().from_html_vars(self._html_valuespec_param_prefix)
                return connection

        raise MKUserError(None, _("The requested connection does not exist."))


def _write_certificate_files(
    certificate: str | tuple[str, tuple[str, str]]
) -> str | tuple[str, tuple[str, str]]:
    type_ = determine_certificate_type(certificate)
    if type_ is CertificateType.BUILTIN:
        return type_.value

    assert isinstance(certificate, tuple)

    _, (private_key, cert) = certificate
    saml2_custom_signature_private_keyfile.write_text(private_key)
    saml2_custom_signature_public_keyfile.write_text(cert)

    return type_.value, (
        str(saml2_custom_signature_private_keyfile),
        str(saml2_custom_signature_public_keyfile),
    )


def _read_certificate_files(
    certificate: str | tuple[str, tuple[str, str]]
) -> str | tuple[str, tuple[str, str]]:
    type_ = determine_certificate_type(certificate)
    if type_ is CertificateType.BUILTIN:
        return type_.value

    assert isinstance(certificate, tuple)
    _, (private_key_str, cert_str) = certificate

    private_key = Path(private_key_str)
    cert = Path(cert_str)

    if not private_key.exists() or not cert.exists():
        return type_.value, ("", "")

    return type_.value, (private_key.read_text(), cert.read_text())


def register(
    mode_registry: ModeRegistry,
) -> None:
    mode_registry.register(ModeSAML2Config)
    mode_registry.register(ModeEditSAML2Config)
