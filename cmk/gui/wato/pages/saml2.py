#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import xml.etree.ElementTree as ET
from collections.abc import Collection, Iterator
from pathlib import Path
from typing import TypeVar

from saml2.config import SPConfig

from cmk.utils.paths import saml2_custom_cert_dir
from cmk.utils.site import omd_site

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
from cmk.gui.userdb.saml2.config import (
    checkmk_server_url,
    checkmk_service_provider_metadata,
    read_certificate_files,
    write_certificate_files,
)
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import (
    CascadingDropdown,
    CertificateWithPrivateKey,
    Dictionary,
    DictionaryEntry,
    DictionaryModel,
    FileUpload,
    FileUploadModel,
    FixedValue,
    HTTPSUrl,
    Integer,
    ListOf,
    rule_option_elements,
    TextAreaUnicode,
    TextInput,
    Tuple,
    UUID,
)
from cmk.gui.wato.pages.userdb_common import (
    add_change,
    add_connections_page_menu,
    connection_actions,
    get_affected_sites,
    render_connections_page,
)

T = TypeVar("T")


class MetadataDisplayText(FixedValue[T]):
    def validate_datatype(self, value: T, varprefix: str) -> None:
        if not isinstance(value, str):
            raise MKUserError(varprefix, _("Value must be string"))


def _metadata() -> list[DictionaryEntry]:
    """This is information the customer must know in order to register Checkmk as a Service Provider
    with the Identity Provider.

    The endpoints are generated dynamically once the UUID of the connection is known (see
    ModeEditSAML2Config).

    Each endpoint must be registered as a trusted URL with the Identity Provider. The Identity
    Provider also checks the source of the requests and whether it can be trusted (entity ID).
    """

    return [
        (
            "checkmk_entity_id",
            MetadataDisplayText(title=_("Entity ID"), value=""),
        ),
        (
            "checkmk_metadata_endpoint",
            MetadataDisplayText(title=_("Metadata endpoint"), value=""),
        ),
        (
            "checkmk_assertion_consumer_service_endpoint",
            MetadataDisplayText(title=_("Assertion Consumer Service endpoint"), value=""),
        ),
    ]


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
        (
            "owned_by_site",
            FixedValue(value=str(omd_site())),
        ),
    ] + rule_option_elements()


def _validate_xml_metadata_text(text: str | bytes, _html_prefix: str) -> None:
    try:
        ET.fromstring(text)
    except (TypeError, ET.ParseError):
        raise MKUserError(None, _("Text is not valid XML"))

    config = SPConfig()
    config.load({})
    metadata = config.load_metadata({"inline": [text]})
    if not metadata.identity_providers():
        raise MKUserError(None, _(("Missing Identity Provider information in metadata")))


def _validate_xml_metadata_file(file_: FileUploadModel, _html_prefix: str) -> None:
    assert isinstance(
        file_, tuple
    )  # str or None is not possible as of valuespec configuration v1.0.0
    # str seems to be a legacy variant, and None would be in the event that the valuespec allows an
    # empty value

    name, content_type, content = file_

    if Path(name).suffix != ".xml":
        raise MKUserError(None, _("Please provide a '.xml' file"))

    if content_type != "text/xml":
        raise MKUserError(None, _("The file does not contain XML text"))

    _validate_xml_metadata_text(content, _html_prefix)


def _connection_properties() -> list[DictionaryEntry]:
    xml_metadata_text_helptext = _(
        "An XML text (file) containing the metadata information of your organisation's Identity "
        "Provider. This is useful if the Checkmk server is not able to access the metadata endpoint "
        "of the Identity Provider. Please note that as a result, any configuration updates that are "
        "applied to the Identity Provider (e.g. updates to certificates) must be updated manually "
        "here as well. We therefore recommend using the metadata endpoint URL option where possible."
    )
    return [
        (
            "idp_metadata",
            CascadingDropdown(
                title=_("Identity Provider metadata"),
                help=_(
                    "Metadata information is exchanged between Checkmk and your Identity Provider "
                    "and contains configuration information to enable a successful SAML communication. "
                    "This includes the Single Sing-On endpoint and bindings used by the Identity "
                    "Provider, as well as details to certificates used for signatures and encryption."
                ),
                choices=[
                    (
                        "url",
                        _("URL"),
                        HTTPSUrl(
                            help=xml_metadata_text_helptext,
                            allow_empty=False,
                        ),
                    ),
                    (
                        "file",
                        _("XML file upload"),
                        FileUpload(
                            help=xml_metadata_text_helptext,
                            allow_empty=False,  # setting this to True will have an effect on the validate function
                            validate=_validate_xml_metadata_file,
                        ),
                    ),
                    (
                        "text",
                        _("XML text"),
                        TextAreaUnicode(
                            help=xml_metadata_text_helptext,
                            allow_empty=False,
                            cols=120,
                            rows=80,
                            validate=_validate_xml_metadata_text,
                        ),
                    ),
                ],
                default_value="url",
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
    metadata = _metadata()
    general_properties = _general_properties()
    connection_properties = _connection_properties()
    user_properties = _user_properties()
    security_properties = _security_properties()
    return Dictionary(
        title=_("SAML Authentication"),
        elements=general_properties
        + metadata
        + connection_properties
        + user_properties
        + security_properties,
        headers=[
            (_("General Properties"), [k for k, _v in general_properties]),
            (_("Checkmk service provider metadata"), [k for k, _v in metadata]),
            (_("Connection"), [k for k, _v in connection_properties]),
            (_("Security"), [k for k, _v in security_properties]),
            (_("Users"), [k for k, _v in user_properties]),
        ],
        render="form",
        form_narrow=True,
        optional_keys=[],
        hidden_keys=["id", "type", "version", "owned_by_site"],
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
        custom_config_dirs = []
        if (index := request.get_integer_input("_delete")) is not None:
            custom_config_dirs.append(
                saml2_custom_cert_dir / load_connection_config(lock=False)[index]["id"]
            )

        return connection_actions(
            config_mode_url=self.mode_url(),
            connection_type=self.type,
            custom_config_dirs=custom_config_dirs,
        )

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
            render_values["signature_certificate"] = read_certificate_files(signature_certificate)

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

        connection_id = user_input["id"]

        connections = load_connection_config(lock=True)

        # The pysaml2 client needs these in separate files.
        user_input["signature_certificate"] = write_certificate_files(
            user_input["signature_certificate"], connection_id
        )
        add_change(
            f"add-or-edit-{user_input['type']}-connection",
            _("Added or edited connection %s") % connection_id,
            get_affected_sites(user_input),
        )

        connection_id = user_input["id"]
        metadata = checkmk_service_provider_metadata(
            checkmk_server_url(user_input["checkmk_server_url"]), connection_id
        )
        user_input["checkmk_entity_id"] = metadata.entity_id
        user_input["checkmk_metadata_endpoint"] = metadata.metadata_endpoint
        user_input[
            "checkmk_assertion_consumer_service_endpoint"
        ] = metadata.assertion_consumer_service_endpoint

        connections = load_connection_config(lock=True)
        updated_connections = [c for c in connections if c["id"] != connection_id]
        updated_connections.append(user_input)
        save_connection_config(updated_connections)

    def _action_clone(self, clone_id: str) -> DictionaryModel:
        for connection in load_connection_config(lock=False):
            if connection["id"] == clone_id:
                connection["id"] = UUID().from_html_vars(self._html_valuespec_param_prefix)
                for key in (k for k, v in _metadata()):
                    # Metadata needs to be regenerated when a connection is cloned
                    connection.pop(key, None)
                return connection

        raise MKUserError(None, _("The requested connection does not exist."))


def register(
    mode_registry: ModeRegistry,
) -> None:
    mode_registry.register(ModeSAML2Config)
    mode_registry.register(ModeEditSAML2Config)
