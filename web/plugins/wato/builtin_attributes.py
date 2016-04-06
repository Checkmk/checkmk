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

declare_host_attribute(ContactGroupsAttribute(),
                       show_in_table = False,
                       show_in_folder = True)

declare_host_attribute(NagiosTextAttribute("alias", "alias", _("Alias"),
                       _("A comment or description of this host"),
                       "", mandatory=False),
                       show_in_table = True,
                       show_in_folder = False)

declare_host_attribute(TextAttribute("ipaddress", _("IPv4 Address"),
                       _("In case the name of the host is not resolvable via <tt>/etc/hosts</tt> "
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
                         "Use this only for hosts with dynamic IP addresses."
                         ),
                         allow_empty = False),
                         show_in_table = True,
                         show_in_folder = False,
                         depends_on_tags = ["ip-v4"])

declare_host_attribute(TextAttribute("ipv6address", _("IPv6 Address"),
                       _("In case the name of the host is not resolvable via <tt>/etc/hosts</tt> "
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
                         "Use this only for hosts with dynamic IP addresses."
                         ),
                         allow_empty = False),
                         show_in_table = True,
                         show_in_folder = False,
                         depends_on_tags = ["ip-v6"])

declare_host_attribute(
    ValueSpecAttribute(
        "snmp_community",
        Password(
            title = _("SNMP Community"),
            help =  _("Using this option you can configure the community which should be used when "
                      "contacting this host via SNMP v1 or v2. It is possible to configure the SNMP community by "
                      "using the <a href=\"%s\">SNMP Communities</a> ruleset, but when you configure "
                      "a community here, this will override the community defined by the rules.") % \
                      html.makeuri([('mode', 'edit_ruleset'), ('varname', 'snmp_communities')]),
            allow_empty = False,
        )),
    show_in_table = False,
    show_in_folder = True,
    depends_on_tags = ['snmp'],
)

# Attribute for configuring parents
class ParentsAttribute(ValueSpecAttribute):
    def __init__(self):
        ValueSpecAttribute.__init__(self, "parents",
               ListOfStrings(
                   title = _("Parents"),
                   help = _("Parents are used to configure the reachability of hosts by the "
                      "monitoring server. A host is considered to be <b>unreachable</b> if all "
                      "of its parents are unreachable or down. Unreachable hosts will not be "
                      "actively monitored.<br><br><b>Clusters</b> automatically configure all "
                      "of their nodes as parents, but only if you do not configure parents "
                      "manually.<br><br>In a distributed setup make sure that the host and all "
                      "of its parents are monitored by the same site."),
                   orientation = "horizontal"))

    def to_nagios(self, value):
        if value:
            return ",".join(value)

    def nagios_name(self):
        return "parents"

    def paint(self, value, hostname):
        parts = [ '<a href="%s">%s</a>' % (
                   "wato.py?" + html.urlencode_vars([("mode", "edit_host"), ("host", hn)]), hn)
                  for hn in value ]
        return "", ", ".join(parts)


declare_host_attribute(ParentsAttribute(),
                       show_in_table = True,
                       show_in_folder = True)

def validate_host_parents(host):
    for parent_name in host.parents():
        if parent_name == host.name():
            raise MKUserError(None, _("You configured the host to be it's own parent, which is not allowed."))

        parent = Host.host(parent_name)
        if not parent:
            raise MKUserError(None, _("You defined the non-existing host '%s' as a parent.") % parent_name)

        if host.site_id() != parent.site_id():
            raise MKUserError(None, _("The parent '%s' is monitored on site '%s' while the host itself "
              "is monitored on site '%s'. Both must be monitored on the same site. Remember: The parent/child "
              "relation is used to describe the reachability of hosts by one monitoring daemon.") %
                (parent_name, parent.site_id(), host.site_id()))

register_hook('validate-host', validate_host_parents)



class NetworkScanAttribute(ValueSpecAttribute):
    def __init__(self):
        def get_all_user_ids():
            return [ (user_id, "%s (%s)" % (user_id, user.get("alias", user_id)))
                     for user_id, user in userdb.load_users(lock = False).items() ]

        ValueSpecAttribute.__init__(self, "network_scan",
            Dictionary(
                elements = [
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
                    ("max_parallel_pings", Integer(
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
                        choices = get_all_user_ids,
                        default_value = lambda: config.user_id,
                    )),
                    ("translate_names", HostnameTranslation(
                        title = _("Translate Hostnames"),
                    )),
                ],
                title = _("Network Scan"),
                help = _("For each folder an automatic network scan can be configured. It will "
                         "try to detect new hosts in the configured IP ranges by sending pings "
                         "to each IP address to check whether or not a host is using this ip "
                         "address. Each new found host will be added to the current folder by "
                         "it's hostname, when resolvable via DNS, or by it's IP address."),
                optional_keys = ["max_parallel_pings", "translate_names"],
                default_text = _("Not configured."),
            )
        )


    def _vs_ip_range(self):
        return CascadingDropdown(
            choices = [
                ("ip_range", _("IP-Range"), Tuple(
                    elements = [
                        IPv4Address(
                            title = _("From:"),
                        ),
                        IPv4Address(
                            title = _("To:"),
                        ),
                    ],
                    orientation = "horizontal",
                )),
                ("ip_network", _("IP Network"), Tuple(
                    elements = [
                        IPv4Address(
                            title = _("Network address:"),
                        ),
                        Integer(
                            title = _("Netmask"),
                            minvalue = 8,
                            maxvalue = 30,
                        ),
                    ],
                    orientation = "horizontal",
                )),
                ("ip_list", _("Explicit List of IP Addresses"), ListOfStrings(
                    valuespec = IPv4Address(),
                    orientation = "horizontal",
                )),
                ("ip_regex_list", _("List of patterns to exclude"), ListOfStrings(
                    valuespec = RegExp(),
                    orientation = "horizontal",
                    help = _("A list of regular expressions which are matched against the found "
                             "IP addresses to exclude them. The matched addresses are excluded."),
                )),
            ]
        )


declare_host_attribute(NetworkScanAttribute(),
                       show_in_table = False,
                       show_in_form = False,
                       show_in_folder = True,
                       show_in_host_search = False,
                       show_inherited_value = False,
                       may_edit = lambda: config.may("wato.manage_hosts"),
                       topic = _("Network Scan"))



class NetworkScanResultAttribute(ValueSpecAttribute):
    def __init__(self):
        ValueSpecAttribute.__init__(self, "network_scan_result",
            Dictionary(
                elements = [
                    ("start", Alternative(
                        title = _("Started"),
                        elements = [
                            FixedValue(None,
                                totext = _("No scan has been started yet."),
                            ),
                            AbsoluteDate(
                                include_time = True,
                                default_value = 0,
                            ),
                        ],
                    )),
                    ("end", Alternative(
                        title = _("Finished"),
                        elements = [
                            FixedValue(None,
                                totext = _("No scan has finished yet."),
                            ),
                            FixedValue(True,
                                totext = "", # currently running
                            ),
                            AbsoluteDate(
                                include_time = True,
                                default_value = 0,
                            ),
                        ],
                    )),
                    ("state", Alternative(
                        title = _("State"),
                        elements = [
                            FixedValue(None,
                                totext = "", # Not started or currently running
                            ),
                            FixedValue(True,
                                totext = _("Succeeded"),
                            ),
                            FixedValue(False,
                                totext = _("Failed"),
                            ),
                        ],
                    )),
                    ("output", TextUnicode(
                        title = _("Output"),
                    )),
                ],
                title = _("Last Scan Result"),
                optional_keys = [],
                default_text = _("No scan performed yet."),
            )
        )



declare_host_attribute(NetworkScanResultAttribute(),
                       show_in_table = False,
                       show_in_form = False,
                       show_in_folder = True,
                       show_in_host_search = False,
                       show_inherited_value = False,
                       editable = False,
                       topic = _("Network Scan"))
