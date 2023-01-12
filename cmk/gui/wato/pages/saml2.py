#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import copy
import json
from collections.abc import Collection, Iterator
from contextlib import suppress
from pathlib import Path

from cmk.utils.paths import (
    saml2_custom_signature_private_keyfile,
    saml2_custom_signature_public_keyfile,
    saml2_signature_private_keyfile,
    saml2_signature_public_keyfile,
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
    save_connection_config,
)
from cmk.gui.plugins.wato.utils import mode_url, redirect, WatoMode
from cmk.gui.plugins.wato.utils.base_modes import ModeRegistry
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.userdb.saml2.connector import ConnectorConfig
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
            render_values = self.from_config_file(connection_id=request.get_ascii_input("id"))

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

    def from_config_file(self, *, connection_id: str | None = None) -> DictionaryModel:
        if not connection_id:
            return {}

        for connection in active_connections_by_type(self.type):
            if connection["id"] == connection_id:
                return _config_to_valuespec(ConnectorConfig(**connection))

        raise MKUserError(None, _("The requested connection does not exist."))

    def to_config_file(self, user_input: DictionaryModel) -> DictionaryModel:
        # The config needs to be serialised to JSON and loaded back into a dict because the .dict()
        # method preserves complex types, which may not be imported depending on the context. E.g.
        # 'Path' should be serialised to 'str'.
        # It can't be serialised to JSON permanently due to existing connectors that have config
        # information in the same file and are serialised to a Python object (i.e. use
        # 'ast.literal_eval' for loading).
        return json.loads(_valuespec_to_config(user_input).json())

    def _validate_user_input(self, user_input: DictionaryModel) -> None:
        self._valuespec.validate_value(user_input, self._html_valuespec_param_prefix)
        self._valuespec.validate_datatype(user_input, self._html_valuespec_param_prefix)

    def _action_save(self) -> None:
        user_input = self._valuespec.from_html_vars(self._html_valuespec_param_prefix)
        self._validate_user_input(user_input)

        connections = load_connection_config(lock=True)
        updated_connections = [c for c in connections if c["id"] != user_input["id"]]
        updated_connections.append(self.to_config_file(user_input))
        save_connection_config(updated_connections)

    def _action_clone(self, clone_id: str) -> DictionaryModel:
        for connection in load_connection_config(lock=False):
            if connection["id"] == clone_id:
                connection["id"] = UUID().from_html_vars(self._html_valuespec_param_prefix)
                return _config_to_valuespec(ConnectorConfig(**connection))

        raise MKUserError(None, _("The requested connection does not exist."))


def _valuespec_to_config(user_input: DictionaryModel) -> ConnectorConfig:
    raw_user_input = copy.deepcopy(user_input)

    interface_config = {
        k: raw_user_input.pop(k)
        for k in [
            "connection_timeout",
            "idp_metadata_endpoint",
            "checkmk_server_url",
        ]
    }
    interface_config["user_attributes"] = {
        k: v
        for k, v in [
            (k, raw_user_input.pop(k))
            for k in [
                "user_id",
                "alias",
                "email",
                "contactgroups",
            ]
        ]
        if v
    }
    interface_config["signature_certificate"] = _certificate_to_config(
        raw_user_input.pop("signature_certificate"),
    )

    raw_user_input["interface_config"] = interface_config

    return ConnectorConfig(**raw_user_input)


def _certificate_to_config(certificate: str | tuple[str, tuple[str, str]]) -> dict[str, Path]:
    if isinstance(certificate, str):
        return {
            "private": saml2_signature_private_keyfile,
            "public": saml2_signature_public_keyfile,
        }

    if not isinstance(certificate, tuple):
        raise ValueError(
            f"Expected str or tuple for signature_certificate, got {type(certificate).__name__}"
        )

    _, (private_key, cert) = certificate
    # The pysaml2 client expects certificates in an actual file
    saml2_custom_signature_public_keyfile.write_text(cert)
    saml2_custom_signature_private_keyfile.write_text(private_key)
    return {
        "private": saml2_custom_signature_private_keyfile,
        "public": saml2_custom_signature_public_keyfile,
    }


def _certificate_from_config(
    signature_certificate: dict[str, Path]
) -> str | tuple[str, tuple[str, str]] | tuple[str, tuple[None, None]]:
    certificate_paths = list(signature_certificate.values())
    if certificate_paths == [
        saml2_signature_private_keyfile,
        saml2_signature_public_keyfile,
    ]:
        return "default"

    with suppress(FileNotFoundError):
        # If the file has disappeared for some reason, there is nothing the user can do except
        # recreate it, so there is no point in failing. If we do, the user will never get a chance
        # to enter certificate details over the GUI configuration page again.
        return (
            "custom",
            (
                saml2_custom_signature_private_keyfile.read_text(),
                saml2_custom_signature_public_keyfile.read_text(),
            ),
        )

    return ("custom", (None, None))


def _config_to_valuespec(config: ConnectorConfig) -> DictionaryModel:
    config_dict = config.dict()
    interface_config = config_dict.pop("interface_config")
    signature_certificate = interface_config.pop("signature_certificate")

    user_attributes_config = {
        k: v or "" for k, v in interface_config.pop("user_attributes").items()
    }

    return {
        **config_dict,
        **interface_config,
        **user_attributes_config,
        "signature_certificate": _certificate_from_config(signature_certificate),
    }


def register(
    mode_registry: ModeRegistry,
) -> None:
    mode_registry.register(ModeSAML2Config)
    mode_registry.register(ModeEditSAML2Config)
