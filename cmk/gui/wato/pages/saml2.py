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
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import (
    make_confirmed_form_submit_link,
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
from cmk.gui.plugins.wato.utils import redirect, WatoMode
from cmk.gui.plugins.wato.utils.base_modes import ModeRegistry
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.userdb.saml2.connector import ConnectorConfig
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import (
    CascadingDropdown,
    CertificateWithPrivateKey,
    Checkbox,
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
            "user_id_attribute",
            TextInput(
                title=_("User ID attribute"),
                help=_(
                    "The attribute used to identify an individual user. This attribute must be unique."
                ),
                default_value="user_id",
                allow_empty=False,
            ),
        ),
        (
            "create_users_on_login",
            Checkbox(
                title=_("Create new users on login"),
                help=_(
                    "If enabled, Checkmk automatically creates new users when they first log in. If "
                    "the user profile cannot be determined based on the current configuration, the "
                    "default user profile from the global settings is used."
                ),
                default_value=True,
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
    def _from_vars(self) -> None:
        self.__configuration = self.from_config_file()
        self.__valuespec = saml2_connection_valuespec()
        self.__html_valuespec_param_prefix = "vs"

    @classmethod
    def name(cls) -> str:
        return "saml_config"

    @classmethod
    def permissions(cls) -> Collection[PermissionName]:
        return ["global"]

    @property
    def type(self) -> str:
        return "saml2"

    @property
    def version(self) -> str:
        return "1.0.0"

    def title(self) -> str:
        title = self.__valuespec.title()
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
                            entries=list(self.page_menu_entries()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )

    def page_menu_entries(self) -> Iterator[PageMenuEntry]:

        yield PageMenuEntry(
            title=_("Save"),
            icon_name="save",
            item=make_form_submit_link("value_editor", "_save"),
            is_shortcut=True,
            is_suggested=True,
            is_enabled=True,
            css_classes=["submit"],
        )
        yield PageMenuEntry(
            title=_("Delete"),
            icon_name="delete",
            item=make_confirmed_form_submit_link(
                form_name="value_editor",
                button_name="_delete",
                message="Do you really want to delete this SAML connection?",
            ),
            is_shortcut=True,
            is_suggested=True,
            is_enabled=True,
            css_classes=["submit"],
        )

    def page(self) -> None:
        html.begin_form("value_editor", method="POST")

        self.__valuespec.render_input_as_form(
            self.__html_valuespec_param_prefix, self.from_config_file()
        )

        forms.end()
        html.hidden_fields()
        html.end_form()

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(self.mode_url())

        if request.has_var("_save"):
            self._action_save()
        elif request.has_var("_delete"):
            self._action_delete()

        return redirect(self.mode_url())

    def from_config_file(self) -> DictionaryModel:
        connections = active_connections_by_type(self.type)

        if not connections:
            return {}

        # Only one SAML connection is currently supported
        return _config_to_valuespec(ConnectorConfig(**connections[0]))

    def to_config_file(self, user_input: DictionaryModel) -> DictionaryModel:
        # The config needs to be serialised to JSON and loaded back into a dict because the .dict()
        # method preserves complex types, which may not be imported depending on the context. E.g.
        # 'Path' should be serialised to 'str'.
        # It can't be serialised to JSON permanently due to existing connectors that have config
        # information in the same file and are serialised to a Python object (i.e. use
        # 'ast.literal_eval' for loading).
        return json.loads(_valuespec_to_config(user_input).json())

    def _connection_id(self) -> str:
        return self.__configuration.get("id", self._user_input()["id"])

    def _user_input(self) -> DictionaryModel:
        return self.__valuespec.from_html_vars(self.__html_valuespec_param_prefix)

    def _validate_user_input(self, user_input: DictionaryModel) -> None:
        self.__valuespec.validate_value(user_input, self.__html_valuespec_param_prefix)
        self.__valuespec.validate_datatype(user_input, self.__html_valuespec_param_prefix)

    def _action_save(self) -> None:
        user_input = self._user_input()
        self._validate_user_input(user_input)

        connections = load_connection_config(lock=True)
        updated_connections = [c for c in connections if c["id"] != self._connection_id()]
        updated_connections.append(self.to_config_file(user_input))
        save_connection_config(updated_connections)

    def _action_delete(self) -> None:
        connections = load_connection_config(lock=True)
        save_connection_config([c for c in connections if c["id"] != self._connection_id()])


def _valuespec_to_config(user_input: DictionaryModel) -> ConnectorConfig:
    interface_config_keys = {
        "connection_timeout",
        "idp_metadata_endpoint",
        "checkmk_server_url",
        "user_id_attribute",
    }
    raw_user_input = copy.deepcopy(user_input)
    interface_config = {k: raw_user_input.pop(k) for k in interface_config_keys}
    raw_user_input["interface_config"] = interface_config
    raw_user_input["interface_config"]["signature_certificate"] = _certificate_to_config(
        raw_user_input.pop("signature_certificate"),
    )
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
    return {
        **config_dict,
        **interface_config,
        "signature_certificate": _certificate_from_config(signature_certificate),
    }


def register(
    mode_registry: ModeRegistry,
) -> None:
    mode_registry.register(ModeSAML2Config)
