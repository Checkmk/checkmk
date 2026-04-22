#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="type-arg"

from __future__ import annotations

import queue
import re
import time
from collections.abc import Collection, Mapping
from multiprocessing import JoinableQueue, Process
from typing import Any, cast, NamedTuple, override, Protocol

from livestatus import (
    BrokerConnection,
    BrokerConnections,
    ConnectionId,
    NetworkSocketDetails,
    SiteConfiguration,
    SiteConfigurations,
)

import cmk.ccc.version as cmk_version
import cmk.gui.sites
import cmk.gui.watolib.activate_changes
import cmk.gui.watolib.changes
import cmk.gui.watolib.sidebar_reload
from cmk.ccc import store
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.store import load_from_mk_file
from cmk.gui import hooks, log
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.generators.host_address import create_host_address
from cmk.gui.form_specs.unstable import LegacyValueSpec
from cmk.gui.form_specs.unstable.cascading_single_choice_extended import (
    CascadingSingleChoiceExtended,
    CascadingSingleChoiceLayout,
)
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
    Tuple,
)
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.site_config import (
    distributed_setup_remote_sites,
    has_distributed_setup_remote_sites,
    is_distributed_setup_remote_site,
    is_replication_enabled,
    site_is_local,
)
from cmk.gui.userdb import connection_choices, saml_connection_choices
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeactionuri
from cmk.gui.valuespec import (
    Dictionary as _LegacyDictionary,
)
from cmk.gui.valuespec import (
    FixedValue as _LegacyFixedValue,
)
from cmk.gui.valuespec import (
    Integer as _LegacyInteger,
)
from cmk.gui.valuespec import (
    IPNetwork,
    ListOfStrings,
    ValueSpec,
)
from cmk.gui.watolib.automation_commands import OMDStatus
from cmk.gui.watolib.automations import (
    do_remote_automation,
    parse_license_state,
)
from cmk.gui.watolib.broker_connections import BrokerConnectionsConfigFile
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.config_domains import (
    ConfigDomainCACertificates,
    ConfigDomainGUI,
)
from cmk.gui.watolib.config_sync import (
    create_distributed_wato_files,
)
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.mode import mode_registry
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile
from cmk.licensing.handler import LicenseState
from cmk.rulesets.internal.form_specs import (
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    FormSpec,
    Integer,
    List,
    MultipleChoice,
    MultipleChoiceElement,
    String,
    validators,
)
from cmk.utils import paths
from cmk.utils.automation_config import RemoteAutomationConfig

STATIC_PERMISSIONS_SITES = ["sites"]


class SitesConfigFile(WatoSingleConfigFile[SiteConfigurations]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=cmk.utils.paths.default_config_dir / "multisite.d/sites.mk",
            config_variable="sites",
            spec_class=SiteConfigurations,
        )


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(SitesConfigFile())


class LivestatusProxyHook(Protocol):
    def livestatus_proxy_form_spec(self) -> FormSpec[Any]: ...
    def on_sites_saved(self, sites: SiteConfigurations) -> None: ...
    def affected_config_domains(self) -> list[ABCConfigDomain]: ...


class NoOpLivestatusProxy:
    def livestatus_proxy_form_spec(self) -> FixedValue:
        return FixedValue(
            value=None,
            title=Title("Use Livestatus proxy daemon"),
            label=Label("Connect directly (not available in Checkmk Community)"),
        )

    def on_sites_saved(self, sites: SiteConfigurations) -> None:
        pass

    def affected_config_domains(self) -> list[ABCConfigDomain]:
        return []


class _DynamicFixedValueText(_LegacyFixedValue):
    """Read-only display of a dynamically-injected string.

    Behaves like the legacy `FixedValue` valuespec but skips the strict
    equality check in `validate_datatype` so that values different from the
    configured default (which is what render-time injection produces) pass
    through cleanly.
    """

    @override
    def validate_datatype(self, value: str, varprefix: str) -> None:
        if not isinstance(value, str):
            raise MKUserError(varprefix, _("Expected string"))


class _DynamicFixedValueTextBlock(_DynamicFixedValueText):
    """Multi-line variant of `_DynamicFixedValueText` rendered inside ``<pre>``.

    Newlines in the dynamically-injected value are preserved so a free-form
    text representation (e.g. a list of inherited connections) renders the
    way it was assembled.
    """

    @override
    def render_input(self, varprefix: str, value: str) -> None:
        html.open_pre(class_="vs_fixed_value")
        html.write_text(value or "")
        html.close_pre()


class DropKeySentinel:
    """Sentinel returned by `to_disk` converters to signal "remove this key".

    The save path in `cmk/gui/wato/pages/sites.py` checks for instances of
    this and `pop`s the key from the `SiteConfiguration` dict instead of
    assigning it. Used to encode "inherit from central site" (for
    ``authentication_connections``) and "disabled" (for
    ``user_attribute_sync_connections``) as key absence on disk.
    """


DROP_KEY: DropKeySentinel = DropKeySentinel()


def _auth_connections_from_disk(value: object) -> tuple[str, object]:
    """Translate the on-disk shape into the cascading-choice tuple.

    The site-edit page pre-renders the dict and converts list → ("list",
    list) / absent → ("central_site", summary) before passing to the form,
    so the typical input here is already a tuple. The bare-shape branches
    handle direct disk loads (legacy/migration paths) and form-resubmission
    after validation failure.
    """
    if isinstance(value, tuple) and len(value) == 2:
        return value[0], value[1]
    # Absent key → form shows "Inherit from central site". The summary is
    # injected by the site-edit page; here we fall back to "-".
    if value is None:
        return "central_site", "-"
    assert isinstance(value, list)
    return "list", value


def _auth_connections_to_disk(value: object) -> object:
    assert isinstance(value, tuple) and len(value) == 2
    choice, payload = value
    if choice == "central_site":
        return DROP_KEY
    assert choice == "list"
    return payload


def _user_attribute_sync_from_disk(value: object) -> tuple[str, object]:
    """Translate the on-disk shape into the cascading-choice tuple.

    Form choices: ``"disabled"`` / ``"all"`` / ``"list"``. The disk shape
    is ``Literal["all"] | list[str]`` with absence meaning "disabled".
    """
    if value is None:
        return "disabled", True
    if value == "all":
        return "all", True
    if isinstance(value, tuple) and len(value) == 2:
        # Already in form-spec tuple shape (e.g. on validation re-render).
        return value[0], value[1]
    assert isinstance(value, list)
    return "list", value


def _user_attribute_sync_to_disk(value: object) -> object:
    """Translate the cascading-choice tuple back to the on-disk shape.

    The cascading choice always arrives as ``(choice_name, payload)``:
    ``"disabled"`` → ``DROP_KEY`` (key absent on disk),
    ``"all"`` → bare ``"all"``,
    ``"list"`` → ``list[str]``.
    """
    assert isinstance(value, tuple) and len(value) == 2
    choice, payload = value
    if choice == "disabled":
        return DROP_KEY
    if choice == "all":
        return "all"
    assert choice == "list"
    return list(payload)


class SiteManagement:
    def __init__(
        self,
        liveproxy_hook: LivestatusProxyHook | None = None,
    ) -> None:
        self._liveproxy_hook = liveproxy_hook or NoOpLivestatusProxy()

    @classmethod
    def connection_method_form_spec(cls) -> CascadingSingleChoiceExtended:
        return CascadingSingleChoiceExtended(
            title=Title("Connection"),
            elements=cls._connection_choices(),
            help_text=Help(
                "When connecting to remote site please make sure "
                "that Livestatus over TCP is activated there. You can use Unix sockets "
                "to connect to foreign sites on localhost. Please make sure that this "
                "site has proper read and write permissions to the Unix socket of the "
                "foreign site."
            ),
            layout=CascadingSingleChoiceLayout.vertical,
        )

    def livestatus_proxy_form_spec(self) -> FormSpec[Any]:
        return self._liveproxy_hook.livestatus_proxy_form_spec()

    @classmethod
    def _connection_choices(cls) -> list[CascadingSingleChoiceElement]:
        return [
            CascadingSingleChoiceElement(
                name="local",
                title=Title("Connect to the local site"),
                parameter_form=FixedValue(value=None, label=Label("")),
            ),
            CascadingSingleChoiceElement(
                name="tcp",
                title=Title("Connect via TCP (IPv4)"),
                parameter_form=cls._tcp_socket_form_spec(ipv6=False),
            ),
            CascadingSingleChoiceElement(
                name="tcp6",
                title=Title("Connect via TCP (IPv6)"),
                parameter_form=cls._tcp_socket_form_spec(ipv6=True),
            ),
            CascadingSingleChoiceElement(
                name="unix",
                title=Title("Connect via Unix socket"),
                parameter_form=Dictionary(
                    elements={
                        "path": DictElement(
                            required=True,
                            parameter_form=String(
                                label=Label("Path:"),
                                custom_validate=[
                                    validators.LengthInRange(
                                        min_value=1,
                                        error_msg=Message("Text field can not be empty"),
                                    )
                                ],
                            ),
                        )
                    }
                ),
            ),
        ]

    @classmethod
    def _tcp_socket_form_spec(cls, ipv6: bool) -> Dictionary:
        return Dictionary(
            elements={
                "address": DictElement(
                    required=True,
                    parameter_form=Tuple(
                        title=Title("TCP address to connect to"),
                        layout="horizontal",
                        elements=[
                            create_host_address(
                                allow_empty=False,
                                allow_ipv4_address=not ipv6,
                                allow_ipv6_address=ipv6,
                            ),
                            Integer(
                                label=Label("Port:"),
                                prefill=DefaultValue(6557),
                                custom_validate=[
                                    validators.NetworkPort(),
                                ],
                            ),
                        ],
                    ),
                ),
                "tls": DictElement(required=True, parameter_form=cls._tls_form_spec()),
            }
        )

    @classmethod
    def _tls_form_spec(cls) -> CascadingSingleChoice:
        return CascadingSingleChoice(
            title=Title("Encryption"),
            elements=[
                CascadingSingleChoiceElement(
                    name="plain_text",
                    title=Title("Plain text (unencrypted)"),
                    parameter_form=FixedValue(
                        value={}, label=Label("Use plain text, unencrypted transport")
                    ),
                ),
                CascadingSingleChoiceElement(
                    name="encrypted",
                    title=Title("Encrypt data using TLS"),
                    parameter_form=Dictionary(
                        elements={
                            "verify": DictElement(
                                required=True,
                                parameter_form=BooleanChoice(
                                    title=Title("Verify server certificate"),
                                    label=Label(
                                        "Verify the Livestatus server certificate using the local site CA"
                                    ),
                                    prefill=DefaultValue(True),
                                    help_text=Help(
                                        "Either verify the server certificate using the site local CA or accept "
                                        "any certificate offered by the server. It is highly recommended to "
                                        "leave this enabled."
                                    ),
                                ),
                            )
                        }
                    ),
                ),
            ],
            help_text=Help(
                "When connecting to Checkmk versions older than 1.6 you can only use plain text "
                "transport. Starting with Checkmk 1.6 it is possible to use encrypted Livestatus "
                "communication. Sites created with 1.6 will automatically use encrypted communication "
                "by default. Sites created with previous versions need to be configured manually to "
                'enable the encryption. Have a look at <a href="werk.py?werk=7017">werk #7017</a> '
                "for further information."
            ),
        )

    @classmethod
    def authentication_connections_form_spec(
        cls,
        site_configuration: SiteConfiguration | None = None,
    ) -> FormSpec[Any]:
        # The "central_site" choice means "inherit from the central site"
        # (encoded on disk as the per-site key being absent). Hide it when
        # the form edits the central site itself, where it would be a
        # self-reference. The on-disk value never carries the form's
        # ``("central_site", _)`` shape; ``_auth_connections_to_disk`` maps
        # it to the ``DROP_KEY`` sentinel that the save path translates to
        # key removal.
        is_local_site = site_configuration is not None and site_is_local(site_configuration)
        elements: list[CascadingSingleChoiceElement[Any]] = []
        if not is_local_site:
            elements.append(
                CascadingSingleChoiceElement(
                    name="central_site",
                    title=Title("Use the same connections as the central site"),
                    parameter_form=cls._central_site_connections_widget(),
                ),
            )
        elements.append(
            CascadingSingleChoiceElement(
                name="list",
                title=Title("Use the following connections"),
                parameter_form=cls._editable_connections_form_spec(),
            ),
        )

        return TransformDataForLegacyFormatOrRecomposeFunction(
            wrapped_form_spec=CascadingSingleChoiceExtended(
                title=Title("Authentication connections"),
                elements=elements,
                prefill=DefaultValue("list"),
                help_text=Help(
                    "Select the connections that are available for login on this site. "
                    "Choose <i>Use the same connections as the central site</i> to inherit "
                    "the central site's selection (changes made on the central site take "
                    "effect after the next configuration sync), or <i>Use the following "
                    "connections</i> to pick specific LDAP and SAML connections. Each "
                    "SAML entry may optionally override the SP entity ID, which is useful "
                    "when multiple sites share the same SAML connection but need to be "
                    "registered separately at the IdP."
                ),
                layout=CascadingSingleChoiceLayout.horizontal,
            ),
            from_disk=_auth_connections_from_disk,
            to_disk=_auth_connections_to_disk,
        )

    @staticmethod
    def _saml_metadata_endpoint_widget() -> LegacyValueSpec:
        return LegacyValueSpec.wrap(
            _DynamicFixedValueText(
                value="-",
                title=_("Metadata endpoint URL"),
                help=_(
                    "URL where this site serves the SAML Service Provider metadata "
                    "for this connection. Derived from the site's <i>Server URL for "
                    "SAML ACS callback</i> and the connection ID. The URL is only "
                    "shown after saving the site configuration and reopening this "
                    "dialog."
                ),
            )
        )

    @staticmethod
    def _saml_acs_endpoint_widget() -> LegacyValueSpec:
        return LegacyValueSpec.wrap(
            _DynamicFixedValueText(
                value="-",
                title=_("Assertion Consumer Service URL"),
                help=_(
                    "URL where this site receives SAML responses from the IdP for "
                    "this connection. Register this URL with the IdP's client "
                    "configuration. The URL is only shown after saving the site "
                    "configuration and reopening this dialog."
                ),
            )
        )

    @classmethod
    def _editable_connections_form_spec(cls) -> List[tuple[str, object]]:
        """Editable list of LDAP/SAML connection picks (the ``"list"`` form)."""
        ldap_elements = [
            SingleChoiceElementExtended(  # astrein: disable=localization-checker
                name=id_,
                title=Title(label),  # astrein: disable=localization-checker
            )
            for id_, label in connection_choices()
        ]
        saml_elements = [
            SingleChoiceElementExtended(  # astrein: disable=localization-checker
                name=id_,
                title=Title(label),  # astrein: disable=localization-checker
            )
            for id_, label in saml_connection_choices()
        ]
        return List(
            element_template=CascadingSingleChoice(
                title=Title("Connection"),
                elements=[
                    CascadingSingleChoiceElement(
                        name="ldap",
                        title=Title("LDAP connection"),
                        parameter_form=SingleChoiceExtended[str](
                            title=Title("LDAP connection"),
                            elements=ldap_elements,
                        ),
                    ),
                    CascadingSingleChoiceElement(
                        name="saml",
                        title=Title("SAML connection"),
                        parameter_form=Dictionary(
                            elements={
                                "connection_id": DictElement(
                                    required=True,
                                    parameter_form=SingleChoiceExtended[str](
                                        title=Title("SAML connection"),
                                        elements=saml_elements,
                                    ),
                                ),
                                "metadata_endpoint": DictElement(
                                    required=True,
                                    parameter_form=cls._saml_metadata_endpoint_widget(),
                                ),
                                "acs_endpoint": DictElement(
                                    required=True,
                                    parameter_form=cls._saml_acs_endpoint_widget(),
                                ),
                            },
                        ),
                    ),
                ],
            ),
            title=Title("Authentication"),
            add_element_label=Label("Add connection"),
            editable_order=False,
        )

    @classmethod
    def _central_site_connections_widget(cls) -> LegacyValueSpec:
        """Read-only multi-line text display of the inherited central-site connections.

        The text is assembled at render time by `populate_saml_site_endpoint_urls()`
        from the central site's own `authentication_connections`: one line per
        LDAP entry, and three indented lines per SAML entry (connection ID,
        metadata endpoint URL, ACS URL).
        """
        return LegacyValueSpec.wrap(
            _DynamicFixedValueTextBlock(
                value="-",
                title=_("Inherited from central site"),
                help=_(
                    "Read-only summary of the connections inherited from the "
                    "central site. Refreshed each time this dialog is opened."
                ),
            )
        )

    @classmethod
    def user_attribute_sync_connections_form_spec(cls) -> FormSpec[Any]:
        return TransformDataForLegacyFormatOrRecomposeFunction(
            wrapped_form_spec=CascadingSingleChoiceExtended(
                title=Title("User attribute synchronization"),
                elements=[
                    CascadingSingleChoiceElement(
                        name="disabled",
                        title=Title("Disable automatic user attribute synchronization"),
                        parameter_form=FixedValue(value=True, label=Label("")),
                    ),
                    CascadingSingleChoiceElement(
                        name="all",
                        title=Title("Sync attributes for all LDAP connections"),
                        parameter_form=FixedValue(value=True, label=Label("")),
                    ),
                    CascadingSingleChoiceElement(
                        name="list",
                        title=Title("Sync attributes only for the following connections"),
                        parameter_form=MultipleChoice(
                            custom_validate=[
                                validators.LengthInRange(min_value=1, error_msg=Message(""))
                            ],
                            elements=[
                                MultipleChoiceElement(  # astrein: disable=localization-checker
                                    name=ident,
                                    title=Title(label),  # astrein: disable=localization-checker
                                )
                                for ident, label in connection_choices()
                            ],
                        ),
                    ),
                ],
                prefill=DefaultValue("all"),
                help_text=Help(
                    "Periodic user attribute synchronization keeps user attributes "
                    "(alias, email, roles, contact groups) up to date on this site. "
                    "This is primarily relevant for LDAP connections. SAML connections "
                    "update attributes only when a user logs in, so they do not need "
                    "to be listed here."
                ),
                layout=CascadingSingleChoiceLayout.horizontal,
            ),
            from_disk=_user_attribute_sync_from_disk,
            to_disk=_user_attribute_sync_to_disk,
        )

    @classmethod
    def is_site_in_broker_connections(cls, site_id: SiteId) -> bool:
        connections = BrokerConnectionsConfigFile().load_for_modification()
        connections_ids = {
            site_id
            for connection in connections.values()
            for site_id in (connection.connectee.site_id, connection.connecter.site_id)
        }

        return site_id in connections_ids

    @classmethod
    def _change_affects_broker_connection(
        cls, current_config: SiteConfiguration, old_config: SiteConfiguration
    ) -> bool:
        return (
            is_replication_enabled(old_config) != is_replication_enabled(current_config)
            or old_config.get("message_broker_port", 5672)
            != current_config.get("message_broker_port", 5672)
            or old_config["multisiteurl"] != current_config["multisiteurl"]
        )

    @classmethod
    def get_connected_sites_to_update(
        cls,
        *,
        new_or_deleted_connection: bool,
        modified_site: SiteId,
        current_config: SiteConfiguration,
        old_config: SiteConfiguration | None,
        site_configs: SiteConfigurations,
    ) -> set[SiteId]:
        connected = {omd_site()}

        if new_or_deleted_connection or (
            old_config
            and is_replication_enabled(old_config) != is_replication_enabled(current_config)
        ):
            connected |= set(distributed_setup_remote_sites(site_configs).keys())
            return connected

        if old_config is None:
            raise MKUserError(None, _("An old configuration is required for existing connections."))

        if not cls._change_affects_broker_connection(current_config, old_config):
            return set()

        connections = BrokerConnectionsConfigFile().load_for_reading()
        for connection in connections.values():
            if modified_site in (
                connection.connectee.site_id,
                connection.connecter.site_id,
            ):
                connected |= {
                    connection.connectee.site_id,
                    connection.connecter.site_id,
                }

        return connected

    @classmethod
    def get_broker_connections(cls) -> BrokerConnections:
        return BrokerConnectionsConfigFile().load_for_reading()

    @classmethod
    def broker_connection_id_exists(cls, connection_id: str) -> bool:
        return connection_id in cls.get_broker_connections()

    @classmethod
    def _validate_broker_connection(
        cls, connection_id: ConnectionId, connection: BrokerConnection, is_new: bool
    ) -> None:
        if not re.match("^[-a-z0-9A-Z_]+$", connection_id):
            raise MKUserError(
                "id", _("The connection id must consist only of letters, digit and the underscore.")
            )

        if connection.connecter.site_id == connection.connectee.site_id:
            raise MKUserError(
                None,
                _("Connecter and connectee sites must be different."),
            )

        if is_new and cls.broker_connection_id_exists(connection_id):
            raise MKUserError(
                None,
                _("Connection ID %s already exists.") % connection_id,
            )

        old_connection_sites = {connection.connecter.site_id, connection.connectee.site_id}
        for _conn_id, conn in cls.get_broker_connections().items():
            if _conn_id == connection_id:
                continue

            if old_connection_sites == {conn.connecter.site_id, conn.connectee.site_id}:
                raise MKUserError(
                    None,
                    _("A connection with the same sites already exists."),
                )

    @classmethod
    def _save_broker_connection_config(
        cls, save_id: str, connection: BrokerConnection, pprint_value: bool
    ) -> tuple[SiteId, SiteId]:
        broker_connections = cls.get_broker_connections()
        broker_connections[ConnectionId(save_id)] = connection
        BrokerConnectionsConfigFile().save(broker_connections, pprint_value)
        return connection.connectee.site_id, connection.connecter.site_id

    @classmethod
    def validate_and_save_broker_connection(
        cls,
        connection_id: ConnectionId,
        connection: BrokerConnection,
        *,
        is_new: bool,
        pprint_value: bool,
    ) -> tuple[SiteId, SiteId]:
        cls._validate_broker_connection(connection_id, connection, is_new)
        return cls._save_broker_connection_config(connection_id, connection, pprint_value)

    @classmethod
    def delete_broker_connection(
        cls, connection_id: ConnectionId, pprint_value: bool
    ) -> tuple[SiteId, SiteId]:
        broker_connections = cls.get_broker_connections()
        if connection_id not in broker_connections:
            raise MKUserError(None, _("Unable to delete unknown connection ID: %s") % connection_id)

        connection = broker_connections[connection_id]
        del broker_connections[connection_id]
        BrokerConnectionsConfigFile().save(broker_connections, pprint_value)

        return connection.connectee.site_id, connection.connecter.site_id

    @classmethod
    def validate_configuration(
        cls,
        site_id: SiteId,
        site_configuration: SiteConfiguration,
        all_sites: SiteConfigurations,
    ) -> None:
        if not re.match("^[-a-z0-9A-Z_]+$", site_id):
            raise MKUserError(
                "id", _("The site id must consist only of letters, digit and the underscore.")
            )

        if not site_configuration.get("alias"):
            raise MKUserError(
                "alias", _("Please enter an alias name or description for the site %s.") % site_id
            )

        if site_configuration["url_prefix"] and site_configuration["url_prefix"][-1] != "/":
            raise MKUserError("url_prefix", _("The URL prefix must end with a slash."))

        # Connection
        if site_configuration["socket"][0] == "local" and site_id != omd_site():
            raise MKUserError(
                "method_sel",
                _(
                    "You can only configure a local site connection for "
                    "the local site. The site IDs ('%s' and '%s') are "
                    "not equal."
                )
                % (site_id, omd_site()),
            )

        # Timeout
        if "timeout" in site_configuration:
            timeout = site_configuration["timeout"]
            try:
                int(timeout)
            except ValueError:
                raise MKUserError(
                    "timeout", _("The timeout %s is not a valid integer number.") % timeout
                )

        # Status host
        status_host = site_configuration.get("status_host")
        if status_host:
            status_host_site, status_host_name = status_host
            if status_host_site not in all_sites:
                raise MKUserError("sh_site", _("The site of the status host does not exist."))
            if status_host_site == site_id:
                raise MKUserError(
                    "sh_site", _("You cannot use the site itself as site of the status host.")
                )
            if not status_host_name:
                raise MKUserError("sh_host", _("Please specify the name of the status host."))

        if is_replication_enabled(site_configuration):
            multisiteurl = site_configuration["multisiteurl"]
            if not multisiteurl:
                raise MKUserError(
                    "multisiteurl",
                    _("Please enter the graphical user interface (GUI) URL of the remote site."),
                )

            if not multisiteurl.endswith("/check_mk/"):
                raise MKUserError(
                    "multisiteurl",
                    _("The graphical user interface (GUI) URL must end with /check_mk/"),
                )

            if not multisiteurl.startswith("http://") and not multisiteurl.startswith("https://"):
                raise MKUserError(
                    "multisiteurl",
                    _(
                        "The graphical user interface (GUI) URL must begin with <tt>http://</tt> or <tt>https://</tt>."
                    ),
                )

            if site_configuration["socket"][0] == "local":
                raise MKUserError(
                    "replication", _("You cannot do replication with the local site.")
                )

        if not is_replication_enabled(site_configuration) and cls.is_site_in_broker_connections(
            site_id
        ):
            raise MKUserError(
                "replication",
                _(
                    "You cannot disable the replication on this site. It is used in a broker peer-to-peer connection."
                ),
            )

    @classmethod
    def load_sites(cls) -> SiteConfigurations:
        return SitesConfigFile().load_for_reading()

    def save_sites(self, sites: SiteConfigurations, *, activate: bool, pprint_value: bool) -> None:
        # TODO: Clean this up
        from cmk.gui.watolib.hosts_and_folders import folder_tree

        SitesConfigFile().save(sites, pprint_value)

        # Do not activate when just the site's global settings have
        # been edited
        if activate:
            # Patch the current requests config with the changed config
            active_config.sites = sites
            folder_tree().invalidate_caches()

            _update_distributed_wato_file(sites)
            cmk.gui.watolib.sidebar_reload.need_sidebar_reload()

            if cmk_version.edition_supports_nagvis(cmk_version.edition(paths.omd_root)):
                _create_nagvis_backends(sites)

            # Call the sites saved hook
            hooks.call("sites-saved", sites)

            self._liveproxy_hook.on_sites_saved(sites)

    def delete_site(self, site_id: SiteId, *, pprint_value: bool, use_git: bool) -> None:
        # TODO: Clean this up
        from cmk.gui.watolib.hosts_and_folders import folder_tree

        sites_config_file = SitesConfigFile()
        all_sites = sites_config_file.load_for_modification()
        if site_id not in all_sites:
            raise MKUserError(None, _("Unable to delete unknown site id: %s") % site_id)

        # Make sure that site is not being used by hosts and folders
        if site_id in folder_tree().root_folder().all_site_ids():
            search_url = makeactionuri(
                request,
                transactions,
                [
                    ("host_search_change_site", "on"),
                    ("host_search_site", site_id),
                    ("host_search", "1"),
                    ("folder", ""),
                    ("mode", "search"),
                    ("filled_in", "edit_host"),
                ],
            )
            raise MKUserError(
                None,
                _(
                    "You cannot delete this connection. It has folders/hosts "
                    'assigned to it. You can use the <a href="%s">host '
                    "search</a> to get a list of the hosts."
                )
                % search_url,
            )

        if self.is_site_in_broker_connections(site_id):
            raise MKUserError(
                None,
                _(
                    "You cannot delete this connection. It is used in a broker peer-to-peer connection."
                ),
            )

        domains = self._affected_config_domains()

        connected_sites = self.get_connected_sites_to_update(
            new_or_deleted_connection=True,
            modified_site=site_id,
            current_config=all_sites[site_id],
            old_config=None,
            site_configs=all_sites,
        )

        del all_sites[site_id]
        self.save_sites(all_sites, activate=True, pprint_value=pprint_value)

        cmk.gui.watolib.changes.add_change(
            action_name="edit-sites",
            text=_("Deleted site %s") % site_id,
            user_id=user.id,
            domains=domains,
            # Exclude site which is about to be removed. The activation won't be executed for that
            # site anymore, so there is no point in adding a change for this site
            sites=list(connected_sites - {site_id}),
            need_restart=True,
            use_git=use_git,
        )
        cmk.gui.watolib.activate_changes.clear_site_replication_status(site_id)

    def _affected_config_domains(self) -> list[ABCConfigDomain]:
        return [ConfigDomainGUI()] + self._liveproxy_hook.affected_config_domains()


class SiteManagementRegistry(Registry[SiteManagement]):
    def plugin_name(self, instance: SiteManagement) -> str:
        return "site_management"


site_management_registry = SiteManagementRegistry()


# Don't use or change this ValueSpec, it is out-of-date. It can't be removed due to CMK-12228.
class LivestatusViaTCP(_LegacyDictionary):
    def __init__(
        self,
        title: str | None = None,
        help: str | None = None,
        tcp_port: int = 6557,
    ) -> None:
        elements: list[tuple[str, ValueSpec]] = [
            (
                "port",
                _LegacyInteger(
                    title=_("TCP port"),
                    default_value=tcp_port,
                    minvalue=1,
                    maxvalue=65535,
                ),
            ),
            (
                "only_from",
                ListOfStrings(
                    title=_("Restrict access to IP addresses"),
                    help=_(
                        "The access to Livestatus via TCP will only be allowed from the "
                        "configured source IP addresses. You can either configure specific "
                        "IP addresses or networks in the syntax <tt>10.3.3.0/24</tt>."
                    ),
                    valuespec=IPNetwork(),
                    orientation="horizontal",
                    allow_empty=False,
                    default_value=["0.0.0.0", "::/0"],
                ),
            ),
            (
                "tls",
                _LegacyFixedValue(
                    True,
                    title=_("Encrypt communication"),
                    totext=_("Encrypt TCP Livestatus connections"),
                    help=_(
                        "Since Checkmk 1.6 it is possible to encrypt the TCP Livestatus "
                        "connections using SSL. This is enabled by default for sites that "
                        "enable Livestatus via TCP with 1.6 or newer. Sites that already "
                        "have this option enabled keep the communication unencrypted for "
                        "compatibility reasons. However, it is highly recommended to "
                        "migrate to an encrypted communication."
                    ),
                ),
            ),
        ]
        super().__init__(
            title=title,
            help=help,
            elements=elements,
            optional_keys=["only_from", "tls"],
        )


def _create_nagvis_backends(sites_config: SiteConfigurations) -> None:
    cfg = [
        "; MANAGED BY CHECK_MK Setup - Last Update: %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
    ]
    for site_id, site in sites_config.items():
        if site_id == omd_site():
            continue  # skip local site, backend already added by omd

        socket = _encode_socket_for_nagvis(site_id, site)

        cfg += [
            "",
            "[backend_%s]" % site_id,
            'backendtype="mklivestatus"',
            'socket="%s"' % socket,
        ]

        if status_host := site.get("status_host"):
            cfg.append('statushost="%s:%s"' % status_host)

        if site["proxy"] is None and is_livestatus_encrypted(site):
            assert isinstance(site["socket"], tuple) and site["socket"][0] in ["tcp", "tcp6"]
            address_spec = cast(NetworkSocketDetails, site["socket"][1])
            tls_settings = address_spec["tls"][1]
            cfg.append("verify_tls_peer=%d" % tls_settings["verify"])
            cfg.append("verify_tls_ca_path=%s" % ConfigDomainCACertificates.trusted_cas_file)

    store.save_text_to_file(
        cmk.utils.paths.omd_root / "etc/nagvis/conf.d/cmk_backends.ini.php", "\n".join(cfg)
    )


def _encode_socket_for_nagvis(site_id: SiteId, site: SiteConfiguration) -> str:
    if site["proxy"] is None and is_livestatus_encrypted(site):
        assert isinstance(site["socket"], tuple) and site["socket"][0] in ["tcp", "tcp6"]
        return "tcp-tls:%s:%d" % cast(NetworkSocketDetails, site["socket"][1])["address"]
    return cmk.gui.sites.encode_socket_for_livestatus(site_id, site)


def _update_distributed_wato_file(sites: SiteConfigurations) -> None:
    """Update the distributed_wato.mk files in the central site
    Makes sure, that in distributed mode we monitor only the hosts that are directly assigned
    to our (the local) site.

    This function should only be called on the central site, since remote sites
    always get their distributed_wato.mk file pushed from the central site.
    """

    distributed_file = cmk.utils.paths.check_mk_config_dir / "distributed_wato.mk"
    if distributed_file.exists() and load_from_mk_file(
        distributed_file, key="is_distributed_setup_remote_site", default=False, lock=False
    ):
        # This is a remote site, do not create/clear distributed_wato.mk files here
        return

    sites_with_replication = False
    for siteid, site in sites.items():
        if is_replication_enabled(site):
            sites_with_replication = True
        if site_is_local(site):
            create_distributed_wato_files(
                base_dir=cmk.utils.paths.omd_root,
                site_id=siteid,
                is_remote=False,
            )

    if not sites_with_replication:
        _clear_distributed_wato_file()


def is_livestatus_encrypted(site: SiteConfiguration) -> bool:
    if not isinstance(site["socket"], tuple):
        return False
    family_spec, address_spec = site["socket"]
    return (
        family_spec in ["tcp", "tcp6"]
        and cast(NetworkSocketDetails, address_spec)["tls"][0] != "plain_text"
    )


def site_globals_editable(all_sites: SiteConfigurations, site: SiteConfiguration) -> bool:
    # Site is a remote site of another site. Allow to edit probably pushed site
    # specific globals when remote Setup is enabled
    if is_distributed_setup_remote_site(all_sites):
        return True

    # Local site: Don't enable site specific locals when no remote sites configured
    if not has_distributed_setup_remote_sites(all_sites):
        # Show the site specific globals only for the central site if it includes changes
        return bool(site.get("globals"))

    return is_replication_enabled(site) or site_is_local(site)


def _clear_distributed_wato_file() -> None:
    p = cmk.utils.paths.check_mk_config_dir / "distributed_wato.mk"
    # We do not delete the file but empty it. That way
    # we do not need write permissions to the conf.d
    # directory!
    if p.exists():
        store.save_text_to_file(p, "")


class PushSnapshotRequest(NamedTuple):
    site_id: SiteId
    tar_content: bytes


def get_effective_global_setting(site_id: SiteId, is_remote_site: bool, varname: str) -> Any:
    effective_global_settings = load_configuration_settings()
    default_values = ABCConfigDomain.get_all_default_globals()

    if is_remote_site:
        current_settings = load_configuration_settings(site_specific=True)
    else:
        sites = site_management_registry["site_management"].load_sites()
        current_settings = sites[site_id].get("globals", {})

    if varname in current_settings:
        return current_settings[varname]

    if varname in effective_global_settings:
        return effective_global_settings[varname]

    return default_values[varname]


class PingResult(NamedTuple):
    version: str
    edition: str
    omd_status: OMDStatus
    license_state: LicenseState | None


class ReplicationStatus(NamedTuple):
    site_id: SiteId
    success: bool
    response: PingResult | Exception


class ReplicationStatusFetcher:
    """Helper class to retrieve the replication status of all relevant sites"""

    def __init__(self) -> None:
        super().__init__()
        self._logger = logger.getChild("replication-status")

    def fetch(
        self,
        sites: Collection[tuple[SiteId, RemoteAutomationConfig]],
        *,
        debug: bool,
    ) -> Mapping[SiteId, ReplicationStatus]:
        self._logger.debug("Fetching replication status for %d sites" % len(sites))
        results_by_site: dict[SiteId, ReplicationStatus] = {}

        # Results are fetched simultaneously from the remote sites
        result_queue: JoinableQueue[ReplicationStatus] = JoinableQueue()

        processes = []
        for site_id, automation_config in sites:
            process = Process(
                target=self._fetch_for_site, args=(site_id, automation_config, result_queue, debug)
            )
            process.start()
            processes.append((site_id, process))

        # Now collect the results from the queue until all processes are finished
        while any(p.is_alive() for site_id, p in processes):
            try:
                result = result_queue.get_nowait()
                result_queue.task_done()
                results_by_site[result.site_id] = result

            except queue.Empty:
                time.sleep(0.5)  # wait some time to prevent CPU hogs

            except Exception as e:
                logger.exception(
                    "error collecting replication results from site %s", result.site_id
                )
                html.show_error(f"{result.site_id}: {e}")

        self._logger.debug("Got results")
        return results_by_site

    def _fetch_for_site(
        self,
        site_id: SiteId,
        automation_config: RemoteAutomationConfig,
        result_queue: JoinableQueue[ReplicationStatus],
        debug: bool,
    ) -> None:
        """Executes the tests on the site. This method is executed in a dedicated
        subprocess (One per site)"""
        self._logger.debug("[%s] Starting" % site_id)
        result = None
        try:
            # TODO: Would be better to clean all open fds that are not needed, but we don't
            # know the FDs of the result_queue pipe. Can we find it out somehow?
            # Cleanup resources of the apache
            # TODO: Needs to be solved for analzye_configuration too
            # for x in range(3, 256):
            #    try:
            #        os.close(x)
            #    except OSError, e:
            #        if e.errno == errno.EBADF:
            #            pass
            #        else:
            #            raise

            # Reinitialize logging targets
            log.init_logging()  # NOTE: We run in a subprocess!

            raw_result = do_remote_automation(automation_config, "ping", [], timeout=5, debug=debug)
            assert isinstance(raw_result, dict)

            result = ReplicationStatus(
                site_id=site_id,
                success=True,
                response=PingResult(
                    version=raw_result["version"],
                    edition=raw_result["edition"],
                    license_state=parse_license_state(raw_result.get("license_state", "")),
                    omd_status=raw_result["omd_status"],
                ),
            )
            self._logger.debug("[%s] Finished" % site_id)
        except Exception as e:
            self._logger.debug("[%s] Failed" % site_id, exc_info=True)
            result = ReplicationStatus(
                site_id=site_id,
                success=False,
                response=e,
            )
        finally:
            if result:
                result_queue.put(result)
            result_queue.close()
            result_queue.join_thread()
            result_queue.join()


def ldap_connections_are_configurable() -> bool:
    return mode_registry.get("ldap_config") is not None
