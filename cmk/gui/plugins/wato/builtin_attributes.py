#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.hooks as hooks
import cmk.gui.userdb as userdb
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
from cmk.gui.valuespec import (
    HostAddress,
    ListOf,
    ListOfStrings,
    Dictionary,
    Age,
    TimeofdayRange,
    Checkbox,
    DropdownChoice,
    Integer,
    CascadingDropdown,
    Tuple,
    IPv4Address,
    RegExp,
    Alternative,
    FixedValue,
    AbsoluteDate,
    TextUnicode,
    SiteChoice,
    ID,
)
from cmk.gui.exceptions import MKUserError

from . import (
    declare_host_attribute,
    SNMPCredentials,
    IPMIParameters,
    ContactGroupsAttribute,
    NagiosTextAttribute,
    ValueSpecAttribute,
    HostnameTranslation,
)

declare_host_attribute(
    ContactGroupsAttribute(),
    show_in_table=False,
    show_in_folder=True,
)

declare_host_attribute(
    NagiosTextAttribute(
        "alias",
        "alias",
        _("Alias"),
        _("A comment or description of this host"),
        "",
        mandatory=False),
    show_in_table=True,
    show_in_folder=False)

declare_host_attribute(
    ValueSpecAttribute(
        "ipaddress",
        HostAddress(
            title=_("IPv4 Address"),
            help=_("In case the name of the host is not resolvable via <tt>/etc/hosts</tt> "
                   "or DNS by your monitoring server, you can specify an explicit IP "
                   "address or a resolvable DNS name of the host here.<br> <b>Notes</b>:<br> "
                   "1. If you leave this attribute empty, hostname resolution will be done when "
                   "you activate the configuration. "
                   "Check_MKs builtin DNS cache is activated per default in the global "
                   "configuration to speed up the activation process. The cache is normally "
                   "updated daily with a cron job. You can manually update the cache with the "
                   "command <tt>cmk -v --update-dns-cache</tt>.<br>"
                   "2. If you enter a DNS name here, the DNS resolution will be carried out "
                   "each time the host is checked. Check_MKs DNS cache will NOT be queried. "
                   "Use this only for hosts with dynamic IP addresses."),
            allow_empty=False,
            allow_ipv6_address=False,
        )),
    show_in_table=True,
    show_in_folder=False,
    depends_on_tags=["ip-v4"],
    topic=_("Address"),
)

declare_host_attribute(
    ValueSpecAttribute(
        "ipv6address",
        HostAddress(
            title=_("IPv6 Address"),
            help=_("In case the name of the host is not resolvable via <tt>/etc/hosts</tt> "
                   "or DNS by your monitoring server, you can specify an explicit IPv6 "
                   "address or a resolvable DNS name of the host here.<br> <b>Notes</b>:<br> "
                   "1. If you leave this attribute empty, hostname resolution will be done when "
                   "you activate the configuration. "
                   "Check_MKs builtin DNS cache is activated per default in the global "
                   "configuration to speed up the activation process. The cache is normally "
                   "updated daily with a cron job. You can manually update the cache with the "
                   "command <tt>cmk -v --update-dns-cache</tt>.<br>"
                   "2. If you enter a DNS name here, the DNS resolution will be carried out "
                   "each time the host is checked. Check_MKs DNS cache will NOT be queried. "
                   "Use this only for hosts with dynamic IP addresses."),
            allow_empty=False,
            allow_ipv4_address=False,
        )),
    show_in_table=True,
    show_in_folder=False,
    depends_on_tags=["ip-v6"],
    topic=_("Address"),
)

declare_host_attribute(
    ValueSpecAttribute(
        "additional_ipv4addresses",
        ListOf(
            HostAddress(
                allow_empty=False,
                allow_ipv6_address=False,
            ),
            title=_("Additional IPv4 addresses"),
            help=_("Here you can specify additional IPv4 addresses. "
                   "These can be used in some active checks like ICMP."),
        )),
    show_in_table=False,
    show_in_folder=False,
    depends_on_tags=["ip-v4"],
    topic=_("Address"),
)

declare_host_attribute(
    ValueSpecAttribute(
        "additional_ipv6addresses",
        ListOf(
            HostAddress(
                allow_empty=False,
                allow_ipv4_address=False,
            ),
            title=_("Additional IPv6 addresses"),
            help=_("Here you can specify additional IPv6 addresses. "
                   "These can be used in some active checks like ICMP."),
        )),
    show_in_table=False,
    show_in_folder=False,
    depends_on_tags=["ip-v6"],
    topic=_("Address"),
)

declare_host_attribute(
    ValueSpecAttribute(
        "snmp_community",
            SNMPCredentials(
                help =  _("Using this option you can configure the community which should be used when "
                          "contacting this host via SNMP v1/v2 or v3. It is possible to configure the SNMP community by "
                          "using the <a href=\"%s\">SNMP Communities</a> ruleset, but when you configure "
                          "a community here, this will override the community defined by the rules.") % \
                            "wato.py?mode=edit_ruleset&varname=snmp_communities",
                default_value = None,
            )
    ),
    show_in_table = False,
    show_in_folder = True,
    depends_on_tags = ['snmp'],
)


# Attribute for configuring parents
class ParentsAttribute(ValueSpecAttribute):
    def __init__(self):
        ValueSpecAttribute.__init__(
            self, "parents",
            ListOfStrings(
                title=_("Parents"),
                help=_("Parents are used to configure the reachability of hosts by the "
                       "monitoring server. A host is considered to be <b>unreachable</b> if all "
                       "of its parents are unreachable or down. Unreachable hosts will not be "
                       "actively monitored.<br><br><b>Clusters</b> automatically configure all "
                       "of their nodes as parents, but only if you do not configure parents "
                       "manually.<br><br>In a distributed setup make sure that the host and all "
                       "of its parents are monitored by the same site."),
                orientation="horizontal"))

    def is_visible(self, for_what):
        return for_what != "cluster"

    def to_nagios(self, value):
        if value:
            return ",".join(value)

    def nagios_name(self):
        return "parents"

    def paint(self, value, hostname):
        parts = [
            html.render_a(hn, "wato.py?" + html.urlencode_vars([("mode", "edit_host"),
                                                                ("host", hn)])) for hn in value
        ]
        return "", HTML(", ").join(parts)


declare_host_attribute(
    ParentsAttribute(),
    show_in_table=True,
    show_in_folder=True,
)


def validate_host_parents(host):
    for parent_name in host.parents():
        if parent_name == host.name():
            raise MKUserError(
                None, _("You configured the host to be it's own parent, which is not allowed."))

        parent = watolib.Host.host(parent_name)
        if not parent:
            raise MKUserError(
                None,
                _("You defined the non-existing host '%s' as a parent.") % parent_name)

        if host.site_id() != parent.site_id():
            raise MKUserError(
                None,
                _("The parent '%s' is monitored on site '%s' while the host itself "
                  "is monitored on site '%s'. Both must be monitored on the same site. Remember: The parent/child "
                  "relation is used to describe the reachability of hosts by one monitoring daemon."
                 ) % (parent_name, parent.site_id(), host.site_id()))


hooks.register('validate-host', validate_host_parents)


class NetworkScanAttribute(ValueSpecAttribute):
    def __init__(self):

        ValueSpecAttribute.__init__(
            self, "network_scan",
            Dictionary(
                elements=self._network_scan_elements,
                title=_("Network Scan"),
                help=_("For each folder an automatic network scan can be configured. It will "
                       "try to detect new hosts in the configured IP ranges by sending pings "
                       "to each IP address to check whether or not a host is using this ip "
                       "address. Each new found host will be added to the current folder by "
                       "it's hostname, when resolvable via DNS, or by it's IP address."),
                optional_keys=["max_parallel_pings", "translate_names"],
                default_text=_("Not configured."),
            ))

    def _network_scan_elements(self):
        return [
            ("ip_ranges", ListOf(self._vs_ip_range(),
                title = _("IP ranges to scan"),
                add_label = _("Add new IP range"),
                text_if_empty = _("No IP range configured"),
            )),
            ("exclude_ranges", ListOf(self._vs_ip_range(),
                title = _("IP ranges to exclude"),
                add_label = _("Add new IP range"),
                text_if_empty = _("No exclude range configured"),
            )),
            ("scan_interval", Age(
                title = _("Scan interval"),
                display = [ "days", "hours" ],
                default_value = 60*60*24,
                minvalue = 3600, # 1 hour
            )),
            ("time_allowed", TimeofdayRange(
                title = _("Time allowed"),
                help = _("Limit the execution of the scan to this time range."),
                allow_empty=False,
            )),
            ("set_ipaddress", Checkbox(
                title = _("Set IPv4 address"),
                help = _("Whether or not to configure the found IP address as the IPv4 "
                         "address of the found hosts."),
                default_value = True,
            ))] + self._optional_tag_criticality_element() +\
            [("max_parallel_pings", Integer(
                title = _("Parallel pings to send"),
                help = _("Set the maximum number of concurrent pings sent to target IP "
                         "addresses."),
                minvalue = 1,
                maxvalue = 200,
                default_value = 100,
            )),
            ("run_as", DropdownChoice(
                title = _("Run as"),
                help = _("Execute the network scan in the Check_MK user context of the "
                         "choosen user. This user needs the permission to add new hosts "
                         "to this folder."),
                choices = self._get_all_user_ids,
                default_value = lambda: config.user.id,
            )),
            ("translate_names", HostnameTranslation(
                title = _("Translate Hostnames"),
            ))
        ]

    def _get_all_user_ids(self):
        return [(user_id, "%s (%s)" % (user_id, user.get("alias", user_id)))
                for user_id, user in userdb.load_users(lock=False).items()]

    def _get_criticality_choices(self):
        """Returns the current configuration of the tag_group criticality"""
        tags = watolib.HosttagsConfiguration()
        tags.load()
        criticality_group = tags.get_tag_group("criticality")
        if not criticality_group:
            return []
        return criticality_group.get_tag_choices()

    def _optional_tag_criticality_element(self):
        """This element is optional. The user may have deleted the tag group criticality"""
        tags = watolib.HosttagsConfiguration()
        tags.load()
        criticality_group = tags.get_tag_group("criticality")
        if not criticality_group:
            return []

        return [("tag_criticality",
                 DropdownChoice(
                     title=_("Set criticality host tag"),
                     help=_("Added hosts will be created as \"offline\" host by default. You "
                            "can change this option to activate monitoring of new hosts after "
                            "next activation of the configuration after the scan."),
                     choices=self._get_criticality_choices,
                     default_value="offline",
                 ))]

    def _vs_ip_range(self):
        return CascadingDropdown(choices=[
            ("ip_range", _("IP-Range"),
             Tuple(
                 elements=[
                     IPv4Address(title=_("From:"),),
                     IPv4Address(title=_("To:"),),
                 ],
                 orientation="horizontal",
             )),
            ("ip_network", _("IP Network"),
             Tuple(
                 elements=[
                     IPv4Address(title=_("Network address:"),),
                     Integer(
                         title=_("Netmask"),
                         minvalue=8,
                         maxvalue=30,
                     ),
                 ],
                 orientation="horizontal",
             )),
            ("ip_list", _("Explicit List of IP Addresses"),
             ListOfStrings(
                 valuespec=IPv4Address(),
                 orientation="horizontal",
             )),
            ("ip_regex_list", _("List of patterns to exclude"),
             ListOfStrings(
                 valuespec=RegExp(mode=RegExp.prefix,),
                 orientation="horizontal",
                 help=_("A list of regular expressions which are matched against the found "
                        "IP addresses to exclude them. The matched addresses are excluded."),
             )),
        ])


declare_host_attribute(
    NetworkScanAttribute(),
    show_in_table=False,
    show_in_form=False,
    show_in_folder=True,
    show_in_host_search=False,
    show_inherited_value=False,
    may_edit=lambda: config.user.may("wato.manage_hosts"),
    topic=_("Network Scan"))


class NetworkScanResultAttribute(ValueSpecAttribute):
    def __init__(self):
        ValueSpecAttribute.__init__(
            self,
            "network_scan_result",
            Dictionary(
                elements=[
                    (
                        "start",
                        Alternative(
                            title=_("Started"),
                            elements=[
                                FixedValue(
                                    None,
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
                                    None,
                                    totext=_("No scan has finished yet."),
                                ),
                                FixedValue(
                                    True,
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
                                    None,
                                    totext="",  # Not started or currently running
                                ),
                                FixedValue(
                                    True,
                                    totext=_("Succeeded"),
                                ),
                                FixedValue(
                                    False,
                                    totext=_("Failed"),
                                ),
                            ],
                        ),
                    ),
                    (
                        "output",
                        TextUnicode(title=_("Output")),
                    ),
                ],
                title=_("Last Scan Result"),
                optional_keys=[],
                default_text=_("No scan performed yet."),
            ))


declare_host_attribute(
    NetworkScanResultAttribute(),
    show_in_table=False,
    show_in_form=False,
    show_in_folder=True,
    show_in_host_search=False,
    show_inherited_value=False,
    editable=False,
    topic=_("Network Scan"))

declare_host_attribute(
    ValueSpecAttribute(
        "management_address",
        HostAddress(
            title=_("Address"),
            help=_("Address (IPv4 or IPv6) or dns name under which the "
                   "management board can be reached. If this is not set, "
                   "the same address as that of the host will be used."),
            allow_empty=False)),
    show_in_table=False,
    show_in_folder=False,
    topic=_("Management Board"))

declare_host_attribute(
    ValueSpecAttribute(
        "management_protocol",
        DropdownChoice(
            title=_("Protocol"),
            help=_("Specify the protocol used to connect to the management board."),
            choices=[
                (None, _("No management board")),
                ("snmp", _("SNMP")),
                ("ipmi", _("IPMI")),
                #("ping", _("Ping-only"))
            ],
        )),
    show_in_table=False,
    show_in_folder=True,
    topic=_("Management Board"))

declare_host_attribute(
    ValueSpecAttribute("management_snmp_community",
                       SNMPCredentials(
                           default_value=None,
                           allow_none=True,
                       )),
    show_in_table=False,
    show_in_folder=True,
    topic=_("Management Board"))


class IPMICredentials(Alternative):
    def __init__(self, **kwargs):
        kwargs["style"] = "dropdown"
        kwargs["elements"] = [
            FixedValue(
                None,
                title=_("No explicit credentials"),
                totext="",
            ),
            IPMIParameters(),
        ]
        super(IPMICredentials, self).__init__(**kwargs)


declare_host_attribute(
    ValueSpecAttribute("management_ipmi_credentials",
                       IPMICredentials(
                           title=_("IPMI credentials"),
                           default_value=None,
                       )),
    show_in_table=False,
    show_in_folder=True,
    topic=_("Management Board"),
)


class SiteAttribute(ValueSpecAttribute):
    def __init__(self):
        # Default is is the local one, if one exists or
        # no one if there is no local site
        ValueSpecAttribute.__init__(
            self, "site",
            SiteChoice(
                title=_("Monitored on site"),
                help=_("Specify the site that should monitor this host."),
                invalid_choice_error=_("The configured site is not known to this site. In case you "
                                       "are configuring in a distributed slave, this may be a host "
                                       "monitored by another site. If you want to modify this "
                                       "host, you will have to change the site attribute to the "
                                       "local site. But this may make the host be monitored from "
                                       "multiple sites.")))

    def get_tag_list(self, value):
        if value is False:
            return ["site:"]
        elif value is not None:
            return ["site:" + value]
        return []


declare_host_attribute(
    SiteAttribute(),
    show_in_table=True,
    show_in_folder=True,
)

declare_host_attribute(
    ValueSpecAttribute(
        "locked",
        Dictionary(
            title=_("Locked"),
            help=_("The host is (partially) managed by an automatic data source like the "
                   "Dynamic Configuration."),
            elements=[
                ("locked_by",
                 Tuple(
                     orientation="horizontal",
                     title_br=False,
                     elements=[
                         SiteChoice(),
                         ID(title=_("Program"),),
                         ID(title=_("Connection ID"),),
                     ],
                     title=_("Locked by"),
                 )),
                ("attributes", ListOf(
                    ID(),
                    title=_("Locked attributes"),
                )),
            ],
        )),
    show_in_table=False,
    show_in_form=True,
    show_in_folder=True,
    show_in_host_search=False,
    show_inherited_value=False,
    editable=False,
)
