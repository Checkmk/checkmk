#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""LDAP configuration and diagnose page"""

import re
from collections.abc import Callable, Collection
from copy import deepcopy
from typing import Any, cast

from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.customer import customer_api
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.page_menu import (
    make_form_submit_link,
    make_simple_form_page_menu,
    PageMenu,
    PageMenuEntry,
)
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.userdb import (
    ACTIVE_DIR,
    get_connection,
    get_ldap_connections,
    LDAPUserConnectionConfig,
    load_connection_config,
    save_connection_config,
)
from cmk.gui.userdb.ldap_connector import (
    ldap_attr_of_connection,
    ldap_attribute_plugins_elements,
    ldap_filter_of_connection,
    LDAPAttributePluginGroupsToRoles,
    LDAPUserConnector,
)
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.escaping import strip_tags
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import DocReference
from cmk.gui.valuespec import (
    Age,
    CascadingDropdown,
    CascadingDropdownChoice,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    FixedValue,
    Float,
    ID,
    Integer,
    LDAPDistinguishedName,
    ListOfStrings,
    MigrateNotUpdated,
    rule_option_elements,
    TextInput,
    Tuple,
    ValueSpec,
)
from cmk.gui.wato.pages.userdb_common import (
    add_change,
    add_connections_page_menu,
    connection_actions,
    get_affected_sites,
    render_connections_page,
)
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode

from ._password_store_valuespecs import MigrateNotUpdatedToIndividualOrStoredPassword


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeLDAPConfig)
    mode_registry.register(ModeEditLDAPConnection)


# .
#   .--Valuespec-----------------------------------------------------------.
#   |           __     __    _                                             |
#   |           \ \   / /_ _| |_   _  ___  ___ _ __   ___  ___             |
#   |            \ \ / / _` | | | | |/ _ \/ __| '_ \ / _ \/ __|            |
#   |             \ V / (_| | | |_| |  __/\__ \ |_) |  __/ (__             |
#   |              \_/ \__,_|_|\__,_|\___||___/ .__/ \___|\___|            |
#   |                                         |_|                          |
#   '----------------------------------------------------------------------'


class LDAPConnectionValuespec(Dictionary):
    def __init__(self, new: bool, connection_id: str | None) -> None:
        self._new = new
        self._connection_id = connection_id
        connection = get_connection(self._connection_id)
        if connection is not None and not isinstance(connection, LDAPUserConnector):
            raise TypeError("connection is not LDAPUserConnector")
        self._connection = connection

        general_elements = self._general_elements()
        connection_elements = self._connection_elements()
        user_elements = self._user_elements()
        group_elements = self._group_elements()
        other_elements = self._other_elements()

        super().__init__(
            title=_("LDAP Connection"),
            elements=general_elements
            + connection_elements
            + user_elements
            + group_elements
            + other_elements,
            headers=[
                (_("General properties"), [key for key, _vs in general_elements]),
                (_("LDAP Connection"), [key for key, _vs in connection_elements]),
                (_("Users"), [key for key, _vs in user_elements]),
                (_("Groups"), [key for key, _vs in group_elements]),
                (_("Attribute sync plug-ins"), ["active_plugins"]),
                (_("Other"), ["cache_livetime"]),
            ],
            render="form",
            form_narrow=True,
            optional_keys=[
                "port",
                "use_ssl",
                "bind",
                "page_size",
                "response_timeout",
                "failover_servers",
                "user_filter",
                "user_filter_group",
                "user_id",
                "lower_user_ids",
                "connect_timeout",
                "version",
                "group_filter",
                "group_member",
                "suffix",
                "create_only_on_login",
            ],
            validate=self._validate_ldap_connection,
        )

    def _general_elements(self) -> list[DictionaryEntry]:
        general_elements: list[DictionaryEntry] = []

        if self._new:
            id_element: DictionaryEntry = (
                "id",
                ID(
                    title=_("ID"),
                    help=_(
                        "The ID of the connection must be a unique text, with the same requirements as an user id. "
                        "It will be used as an internal key when objects refer to the connection."
                    ),
                    allow_empty=False,
                    size=12,
                ),
            )
        else:
            id_element = (
                "id",
                FixedValue(
                    value=self._connection_id,
                    title=_("ID"),
                ),
            )

        general_elements += [id_element]

        general_elements += customer_api().customer_choice_element()

        general_elements += rule_option_elements()

        return general_elements

    def _connection_elements(self) -> list[tuple[str, ValueSpec]]:
        connection_elements: list[tuple[str, ValueSpec]] = [
            (
                "directory_type",
                CascadingDropdown(
                    title=_("Directory type"),
                    help=_(
                        "Select the software the LDAP directory is based on. Depending on "
                        "the selection e.g. the attribute names used in LDAP queries will "
                        "be altered."
                    ),
                    choices=[
                        ("ad", _("Active Directory"), self._vs_directory_options("ad")),
                        ("openldap", _("OpenLDAP"), self._vs_directory_options("openldap")),
                        (
                            "389directoryserver",
                            _("389 Directory Server"),
                            self._vs_directory_options("389directoryserver"),
                        ),
                    ],
                ),
            ),
            (
                "bind",
                Tuple(
                    title=_("Bind credentials"),
                    help=_(
                        "Set the credentials to be used to connect to the LDAP server. The "
                        "used account must not be allowed to do any changes in the directory "
                        "the whole connection is read only. "
                        "In some environment an anonymous connect/bind is allowed, in this "
                        "case you don't have to configure anything here."
                        "It must be possible to list all needed user and group objects from the "
                        "directory."
                    ),
                    elements=[
                        LDAPDistinguishedName(
                            title=_("Bind DN"),
                            help=_(
                                "Specify the distinguished name to be used to bind to "
                                "the LDAP directory, e. g. <tt>CN=ldap,OU=users,DC=example,DC=com</tt>"
                            ),
                            size=63,
                        ),
                        MigrateNotUpdatedToIndividualOrStoredPassword(
                            title=_("Bind password"),
                            help=_(
                                "Specify the password to be used to bind to the LDAP directory."
                            ),
                        ),
                    ],
                ),
            ),
            (
                "port",
                Integer(
                    title=_("TCP port"),
                    help=_(
                        "This variable allows to specify the TCP port to "
                        "be used to connect to the LDAP server. "
                    ),
                    minvalue=1,
                    maxvalue=65535,
                    default_value=389,
                ),
            ),
            (
                "use_ssl",
                FixedValue(
                    title=_("Use SSL"),
                    help=_(
                        "Connect to the LDAP server with a SSL encrypted connection. The "
                        '<a href="wato.py?mode=edit_configvar&site=&varname=trusted_certificate_authorities">trusted '
                        "certificates authorities</a> configured in Checkmk will be used to validate the "
                        "certificate provided by the LDAP server."
                    ),
                    value=True,
                    totext=_("Encrypt the network connection using SSL."),
                ),
            ),
            (
                "connect_timeout",
                Float(
                    title=_("Connect timeout"),
                    help=_("Timeout for the initial connection to the LDAP server in seconds."),
                    unit=_("Seconds"),
                    minvalue=1.0,
                    default_value=2.0,
                ),
            ),
            (
                "version",
                DropdownChoice(
                    title=_("LDAP version"),
                    help=_(
                        "Select the LDAP version the LDAP server is serving. Most modern "
                        "servers use LDAP version 3."
                    ),
                    choices=[(2, "2"), (3, "3")],
                    default_value=3,
                ),
            ),
            (
                "page_size",
                Integer(
                    title=_("Page size"),
                    help=_(
                        "LDAP searches can be performed in paginated mode, for example to improve "
                        "the performance. This enables pagination and configures the size of the pages."
                    ),
                    minvalue=1,
                    default_value=1000,
                ),
            ),
            (
                "response_timeout",
                Integer(
                    title=_("Response timeout"),
                    unit=_("Seconds"),
                    help=_("Timeout for LDAP query responses."),
                    minvalue=0,
                    default_value=5,
                ),
            ),
            (
                "suffix",
                TextInput(
                    allow_empty=False,
                    title=_("LDAP connection suffix"),
                    help=_(
                        "The LDAP connection suffix can be used to distinguish equal named objects "
                        "(name conflicts), for example user accounts, from different LDAP connections.<br>"
                        "It is used in the following situations:<br><br>"
                        "During LDAP synchronization, the LDAP sync might discover that a user to be "
                        "synchronized from from the current LDAP is already being synchronized from "
                        "another LDAP connection. Without the suffix configured this results in a name "
                        "conflict and the later user not being synchronized. If the connection has a "
                        "suffix configured, this suffix is added to the later username in case of the name "
                        "conflict to resolve it. The user will then be named <tt>[username]@[suffix]</tt> "
                        "instead of just <tt>[username]</tt>.<br><br>"
                        "In the case a user which users name is existing in multiple LDAP directories, "
                        "but associated to different persons, your user can insert <tt>[username]@[suffix]</tt>"
                        " during login instead of just the plain <tt>[username]</tt> to tell which LDAP "
                        "directory he is assigned to. Users without name conflict just need to provide their "
                        "regular username as usual."
                    ),
                    regex=re.compile(r"^[A-Z0-9.-]+(?:\.[A-Z]{2,24})?$", re.I),
                    validate=self._validate_ldap_connection_suffix,
                ),
            ),
        ]

        return connection_elements

    def _vs_directory_options(self, ty: str) -> Dictionary:
        connect_to_choices: list[CascadingDropdownChoice] = [
            (
                "fixed_list",
                _("Manually specify list of LDAP servers"),
                Dictionary(
                    elements=[
                        (
                            "server",
                            TextInput(
                                title=_("LDAP Server"),
                                help=_(
                                    "Set the host address of the LDAP server. Might be an IP address or "
                                    "resolvable host name."
                                ),
                                allow_empty=False,
                            ),
                        ),
                        (
                            "failover_servers",
                            ListOfStrings(
                                title=_("Failover servers"),
                                help=_(
                                    "When the connection to the first server fails with connect specific errors "
                                    "like timeouts or some other network related problems, the connect mechanism "
                                    "will try to use this server instead of the server configured above. If you "
                                    "use persistent connections (default), the connection is being used until the "
                                    "LDAP is not reachable or the local webserver is restarted."
                                ),
                                allow_empty=False,
                            ),
                        ),
                    ],
                    optional_keys=["failover_servers"],
                ),
            ),
        ]

        if ty == "ad":
            connect_to_choices.append(
                (
                    "discover",
                    _("Automatically discover LDAP server"),
                    Dictionary(
                        elements=[
                            (
                                "domain",
                                TextInput(
                                    title=_("DNS domain name to discover LDAP servers of"),
                                    help=_(
                                        "Configure the DNS domain name of your Active directory domain here, Checkmk "
                                        "will then query this domain for it's closest domain controller to communicate "
                                        "with."
                                    ),
                                    allow_empty=False,
                                ),
                            ),
                        ],
                        optional_keys=[],
                    ),
                ),
            )

        return Dictionary(
            elements=[
                (
                    "connect_to",
                    CascadingDropdown(
                        title=_("Connect to"),
                        choices=connect_to_choices,
                    ),
                ),
            ],
            optional_keys=[],
        )

    def _user_elements(self) -> list[tuple[str, ValueSpec]]:
        user_elements: list[tuple[str, ValueSpec]] = [
            (
                "user_dn",
                LDAPDistinguishedName(
                    title=_("User base DN"),
                    help=_(
                        "Give a base distinguished name here, e. g. <tt>OU=users,DC=example,DC=com</tt><br> "
                        "All user accounts to synchronize must be located below this one."
                    ),
                    size=80,
                ),
            ),
            (
                "user_scope",
                DropdownChoice(
                    title=_("Search scope"),
                    help=_(
                        "Scope to be used in LDAP searches. In most cases <i>Search whole subtree below "
                        "the base DN</i> is the best choice. "
                        "It searches for matching objects recursively."
                    ),
                    choices=[
                        ("sub", _("Search whole subtree below the base DN")),
                        ("base", _("Search only the entry at the base DN")),
                        ("one", _("Search all entries one level below the base DN")),
                    ],
                    default_value="sub",
                ),
            ),
            (
                "user_filter",
                TextInput(
                    title=_("Search filter"),
                    help=_(
                        "Using this option you can define an optional LDAP filter which is used during "
                        "LDAP searches. It can be used to only handle a subset of the users below the given "
                        "base DN.<br><br>Some common examples:<br><br> "
                        "All user objects in LDAP:<br> "
                        "<tt>(&(objectclass=user)(objectcategory=person))</tt><br> "
                        "Members of a group:<br> "
                        "<tt>(&(objectclass=user)(objectcategory=person)(memberof=CN=cmk-users,OU=groups,DC=example,DC=com))</tt><br> "
                        "Members of a nested group:<br> "
                        "<tt>(&(objectclass=user)(objectcategory=person)(memberof:1.2.840.113556.1.4.1941:=CN=cmk-users,OU=groups,DC=example,DC=com))</tt><br>"
                    ),
                    size=80,
                    default_value=lambda: ldap_filter_of_connection(
                        self._connection, "users", False
                    ),
                ),
            ),
            (
                "user_filter_group",
                LDAPDistinguishedName(
                    title=_("Filter group (see help)"),
                    help=_(
                        "Using this option you can define the DN of a group object which is used to filter the users. "
                        "Only members of this group will then be synchronized. This is a filter which can be "
                        'used to extend capabilities of the regular "Search Filter". Using the search filter '
                        "you can only define filters which directly apply to the user objects. To filter by "
                        "group memberships, you can use the <tt>memberOf</tt> attribute of the user objects in some "
                        "directories. But some directories do not have such attributes because the memberships "
                        "are stored in the group objects as e.g. <tt>member</tt> attributes. You should use the "
                        "regular search filter whenever possible and only use this filter when it is really "
                        "necessary. Finally you can say, you should not use this option when using Active Directory. "
                        "This option is necessary in OpenLDAP directories when you like to filter by group membership.<br><br>"
                        "If using, give a plain distinguished name of a group here, e. g. "
                        "<tt>CN=cmk-users,OU=groups,DC=example,DC=com</tt>"
                    ),
                    size=80,
                ),
            ),
            (
                "user_id",
                TextInput(
                    title=_("User-ID attribute"),
                    help=_(
                        "The attribute used to identify the individual users. It must have "
                        "unique values to make an user identifyable by the value of this "
                        "attribute."
                    ),
                    default_value=lambda: ldap_attr_of_connection(self._connection, "user_id"),
                ),
            ),
            (
                "lower_user_ids",
                FixedValue(
                    title=_("Lower case User-IDs"),
                    help=_("Convert imported User-IDs to lower case during synchronization."),
                    value=True,
                    totext=_("Enforce lower case User-IDs."),
                ),
            ),
            (
                "user_id_umlauts",
                MigrateNotUpdated(
                    valuespec=DropdownChoice(
                        title=_("Umlauts in User-IDs (deprecated)"),
                        help=_(
                            "Checkmk was not not supporting special characters (like Umlauts) in "
                            "User-IDs. To deal with LDAP users having umlauts in their User-IDs "
                            "you had the choice to replace umlauts with other characters. This option "
                            "is still available for compatibility reasons, but you are adviced to use "
                            'the "keep" option for new installations.'
                        ),
                        choices=[
                            ("keep", _("Keep special characters")),
                            ("replace", _('Replace umlauts like "&uuml;" with "ue"')),
                        ],
                        default_value="keep",
                    ),
                    migrate=lambda x: "keep" if (x == "skip") else x,
                ),
            ),
            (
                "create_only_on_login",
                FixedValue(
                    title=_("Create users only on login"),
                    value=True,
                    totext=_(
                        "Instead of creating the user accounts during the regular sync, create "
                        "the user on the first login."
                    ),
                ),
            ),
        ]

        return user_elements

    def _group_elements(self) -> list[tuple[str, ValueSpec]]:
        group_elements: list[tuple[str, ValueSpec]] = [
            (
                "group_dn",
                LDAPDistinguishedName(
                    title=_("Group base DN"),
                    help=_(
                        "Give a base distinguished name here, e. g. <tt>OU=groups,DC=example,DC=com</tt><br> "
                        "All groups used must be located below this one."
                    ),
                    size=80,
                ),
            ),
            (
                "group_scope",
                DropdownChoice(
                    title=_("Search scope"),
                    help=_(
                        "Scope to be used in group related LDAP searches. In most cases "
                        "<i>Search whole subtree below the base DN</i> "
                        "is the best choice. It searches for matching objects in the given base "
                        "recursively."
                    ),
                    choices=[
                        ("sub", _("Search whole subtree below the base DN")),
                        ("base", _("Search only the entry at the base DN")),
                        ("one", _("Search all entries one level below the base DN")),
                    ],
                    default_value="sub",
                ),
            ),
            (
                "group_filter",
                TextInput(
                    title=_("Search filter"),
                    help=_(
                        "Using this option you can define an optional LDAP filter which is used "
                        "during group related LDAP searches. It can be used to only handle a "
                        "subset of the groups below the given base DN.<br><br>"
                        "e.g. <tt>(objectclass=group)</tt>"
                    ),
                    size=80,
                    default_value=lambda: ldap_filter_of_connection(
                        self._connection, "groups", False
                    ),
                ),
            ),
            (
                "group_member",
                TextInput(
                    title=_("Member attribute"),
                    help=_("The attribute used to identify users group memberships."),
                    default_value=lambda: ldap_attr_of_connection(self._connection, "member"),
                ),
            ),
        ]

        return group_elements

    def _other_elements(self) -> list[tuple[str, ValueSpec]]:
        other_elements: list[tuple[str, ValueSpec]] = [
            (
                "active_plugins",
                Dictionary(
                    title=_("Attribute sync plug-ins"),
                    help=_(
                        "It is possible to fetch several attributes of users, like email or full names, "
                        "from the LDAP directory. This is done by plug-ins which can be individually enabled "
                        "or disabled. When enabling a plug-in, it is used upon the next synchronization of "
                        "user accounts for gathering their attributes. The user options which get imported "
                        "into Checkmk from LDAP will be locked in Setup."
                    ),
                    elements=lambda: ldap_attribute_plugins_elements(self._connection),
                    default_keys=["email", "alias", "auth_expire"],
                ),
            ),
            (
                "cache_livetime",
                Age(
                    title=_("Sync interval"),
                    help=_(
                        "This option defines the interval of the LDAP synchronization. This setting is only "
                        "used by sites which have the "
                        '<a href="wato.py?mode=sites">Automatic User '
                        "Synchronization</a> enabled.<br><br>"
                        "Please note: Passwords of the users are never stored in Setup and therefor never cached!"
                    ),
                    minvalue=60,
                    default_value=300,
                    display=["days", "hours", "minutes"],
                ),
            ),
        ]

        return other_elements

    def _validate_ldap_connection(self, value: dict[str, Any], varprefix: str) -> None:
        for role_id, group_specs in value["active_plugins"].get("groups_to_roles", {}).items():
            if role_id == "nested":
                continue  # This is the option to enabled/disable nested group handling, not a role to DN entry

            for index, group_spec in enumerate(group_specs):
                dn, connection_id = group_spec

                if connection_id is None:
                    group_dn = value["group_dn"]

                else:
                    connection = get_connection(connection_id)
                    if not connection:
                        continue
                    assert isinstance(connection, LDAPUserConnector)
                    group_dn = connection.get_group_dn()

                if not group_dn:
                    raise MKUserError(
                        varprefix,
                        _(
                            "You need to configure the group base DN to be able to "
                            "use the roles synchronization plug-in."
                        ),
                    )

                if not dn.lower().endswith(group_dn.lower()):
                    varname = "connection_p_active_plugins_p_groups_to_roles_p_%s_1_%d" % (
                        role_id,
                        index,
                    )
                    raise MKUserError(
                        varname, _("The configured DN does not match the group base DN.")
                    )

    def _validate_ldap_connection_suffix(self, value: str, varprefix: str) -> None:
        for connection in active_config.user_connections:
            suffix = connection.get("suffix")
            if suffix is None:
                continue

            connection_id = connection["id"]
            if connection_id != self._connection_id and value == suffix:
                raise MKUserError(
                    varprefix,
                    _("This suffix is already used by connection %s. Please choose another one.")
                    % connection_id,
                )


class ModeLDAPConfig(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "ldap_config"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["global"]

    @property
    def type(self) -> str:
        return "ldap"

    def title(self) -> str:
        return _("LDAP connections")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return add_connections_page_menu(
            title=self.title(),
            edit_mode_path="edit_ldap_connection",
            breadcrumb=breadcrumb,
            documentation_reference=DocReference.LDAP,
        )

    def action(self) -> ActionResult:
        return connection_actions(
            config_mode_url=self.mode_url(), connection_type=self.type, custom_config_dirs=()
        )

    def page(self) -> None:
        render_connections_page(
            connection_type=self.type,
            edit_mode_path="edit_ldap_connection",
            config_mode_path="ldap_config",
        )


class ModeEditLDAPConnection(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "edit_ldap_connection"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["global"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeLDAPConfig

    def _from_vars(self) -> None:
        self._connection_id = request.get_ascii_input("id")
        self._connection_cfg: LDAPUserConnectionConfig

        if self._connection_id is None:
            if (clone_id := request.var("clone")) is not None:
                self._cloned_connection(clone_id)
            else:
                self._new_connection()
        else:
            self._new = False
            self._connection_cfg = get_ldap_connections()[self._connection_id]

    def _new_connection(self) -> None:
        self._new = True
        directory_type: ACTIVE_DIR = ("ad", {"connect_to": ("fixed_list", {"server": ""})})
        self._connection_cfg = {
            "id": "",
            "description": "",
            "comment": "",
            "docu_url": "",
            "disabled": False,
            "directory_type": directory_type,
            "user_dn": "",
            "user_scope": "sub",
            "user_id_umlauts": "keep",
            "group_dn": "",
            "group_scope": "sub",
            "active_plugins": {},
            "cache_livetime": 300,
            "type": "ldap",
        }

    def _cloned_connection(self, clone_id: str) -> None:
        self._new = True
        ldap_connections = get_ldap_connections()
        self._connection_cfg = deepcopy(ldap_connections[clone_id])
        while self._connection_cfg["id"] in ldap_connections:
            self._connection_cfg["id"] += "x"

        self._connection_id = self._connection_cfg["id"]

    def title(self) -> str:
        if self._new:
            return _("Add LDAP connection")
        assert self._connection_id is not None
        return _("Edit LDAP connection: %s") % self._connection_id

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Connection"),
            breadcrumb,
            form_name="connection",
            button_name="_save",
            save_title=_("Save"),
        )
        menu.dropdowns[0].topics[0].entries.insert(
            1,
            PageMenuEntry(
                title=_("Save & test"),
                icon_name="save",
                item=make_form_submit_link(form_name="connection", button_name="_test"),
                is_shortcut=True,
                is_suggested=True,
            ),
        )

        return menu

    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return None

        _all_connections = {
            c["id"]: c for c in load_connection_config(lock=transactions.is_transaction())
        }

        vs = self._valuespec()
        connection_cfg = cast(LDAPUserConnectionConfig, vs.from_html_vars("connection"))
        vs.validate_value(dict(connection_cfg), "connection")
        connection_cfg["type"] = "ldap"

        if self._new:
            if connection_cfg["id"] in _all_connections:
                raise MKUserError(
                    "id",
                    _("The ID %s is already used by another connection.")
                    % self._connection_cfg["id"],
                )
            _all_connections[connection_cfg["id"]] = connection_cfg
            add_change(
                action_name="new-ldap-connection",
                text=_("Created new LDAP connection"),
                sites=get_affected_sites(connection_cfg),
            )

        else:
            _all_connections[connection_cfg["id"]] = connection_cfg
            add_change(
                action_name="edit-ldap-connection",
                text=_("Changed LDAP connection %s") % connection_cfg["id"],
                sites=get_affected_sites(connection_cfg),
            )

        self._connection_cfg = connection_cfg
        connection_list = list(_all_connections.values())
        save_connection_config(connection_list)
        active_config.user_connections = connection_list  # make directly available on current page

        if request.var("_save"):
            return redirect(mode_url("ldap_config"))

        # Handle the case where a user hit "Save & Test" during creation
        return redirect(self.mode_url(_test="1", id=self._connection_cfg["id"]))

    def page(self) -> None:
        html.open_div(id_="ldap")
        html.open_table()
        html.open_tr()

        html.open_td()
        with html.form_context("connection", method="POST"):
            html.prevent_password_auto_completion()
            vs = self._valuespec()
            vs.render_input("connection", dict(self._connection_cfg))
            vs.set_focus("connection")
            html.hidden_fields()
        html.close_td()

        html.open_td(style="padding-left:10px;vertical-align:top")
        html.h2(_("Diagnostics"))
        if not request.var("_test") or not self._connection_id:
            html.show_message(
                HTML.without_escaping(
                    "<p>%s</p><p>%s</p>"
                    % (
                        _(
                            "You can verify the single parts of your ldap configuration using this "
                            "dialog. Simply make your configuration in the form on the left side and "
                            'hit the "Save & Test" button to execute the tests. After '
                            "the page reload, you should see the results of the test here."
                        ),
                        _(
                            "If you need help during configuration or experience problems, please refer "
                            'to the <a target="_blank" '
                            'href="https://checkmk.com/checkmk_multisite_ldap_integration.html">'
                            "LDAP Documentation</a>."
                        ),
                    )
                )
            )
        else:
            connection = get_connection(self._connection_id)
            assert isinstance(connection, LDAPUserConnector)

            for address in connection.servers():
                html.h3("{}: {}".format(_("Server"), address))
                with table_element("test", searchable=False) as table:
                    for title, test_func in self._tests():
                        table.row()
                        try:
                            state, msg = test_func(connection, address)
                        except Exception as e:
                            state = False
                            msg = _("Exception: %s") % e
                            logger.exception("error testing LDAP %s for %s", title, address)

                        if state:
                            img = html.render_icon("checkmark", _("Success"))
                        else:
                            img = html.render_icon("cross", _("Failed"))

                        table.cell(_("Test"), title)
                        table.cell(_("State"), img)
                        table.cell(_("Details"), msg)

            connection.disconnect()

        html.close_td()
        html.close_tr()
        html.close_table()
        html.close_div()

    def _tests(
        self,
    ) -> list[tuple[str, Callable[[LDAPUserConnector, str], tuple[bool, str | None]]]]:
        return [
            (_("Connection"), self._test_connect),
            (_("User Base-DN"), self._test_user_base_dn),
            (_("Count Users"), self._test_user_count),
            (_("Group Base-DN"), self._test_group_base_dn),
            (_("Count Groups"), self._test_group_count),
            (_("Sync-Plug-in: Roles"), self._test_groups_to_roles),
        ]

    def _test_connect(self, connection: LDAPUserConnector, address: str) -> tuple[bool, str | None]:
        conn, msg = connection.connect_server(address)
        if conn:
            return (True, _("Connection established. The connection settings seem to be ok."))
        return (False, msg)

    def _test_user_base_dn(
        self, connection: LDAPUserConnector, address: str
    ) -> tuple[bool, str | None]:
        if not connection.has_user_base_dn_configured():
            return (False, _("The User Base DN is not configured."))
        connection.connect(enforce_new=True, enforce_server=address)
        if connection.user_base_dn_exists():
            return (True, _("The User Base DN could be found."))
        if connection.has_bind_credentials_configured():
            return (
                False,
                _(
                    "The User Base DN could not be found. Maybe the provided "
                    "user (provided via bind credentials) has no permission to "
                    "access the Base DN or the credentials are wrong."
                ),
            )
        return (
            False,
            _(
                "The User Base DN could not be found. Seems you need "
                "to configure proper bind credentials."
            ),
        )

    def _test_user_count(
        self, connection: LDAPUserConnector, address: str
    ) -> tuple[bool, str | None]:
        if not connection.has_user_base_dn_configured():
            return (False, _("The User Base DN is not configured."))
        connection.connect(enforce_new=True, enforce_server=address)
        try:
            ldap_users = connection.get_users()
            msg = _("Found no user object for synchronization. Please check your filter settings.")
        except Exception as e:
            ldap_users = None
            msg = "%s" % e
            if "successful bind must be completed" in msg:
                if not connection.has_bind_credentials_configured():
                    return (False, _("Please configure proper bind credentials."))
                return (
                    False,
                    _(
                        "Maybe the provided user (provided via bind credentials) has not "
                        "enough permissions or the credentials are wrong."
                    ),
                )

        if ldap_users and len(ldap_users) > 0:
            return (True, _("Found %d users for synchronization.") % len(ldap_users))
        return (False, msg)

    def _test_group_base_dn(
        self, connection: LDAPUserConnector, address: str
    ) -> tuple[bool, str | None]:
        if not connection.has_group_base_dn_configured():
            return (False, _("The Group Base DN is not configured, not fetching any groups."))
        connection.connect(enforce_new=True, enforce_server=address)
        if connection.group_base_dn_exists():
            return (True, _("The Group Base DN could be found."))
        return (False, _("The Group Base DN could not be found."))

    def _test_group_count(
        self, connection: LDAPUserConnector, address: str
    ) -> tuple[bool, str | None]:
        if not connection.has_group_base_dn_configured():
            return (False, _("The Group Base DN is not configured, not fetching any groups."))
        connection.connect(enforce_new=True, enforce_server=address)
        try:
            ldap_groups = connection.get_groups()
            msg = _("Found no group object for synchronization. Please check your filter settings.")
        except Exception as e:
            ldap_groups = None
            msg = "%s" % e
            if "successful bind must be completed" in msg:
                if not connection.has_bind_credentials_configured():
                    return (False, _("Please configure proper bind credentials."))
                return (
                    False,
                    _(
                        "Maybe the provided user (provided via bind credentials) has not "
                        "enough permissions or the credentials are wrong."
                    ),
                )
        if ldap_groups and len(ldap_groups) > 0:
            return (True, _("Found %d groups for synchronization.") % len(ldap_groups))
        return (False, msg)

    def _test_groups_to_roles(
        self, connection: LDAPUserConnector, address: str
    ) -> tuple[bool, str | None]:
        active_plugins = connection.active_plugins()
        if "groups_to_roles" not in active_plugins:
            return True, _("Skipping this test (plug-in is not enabled)")

        params = active_plugins["groups_to_roles"]
        connection.connect(enforce_new=True, enforce_server=address)

        plugin = LDAPAttributePluginGroupsToRoles()
        ldap_groups = plugin.fetch_needed_groups_for_groups_to_roles(connection, params)

        num_groups = 0

        for role_id, value in active_plugins["groups_to_roles"].items():
            if value is True:
                continue

            # We have typing for active_plugins["groups_to_roles"], however it doesn't
            # take into account the old config mentioned below.
            group_specs = cast(list, value)

            for group_spec in group_specs:
                if isinstance(group_spec, str):
                    dn = group_spec  # be compatible to old config without connection spec
                elif not isinstance(group_spec, tuple):
                    continue  # skip non configured ones (old valuespecs allowed None)
                else:
                    dn = group_spec[0]

                if dn.lower() not in ldap_groups:
                    return False, _('Could not find the group "%s" specified for role %s') % (
                        strip_tags(dn),
                        role_id,
                    )

                num_groups += 1
        return True, _("Found all %d groups.") % num_groups

    def _valuespec(self) -> LDAPConnectionValuespec:
        return LDAPConnectionValuespec(self._new, self._connection_id)
