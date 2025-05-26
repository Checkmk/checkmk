#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from collections.abc import Callable, Sequence
from typing import Any, Literal

from marshmallow import ValidationError

from cmk.ccc.hostaddress import HostName
from cmk.ccc.user import UserId

import cmk.utils.tags
from cmk.utils.tags import TagGroupID

from cmk.gui import fields as gui_fields
from cmk.gui import hooks, userdb
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.converter import TransformDataForLegacyFormatOrRecomposeFunction
from cmk.gui.form_specs.generators.host_address import create_host_address
from cmk.gui.form_specs.generators.setup_site_choice import create_setup_site_choice
from cmk.gui.form_specs.generators.snmp_credentials import create_snmp_credentials
from cmk.gui.form_specs.private import labels as fs_labels
from cmk.gui.form_specs.private import ListOfStrings as FSListOfStrings
from cmk.gui.form_specs.private import (
    OptionalChoice,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.site_config import has_wato_slave_sites, is_wato_slave_site
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import urlencode_vars
from cmk.gui.valuespec import (
    AbsoluteDate,
    Age,
    Alternative,
    AlternativeModel,
    CascadingDropdown,
    Checkbox,
    DEF_VALUE,
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
    TimeofdayRangeValue,
    Transform,
    Tuple,
    ValueSpec,
    ValueSpecDefault,
    ValueSpecHelp,
    ValueSpecText,
    ValueSpecValidateFunc,
)
from cmk.gui.watolib.attributes import create_ipmi_parameters, IPMIParameters, SNMPCredentials
from cmk.gui.watolib.config_hostname import ConfigHostname
from cmk.gui.watolib.host_attributes import (
    ABCHostAttributeNagiosText,
    ABCHostAttributeValueSpec,
    host_attribute_choices,
    HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS,
    HOST_ATTRIBUTE_TOPIC_CUSTOM_ATTRIBUTES,
    HOST_ATTRIBUTE_TOPIC_MANAGEMENT_BOARD,
    HOST_ATTRIBUTE_TOPIC_META_DATA,
    HOST_ATTRIBUTE_TOPIC_MONITORING_DATASOURCES,
    HOST_ATTRIBUTE_TOPIC_NETWORK_ADDRESS,
    HOST_ATTRIBUTE_TOPIC_NETWORK_SCAN,
    HostAttributeTopic,
)
from cmk.gui.watolib.hosts_and_folders import Host
from cmk.gui.watolib.tags import TagConfigFile
from cmk.gui.watolib.translation import HostnameTranslation

import cmk.fields.validators
from cmk import fields
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    InvalidElementMode,
    InvalidElementValidator,
    List,
    MonitoredHost,
    String,
)


class HostAttributeAlias(ABCHostAttributeNagiosText):
    @property
    def _size(self):
        return 64

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS

    def is_show_more(self) -> bool:
        return True

    @classmethod
    def sort_index(cls) -> int:
        return 10

    def name(self) -> str:
        return "alias"

    def nagios_name(self):
        return "alias"

    def is_explicit(self) -> bool:
        return True

    def title(self) -> str:
        return _("Alias")

    def help(self):
        return _("Add a comment or describe this host")

    def show_in_folder(self):
        return False

    def openapi_field(self) -> gui_fields.Field:
        return fields.String(description=self.help())


class HostAttributeIPv4Address(ABCHostAttributeValueSpec):
    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_NETWORK_ADDRESS

    @classmethod
    def sort_index(cls) -> int:
        return 30

    def name(self) -> str:
        return "ipaddress"

    def show_in_folder(self):
        return False

    def depends_on_tags(self):
        return ["ip-v4"]

    def valuespec(self) -> ValueSpec:
        return HostAddress(
            title=_("IPv4 address"),
            help=_(
                "Specify an explicit IP address or resolvable DNS name here, if "
                "the host name is not resolvable via <tt>/etc/hosts</tt> or DNS. "
                "If you do not set this attribute, host name resolution will be "
                "performed when the configuration is enabled. Checkmk's "
                "built-in DNS cache is enabled by default in the global "
                "configuration to speed up the activation process. The cache is "
                "normally updated daily by a cron job. You can manually update "
                "the cache with the <tt>cmk -v --update-dns-cache</tt> "
                "command.<br><br><b>Dynamic IP addresses only:</b><br>If you "
                "enter a DNS name here, the DNS resolution will be performed "
                "each time the host is checked. Checkmk's DNS cache is "
                "<b>NOT</b> queried."
            ),
            allow_empty=False,
            allow_ipv6_address=False,
        )

    def form_spec(self) -> String:
        return create_host_address(
            title=Title("IPv4 address"),
            help_text=Help(
                "Specify an explicit IP address or resolvable DNS name here, if "
                "the host name is not resolvable via <tt>/etc/hosts</tt> or DNS. "
                "If you do not set this attribute, host name resolution will be "
                "performed when the configuration is enabled. Checkmk's "
                "built-in DNS cache is enabled by default in the global "
                "configuration to speed up the activation process. The cache is "
                "normally updated daily by a cron job. You can manually update "
                "the cache with the <tt>cmk -v --update-dns-cache</tt> "
                "command.<br><br><b>Dynamic IP addresses only:</b><br>If you "
                "enter a DNS name here, the DNS resolution will be performed "
                "each time the host is checked. Checkmk's DNS cache is "
                "<b>NOT</b> queried."
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
                    fields.ValidateHostName(),
                ]
            ),
        )


class HostAttributeIPv6Address(ABCHostAttributeValueSpec):
    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_NETWORK_ADDRESS

    @classmethod
    def sort_index(cls) -> int:
        return 40

    def name(self) -> str:
        return "ipv6address"

    def show_in_folder(self):
        return False

    def depends_on_tags(self):
        return ["ip-v6"]

    def valuespec(self) -> ValueSpec:
        return HostAddress(
            title=_("IPv6 address"),
            help=_(
                "Specify an explicit IPv6 address or resolvable DNS name here, if "
                "the host name is not resolvable via <tt>/etc/hosts</tt> or DNS. "
                "If you do not set this attribute, host name resolution will be "
                "performed when the configuration is enabled. Checkmk's "
                "built-in DNS cache is enabled by default in the global "
                "configuration to speed up the activation process. The cache is "
                "normally updated daily by a cron job. You can manually update "
                "the cache with the <tt>cmk -v --update-dns-cache</tt> "
                "command.<br><br><b>Dynamic IP addresses only:</b><br>If you "
                "enter a DNS name here, the DNS resolution will be performed "
                "each time the host is checked. Checkmk's DNS cache is "
                "<b>NOT</b> queried."
            ),
            allow_empty=False,
            allow_ipv4_address=False,
        )

    def form_spec(self) -> String:
        return create_host_address(
            title=Title("IPv6 address"),
            help_text=Help(
                "Specify an explicit IPv6 address or resolvable DNS name here, if "
                "the host name is not resolvable via <tt>/etc/hosts</tt> or DNS. "
                "If you do not set this attribute, host name resolution will be "
                "performed when the configuration is enabled. Checkmk's "
                "built-in DNS cache is enabled by default in the global "
                "configuration to speed up the activation process. The cache is "
                "normally updated daily by a cron job. You can manually update "
                "the cache with the <tt>cmk -v --update-dns-cache</tt> "
                "command.<br><br><b>Dynamic IP addresses only:</b><br>If you "
                "enter a DNS name here, the DNS resolution will be performed "
                "each time the host is checked. Checkmk's DNS cache is "
                "<b>NOT</b> queried."
            ),
            allow_empty=False,
            allow_ipv4_address=False,
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.String(
            description="An IPv6 address.",
            validate=fields.ValidateAnyOfValidators(
                [
                    fields.ValidateIPv6(),
                    fields.ValidateHostName(),
                ]
            ),
        )


class HostAttributeAdditionalIPv4Addresses(ABCHostAttributeValueSpec):
    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_NETWORK_ADDRESS

    @classmethod
    def sort_index(cls) -> int:
        return 50

    def is_show_more(self) -> bool:
        return True

    def name(self) -> str:
        return "additional_ipv4addresses"

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return False

    def depends_on_tags(self):
        return ["ip-v4"]

    def valuespec(self) -> ValueSpec:
        return ListOf(
            valuespec=HostAddress(
                allow_empty=False,
                allow_ipv6_address=False,
            ),
            title=_("Additional IPv4 addresses"),
            help=_(
                "Specify additional IPv4 addresses here. These can be used in "
                "active checks such as ICMP."
            ),
        )

    def form_spec(self) -> List:
        return List[str](
            title=Title("Additional IPv4 addresses"),
            help_text=Help(
                "Specify additional IPv4 addresses here. These can be used in "
                "active checks such as ICMP."
            ),
            element_template=create_host_address(allow_empty=False, allow_ipv6_address=False),
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.List(
            fields.String(
                validate=fields.ValidateAnyOfValidators(
                    [
                        fields.ValidateIPv4(),
                        fields.ValidateHostName(),
                    ]
                )
            ),
            description="A list of IPv4 addresses.",
        )


class HostAttributeAdditionalIPv6Addresses(ABCHostAttributeValueSpec):
    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_NETWORK_ADDRESS

    @classmethod
    def sort_index(cls) -> int:
        return 60

    def is_show_more(self) -> bool:
        return True

    def name(self) -> str:
        return "additional_ipv6addresses"

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return False

    def depends_on_tags(self):
        return ["ip-v6"]

    def valuespec(self) -> ValueSpec:
        return ListOf(
            valuespec=HostAddress(
                allow_empty=False,
                allow_ipv4_address=False,
            ),
            title=_("Additional IPv6 addresses"),
            help=_(
                "Specify additional IPv6 addresses here. These can be used in "
                "active checks such as ICMP."
            ),
        )

    def form_spec(self) -> List:
        return List[str](
            title=Title("Additional IPv6 addresses"),
            help_text=Help(
                "Specify additional IPv6 addresses here. These can be used in "
                "active checks such as ICMP."
            ),
            element_template=create_host_address(allow_empty=False, allow_ipv4_address=False),
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.List(
            fields.String(
                validate=fields.ValidateAnyOfValidators(
                    [
                        fields.ValidateIPv6(),
                        fields.ValidateHostName(),
                    ]
                ),
            ),
            description="A list of IPv6 addresses.",
        )


class HostAttributeSNMPCommunity(ABCHostAttributeValueSpec):
    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_MONITORING_DATASOURCES

    @classmethod
    def sort_index(cls) -> int:
        return 70

    def name(self) -> str:
        return "snmp_community"

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return True

    def depends_on_tags(self):
        return ["snmp"]

    def valuespec(self) -> ValueSpec:
        return SNMPCredentials(
            help=_(
                "Configure the community to be used when contacting this host via SNMP v1/v2 or "
                "v3. You can also configure the SNMP community using the <a href='%s'>SNMP "
                "credentials of monitored host</a> rule set. Configuring a community here explicitly "
                "overrides the community defined by a rule. Communication via SNMP v1 and v2c "
                "is unencrypted. Consider using SNMP v3 for a higher level of security."
            )
            % "wato.py?mode=edit_ruleset&varname=snmp_communities",
            default_value=None,
        )

    def form_spec(self) -> TransformDataForLegacyFormatOrRecomposeFunction:
        return create_snmp_credentials(
            help_text=Help(
                "Configure the community to be used when contacting this host via SNMP v1/v2 or "
                "v3. You can also configure the SNMP community using the <a href='%s'>SNMP "
                "credentials of monitored host</a> ruleset. Configuring a community explicitly "
                "here overrides the community defined by a rule. Communication via SNMP v1 and v2c "
                "is unencrypted. Consider using SNMP v3 for a higher level of security."
            )
            % "wato.py?mode=edit_ruleset&varname=snmp_communities",
            default_value="community",
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


class HostAttributeParents(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "parents"

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS

    @classmethod
    def sort_index(cls) -> int:
        return 80

    def is_show_more(self) -> bool:
        return True

    def show_in_table(self) -> bool:
        return True

    def show_in_folder(self) -> bool:
        return True

    def valuespec(self) -> ValueSpec:
        return ListOfStrings(
            valuespec=ConfigHostname(),  # type: ignore[arg-type]  # should be Valuespec[str]
            title=_("Parents"),
            help=_(
                "Parents are used to configure the reachability of hosts to the "
                "monitoring server. A host is considered unreachable if all of "
                "its parents are unreachable or down. Unreachable hosts are not "
                "actively monitored.<br><br><b>Clusters</b> automatically "
                "configure all their nodes as Parents, but only if you do not "
                "manually configure Parents.<br><br><b>Distributed "
                "setup:</b><br>Make sure that the host and all its parents are "
                "monitored by the same site."
            ),
            orientation="horizontal",
        )

    def form_spec(self) -> FSListOfStrings:
        return FSListOfStrings(
            title=Title("Parents"),
            help_text=Help(
                "Parents are used to configure the reachability of hosts to the "
                "monitoring server. A host is considered unreachable if all of "
                "its parents are unreachable or down. Unreachable hosts are not "
                "actively monitored.<br><br><b>Clusters</b> automatically "
                "configure all their nodes as Parents, but only if you do not "
                "manually configure Parents.<br><br><b>Distributed "
                "setup:</b><br>Make sure that the host and all its parents are "
                "monitored by the same site."
            ),
            string_spec=MonitoredHost(title=Title("Host")),
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.List(
            gui_fields.HostField(should_exist=True, skip_validation_on_view=True),
            description="A list of parents of this host.",
        )

    def is_visible(self, for_what: str, new: bool) -> bool:
        return for_what != "cluster"

    def to_nagios(self, value: str) -> str | None:
        if value:
            return ",".join(value)
        return None

    def nagios_name(self) -> str:
        return "parents"

    def is_explicit(self) -> bool:
        return True

    def paint(self, value: str, hostname: HostName) -> tuple[str, HTML]:
        parts = [
            HTMLWriter.render_a(
                hn, "wato.py?" + urlencode_vars([("mode", "edit_host"), ("host", hn)])
            )
            for hn in value
        ]
        return "", HTML.without_escaping(", ").join(parts)

    def filter_matches(self, crit: list, value: list, hostname: HostName) -> bool:
        return any(item in value for item in crit)


def validate_host_parents(host):
    for parent_name in host.parents():
        if parent_name == host.name():
            raise MKUserError(
                None,
                _("You configured the host to be its own parent, which is not allowed."),
            )

        parent = Host.host(parent_name)
        if not parent:
            raise MKUserError(
                None,
                _("You defined the non-existing host '%s' as a parent.") % parent_name,
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


@hooks.request_memoize()
def _get_criticality_choices():
    """Returns the current configuration of the tag_group criticality"""
    tags = cmk.utils.tags.TagConfig.from_config(TagConfigFile().load_for_reading())
    criticality_group = tags.get_tag_group(TagGroupID("criticality"))
    if not criticality_group:
        return []

    return criticality_group.get_tag_choices()


class HostAttributeNetworkScan(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "network_scan"

    def may_edit(self):
        return user.may("wato.manage_hosts")

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_NETWORK_SCAN

    @classmethod
    def sort_index(cls) -> int:
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

    def valuespec(self) -> ValueSpec:
        return Dictionary(
            elements=self._network_scan_elements,
            title=_("Network scan"),
            help=_(
                "For each folder an automatic network scan can be configured. It will "
                "try to detect new hosts in the configured IP ranges by sending pings "
                "to each IP address to check whether or not a host is using this IP "
                "address. Each new found host will be added to the current folder by "
                "its host name, when resolvable via DNS, or by its IP address."
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
                "the folder by it's host name (if possible) or IP address."
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
                    valuespec=ListOf(
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
                    to_valuespec=self._time_allowed_to_valuespec,
                    from_valuespec=sorted,
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
                        "Set the maximum number of concurrent pings sent to target IP addresses."
                    ),
                    minvalue=1,
                    maxvalue=200,
                    default_value=100,
                ),
            ),
            (
                "run_as",
                DropdownChoice[UserId](
                    title=_("Run as"),
                    help=_(
                        "Execute the network scan in the Checkmk user context of the "
                        "chosen user. This user needs the permission to add new hosts "
                        "to this folder."
                    ),
                    choices=self._get_all_user_ids,
                    default_value=lambda: user.id if user.id is not None else DEF_VALUE,
                ),
            ),
            (
                "translate_names",
                HostnameTranslation(
                    title=_("Translate host names"),
                ),
            ),
        ]

        return elements

    @staticmethod
    def _time_allowed_to_valuespec(
        # we need list as input type here because Sequence[TimeofdayRangeValue] is hard to
        # distinguish from TimeofdayRangeValue
        v: TimeofdayRangeValue | list[TimeofdayRangeValue],
    ) -> list[TimeofdayRangeValue]:
        return v if isinstance(v, list) else [v]

    def _get_all_user_ids(self) -> Sequence[tuple[UserId, str]]:
        return [
            (user_id, "{} ({})".format(user_id, user.get("alias", user_id)))
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
        options: list[tuple[str, str, ValueSpec[Any]]] = [
            (
                "ip_range",
                _("IP range"),
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
                _("IP network"),
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
                _("Explicit list of IP addresses"),
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


class HostAttributeNetworkScanResult(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "network_scan_result"

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_NETWORK_SCAN

    @classmethod
    def sort_index(cls) -> int:
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

    def openapi_editable(self):
        return False

    def openapi_field(self) -> gui_fields.Field:
        return fields.Nested(
            gui_fields.NetworkScanResult,
            description="Read only access to the network scan result",
        )

    def valuespec(self) -> ValueSpec:
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


class HostAttributeManagementAddress(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "management_address"

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_MANAGEMENT_BOARD

    @classmethod
    def sort_index(cls) -> int:
        return 120

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return False

    def valuespec(self) -> ValueSpec:
        return HostAddress(
            title=_("Address"),
            help=_(
                "Address (IPv4 or IPv6) or dns name under which the "
                "management board can be reached. If this is not set, "
                "the same address as that of the host will be used."
            ),
            allow_empty=False,
        )

    def form_spec(self) -> String:
        return create_host_address(
            title=Title("Address"),
            help_text=Help(
                "Address (IPv4 or IPv6) or dns name under which the "
                "management board can be reached. If this is not set, "
                "the same address as that of the host will be used."
            ),
            allow_empty=False,
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.String(
            description="Address (IPv4, IPv6 or host name) under which the management board can be reached.",
            validate=fields.ValidateAnyOfValidators(
                [
                    fields.ValidateIPv4(),
                    fields.ValidateIPv6(),
                    fields.ValidateHostName(),
                ]
            ),
        )


class HostAttributeManagementProtocol(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "management_protocol"

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_MANAGEMENT_BOARD

    @classmethod
    def sort_index(cls) -> int:
        return 110

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return True

    def valuespec(self) -> ValueSpec:
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

    def form_spec(self) -> SingleChoiceExtended:
        return SingleChoiceExtended(
            title=Title("Protocol"),
            help_text=Help("Specify the protocol used to connect to the management board."),
            elements=[
                SingleChoiceElementExtended(
                    name=None,
                    title=Title("No management board"),
                ),
                SingleChoiceElementExtended(
                    name="snmp",
                    title=Title("SNMP"),
                ),
                SingleChoiceElementExtended(
                    name="ipmi",
                    title=Title("IPMI"),
                ),
            ],
        )

    def openapi_field(self) -> gui_fields.Field:
        return gui_fields.HostAttributeManagementBoardField()


class HostAttributeManagementSNMPCommunity(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "management_snmp_community"

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_MANAGEMENT_BOARD

    @classmethod
    def sort_index(cls) -> int:
        return 130

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return True

    def valuespec(self) -> ValueSpec:
        return SNMPCredentials(
            default_value=None,
            allow_none=True,
        )

    def form_spec(self) -> TransformDataForLegacyFormatOrRecomposeFunction:
        return create_snmp_credentials(
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
    def __init__(
        self,
        match: Callable[[AlternativeModel], int] | None = None,
        show_alternative_title: bool = False,
        on_change: str | None = None,
        orientation: Literal["horizontal", "vertical"] = "vertical",
        # ValueSpec
        title: str | None = None,
        help: ValueSpecHelp | None = None,
        default_value: ValueSpecDefault[AlternativeModel] = DEF_VALUE,
        validate: ValueSpecValidateFunc[AlternativeModel] | None = None,
    ):
        super().__init__(
            elements=[
                FixedValue(
                    value=None,
                    title=_("No explicit credentials"),
                    totext="",
                ),
                IPMIParameters(),
            ],
            match=match,
            show_alternative_title=show_alternative_title,
            on_change=on_change,
            orientation=orientation,
            title=title,
            help=help,
            default_value=default_value,
            validate=validate,
        )


class HostAttributeManagementIPMICredentials(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "management_ipmi_credentials"

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_MANAGEMENT_BOARD

    @classmethod
    def sort_index(cls) -> int:
        return 140

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return True

    def valuespec(self) -> ValueSpec:
        return IPMICredentials(
            title=_("IPMI credentials"),
            default_value=None,
        )

    def form_spec(self) -> OptionalChoice:
        return OptionalChoice(
            title=Title("Explicit credentials"),
            none_label=Label(""),
            parameter_form=create_ipmi_parameters(),
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.Nested(
            gui_fields.IPMIParameters,
            description="IPMI credentials",
            required=False,
            allow_none=True,
        )


class HostAttributeSite(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "site"

    def is_show_more(self) -> bool:
        return not (has_wato_slave_sites() or is_wato_slave_site())

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS

    @classmethod
    def sort_index(cls) -> int:
        return 20

    def show_in_table(self):
        return True

    def show_in_folder(self):
        return True

    def valuespec(self) -> ValueSpec:
        return SetupSiteChoice(
            title=_("Monitored on site"),
            help=_("Specify the site that should monitor this host."),
            invalid_choice_error=_(
                "The configured site is not known to this site. In case you "
                "are configuring in a remote site, this may be a host "
                "monitored by another site. If you want to modify this "
                "host, you will have to change the site attribute to the "
                "local site. But this may make the host be monitored from "
                "multiple sites."
            ),
        )

    def form_spec(self) -> SingleChoiceExtended[str]:
        return create_setup_site_choice(
            title=Title("Monitored on site"),
            help_text=Help("Specify the site that should monitor this host."),
            invalid_element_validation=InvalidElementValidator(
                mode=InvalidElementMode.KEEP,
                error_msg=Message(
                    "The configured site is not known to this site. In case you "
                    "are configuring in a remote site, this may be a host "
                    "monitored by another site. If you want to modify this "
                    "host, you will have to change the site attribute to the "
                    "local site. But this may make the host be monitored from "
                    "multiple sites."
                ),
            ),
        )

    def openapi_field(self) -> gui_fields.Field:
        return gui_fields.SiteField(
            description="The site that should monitor this host.",
            presence="might_not_exist_on_view",
        )

    def get_tag_groups(self, value):
        # Compatibility code for pre 2.0 sites. The SetupSiteChoice valuespec was previously setting
        # a "False" value instead of "" on remote sites. May be removed with 2.1.
        if value is False:
            return {"site": ""}

        if value is not None:
            return {"site": value}

        return {}


class HostAttributeLockedBy(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "locked_by"

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_META_DATA

    @classmethod
    def sort_index(cls) -> int:
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

    def valuespec(self) -> ValueSpec:
        return Transform(
            valuespec=LockedByValuespec(),
            to_valuespec=tuple,
            from_valuespec=list,
        )

    def openapi_field(self) -> fields.Field:
        return fields.Nested(
            gui_fields.LockedBy,
            description=(
                "Identity of the entity which locked the locked_attributes. "
                "The identity is built out of the Site ID, the program name and the connection ID."
            ),
        )

    def filter_matches(
        self,
        crit: list[str],
        value: list[str] | tuple[str, str, str],
        hostname: HostName,
    ) -> bool:
        return crit == list(value)


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


class HostAttributeLockedAttributes(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "locked_attributes"

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_META_DATA

    @classmethod
    def sort_index(cls) -> int:
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

    def valuespec(self) -> ValueSpec:
        return ListOf(
            valuespec=DropdownChoice(choices=host_attribute_choices),
            title=_("Locked attributes"),
            text_if_empty=_("Not locked"),
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.List(
            fields.String(),
            description="Name of host attributes which are locked in the UI.",
        )


class HostAttributeMetaData(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "meta_data"

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_META_DATA

    @classmethod
    def sort_index(cls) -> int:
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

    def openapi_editable(self) -> bool:
        return False

    def valuespec(self) -> ValueSpec:
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


class HostAttributeDiscoveryFailed(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "inventory_failed"

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_META_DATA

    @classmethod
    def sort_index(cls) -> int:
        return 200

    def show_in_table(self):
        return False

    def show_in_form(self):
        return False

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

    def openapi_editable(self) -> bool:
        return True

    def valuespec(self) -> ValueSpec:
        return Checkbox(
            title=_("Discovery failed"),
            help=self._help_text(),
            default_value=False,
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.Boolean(
            example=False,
            required=False,
            description=self._help_text(),
        )

    def _help_text(self) -> str:
        return _(
            "Whether or not the last bulk discovery failed. It is set to True once it fails "
            "and unset in case a later discovery succeeds."
        )

    def get_tag_groups(self, value):
        return {}


class HostAttributeWaitingForDiscovery(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "waiting_for_discovery"

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_CUSTOM_ATTRIBUTES

    @classmethod
    def sort_index(cls) -> int:
        return 210

    def show_in_table(self):
        return False

    def show_in_form(self):
        return False

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

    def openapi_editable(self) -> bool:
        return True

    def valuespec(self) -> ValueSpec:
        return Checkbox(
            title=_("Waiting for discovery"),
            help=self._help_text(),
            default_value=False,
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.Boolean(
            example=False,
            required=False,
            description=self._help_text(),
        )

    def _help_text(self) -> str:
        return _(
            "This indicates that the host is waiting for a bulk discovery. It is set to True once the host is in the queue. It will be "
            "removed after the discovery is ended."
        )

    def get_tag_groups(self, value):
        return {}


class HostAttributeLabels(ABCHostAttributeValueSpec):
    def name(self) -> str:
        return "labels"

    def title(self) -> str:
        return _("Labels")

    def topic(self) -> HostAttributeTopic:
        return HOST_ATTRIBUTE_TOPIC_CUSTOM_ATTRIBUTES

    @classmethod
    def sort_index(cls) -> int:
        return 190

    def help(self):
        return _(
            "Labels allow you to flexibly group your hosts in order to "
            "refer to them later at other places in Checkmk, e.g. in rule "
            "chains.<br><b>Label format:</b> key:value<br><br>Neither the "
            "key nor the value can contain ‘:’. Checkmk does not perform "
            "any other validation on the labels you use."
        )

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return True

    def valuespec(self) -> ValueSpec:
        return Labels(world=Labels.World.CONFIG, label_source=Labels.Source.EXPLICIT)

    def form_spec(self) -> fs_labels.Labels:
        return fs_labels.Labels(
            world=fs_labels.World.CONFIG, label_source=fs_labels.Source.EXPLICIT
        )

    def openapi_field(self) -> gui_fields.Field:
        return fields.Dict(
            description=self.help(),
            keys=fields.String(description="The host label key", validate=self._validate_label_key),
            values=fields.String(
                description="The host label value", validate=self._validate_label_value
            ),
        )

    def _validate_label_key(self, data: str) -> None:
        if ":" in data:
            raise ValidationError(f"Invalid label key: {data!r}")

    def _validate_label_value(self, data: str) -> None:
        if ":" in data:
            raise ValidationError(f"Invalid label value: {data!r}")

    def filter_matches(self, crit, value, hostname):
        return set(value).issuperset(set(crit))
