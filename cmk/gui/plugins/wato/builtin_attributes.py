#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import Any

import cmk.utils.tags
from cmk.utils.type_defs import HostName, List
from cmk.utils.version import Edition, is_plus_edition

import cmk.gui.hooks as hooks
import cmk.gui.userdb as userdb
import cmk.gui.watolib as watolib
from cmk.gui import fields as gui_fields
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html, user
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    ABCHostAttributeNagiosText,
    ABCHostAttributeNagiosValueSpec,
    ABCHostAttributeValueSpec,
    ConfigHostname,
    host_attribute_registry,
    HostAttributeTopicAddress,
    HostAttributeTopicBasicSettings,
    HostAttributeTopicCustomAttributes,
    HostAttributeTopicDataSources,
    HostAttributeTopicManagementBoard,
    HostAttributeTopicMetaData,
    HostAttributeTopicNetworkScan,
    HostnameTranslation,
    IPMIParameters,
    SNMPCredentials,
)
from cmk.gui.sites import has_wato_slave_sites, is_wato_slave_site
from cmk.gui.utils.urls import urlencode_vars
from cmk.gui.valuespec import (
    AbsoluteDate,
    Age,
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    FixedValue,
    HostAddress,
    ID,
    Integer,
    IPv4Address,
    Labels,
    ListOf,
    ListOfStrings,
    RegExp,
    SetupSiteChoice,
    TextInput,
    TimeofdayRange,
    Transform,
    Tuple,
    ValueSpecText,
)

from cmk import fields


@host_attribute_registry.register
class HostAttributeAlias(ABCHostAttributeNagiosText):
    @property
    def _size(self):
        return 64

    def topic(self):
        return HostAttributeTopicBasicSettings

    def is_show_more(self) -> bool:
        return True

    @classmethod
    def sort_index(cls):
        return 10

    def name(self):
        return "alias"

    def nagios_name(self):
        return "alias"

    def is_explicit(self) -> bool:
        return True

    def title(self):
        return _("Alias")

    def help(self):
        return _("A comment or description of this host")

    def show_in_folder(self):
        return False

    def openapi_field(self) -> gui_fields.Field:
        return fields.String(description=self.help())


@host_attribute_registry.register
class HostAttributeIPv4Address(ABCHostAttributeValueSpec):
    def topic(self):
        return HostAttributeTopicAddress

    @classmethod
    def sort_index(cls):
        return 30

    def name(self):
        return "ipaddress"

    def show_in_folder(self):
        return False

    def depends_on_tags(self):
        return ["ip-v4"]

    def valuespec(self):
        return HostAddress(
            title=_("IPv4 address"),
            help=_(
                "In case the name of the host is not resolvable via <tt>/etc/hosts</tt> "
                "or DNS by your monitoring server, you can specify an explicit IP "
                "address or a resolvable DNS name of the host here.<br> <b>Notes</b>:<br> "
                "1. If you do not set this attribute, hostname resolution will be done when "
                "you activate the configuration. "
                "Check_MKs builtin DNS cache is activated per default in the global "
                "configuration to speed up the activation process. The cache is normally "
                "updated daily with a cron job. You can manually update the cache with the "
                "command <tt>cmk -v --update-dns-cache</tt>.<br>"
                "2. If you enter a DNS name here, the DNS resolution will be carried out "
                "each time the host is checked. Check_MKs DNS cache will NOT be queried. "
                "Use this only for hosts with dynamic IP addresses."
            ),
            allow_empty=False,
            allow_ipv6_address=False,
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.String(
            description="An IPv4 address.",
            validate=fields.ValidateAnyOfValidators(
                [
                    fields.ValidateIPv4(),
                    gui_fields.ValidateHostName(),
                ]
            ),
        )


@host_attribute_registry.register
class HostAttributeIPv6Address(ABCHostAttributeValueSpec):
    def topic(self):
        return HostAttributeTopicAddress

    @classmethod
    def sort_index(cls):
        return 40

    def name(self):
        return "ipv6address"

    def show_in_folder(self):
        return False

    def depends_on_tags(self):
        return ["ip-v6"]

    def valuespec(self):
        return HostAddress(
            title=_("IPv6 Address"),
            help=_(
                "In case the name of the host is not resolvable via <tt>/etc/hosts</tt> "
                "or DNS by your monitoring server, you can specify an explicit IPv6 "
                "address or a resolvable DNS name of the host here.<br> <b>Notes</b>:<br> "
                "1. If you do not set this attribute, hostname resolution will be done when "
                "you activate the configuration. "
                "Check_MKs builtin DNS cache is activated per default in the global "
                "configuration to speed up the activation process. The cache is normally "
                "updated daily with a cron job. You can manually update the cache with the "
                "command <tt>cmk -v --update-dns-cache</tt>.<br>"
                "2. If you enter a DNS name here, the DNS resolution will be carried out "
                "each time the host is checked. Check_MKs DNS cache will NOT be queried. "
                "Use this only for hosts with dynamic IP addresses."
            ),
            allow_empty=False,
            allow_ipv4_address=False,
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.String(
            description="An IPv6 address.",
            validate=fields.ValidateIPv6(),
        )


@host_attribute_registry.register
class HostAttributeAdditionalIPv4Addresses(ABCHostAttributeValueSpec):
    def topic(self):
        return HostAttributeTopicAddress

    @classmethod
    def sort_index(cls):
        return 50

    def is_show_more(self) -> bool:
        return True

    def name(self):
        return "additional_ipv4addresses"

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return False

    def valuespec(self):
        return ListOf(
            valuespec=HostAddress(
                allow_empty=False,
                allow_ipv6_address=False,
            ),
            title=_("Additional IPv4 addresses"),
            help=_(
                "Here you can specify additional IPv4 addresses. "
                "These can be used in some active checks like ICMP."
            ),
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.List(
            fields.String(
                validate=fields.ValidateAnyOfValidators(
                    [
                        fields.ValidateIPv4(),
                        gui_fields.ValidateHostName(),
                    ]
                )
            ),
            description="A list of IPv4 addresses.",
        )


@host_attribute_registry.register
class HostAttributeAdditionalIPv6Addresses(ABCHostAttributeValueSpec):
    def topic(self):
        return HostAttributeTopicAddress

    @classmethod
    def sort_index(cls):
        return 60

    def is_show_more(self) -> bool:
        return True

    def name(self):
        return "additional_ipv6addresses"

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return False

    def valuespec(self):
        return ListOf(
            valuespec=HostAddress(
                allow_empty=False,
                allow_ipv4_address=False,
            ),
            title=_("Additional IPv6 addresses"),
            help=_(
                "Here you can specify additional IPv6 addresses. "
                "These can be used in some active checks like ICMP."
            ),
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.List(
            fields.String(validate=fields.ValidateIPv6()),
            description="A list of IPv6 addresses.",
        )


@host_attribute_registry.register
class HostAttributeAgentConnection(ABCHostAttributeNagiosValueSpec):
    def topic(self):
        return HostAttributeTopicDataSources

    @classmethod
    def sort_index(cls):
        return 64  # after agent, before snmp

    def is_show_more(self) -> bool:
        # non plus edition currently only has one option
        return not is_plus_edition()

    def name(self):
        return "cmk_agent_connection"

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return True

    def depends_on_tags(self):
        return ["checkmk-agent"]

    def nagios_name(self) -> str:
        return self.name()

    def to_nagios(self, value: str) -> str:
        return value

    def valuespec(self):
        return DropdownChoice(
            title=_("Checkmk agent connection mode"),
            choices=[
                ("pull-agent", _("Pull: Checkmk server contacts the agent")),
                (
                    "push-agent",
                    _("Push: Checkmk agent contacts the server (%s only)")
                    % Edition.CPE.short.upper(),
                ),
            ],
            help=_(
                "By default the server will try to contact the monitored host and pull the"
                " data by initializing a TCP connection. "
                "On the %s you can configure a push configuration, where the monitored host is"
                " expected to send the data to the monitoring server without being actively"
                " triggered."
            )
            % Edition.CPE.title,
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.String(
            enum=["pull-agent", "push-agent"],
            description=(
                "This configures the communication direction of this host.\n"
                " * `pull-agent` (default) - The server will try to contact the monitored host and pull the data by initializing a TCP connection\n"
                " * `push-agent` - the host is expected to send the data to the monitoring server without being triggered\n"
            ),
        )


@host_attribute_registry.register
class HostAttributeSNMPCommunity(ABCHostAttributeValueSpec):
    def topic(self):
        return HostAttributeTopicDataSources

    @classmethod
    def sort_index(cls):
        return 70

    def name(self):
        return "snmp_community"

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return True

    def depends_on_tags(self):
        return ["snmp"]

    def valuespec(self):
        return SNMPCredentials(
            help=_(
                "Using this option you can configure the community which should be used when "
                "contacting this host via SNMP v1/v2 or v3. It is possible to configure the SNMP community by "
                'using the <a href="%s">SNMP Communities</a> ruleset, but when you configure '
                "a community here, this will override the community defined by the rules."
            )
            % "wato.py?mode=edit_ruleset&varname=snmp_communities",
            default_value=None,
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.Nested(
            gui_fields.SNMPCredentials,
            description=(
                "The SNMP access configuration. A configured SNMP v1/v2 community here "
                "will have precedence over any configured SNMP community rule. For this "
                "attribute to take effect, the attribute `tag_snmp_ds` needs to be set "
                "first."
            ),
        )


@host_attribute_registry.register
class HostAttributeParents(ABCHostAttributeValueSpec):
    def name(self):
        return "parents"

    def topic(self):
        return HostAttributeTopicBasicSettings

    @classmethod
    def sort_index(cls):
        return 80

    def is_show_more(self) -> bool:
        return True

    def show_in_table(self):
        return True

    def show_in_folder(self):
        return True

    def valuespec(self):
        return ListOfStrings(
            valuespec=ConfigHostname(),
            title=_("Parents"),
            help=_(
                "Parents are used to configure the reachability of hosts by the "
                "monitoring server. A host is considered to be <b>unreachable</b> if all "
                "of its parents are unreachable or down. Unreachable hosts will not be "
                "actively monitored.<br><br><b>Clusters</b> automatically configure all "
                "of their nodes as parents, but only if you do not configure parents "
                "manually.<br><br>In a distributed setup make sure that the host and all "
                "of its parents are monitored by the same site."
            ),
            orientation="horizontal",
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.List(
            gui_fields.HostField(should_exist=True),
            description="A list of parents of this host.",
        )

    def is_visible(self, for_what, new):
        return for_what != "cluster"

    def to_nagios(self, value):
        if value:
            return ",".join(value)

    def nagios_name(self):
        return "parents"

    def is_explicit(self) -> bool:
        return True

    def paint(self, value, hostname):
        parts = [
            html.render_a(hn, "wato.py?" + urlencode_vars([("mode", "edit_host"), ("host", hn)]))
            for hn in value
        ]
        return "", HTML(", ").join(parts)

    def filter_matches(self, crit: List, value: List, hostname: HostName) -> bool:
        return any(item in value for item in crit)


def validate_host_parents(host):
    for parent_name in host.parents():
        if parent_name == host.name():
            raise MKUserError(
                None, _("You configured the host to be it's own parent, which is not allowed.")
            )

        parent = watolib.Host.host(parent_name)
        if not parent:
            raise MKUserError(
                None, _("You defined the non-existing host '%s' as a parent.") % parent_name
            )

        if host.site_id() != parent.site_id():
            raise MKUserError(
                None,
                _(
                    "The parent '%s' is monitored on site '%s' while the host itself "
                    "is monitored on site '%s'. Both must be monitored on the same site. Remember: The parent/child "
                    "relation is used to describe the reachability of hosts by one monitoring daemon."
                )
                % (parent_name, parent.site_id(), host.site_id()),
            )


hooks.register_builtin("validate-host", validate_host_parents)


@hooks.request_memoize()
def _get_criticality_choices():
    """Returns the current configuration of the tag_group criticality"""
    tags = cmk.utils.tags.TagConfig.from_config(watolib.TagConfigFile().load_for_reading())
    criticality_group = tags.get_tag_group("criticality")
    if not criticality_group:
        return []

    return criticality_group.get_tag_choices()


@host_attribute_registry.register
class HostAttributeNetworkScan(ABCHostAttributeValueSpec):
    def name(self):
        return "network_scan"

    def may_edit(self):
        return user.may("wato.manage_hosts")

    def topic(self):
        return HostAttributeTopicNetworkScan

    @classmethod
    def sort_index(cls):
        return 90

    def show_in_table(self):
        return False

    def show_in_form(self):
        return False

    def show_in_folder(self):
        return True

    def show_in_host_search(self):
        return False

    def show_inherited_value(self):
        return False

    def valuespec(self):
        return Dictionary(
            elements=self._network_scan_elements,
            title=_("Network Scan"),
            help=_(
                "For each folder an automatic network scan can be configured. It will "
                "try to detect new hosts in the configured IP ranges by sending pings "
                "to each IP address to check whether or not a host is using this ip "
                "address. Each new found host will be added to the current folder by "
                "it's hostname, when resolvable via DNS, or by it's IP address."
            ),
            optional_keys=["max_parallel_pings", "translate_names"],
            default_text=_("Not configured."),
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.Nested(
            gui_fields.NetworkScan,
            description=(
                "Configuration for automatic network scan. Pings will be"
                "sent to each IP address in the configured ranges to check"
                "if a host is up or down. Each found host will be added to"
                "the folder by it's hostname (if possible) or IP address."
            ),
        )

    def _network_scan_elements(self):
        elements = [
            (
                "ip_ranges",
                ListOf(
                    valuespec=self._vs_ip_range(),
                    title=_("IP ranges to scan"),
                    add_label=_("Add new IP range"),
                    text_if_empty=_("No IP range configured"),
                ),
            ),
            (
                "exclude_ranges",
                ListOf(
                    valuespec=self._vs_ip_range(
                        with_regexp=True
                    ),  # regexp only used when excluding
                    title=_("IP ranges to exclude"),
                    add_label=_("Add new IP range"),
                    text_if_empty=_("No exclude range configured"),
                ),
            ),
            (
                "scan_interval",
                Age(
                    title=_("Scan interval"),
                    display=["days", "hours"],
                    default_value=60 * 60 * 24,
                    minvalue=3600,  # 1 hour
                ),
            ),
            (
                "time_allowed",
                Transform(
                    ListOf(
                        valuespec=TimeofdayRange(
                            allow_empty=False,
                        ),
                        title=_("Time allowed"),
                        help=_("Limit the execution of the scan to this time range."),
                        allow_empty=False,
                        style=ListOf.Style.FLOATING,
                        movable=False,
                        default_value=[((0, 0), (24, 0))],
                    ),
                    forth=lambda x: [x] if isinstance(x, tuple) else x,
                    back=sorted,
                ),
            ),
            (
                "set_ipaddress",
                Checkbox(
                    title=_("Set IPv4 address"),
                    help=_(
                        "Whether or not to configure the found IP address as the IPv4 "
                        "address of the found hosts."
                    ),
                    default_value=True,
                ),
            ),
        ]

        elements += self._optional_tag_criticality_element()
        elements += [
            (
                "max_parallel_pings",
                Integer(
                    title=_("Parallel pings to send"),
                    help=_(
                        "Set the maximum number of concurrent pings sent to target IP " "addresses."
                    ),
                    minvalue=1,
                    maxvalue=200,
                    default_value=100,
                ),
            ),
            (
                "run_as",
                DropdownChoice(
                    title=_("Run as"),
                    help=_(
                        "Execute the network scan in the Check_MK user context of the "
                        "choosen user. This user needs the permission to add new hosts "
                        "to this folder."
                    ),
                    choices=self._get_all_user_ids,
                    default_value=lambda: user.id,
                ),
            ),
            (
                "translate_names",
                HostnameTranslation(
                    title=_("Translate Hostnames"),
                ),
            ),
        ]

        return elements

    def _get_all_user_ids(self):
        return [
            (user_id, "%s (%s)" % (user_id, user.get("alias", user_id)))
            for user_id, user in userdb.load_users(lock=False).items()
        ]

    def _optional_tag_criticality_element(self):
        """This element is optional. The user may have deleted the tag group criticality"""
        choices = _get_criticality_choices()
        if not choices:
            return []

        return [
            (
                "tag_criticality",
                DropdownChoice(
                    title=_("Set criticality host tag"),
                    help=_(
                        'Added hosts will be created as "offline" host by default. You '
                        "can change this option to activate monitoring of new hosts after "
                        "next activation of the configuration after the scan."
                    ),
                    choices=choices,
                    default_value="offline",
                ),
            )
        ]

    def _vs_ip_range(self, with_regexp=False):
        # NOTE: The `ip_regex_list` choice is only used in the `exclude_ranges` key.
        options = [
            (
                "ip_range",
                _("IP-Range"),
                Tuple(
                    elements=[
                        IPv4Address(
                            title=_("From:"),
                        ),
                        IPv4Address(
                            title=_("To:"),
                        ),
                    ],
                    orientation="horizontal",
                ),
            ),
            (
                "ip_network",
                _("IP Network"),
                Tuple(
                    elements=[
                        IPv4Address(
                            title=_("Network address:"),
                        ),
                        Integer(
                            title=_("Netmask"),
                            minvalue=8,
                            maxvalue=30,
                            default_value=24,
                        ),
                    ],
                    orientation="horizontal",
                    help=_(
                        "Please avoid very large subnet sizes/ranges. A netmask value of /21 is "
                        "probably ok, while larger subnets (i.e. smaller netmask values) will lead "
                        "to excessive runtimes."
                    ),
                ),
            ),
            (
                "ip_list",
                _("Explicit List of IP Addresses"),
                ListOfStrings(
                    valuespec=IPv4Address(),
                    orientation="horizontal",
                ),
            ),
        ]
        regexp_exclude = (
            "ip_regex_list",
            _("List of patterns to exclude"),
            ListOfStrings(
                valuespec=RegExp(
                    mode=RegExp.prefix,
                ),
                orientation="horizontal",
                help=_(
                    "A list of regular expressions which are matched against the found "
                    "IP addresses to exclude them. The matched addresses are excluded."
                ),
            ),
        )
        if with_regexp:
            options.append(regexp_exclude)
        return CascadingDropdown(choices=options)


@host_attribute_registry.register
class HostAttributeNetworkScanResult(ABCHostAttributeValueSpec):
    def name(self):
        return "network_scan_result"

    def topic(self):
        return HostAttributeTopicNetworkScan

    @classmethod
    def sort_index(cls):
        return 100

    def show_in_table(self):
        return False

    def show_in_form(self):
        return False

    def show_in_folder(self):
        return True

    def show_in_host_search(self):
        return False

    def show_inherited_value(self):
        return False

    def editable(self):
        return False

    def openapi_field(self) -> gui_fields.Field:
        return fields.Nested(
            gui_fields.NetworkScanResult, description="Read only access to the network scan result"
        )

    def valuespec(self):
        return Dictionary(
            elements=[
                (
                    "start",
                    Alternative(
                        title=_("Started"),
                        elements=[
                            FixedValue(
                                value=None,
                                totext=_("No scan has been started yet."),
                            ),
                            AbsoluteDate(
                                include_time=True,
                                default_value=0,
                            ),
                        ],
                    ),
                ),
                (
                    "end",
                    Alternative(
                        title=_("Finished"),
                        elements=[
                            FixedValue(
                                value=None,
                                totext=_("No scan has finished yet."),
                            ),
                            FixedValue(
                                value=True,
                                totext="",  # currently running
                            ),
                            AbsoluteDate(
                                include_time=True,
                                default_value=0,
                            ),
                        ],
                    ),
                ),
                (
                    "state",
                    Alternative(
                        title=_("State"),
                        elements=[
                            FixedValue(
                                value=None,
                                totext="",  # Not started or currently running
                            ),
                            FixedValue(
                                value=True,
                                totext=_("Succeeded"),
                            ),
                            FixedValue(
                                value=False,
                                totext=_("Failed"),
                            ),
                        ],
                    ),
                ),
                (
                    "output",
                    TextInput(
                        title=_("Output"),
                    ),
                ),
            ],
            title=_("Last Scan Result"),
            optional_keys=[],
            default_text=_("No scan performed yet."),
        )


@host_attribute_registry.register
class HostAttributeManagementAddress(ABCHostAttributeValueSpec):
    def name(self):
        return "management_address"

    def topic(self):
        return HostAttributeTopicManagementBoard

    @classmethod
    def sort_index(cls):
        return 120

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return False

    def valuespec(self):
        return HostAddress(
            title=_("Address"),
            help=_(
                "Address (IPv4 or IPv6) or dns name under which the "
                "management board can be reached. If this is not set, "
                "the same address as that of the host will be used."
            ),
            allow_empty=False,
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.String(
            description="Address (IPv4 or IPv6) under which the management board can be reached.",
            validate=fields.ValidateAnyOfValidators(
                [
                    fields.ValidateIPv4(),
                    fields.ValidateIPv6(),
                ]
            ),
        )


@host_attribute_registry.register
class HostAttributeManagementProtocol(ABCHostAttributeValueSpec):
    def name(self):
        return "management_protocol"

    def topic(self):
        return HostAttributeTopicManagementBoard

    @classmethod
    def sort_index(cls):
        return 110

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return True

    def valuespec(self):
        return DropdownChoice(
            title=_("Protocol"),
            help=_("Specify the protocol used to connect to the management board."),
            choices=[
                (None, _("No management board")),
                ("snmp", _("SNMP")),
                ("ipmi", _("IPMI")),
                # ("ping", _("Ping-only"))
            ],
        )

    def openapi_field(self) -> gui_fields.Field:
        return gui_fields.HostAttributeManagementBoardField()


@host_attribute_registry.register
class HostAttributeManagementSNMPCommunity(ABCHostAttributeValueSpec):
    def name(self):
        return "management_snmp_community"

    def topic(self):
        return HostAttributeTopicManagementBoard

    @classmethod
    def sort_index(cls):
        return 130

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return True

    def valuespec(self):
        return SNMPCredentials(
            default_value=None,
            allow_none=True,
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.Nested(
            gui_fields.SNMPCredentials,
            description="SNMP credentials",
            allow_none=True,
        )


class IPMICredentials(Alternative):
    def __init__(self, **kwargs):
        kwargs["elements"] = [
            FixedValue(
                value=None,
                title=_("No explicit credentials"),
                totext="",
            ),
            IPMIParameters(),
        ]
        super().__init__(**kwargs)


@host_attribute_registry.register
class HostAttributeManagementIPMICredentials(ABCHostAttributeValueSpec):
    def name(self):
        return "management_ipmi_credentials"

    def topic(self):
        return HostAttributeTopicManagementBoard

    @classmethod
    def sort_index(cls):
        return 140

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return True

    def valuespec(self):
        return IPMICredentials(
            title=_("IPMI credentials"),
            default_value=None,
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.Nested(
            gui_fields.IPMIParameters,
            description="IPMI credentials",
            required=False,
        )


@host_attribute_registry.register
class HostAttributeSite(ABCHostAttributeValueSpec):
    def name(self):
        return "site"

    def is_show_more(self) -> bool:
        return not (has_wato_slave_sites() or is_wato_slave_site())

    def topic(self):
        return HostAttributeTopicBasicSettings

    @classmethod
    def sort_index(cls):
        return 20

    def show_in_table(self):
        return True

    def show_in_folder(self):
        return True

    def valuespec(self):
        return SetupSiteChoice(
            title=_("Monitored on site"),
            help=_("Specify the site that should monitor this host."),
            invalid_choice_error=_(
                "The configured site is not known to this site. In case you "
                "are configuring in a distributed slave, this may be a host "
                "monitored by another site. If you want to modify this "
                "host, you will have to change the site attribute to the "
                "local site. But this may make the host be monitored from "
                "multiple sites."
            ),
        )

    def openapi_field(self) -> gui_fields.Field:
        return gui_fields.SiteField(description="The site that should monitor this host.")

    def get_tag_groups(self, value):
        # Compatibility code for pre 2.0 sites. The SetupSiteChoice valuespec was previously setting
        # a "False" value instead of "" on remote sites. May be removed with 2.1.
        if value is False:
            return {"site": ""}

        if value is not None:
            return {"site": value}

        return {}


@host_attribute_registry.register
class HostAttributeLockedBy(ABCHostAttributeValueSpec):
    def name(self):
        return "locked_by"

    def topic(self):
        return HostAttributeTopicMetaData

    @classmethod
    def sort_index(cls):
        return 160

    def show_in_table(self):
        return False

    def show_in_form(self):
        return True

    def show_on_create(self):
        return False

    def show_in_folder(self):
        return False

    def show_in_host_search(self):
        return True

    def show_inherited_value(self):
        return False

    def editable(self):
        return False

    def valuespec(self):
        return Transform(
            LockedByValuespec(),
            forth=tuple,
            back=list,
        )

    def openapi_field(self) -> fields.Field:
        pass


class LockedByValuespec(Tuple):
    def __init__(self) -> None:
        super().__init__(
            orientation="horizontal",
            title_br=False,
            elements=[
                SetupSiteChoice(),
                ID(
                    title=_("Program"),
                ),
                ID(
                    title=_("Connection ID"),
                ),
            ],
            title=_("Locked by"),
            help=_(
                "The host is (partially) managed by an automatic data source like the "
                "dynamic configuration."
            ),
        )

    def value_to_html(self, value: tuple[Any, ...]) -> ValueSpecText:
        if not value or not value[1] or not value[2]:
            return _("Not locked")
        return super().value_to_html(value)


@host_attribute_registry.register
class HostAttributeLockedAttributes(ABCHostAttributeValueSpec):
    def name(self):
        return "locked_attributes"

    def topic(self):
        return HostAttributeTopicMetaData

    @classmethod
    def sort_index(cls):
        return 170

    def show_in_table(self):
        return False

    def show_in_form(self):
        return True

    def show_on_create(self):
        return False

    def show_in_folder(self):
        return False

    def show_in_host_search(self):
        return False

    def show_inherited_value(self):
        return False

    def editable(self):
        return False

    def valuespec(self):
        return ListOf(
            valuespec=DropdownChoice(choices=host_attribute_registry.get_choices),
            title=_("Locked attributes"),
            text_if_empty=_("Not locked"),
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.List(
            fields.String(),
            description="Attributes which are locked.",
        )


@host_attribute_registry.register
class HostAttributeMetaData(ABCHostAttributeValueSpec):
    def name(self):
        return "meta_data"

    def topic(self):
        return HostAttributeTopicMetaData

    @classmethod
    def sort_index(cls):
        return 155

    def show_in_table(self):
        return False

    def show_in_form(self):
        return True

    def show_on_create(self):
        return False

    def show_in_folder(self):
        return True

    def show_in_host_search(self):
        return False

    def show_inherited_value(self):
        return False

    def editable(self):
        return False

    def valuespec(self):
        return Dictionary(
            elements=[
                (
                    "created_at",
                    Alternative(
                        title=_("Created at"),
                        elements=[
                            FixedValue(
                                value=None,
                                totext=_("Sometime before 1.6"),
                            ),
                            AbsoluteDate(
                                include_time=True,
                                default_value=0,
                            ),
                        ],
                        default_value=time.time(),
                    ),
                ),
                (
                    "created_by",
                    Alternative(
                        title=_("Created by"),
                        elements=[
                            FixedValue(
                                value=None,
                                totext=_("Someone before 1.6"),
                            ),
                            TextInput(
                                title=_("Created by"),
                                default_value="unknown",
                            ),
                        ],
                        default_value=lambda: user.id,
                    ),
                ),
            ],
            title=_("Created"),
            optional_keys=[],
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.Nested(
            gui_fields.MetaData, description="Read only access to configured metadata."
        )


@host_attribute_registry.register
class HostAttributeLabels(ABCHostAttributeValueSpec):
    def name(self):
        return "labels"

    def title(self):
        return _("Labels")

    def topic(self):
        return HostAttributeTopicCustomAttributes

    @classmethod
    def sort_index(cls):
        return 190

    def help(self):
        return _(
            "With the help of labels you can flexibly group your hosts in "
            "order to refer to them later at other places in Check_MK, e.g. in rule chains. "
            "A label always consists of a combination of key and value in the format "
            '"key:value". A host can only have one value per key. Check_MK will not perform '
            "any validation on the labels you use."
        )

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return True

    def valuespec(self):
        return Labels(world=Labels.World.CONFIG, label_source=Labels.Source.EXPLICIT)

    def openapi_field(self) -> gui_fields.Field:
        return fields.Dict(
            description=self.help(),
        )

    def filter_matches(self, crit, value, hostname):
        return set(value).issuperset(set(crit))
