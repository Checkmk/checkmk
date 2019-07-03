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

import cmk.defines as defines

# Rules for configuring parameters of checks (services)

register_rulegroup("checkparams", _("Parameters for discovered services"),
    _("Levels and other parameters for checks found by the Check_MK service discovery.\n"
      "Use these rules in order to define parameters like filesystem levels, "
      "levels for CPU load and other things for services that have been found "
      "by the automatic service discovery of Check_MK."))
group = "checkparams"

subgroup_networking =   _("Networking")
subgroup_storage =      _("Storage, Filesystems and Files")
subgroup_os =           _("Operating System Resources")
subgroup_printing =     _("Printers")
subgroup_environment =  _("Temperature, Humidity, Electrical Parameters, etc.")
subgroup_applications = _("Applications, Processes & Services")
subgroup_virt =         _("Virtualization")
subgroup_hardware =     _("Hardware, BIOS")
subgroup_inventory =    _("Discovery - automatic service detection")

# register_rule(group, varname, valuespec = None, title = None,
#               help = None, itemspec = None, itemtype = None, itemname = None,
#               itemhelp = None, itemenum = None,
#               match = "first", optional = False, factory_default = NO_FACTORY_DEFAULT)
# register_check_parameters(subgroup, checkgroup, title, valuespec, itemspec, match_type, has_inventory=True, register_static_check=True)

# TODO: Sort all rules and check parameters into the figlet header sections.
# Beware: there are dependencies, so sometimes the order matters.  All rules
# that are not yet handles are in the last section: in "Unsorted".  Move rules
# from there into their appropriate sections until "Unsorted" is empty.
# Create new rules directly in the correct secions.

#   .--Networking----------------------------------------------------------.
#   |        _   _      _                      _    _                      |
#   |       | \ | | ___| |___      _____  _ __| | _(_)_ __   __ _          |
#   |       |  \| |/ _ \ __\ \ /\ / / _ \| '__| |/ / | '_ \ / _` |         |
#   |       | |\  |  __/ |_ \ V  V / (_) | |  |   <| | | | | (_| |         |
#   |       |_| \_|\___|\__| \_/\_/ \___/|_|  |_|\_\_|_| |_|\__, |         |
#   |                                                       |___/          |
#   '----------------------------------------------------------------------'

register_rule(group + "/" + subgroup_networking,
    "ping_levels",
    Dictionary(
        title = _("PING and host check parameters"),
        help = _("This rule sets the parameters for the host checks (via <tt>check_icmp</tt>) "
                 "and also for PING checks on ping-only-hosts. For the host checks only the "
                 "critical state is relevant, the warning levels are ignored."),
        elements = check_icmp_params,
        ),
        match="dict")

register_check_parameters(
    subgroup_networking,
    "palo_alto_sessions",
    "Palo Alto Active Sessions",
    Dictionary(
        elements = [
            ("levels_sessions_used",
            Tuple(
                title = "Levels for sessions used",
                elements = [
                    Integer(title = "Warning at", default_value = 60, unit = u"%"),
                    Integer(title = "Critical at", default_value = 70, unit = u"%"),
                ])),
        ]),
    None,
    "dict"
)

register_check_parameters(
    subgroup_networking,
    "fortinet_signatures",
    "Fortigate Signatures",
    Dictionary(
        elements = [
            ('av_age',
             Tuple(title = "Age of Anti-Virus signature",
                   elements = [
                       Age(title=_("Warning at"), default_value = 86400),
                       Age(title=_("Critical at"), default_value = 2*86400),
                   ])),
            ('ips_age',
             Tuple(title = "Age of Intrusion Prevention signature",
                   elements = [
                       Age(title=_("Warning at"), default_value = 86400),
                       Age(title=_("Critical at"), default_value = 2*86400),
                   ])),
        ]
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_networking,
    "huawei_osn_laser",
    _("OSN Laser attenuation"),
    Dictionary(
        elements = [
            ('levels_low_in',
             Tuple(
                title = _('Levels for laser input'),
                default_value = (-160.0, -180.0),
                elements = [
                    Integer( title = _("Warning below")),
                    Integer( title = _("Critical below"))
            ])),
            ('levels_low_out',
             Tuple(
                title = _('Levels for laser output'),
                default_value = (-160.0, -180.0),
                elements = [
                    Integer( title = _("Warning below")),
                    Integer( title = _("Critical below"))
            ])),
        ]
    ),
    TextAscii( title = _("Laser id")),
    match_type = "dict",
)

register_check_parameters(
    subgroup_networking,
    "brocade_optical",
    "Brocade Optical Signal",
    Dictionary(
        elements = [
            ('temp',     Checkbox(title = _("Temperature Alert"),
                                  default_value = True)
             ),
            ('tx_light', Checkbox(title = _("TX Light alert"),
                                  label = _("TX Light alert"),
                                  default_value = False)),
            ('rx_light', Checkbox(title = _("RX Light alert"),
                                  label = _("TX Light alert"),
                                  default_value = False)),
            ('lanes',    Checkbox(
                            title = _("Lanes"),
                            label = _("Monitor & Graph Lanes"),
                            help  = _("Monitor and graph the lanes, if the port has multiple"))),
        ],
        optional_keys=[]
    ),
    TextAscii(
        title = _("Interface id"),
    ),
    match_type = "dict"
)

register_check_parameters(
        subgroup_applications,
        "mtr",
        _("Traceroute with MTR"),
        Dictionary(
                help = _("This ruleset can be used to change MTR's (Matt's traceroute) warning and crit levels for packet loss, average "\
                 "roundtrip and standard deviation."),
                elements = [
                        ("avg",
                                Tuple(
                                        title = _("Average roundtrip time in ms"),
                                        elements = [
                                                Integer(title = _("Warning at"), default_value = 150, unit = _("ms"), min_value = 0 ),
                                                Integer(title = _("Critical at"), default_value = 250, unit = _("ms"), min_value = 0 ),
                                                ],
                                        help = _("The maximum average roundtrip time in ms before this service goes into warning/critical. "\
                             "This alarm only applies to the target host, not the hops in between."),
                                        ),
                                ),
                        ("stddev",
                                Tuple(
                                        title = _("Standard deviation of roundtrip times in ms"),
                                        elements = [
                                                Integer(title = _("Warning at"), default_value = 150, unit = _("ms"), min_value = 0 ),
                                                Integer(title = _("Critical at"), default_value = 250, unit = _("ms"), min_value = 0 ),
                                                ],
                                        help = _("The maximum standard deviation on the roundtrip time in ms before this service goes into"\
                             "warning/critical. This alarm only applies to the target host, not the hops in between."),
                                        ),
                                ),
                        ("loss",
                                Tuple(
                                        title = _("Packet loss in percentage"),
                                        elements = [
                                                Integer(title = _("Warning at"), default_value = 10, unit = _("%"), min_value = 0 ),
                                                Integer(title = _("Critical at"), default_value = 25, unit = _("%"), min_value = 0 ),
                                                ],
                                        help = _("The maximum allowed percentage of packet loss to the destination before this service "\
                             "goes into warning/critical."),
                                        ),
                                ),
                        ],
                optional_keys = False,
        ),
        TextAscii(
                title = _("MTR destination"),
                help = _("Specify the name of the destination host, i.e. <tt>www.mathias-kettner.com</tt>"),
                allow_empty = False
        ),
        'dict'
)

fortigate_sessions_element = Tuple(
    title = _(u"Levels for active sessions"),
    elements = [
        Integer( title = _(u"Warning at"), default_value = 100000, size = 10 ),
        Integer( title = _(u"Critical at"), default_value = 150000, size = 10 ),
    ])

register_check_parameters(
    subgroup_networking,
    "fortigate_sessions",
    _(u"Fortigate Active Sessions"),
    fortigate_sessions_element,
    None,
    "first"
)

register_check_parameters(
    subgroup_networking,
    "fortigate_node_sessions",
    _(u"Fortigate Active Sessions"),
    fortigate_sessions_element,
    TextAscii(
        title = _("Node name"),
        allow_empty = False
    ),
    "first"
)

register_check_parameters(
    subgroup_networking,
    "f5_bigip_cluster_v11",
    _(u"Configuration Sync Status for F5 BigIP devices"),
    Dictionary(
        title = _("Interpretation of Config Sync Status"),
        elements = [
            ("0", MonitoringState(title = "Unknown", default_value = 3)),
            ("1", MonitoringState(title = "Syncing", default_value = 0)),
            ("2", MonitoringState(title = "Need Manual Sync", default_value = 1)),
            ("3", MonitoringState(title = "In Sync", default_value = 0)),
            ("4", MonitoringState(title = "Sync Failed", default_value = 2)),
            ("5", MonitoringState(title = "Sync Disconnected", default_value = 2)),
            ("6", MonitoringState(title = "Standalone", default_value = 2)),
            ("7", MonitoringState(title = "Awaiting Initial Sync", default_value = 1)),
            ("8", MonitoringState(title = "Incompatible Version", default_value = 2)),
            ("9", MonitoringState(title = "Partial Sync", default_value = 2)),
        ]
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "f5_bigip_snat",
    _("F5 Loadbalancer Source NAT"),
    Dictionary(
        elements = [
            ( "if_in_octets",
                Levels(
                    title = _("Incoming Traffic Maximum"),
                    unit = _("bytes/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_in_octets_lower",
                Levels(
                    title = _("Incoming Traffic Minimum"),
                    unit = _("bytes/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_out_octets",
                Levels(
                    title = _("Outgoing Traffic Maximum"),
                    unit = _("bytes/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_out_octets_lower",
                Levels(
                    title = _("Outgoing Traffic Minimum"),
                    unit = _("bytes/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_total_octets",
                Levels(
                    title = _("Total Traffic Maximum"),
                    unit = _("bytes/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_total_octets_lower",
                Levels(
                    title = _("Total Traffic Minimum"),
                    unit = _("bytes/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),


            ( "if_in_pkts",
                Levels(
                    title = _("Incoming Packets Maximum"),
                    unit = _("packets/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_in_pkts_lower",
                Levels(
                    title = _("Incoming Packets Minimum"),
                    unit = _("packets/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_out_pkts",
                Levels(
                    title = _("Outgoing Packets Maximum"),
                    unit = _("packets/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_out_pkts_lower",
                Levels(
                    title = _("Outgoing Packets Minimum"),
                    unit = _("packets/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_total_pkts",
                Levels(
                    title = _("Total Packets Maximum"),
                    unit = _("packets/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_total_pkts_lower",
                Levels(
                    title = _("Total Packets Minimum"),
                    unit = _("packets/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            )
                ]
        ),
        TextAscii(
                title = _("Source NAT Name"),
                allow_empty = False
        ),
        'dict'
)


register_check_parameters(
    subgroup_applications,
    "veritas_vcs",
    _("Veritas Cluster Server"),
    Dictionary(
        elements = [
            ("map_states", Dictionary(
                title=_("Map Attribute 'State'"),
                elements=[
                    ("ONLINE",  MonitoringState(title=_("ONLINE"), default_value=0)),
                    ("RUNNING", MonitoringState(title=_("RUNNING"), default_value=0)),
                    ("OK",      MonitoringState(title=_("OK"), default_value=0)),
                    ("OFFLINE", MonitoringState(title=_("OFFLINE"), default_value=1)),
                    ("EXITED",  MonitoringState(title=_("EXITED"), default_value=1)),
                    ("PARTIAL", MonitoringState(title=_("PARTIAL"), default_value=1)),
                    ("FAULTED", MonitoringState(title=_("FAULTED"), default_value=2)),
                    ("UNKNOWN", MonitoringState(title=_("UNKNOWN"), default_value=3)),
                    ("default", MonitoringState(title=_("States other than the above"), default_value=1)),
                ],
                optional_keys=False,
            )),
            ("map_frozen", Dictionary(
                title=_("Map Attribute 'Frozen'"),
                elements=[
                    ("tfrozen", MonitoringState(title=_("Temporarily frozen"), default_value=1)),
                    ("frozen",  MonitoringState(title=_("Frozen"), default_value=2)),
                ],
                optional_keys=False,
            )),
        ]),
        TextAscii(title=_("Cluster Name")),
        'dict'
)


register_check_parameters(
    subgroup_applications,
    "f5_bigip_vserver",
    _("F5 Loadbalancer VServer"),
    Dictionary(
        elements = [
            ( "if_in_octets",
                Levels(
                    title = _("Incoming Traffic Maximum"),
                    unit = _("bytes/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_in_octets_lower",
                Levels(
                    title = _("Incoming Traffic Minimum"),
                    unit = _("bytes/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_out_octets",
                Levels(
                    title = _("Outgoing Traffic Maximum"),
                    unit = _("bytes/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_out_octets_lower",
                Levels(
                    title = _("Outgoing Traffic Minimum"),
                    unit = _("bytes/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_total_octets",
                Levels(
                    title = _("Total Traffic Maximum"),
                    unit = _("bytes/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_total_octets_lower",
                Levels(
                    title = _("Total Traffic Minimum"),
                    unit = _("bytes/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_in_pkts",
                Levels(
                    title = _("Incoming Packets Maximum"),
                    unit = _("packets/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_in_pkts_lower",
                Levels(
                    title = _("Incoming Packets Minimum"),
                    unit = _("packets/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_out_pkts",
                Levels(
                    title = _("Outgoing Packets Maximum"),
                    unit = _("packets/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_out_pkts_lower",
                Levels(
                    title = _("Outgoing Packets Minimum"),
                    unit = _("packets/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_total_pkts",
                Levels(
                    title = _("Total Packets Maximum"),
                    unit = _("packets/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "if_total_pkts_lower",
                Levels(
                    title = _("Total Packets Minimum"),
                    unit = _("packets/s"),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ("state", Dictionary(
                title=_("Map states"),
                elements=[
                    ("is_disabled",
                        MonitoringState(title=_("Is disabled"), default_value=1)),
                    ("is_up_and_available",
                        MonitoringState(title=_("Is up and available"), default_value=0)),
                    ("is_currently_not_available",
                        MonitoringState(title=_("Is currently not available"), default_value=2)),
                    ("is_not_available",
                        MonitoringState(title=_("Is not available"), default_value=2)),
                    ("availability_is_unknown",
                        MonitoringState(title=_("Availability is unknown"), default_value=1)),
                    ("is_unlicensed",
                        MonitoringState(title=_("Is unlicensed"), default_value=3)),
                    ("children_pool_members_down_if_not_available",
                        # Special handling, see check plugin
                        MonitoringState(title=_("The children pool member(s) are down if VServer is not available"), default_value=0)),
                ],
                optional_keys=False,
            )),
        ]),
        TextAscii(
                title = _("VServer name"),
                allow_empty = False
        ),
        'dict'
)


register_check_parameters(
    subgroup_applications,
    "cluster_status",
    _("Cluster status"),
    Dictionary(
        elements = [
            ("type",
             DropdownChoice(
                title = _("Cluster type"),
                help = _("Expected cluster type."),
                choices = [
                        ( "active_standby" , _("active / standby") ),
                        ( "active_active" , _("active / active") ),
                ],
                default_value = "active_standby"
             )
            ),
            ("v11_2_states",
                Dictionary(
                    title = _("Interpretation of failover cluster state"),
                    help  = _("Here you can set the failover state for BIG-IP system of version 11.2.0"),
                    elements = [
                        ("0", MonitoringState(title = "Unknown", default_value = 3)),
                        ("1", MonitoringState(title = "Offline", default_value = 2)),
                        ("2", MonitoringState(title = "Forced offline", default_value = 2)),
                        ("3", MonitoringState(title = "Standby", default_value = 0)),
                        ("4", MonitoringState(title = "Active", default_value = 0)),
                    ]
                )
            )
        ],
        required_keys = ["type"]
    ),
    None,
    "dict"
)


register_check_parameters(
    subgroup_networking,
    "cisco_asa_failover",
    _("Failover states"),
    Dictionary(
        elements = [
            ("primary",
            DropdownChoice(
                title = _("Primary Device"),
                help = _("The role of the primary device"),
                choices = [
                    ( "active", _("Active unit") ),
                    ( "standby", _("Standby unit") ),
                ],
                default_value = "active",
            )),
            ("secondary",
            DropdownChoice(
                title = _("Secondary Device"),
                help = _("The role of the secondary device"),
                choices = [
                    ( "active", _("Active unit") ),
                    ( "standby", _("Standby unit") ),
                ],
                default_value = "standby",
            )),
            ("failover_state",
            MonitoringState(
                title = _("Failover state"),
                help = _("State if conditions above are not satisfied"),
                default_value = 0,
            )),
        ]
    ),
    None,
    "dict",
)


register_check_parameters(
    subgroup_networking,
    "threepar_ports",
    _("3PAR Ports"),
    Dictionary(
        elements = [
            ("1_link",
             MonitoringState(
                title = _("Link State: CONFIG_WAIT"),
                default_value = 1)
            ),
            ("2_link",
             MonitoringState(
                title = _("Link State: ALPA_WAIT"),
                default_value = 1)
            ),
            ("3_link",
             MonitoringState(
                title = _("Link State: LOGIN_WAIT"),
                default_value = 1)
            ),
            ("4_link",
             MonitoringState(
                title = _("Link State: READY"),
                default_value = 0)
            ),
            ("5_link",
             MonitoringState(
                title = _("Link State: LOSS_SYNC"),
                default_value = 2)
            ),
            ("6_link",
             MonitoringState(
                title = _("Link State: ERROR_STATE"),
                default_value = 2)
            ),
            ("7_link",
             MonitoringState(
                title = _("Link State: XXX"),
                default_value = 1)
            ),
            ("8_link",
             MonitoringState(
                title = _("Link State: NOPARTICIPATE"),
                default_value = 0)
            ),
            ("9_link",
             MonitoringState(
                title = _("Link State: COREDUMP"),
                default_value = 1)
            ),
            ("10_link",
             MonitoringState(
                title = _("Link State: OFFLINE"),
                default_value = 1)
            ),
            ("11_link",
             MonitoringState(
                title = _("Link State: FWDEAD"),
                default_value = 1)
            ),
            ("12_link",
             MonitoringState(
                title = _("Link State: IDLE_FOR_RESET"),
                default_value = 1)
            ),
            ("13_link",
             MonitoringState(
                title = _("Link State: DHCP_IN_PROGESS"),
                default_value = 1)
            ),
            ("14_link",
             MonitoringState(
                title = _("Link State: PENDING_RESET"),
                default_value = 1)
            ),
            ("1_fail",
             MonitoringState(
                title = _("Failover State: NONE"),
                default_value = 0)
            ),
            ("2_fail",
             MonitoringState(
                title = _("Failover State: FAILOVER_PENDING"),
                default_value = 2)
            ),
            ("3_fail",
             MonitoringState(
                title = _("Failover State: FAILED_OVER"),
                default_value = 2)
            ),
            ("4_fail",
             MonitoringState(
                title = _("Failover State: ACTIVE"),
                default_value = 2)
            ),
            ("5_fail",
             MonitoringState(
                title = _("Failover State: ACTIVE_DOWN"),
                default_value = 2)
            ),
            ("6_fail",
             MonitoringState(
                title = _("Failover State: ACTIVE_FAILED"),
                default_value = 2)
            ),
            ("7_fail",
             MonitoringState(
                title = _("Failover State: FAILBACK_PENDING"),
                default_value = 1)
            ),
    ]
    ),
    TextAscii(
        title = _("Port"),
        help = _("The Port Description")
    ),
    "dict",
)

register_check_parameters(
    subgroup_networking,
    "ipsecvpn",
    _(u"Fortigate IPSec VPN Tunnels"),
    Transform(
        Dictionary(
            elements=[
                ("levels", Tuple(
                    title=_("Levels for number of down channels"),
                    elements=[
                        Integer(title=_("Warning at"), default_value=1),
                        Integer(title=_("Critical at"), default_value=2),
                    ])),
                ("tunnels_ignore_levels", ListOfStrings(title = _("Tunnels which ignore levels")))
            ],
            optional_keys = []
        ),
        forth=lambda params: type(params) == dict and params or { "levels" : params },
    ),
    None,
    "dict",
)

register_check_parameters(
    subgroup_networking,
    "hp_hh3c_ext_states",
    _("States of HP Switch modules"),
    Dictionary(
        elements=[
            ("oper", Dictionary(
                title=_("Operational states"),
                elements=[
                    ("not_supported", MonitoringState(title=_("Not supported"), default_value=1)),
                    ("disabled", MonitoringState(title=_("Disabled"), default_value=2)),
                    ("enabled", MonitoringState(title=_("Enabled"), default_value=0)),
                    ("dangerous", MonitoringState(title=_("Dangerous"), default_value=2)),
                ]
            )),
            ("admin", Dictionary(
                title=_("Administrative states"),
                elements=[
                    ("not_supported", MonitoringState(title=_("Not supported"), default_value=1)),
                    ("locked", MonitoringState(title=_("Locked"), default_value=0)),
                    ("shutting_down", MonitoringState(title=_("Shutting down"), default_value=2)),
                    ("unlocked", MonitoringState(title=_("Unlocked"), default_value=2)),
                ]
            )),
        ]
    ),
    TextAscii(
        title = _("Port"),
        help = _("The Port Description")
    ),
    "dict",
)


#.
#   .--Inventory-----------------------------------------------------------.
#   |            ___                      _                                |
#   |           |_ _|_ ____   _____ _ __ | |_ ___  _ __ _   _              |
#   |            | || '_ \ \ / / _ \ '_ \| __/ _ \| '__| | | |             |
#   |            | || | | \ V /  __/ | | | || (_) | |  | |_| |             |
#   |           |___|_| |_|\_/ \___|_| |_|\__\___/|_|   \__, |             |
#   |                                                   |___/              |
#   '----------------------------------------------------------------------'

def transform_ipmi_inventory_rules(p):
    if type(p) == dict:
        if p.get("summarize", True):
            summarize = True
        else:
            summarize = False

        if summarize:
            p = 'summarize'
        else:
            if p.get('ignored_sensors', []):
                p = ('single', {'ignored_sensors' : p["ignored_sensors"]})
            else:
                p = ('single', {})
    return p

register_rule(
    group + '/' + subgroup_inventory,
    varname = "inventory_ipmi_rules",
    title = _("Discovery of IPMI sensors"),
    valuespec = Transform(CascadingDropdown(
        orientation = "vertical",
        choices = [
            ("summarize", _("Summary")),
            ("single" ,   _("Single"),
                Dictionary(
                    show_titles = True,
                    elements = [
                        ( "ignored_sensors",
                            ListOfStrings(
                                title = _("Ignore the following IPMI sensors"),
                                help  = _("Names of IPMI sensors that should be ignored during inventory "
                                          "and when summarizing."
                                          "The pattern specified here must match exactly the beginning of "
                                          "the actual sensor name (case sensitive)."),
                                orientation = "horizontal"
                                )
                            ),
                        ( "ignored_sensorstates",
                            ListOfStrings(
                                title = _("Ignore the following IPMI sensor states"),
                                help  = _("IPMI sensors with these states that should be ignored during inventory "
                                          "and when summarizing."
                                          "The pattern specified here must match exactly the beginning of "
                                          "the actual sensor name (case sensitive)."),
                                orientation = "horizontal",
                                )
                        ),
                    ]
                ),
            ),
        ]
    ), forth = transform_ipmi_inventory_rules ),
    match = 'first'
)


register_rule(group + '/' + subgroup_inventory,
    varname = "ewon_discovery_rules",
    title = _("eWON Discovery"),
    help = _("The ewon vpn routers can rely data from a secondary device via snmp. "
            "It doesn't however allow discovery of the device type relayed this way. "
            "To allow interpretation of the data you need to pick the device manually."),
    valuespec = DropdownChoice(
        title = _("Device Type"),
        label = _("Select device type"),
        choices = [
            (None, _("None selected")),
            ("oxyreduct", _("Wagner OxyReduct")),
        ],
        default_value = None,
    ),
    match = 'first'
)


register_rule(
    group + '/' + subgroup_inventory,
    varname = "mssql_transactionlogs_discovery",
    title = _("MSSQL Datafile and Transactionlog Discovery"),
    valuespec = Dictionary(
        elements = [
            ("summarize_datafiles", Checkbox(
                title = _("Display only a summary of all Datafiles"), label =
                _("Summarize Datafiles"),
            )), ("summarize_transactionlogs", Checkbox(
                title = _("Display only a summary of all Transactionlogs"),
                label = _("Summarize Transactionlogs"),
            )),
        ],
        optional_keys = []
    ),
    match = "first"
)

register_rule(group + '/' + subgroup_inventory,
    varname   = "inventory_services_rules",
    title     = _("Windows Service Discovery"),
    valuespec = Dictionary(
        elements = [
            ('services', ListOfStrings(
                title = _("Services (Regular Expressions)"),
                help  = _('Regular expressions matching the begining of the internal name '
                          'or the description of the service. '
                          'If no name is given then this rule will match all services. The '
                          'match is done on the <i>beginning</i> of the service name. It '
                          'is done <i>case sensitive</i>. You can do a case insensitive match '
                          'by prefixing the regular expression with <tt>(?i)</tt>. Example: '
                          '<tt>(?i).*mssql</tt> matches all services which contain <tt>MSSQL</tt> '
                          'or <tt>MsSQL</tt> or <tt>mssql</tt> or...'),

                orientation = "horizontal",
            )),
            ('state', DropdownChoice(
                choices = [
                    ('running', _('Running')),
                    ('stopped', _('Stopped')),
                ],
                title = _("Create check if service is in state"),
            )),
            ('start_mode', DropdownChoice(
                choices = [
                    ('auto',     _('Automatic')),
                    ('demand',   _('Manual')),
                    ('disabled', _('Disabled')),
                ],
                title = _("Create check if service is in start mode"),
            )),
        ],
        help = _('This rule can be used to configure the inventory of the windows services check. '
                 'You can configure specific windows services to be monitored by the windows check by '
                 'selecting them by name, current state during the inventory, or start mode.'),
    ),
    match = 'all',
)

register_rule(group + '/' + subgroup_inventory,
    varname="inventory_solaris_services_rules",
    title=_("Solaris Service Discovery"),
    valuespec=Dictionary(
        elements=[
            ('descriptions', ListOfStrings(title=_("Descriptions"))),
            ('categories', ListOfStrings(title=_("Categories"))),
            ('names', ListOfStrings(title=_("Names"))),
            ('instances', ListOfStrings(title=_("Instances"))),
            ('states', ListOf(
                DropdownChoice(
                    choices=[
                        ("online", _("online")),
                        ("disabled", _("disabled")),
                        ("maintenance", _("maintenance")),
                        ("legacy_run", _("legacy run")),
                    ],
                ),
                title=_("States"),
            )),
            ('outcome', Alternative(
                title=_("Service name"),
                style = "dropdown",
                elements=[
                    FixedValue("full_descr", title=_("Full Description"), totext=""),
                    FixedValue("descr_without_prefix", title=_("Description without type prefix"), totext=""),
                ],
            )),
        ],
        help = _('This rule can be used to configure the inventory of the windows services check. '
                 'You can configure specific windows services to be monitored by the windows check by '
                 'selecting them by name, current state during the inventory, or start mode.'),
    ),
    match = 'all',
)

register_rule(group + '/' + subgroup_inventory,
    varname   = "discovery_win_dhcp_pools",
    title     = _("Discovery of Windows DHCP Pools"),
    valuespec = Dictionary(
        elements = [
          ( "empty_pools",
             Checkbox(
                 title = _("Discovery of empty DHCP pools"),
                 label = _("Include empty pools into the monitoring"),
                 help = _("You can activate the creation of services for "
                          "DHCP pools, which contain no IP addresses."),
          )),
        ]
    ),
    match = 'dict',
)


register_rule(group + '/' + subgroup_inventory,
    varname   = "inventory_if_rules",
    title     = _("Network Interface and Switch Port Discovery"),
    valuespec = Dictionary(
        elements = [
        ( "use_desc", DropdownChoice(
            choices = [
                (True,  _('Use description')),
                (False, _('Do not use description')),
            ],
            title = _("Description as service name for network interface checks"),
            help = _("This option lets Check_MK use the interface description as item instead "
                     "of the port number. If no description is available then the port number is "
                     "used anyway.")
        )),
        ( "use_alias", DropdownChoice(
            choices = [
                (True,  _('Use alias')),
                (False, _('Do not use alias')),
            ],
            title = _("Alias as service name for network interface checks"),
            help = _("This option lets Check_MK use the alias of the port (ifAlias) as item instead "
                     "of the port number. If no alias is available then the port number is used "
                     "anyway.")
        )),
        ( "pad_portnumbers", DropdownChoice(
            choices = [
                (True,  _('Pad port numbers with zeros')),
                (False, _('Do not pad')),
            ],
            title = _("Port numbers"),
            help = _("If this option is activated then Check_MK will pad port numbers of "
                     "network interfaces with zeroes so that all port descriptions from "
                     "all ports of a host or switch have the same length and thus sort "
                     "currectly in the GUI. In versions prior to 1.1.13i3 there was no "
                     "padding. You can switch back to the old behaviour by disabling this "
                     "option. This will retain the old service descriptions and the old "
                     "performance data."),
        )),
        ( "match_alias",
          ListOfStrings(
              title = _("Match interface alias (regex)"),
              help = _("Only discover interfaces whose alias matches one of the configured "
                       "regular expressions. The match is done on the beginning of the alias. "
                       "This allows you to select interfaces based on the alias without having "
                       "the alias be part of the service description."),
              orientation = "horizontal",
              valuespec = RegExp(
                  size = 32,
                  mode = RegExp.prefix,
              ),
        )),
        ( "match_desc",
          ListOfStrings(
              title = _("Match interface description (regex)"),
              help = _("Only discover interfaces whose the description matches one of the configured "
                       "regular expressions. The match is done on the beginning of the description. "
                       "This allows you to select interfaces based on the description without having "
                       "the alias be part of the service description."),
              orientation = "horizontal",
              valuespec = RegExp(
                  size = 32,
                  mode = RegExp.prefix,
              ),
        )),
        ( "portstates",
          ListChoice(title = _("Network interface port states to discover"),
              help = _("When doing discovery on switches or other devices with network interfaces "
                       "then only ports found in one of the configured port states will be added to the monitoring. "
                       "Note: the state <i>admin down</i> is in fact not an <tt>ifOperStatus</tt> but represents the "
                       "<tt>ifAdminStatus</tt> of <tt>down</tt> - a port administratively switched off. If you check this option "
                       "then an alternate version of the check is being used that fetches the <tt>ifAdminState</tt> in addition. "
                       "This will add about 5% of additional SNMP traffic."),
              choices = defines.interface_oper_states(),
              toggle_all = True,
              default_value = ['1'],
        )),
        ( "porttypes",
          DualListChoice(title = _("Network interface port types to discover"),
              help = _("When doing discovery on switches or other devices with network interfaces "
                       "then only ports of the specified types will be created services for."),
              choices = defines.interface_port_types(),
              custom_order = True,
              rows = 40,
              toggle_all = True,
              default_value = [ '6', '32', '62', '117', '127', '128', '129', '180', '181', '182', '205','229' ],
        )),
        ( "rmon", DropdownChoice(
            choices = [
                (True,  _("Create extra service with RMON statistics data (if available for the device)")),
                (False, _('Do not create extra services')),
            ],
            title = _("Collect RMON statistics data"),
            help = _("If you enable this option, for every RMON capable switch port an additional service will "
                     "be created which is always OK and collects RMON data. This will give you detailed information "
                     "about the distribution of packet sizes transferred over the port. Note: currently "
                     "this extra RMON check does not honor the inventory settings for switch ports. In a future "
                     "version of Check_MK RMON data may be added to the normal interface service and not add "
                     "an additional service."),
        )),
        ],
        help = _('This rule can be used to control the inventory for network ports. '
                 'You can configure the port types and port states for inventory'
                 'and the use of alias or description as service name.'),
    ),
    match = 'list',
)

_brocade_fcport_adm_choices = [
    ( 1, 'online(1)'),
    ( 2, 'offline(2)'),
    ( 3, 'testing(3)'),
    ( 4, 'faulty(4)'),
]

_brocade_fcport_op_choices = [
    ( 0, 'unkown(0)'),
    ( 1, 'online(1)'),
    ( 2, 'offline(2)'),
    ( 3, 'testing(3)'),
    ( 4, 'faulty(4)'),
]

_brocade_fcport_phy_choices = [
    ( 1, 'noCard(1)'),
    ( 2, 'noTransceiver(2)'),
    ( 3, 'laserFault(3)'),
    ( 4, 'noLight(4)'),
    ( 5, 'noSync(5)'),
    ( 6, 'inSync(6)'),
    ( 7, 'portFault(7)'),
    ( 8, 'diagFault(8)'),
    ( 9, 'lockRef(9)'),
    ( 10, 'validating(10)'),
    ( 11, 'invalidModule(11)'),
    ( 14, 'noSigDet(14)'),
    ( 255, 'unkown(255)'),
]


register_rule(group + '/' + subgroup_inventory,
    varname   = "brocade_fcport_inventory",
    title     = _("Brocade Port Discovery"),
    valuespec = Dictionary(
        elements = [
         ("use_portname", Checkbox(
                title = _("Use port name as service name"),
                label = _("use port name"),
                default_value = True,
                help = _("This option lets Check_MK use the port name as item instead of the "
                         "port number. If no description is available then the port number is "
                         "used anyway."))),
        ("show_isl", Checkbox(
                title = _("add \"ISL\" to service description for interswitch links"),
                label = _("add ISL"),
                default_value = True,
                help = _("This option lets Check_MK add the string \"ISL\" to the service "
                         "description for interswitch links."))),
        ("admstates", ListChoice(title = _("Administrative port states to discover"),
                help = _("When doing service discovery on brocade switches only ports with the given administrative "
                         "states will be added to the monitoring system."),
                choices = _brocade_fcport_adm_choices,
                columns = 1,
                toggle_all = True,
                default_value = ['1', '3', '4' ],
        )),
        ("phystates", ListChoice(title = _("Physical port states to discover"),
                help = _("When doing service discovery on brocade switches only ports with the given physical "
                         "states will be added to the monitoring system."),
                choices = _brocade_fcport_phy_choices,
                columns = 1,
                toggle_all = True,
                default_value =  [ 3, 4, 5, 6, 7, 8, 9, 10 ]
        )),
        ("opstates", ListChoice(title = _("Operational port states to discover"),
                help = _("When doing service discovery on brocade switches only ports with the given operational "
                         "states will be added to the monitoring system."),
                choices = _brocade_fcport_op_choices,
                columns = 1,
                toggle_all = True,
                default_value = [ 1, 2, 3, 4 ]
        )),
        ],
        help = _('This rule can be used to control the service discovery for brocade ports. '
                 'You can configure the port states for inventory '
                 'and the use of the description as service name.'),
    ),
    match = 'dict',
)

# Next step in conversion: introduce "levels"
def ps_convert_from_singlekeys(old_params):
    params = {}
    params.update(ps_convert_from_tuple(old_params))
    if "warnmin" in params:
        params["levels"] = (
            params.get("warnmin",     1),
            params.get("okmin",       1),
            params.get("warnmax", 99999),
            params.get("okmax",   99999),
        )
        for key in [ "warnmin", "warnmax", "okmin", "okmax" ]:
            if key in params:
                del params[key]
    return params

def ps_convert_inventorized_from_singlekeys(old_params):
    params = ps_convert_from_singlekeys(old_params)
    if 'user' in params:
        del params['user']
    if 'process' in params:
        del params['process']
    return params


process_level_elements = [
    ('levels', Tuple(
        title = _('Levels for process count'),
        help = _("Please note that if you specify and also if you modify levels here, the change is activated "
                 "only during an inventory.  Saving this rule is not enough. This is due to the nature of inventory rules."),
        elements = [
            Integer(
                title = _("Critical below"),
                unit = _("processes"),
                default_value = 1,
            ),
            Integer(
                title = _("Warning below"),
                unit = _("processes"),
                default_value = 1,
            ),
            Integer(
                title = _("Warning above"),
                unit = _("processes"),
                default_value = 99999,
            ),
            Integer(
                title = _("Critical above"),
                unit = _("processes"),
                default_value = 99999,
            ),
        ],
    )),
    ( "cpulevels",
      Tuple(
        title = _("Levels on total CPU utilization"),
        help = _("By activating this options you can set levels on the total "
                 "CPU utilization of all included processes."),
        elements = [
           Percentage(title = _("Warning at"),  default_value = 90, maxvalue = 10000),
           Percentage(title = _("Critical at"), default_value = 98, maxvalue = 10000),
        ],
    )),
    ( "cpu_average",
     Integer(
         title = _("CPU Averaging"),
         help = _("By activating averaging, Check_MK will compute the average of "
                  "the total CPU utilization over a given interval. If you have defined "
                  "alerting levels then these will automatically be applied on the "
                  "averaged value. This helps to mask out short peaks. "),
         unit = _("minutes"),
         minvalue = 1,
         default_value = 15,
     )),
    ( "single_cpulevels",
      Tuple(
        title = _("Levels on CPU utilization of a single process"),
        help = _("Here you can define levels on the CPU utilization of single "
                 "processes. For performance reasons CPU Averaging will not be "
                 "applied to to the levels of single processes."),
        elements = [
           Percentage(title = _("Warning at"),  default_value = 90, maxvalue = 10000),
           Percentage(title = _("Critical at"), default_value = 98, maxvalue = 10000),
        ],
    )),
    ( "max_age",
      Tuple(
        title = _("Maximum allowed age"),
        help = _("Alarms you if the age of the process (not the consumed CPU "
                 "time, but the real time) exceed the configured levels."),
        elements = [
            Age(title=_("Warning at"), default_value = 3600),
            Age(title=_("Critical at"), default_value = 7200),
        ]
    )),
    ( "virtual_levels",
       Tuple(
         title = _("Virtual memory usage"),
         elements = [
             Filesize(title = _("Warning at"), default_value = 1000 * 1024 * 1024 * 1024),
             Filesize(title = _("Critical at"), default_value = 2000 * 1024 * 1024 * 1024),
         ],
    )),
    ( "resident_levels",
       Tuple(
         title = _("Physical memory usage"),
         elements = [
             Filesize(title = _("Warning at"), default_value = 100 * 1024 * 1024),
             Filesize(title = _("Critical at"), default_value = 200 * 1024 * 1024),
         ],
    )),
    ( "resident_levels_perc",
      Tuple(
        title = _("Physical memory usage, in percentage of total RAM"),
        elements = [
            Percentage(title = _("Warning at"), default_value = 25.0),
            Percentage(title = _("Critical at"), default_value = 50.0),
        ]
    )),
    ( "handle_count", Tuple(
         title = _('Handle Count (Windows only)'),
         help  = _("The number of object handles in the processes object table. This includes open handles to "
                   "threads, files and other resources like registry keys."),
         elements = [
             Integer(
                 title = _("Warning above"),
                 unit = _("handles"),
             ),
             Integer(
                 title = _("Critical above"),
                 unit = _("handles"),
             ),
         ],
    )),
    ('process_info', DropdownChoice(
        title = _("Enable per-process details in long-output"),
        label = _("Enable per-process details"),
        help  = _("If active, the long output of this service will contain a list of "
                    "all the matching processes and their details (i.e. PID, CPU usage, memory usage). "
                    "Please note that HTML output will only work if \"Escape HTML codes in plugin output\" is "
                    "disabled in global settings. This might expose you to Cross-Site-Scripting (everyone "
                    "with write-access to checks could get scripts executed on the monitoring site in the context "
                    "of the user of the monitoring site) so please do this if you understand the consequences."),
        choices = [
            (None, _("Disable")),
            ("text", _("Text output")),
            ("html", _("HTML output"))
        ],
        default_value = "disable",
    )),
]

# In version 1.2.4 the check parameters for the resulting ps check
# where defined in the dicovery rule. We moved that to an own rule
# in the classical check parameter style. In order to support old
# configuration we allow reading old discovery rules and ship these
# settings in an optional sub-dictionary.
def convert_inventory_processes(old_dict):
    new_dict = { "default_params" : {} }
    for key, value in old_dict.items():
        if key in ['levels', 'handle_count', 'cpulevels', 'cpu_average', 'virtual_levels', 'resident_levels']:
            new_dict["default_params"][key] = value
        elif key != "perfdata":
            new_dict[key] = value
    return new_dict

register_rule(group + '/' + subgroup_inventory,
    varname   = "inventory_processes_rules",
    title     = _('Process Discovery'),
    help      = _("This ruleset defines criteria for automatically creating checks for running processes "
                  "based upon what is running when the service discovery is done. These services will be "
                  "created with default parameters. They will get critical when no process is running and "
                  "OK otherwise. You can parameterize the check with the ruleset <i>State and count of processes</i>."),
    valuespec = Transform(
        Dictionary(
            elements = [
                ('descr', TextAscii(
                    title = _('Process Name'),
                    style = "dropdown",
                    allow_empty = False,
                    help  = _('<p>The process name may contain one or more occurances of <tt>%s</tt>. If you do this, then the pattern must be a regular '
                              'expression and be prefixed with ~. For each <tt>%s</tt> in the description, the expression has to contain one "group". A group '
                              'is a subexpression enclosed in brackets, for example <tt>(.*)</tt> or <tt>([a-zA-Z]+)</tt> or <tt>(...)</tt>. When the inventory finds a process '
                              'matching the pattern, it will substitute all such groups with the actual values when creating the check. That way one '
                              'rule can create several checks on a host.</p>'
                              '<p>If the pattern contains more groups then occurrances of <tt>%s</tt> in the service description then only the first matching '
                              'subexpressions  are used for the  service descriptions. The matched substrings corresponding to the remaining groups '
                              'are copied into the regular expression, nevertheless.</p>'
                              '<p>As an alternative to <tt>%s</tt> you may also use <tt>%1</tt>, <tt>%2</tt>, etc. '
                              'These will be replaced by the first, second, ... matching group. This allows you to reorder things.</p>'
                              ),
                )),
                ('match', Alternative(
                    title = _("Process Matching"),
                    style = "dropdown",
                    elements = [
                        TextAscii(
                            title = _("Exact name of the process without argments"),
                            label = _("Executable:"),
                            size = 50,
                        ),
                        Transform(
                            RegExp(
                                size = 50,
                                mode = RegExp.prefix,
                            ),
                            title = _("Regular expression matching command line"),
                            label = _("Command line:"),
                            help = _("This regex must match the <i>beginning</i> of the complete "
                                     "command line of the process including arguments"),
                            forth = lambda x: x[1:],   # remove ~
                            back  = lambda x: "~" + x, # prefix ~
                        ),
                        FixedValue(
                            None,
                            totext = "",
                            title = _("Match all processes"),
                        )
                    ],
                    match = lambda x: (not x and 2) or (x[0] == '~' and 1 or 0),
                    default_value = '/usr/sbin/foo',
                )),
                ('user', Alternative(
                    title = _('Name of the User'),
                    style = "dropdown",
                    elements = [
                        FixedValue(
                            None,
                            totext = "",
                            title = _("Match all users"),
                        ),
                        TextAscii(
                            title = _('Exact name of the user'),
                            label = _("User:"),
                        ),
                        FixedValue(
                            False,
                            title = _('Grab user from found processess'),
                            totext = '',
                        ),
                    ],
                    help = _('<p>The user specification can either be a user name (string). The inventory will then trigger only if that user matches '
                             'the user the process is running as and the resulting check will require that user. Alternatively you can specify '
                             '"grab user". If user is not selected the created check will not check for a specific user.</p>'
                             '<p>Specifying "grab user" makes the created check expect the process to run as the same user as during inventory: the user '
                             'name will be hardcoded into the check. In that case if you put %u into the service description, that will be replaced '
                             'by the actual user name during inventory. You need that if your rule might match for more than one user - your would '
                             'create duplicate services with the same description otherwise.</p><p>Windows users are specified by the namespace followed by '
                             'the actual user name. For example "\\\\NT AUTHORITY\NETWORK SERVICE" or "\\\\CHKMKTEST\Administrator".</p>'),
                )),
                ('icon', UserIconOrAction(
                    title = _("Add custom icon or action"),
                    help = _("You can assign icons or actions to the found services in the status GUI."),
                )),
                ('default_params',
                 Dictionary(
                     title = _("Default parameters for detected services"),
                     help = _("Here you can select default parameters that are being set "
                              "for detected services. Note: the preferred way for setting parameters is to use "
                              "the rule set <a href='wato.py?varname=checkgroup_parameters%3Apsmode=edit_ruleset'> "
                              "State and Count of Processes</a> instead. "
                              "A change there will immediately be active, while a change in this rule "
                              "requires a re-discovery of the services."),
                     elements = process_level_elements,
                     ignored_keys=["match_groups"],
                )),
            ],
            required_keys = [ "descr" ],
        ),
        forth = convert_inventory_processes,
    ),
    match = 'all',
)

register_rule(group + '/' + subgroup_inventory,
    varname   = "inv_domino_tasks_rules",
    title     = _('Lotus Domino Task Discovery'),
    help      = _("This rule controls the discovery of tasks on Lotus Domino systems. "
                  "Any changes later on require a host re-discovery"),
    valuespec = Dictionary(
        elements = [
            ('descr', TextAscii(
                title = _('Service Description'),
                allow_empty = False,
                help  = _('<p>The service description may contain one or more occurances of <tt>%s</tt>. In this '
                          'case, the pattern must be a regular expression prefixed with ~. For each '
                          '<tt>%s</tt> in the description, the expression has to contain one "group". A group '
                          'is a subexpression enclosed in brackets, for example <tt>(.*)</tt> or '
                          '<tt>([a-zA-Z]+)</tt> or <tt>(...)</tt>. When the inventory finds a task '
                          'matching the pattern, it will substitute all such groups with the actual values when '
                          'creating the check. In this way one rule can create several checks on a host.</p>'
                          '<p>If the pattern contains more groups than occurrences of <tt>%s</tt> in the service '
                          'description, only the first matching subexpressions are used for the service '
                          'descriptions. The matched substrings corresponding to the remaining groups '
                          'are nevertheless copied into the regular expression.</p>'
                          '<p>As an alternative to <tt>%s</tt> you may also use <tt>%1</tt>, <tt>%2</tt>, etc. '
                          'These expressions will be replaced by the first, second, ... matching group, allowing '
                          'you to reorder things.</p>'
                          ),
            )),
            ('match', Alternative(
                title = _("Task Matching"),
                elements = [
                    TextAscii(
                        title = _("Exact name of the task"),
                        size = 50,
                    ),
                    Transform(
                        RegExp(
                            size = 50,
                            mode = RegExp.prefix,
                        ),
                        title = _("Regular expression matching command line"),
                        help = _("This regex must match the <i>beginning</i> of the task"),
                        forth = lambda x: x[1:],   # remove ~
                        back  = lambda x: "~" + x, # prefix ~
                    ),
                    FixedValue(
                        None,
                        totext = "",
                        title = _("Match all tasks"),
                    )
                ],
                match = lambda x: (not x and 2) or (x[0] == '~' and 1 or 0),
                default_value = 'foo',
            )),
            ('levels', Tuple(
                title = _('Levels'),
                help = _("Please note that if you specify and also if you modify levels here, the change is "
                         "activated only during an inventory.  Saving this rule is not enough. This is due to "
                         "the nature of inventory rules."),
                elements = [
                    Integer(
                        title = _("Critical below"),
                        unit = _("processes"),
                        default_value = 1,
                    ),
                    Integer(
                        title = _("Warning below"),
                        unit = _("processes"),
                        default_value = 1,
                    ),
                    Integer(
                        title = _("Warning above"),
                        unit = _("processes"),
                        default_value = 1,
                    ),
                    Integer(
                        title = _("Critical above"),
                        unit = _("processes"),
                        default_value = 1,
                    ),
                ],
            )),
        ],
        required_keys = ['match', 'levels', 'descr'],
    ),
    match = 'all',
)

register_rule(group + '/' + subgroup_inventory,
    varname   = "inventory_sap_values",
    title     = _('SAP R/3 Single Value Inventory'),
    valuespec = Dictionary(
        elements = [
            ('match', Alternative(
                title = _("Node Path Matching"),
                elements = [
                    TextAscii(
                        title = _("Exact path of the node"),
                        size = 100,
                    ),
                    Transform(
                        RegExp(
                            size = 100,
                            mode = RegExp.prefix,
                        ),
                        title = _("Regular expression matching the path"),
                        help = _("This regex must match the <i>beginning</i> of the complete "
                                 "path of the node as reported by the agent"),
                        forth = lambda x: x[1:],   # remove ~
                        back  = lambda x: "~" + x, # prefix ~
                    ),
                    FixedValue(
                        None,
                        totext = "",
                        title = _("Match all nodes"),
                    )
                ],
                match = lambda x: (not x and 2) or (x[0] == '~' and 1 or 0),
                default_value = 'SAP CCMS Monitor Templates/Dialog Overview/Dialog Response Time/ResponseTime',
            )),
            ('limit_item_levels', Integer(
                title = _("Limit Path Levels for Service Names"),
                unit = _('path levels'),
                minvalue = 1,
                help = _("The service descriptions of the inventorized services are named like the paths "
                         "in SAP. You can use this option to let the inventory function only use the last "
                         "x path levels for naming."),
            )),
        ],
        optional_keys = ['limit_item_levels'],
    ),
    match = 'all',
)

register_rule(group + '/' + subgroup_inventory,
    varname   = "sap_value_groups",
    title     = _('SAP Value Grouping Patterns'),
    help      = _('The check <tt>sap.value</tt> normally creates one service for each SAP value. '
                  'By defining grouping patterns, you can switch to the check <tt>sap.value-groups</tt>. '
                  'That check monitors a list of SAP values at once.'),
    valuespec = ListOf(
        Tuple(
            help = _("This defines one value grouping pattern"),
            show_titles = True,
            orientation = "horizontal",
            elements = [
                TextAscii(
                     title = _("Name of group"),
                ),
                Tuple(
                    show_titles = True,
                    orientation = "vertical",
                    elements = [
                        RegExpUnicode(
                            title = _("Include Pattern"),
                            mode = RegExp.prefix,
                        ),
                        RegExpUnicode(
                            title = _("Exclude Pattern"),
                            mode = RegExp.prefix,
                        )
                    ],
                ),
            ],
        ),
        add_label = _("Add pattern group"),
    ),
    match = 'all',
)

register_rule(group + '/' + subgroup_inventory,
    varname   = "inventory_heartbeat_crm_rules",
    title     = _("Heartbeat CRM Discovery"),
    valuespec = Dictionary(
        elements = [
            ("naildown_dc", Checkbox(
                   title = _("Naildown the DC"),
                   label = _("Mark the currently distinguished controller as preferred one"),
                   help = _("Nails down the DC to the node which is the DC during discovery. The check "
                            "will report CRITICAL when another node becomes the DC during later checks.")
            )),
            ("naildown_resources", Checkbox(
                   title = _("Naildown the resources"),
                   label = _("Mark the nodes of the resources as preferred one"),
                   help = _("Nails down the resources to the node which is holding them during discovery. "
                            "The check will report CRITICAL when another holds the resource during later checks.")
            )),
        ],
        help = _('This rule can be used to control the discovery for Heartbeat CRM checks.'),
        optional_keys = [],
    ),
    match = 'dict',
)

register_rule(group + '/' + subgroup_inventory,
    varname     = "inventory_df_rules",
    title       = _("Discovery parameters for filesystem checks"),
    valuespec   = Dictionary(
        elements = [
            ("include_volume_name", Checkbox(
                title = _("Include Volume name in item")
                )),
            ("ignore_fs_types", ListChoice(
                title = _("Filesystem types to ignore"),
                choices = [
                    ("tmpfs", "tmpfs"),
                    ("nfs", "nfs"),
                    ("smbfs", "smbfs"),
                    ("cifs", "cifs"),
                    ("iso9660", "iso9660"),
                ],
                default_value = [ "tmpfs", "nfs", "smbfs", "cifs", "iso9660" ]
                )),
            ("never_ignore_mountpoints", ListOf(
                TextUnicode(),
                title = _(u"Mountpoints to never ignore"),
                help =_(u"Regardless of filesystem type, these mountpoints will always be discovered."
                        u"Globbing or regular expressions are currently not supported."),
                )),
            ],
        ),
    match = "dict",
)

register_rule(group + '/' + subgroup_inventory,
    varname     = "inventory_mssql_counters_rules",
    title       = _("Include MSSQL Counters services"),
    valuespec   = Dictionary(elements=[
            ("add_zero_based_services", Checkbox(title=_("Include service with zero base."))),
        ],
        optional_keys = []
    ),
    match = "dict",
)

register_rule(
    "%s/%s" % (group, subgroup_inventory),
    varname="inventory_fujitsu_ca_ports",
    title=_("Discovery of Fujtsu storage CA ports"),
    valuespec=Dictionary(
        elements=[
            ("indices", ListOfStrings(title=_("CA port indices"))),
            ("modes", DualListChoice(
                title=_("CA port modes"),
                choices=[
                    ("CA", _("CA")),
                    ("RA", _("RA")),
                    ("CARA", _("CARA")),
                    ("Initiator", _("Initiator")),
                ],
                row=4,
                size=30,
            )),
        ],
    ),
    match="dict",
)

#.
#   .--Applications--------------------------------------------------------.
#   |          _                _ _           _   _                        |
#   |         / \   _ __  _ __ | (_) ___ __ _| |_(_) ___  _ __  ___        |
#   |        / _ \ | '_ \| '_ \| | |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |       / ___ \| |_) | |_) | | | (_| (_| | |_| | (_) | | | \__ \       |
#   |      /_/   \_\ .__/| .__/|_|_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |              |_|   |_|                                               |
#   '----------------------------------------------------------------------'

register_rule(group + '/' + subgroup_applications,
    varname   = "logwatch_rules",
    title     = _('Logwatch Patterns'),
    valuespec = Transform(
      Dictionary(
        elements = [
                    ("reclassify_patterns",
                         ListOf(
                           Tuple(
                               help = _("This defines one logfile pattern rule"),
                               show_titles = True,
                               orientation = "horizontal",
                               elements = [
                                  DropdownChoice(
                                    title = _("State"),
                                    choices = [
                                        ('C', _('CRITICAL')),
                                        ('W', _('WARNING')),
                                        ('O', _('OK')),
                                        ('I', _('IGNORE')),
                                    ],
                                  ),
                                  RegExpUnicode(
                                      title = _("Pattern (Regex)"),
                                      size  = 40,
                                      mode = RegExp.infix,
                                  ),
                                  TextUnicode(
                                      title = _("Comment"),
                                      size  = 40,
                                  ),
                               ]
                           ),
                           title = _("Reclassify state matching regex pattern"),
                           help = _('<p>You can define one or several patterns (regular expressions) in each logfile pattern rule. '
                                    'These patterns are applied to the selected logfiles to reclassify the '
                                    'matching log messages. The first pattern which matches a line will '
                                    'be used for reclassifying a message. You can use the '
                                    '<a href="wato.py?mode=pattern_editor">Logfile Pattern Analyzer</a> '
                                    'to test the rules you defined here.</p>'
                                    '<p>Select "Ignore" as state to get the matching logs deleted. Other states will keep the '
                                    'log entries but reclassify the state of them.</p>'),
                           add_label = _("Add pattern"),

                         ),
                    ),
                    ("reclassify_states", Dictionary(
                            title = _("Reclassify complete state"),
                            help  = _("This setting allows you to convert all incoming states to another state. "
                                      "The option is applied before the state conversion via regexes. So the regex values can "
                                      "modify the state even further."),
                            elements = [ ("c_to",
                               DropdownChoice(
                                 title = _("Change CRITICAL State to"),
                                 choices = [
                                     ('C', _('CRITICAL')),
                                     ('W', _('WARNING')),
                                     ('O', _('OK')),
                                     ('I', _('IGNORE')),
                                     ('.', _('Context Info')),
                                 ],
                                 default_value = "C",
                               )),
                               ("w_to", DropdownChoice(
                                 title = _("Change WARNING State to"),
                                 choices = [
                                     ('C', _('CRITICAL')),
                                     ('W', _('WARNING')),
                                     ('O', _('OK')),
                                     ('I', _('IGNORE')),
                                     ('.', _('Context Info')),
                                 ],
                                 default_value = "W",
                               )),
                               ("o_to", DropdownChoice(
                                 title = _("Change OK State to"),
                                 choices = [
                                     ('C', _('CRITICAL')),
                                     ('W', _('WARNING')),
                                     ('O', _('OK')),
                                     ('I', _('IGNORE')),
                                     ('.', _('Context Info')),
                                 ],
                                 default_value = "O",
                               )),
                               ("._to", DropdownChoice(
                                 title = _("Change Context Info to"),
                                 choices = [
                                     ('C', _('CRITICAL')),
                                     ('W', _('WARNING')),
                                     ('O', _('OK')),
                                     ('I', _('IGNORE')),
                                     ('.', _('Context Info')),
                                 ],
                                 default_value = ".",
                               )),
                            ],
                            optional_keys = False
                        ),
                    )

            ],
            optional_keys = [ "reclassify_states" ],
        ),
        forth = lambda x: type(x) == dict and x or {"reclassify_patterns": x}
    ),
    itemtype = 'item',
    itemname = 'Logfile',
    itemhelp = _("Put the item names of the logfiles here. For example \"System$\" "
                 "to select the service \"LOG System\". You can use regular "
                 "expressions which must match the beginning of the logfile name."),
    match = 'all',
)


register_check_parameters(
    subgroup_applications,
    "local",
    _("Settings for local checks"),
    Dictionary(
        elements = [
            ("outcome_on_cluster", DropdownChoice(choices = [
                ("worst", _("Worst state")),
                ("best",  _("Best state")),
            ],
            title = _("Clusters: Prefered check result of local checks"),
            help  = _("If you're running local checks on clusters via clustered services rule "
                      "you can influence the check result with this rule. You can choose between "
                      "best or worst state. Default setting is worst state."),
            default_value = "worst"))
        ]
    ),
    TextAscii(title = _("Name of local item")),
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "threepar_remotecopy",
    _("3PAR Remote Copy"),
    Dictionary(
        elements = [
            ("1",
             MonitoringState(
                title = _("Status: NORMAL"),
                default_value = 0,
             )
            ),
            ("2",
             MonitoringState(
                title = _("Status: STARTUP"),
                default_value = 1,
             )
            ),
            ("3",
             MonitoringState(
                title = _("Status: SHUTDOWN"),
                default_value = 1,
             )
            ),
            ("4",
             MonitoringState(
                title = _("Status: ENABLE"),
                default_value = 0,
             )
            ),
            ("5",
             MonitoringState(
                title = _("Status: DISBALE"),
                default_value = 2,
             )
            ),
            ("6",
             MonitoringState(
                title = _("Status: INVALID"),
                default_value = 2,
             )
            ),
            ("7",
             MonitoringState(
                title = _("Status: NODEUP"),
                default_value = 1,
             )
            ),
            ("8",
             MonitoringState(
                title = _("Status: UPGRADE"),
                default_value = 0,
             )
            ),
        ]
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "livestatus_status",
    _("Performance and settings of a Check_MK site"),
    Dictionary(
        help = _("When monitoring the performance of a monitoring site (i.e. its core) "
                 "then also settings are being checked, e.g. for manually disabled notifications. "
                 "The status of the various situations can be configured here."),
        elements = [
            ( "site_stopped",
              MonitoringState(title = "State when the site is stopped", default_value = 2)),
            ( "execute_host_checks",
              MonitoringState(title = "State when host checks are disabled", default_value = 2)),
            ( "execute_service_checks",
              MonitoringState(title = "State when service checks are disabled", default_value = 2)),
            ( "accept_passive_host_checks",
              MonitoringState(title = "State when not accepting passive host checks", default_value = 2)),
            ( "accept_passive_service_checks",
              MonitoringState(title = "State when not accepting passive service checks", default_value = 2)),
            ( "check_host_freshness",
              MonitoringState(title = "State when not checking host freshness", default_value = 2)),
            ( "check_service_freshness",
              MonitoringState(title = "State when not checking service freshness", default_value = 2)),
            ( "enable_event_handlers",
              MonitoringState(title = "State when event handlers are disabled", default_value = 0)),
            ( "enable_flap_detection",
              MonitoringState(title = "State when flap detection is disabled", default_value = 1)),
            ( "enable_notifications",
              MonitoringState(title = "State when notifications are disabled", default_value = 2)),
            ( "process_performance_data",
              MonitoringState(title = "State when performance data is disabled", default_value = 1)),
            ( "check_external_commands",
              MonitoringState(title = "State when not checking external commands", default_value = 2)),
        ]
    ),
    TextAscii(
        title = _("Name of the monitoring site"),
    ),
    match_type = "dict",
)


register_check_parameters(
    subgroup_applications,
    "ad_replication",
    _("Active Directory Replication"),
    Tuple(
        help = _("The number of replication failures"),
        elements = [
           Integer(title = _("Warning at"), unit = _("failures")),
           Integer(title = _("Critical at"), unit = _("failures")),
        ]
      ),
    TextAscii(
        title = _("Replication Partner"),
        help = _("The name of the replication partner (Destination DC Site/Destination DC)."),
    ),
    match_type = "first",
)


register_check_parameters(
    subgroup_applications,
    "mq_queues",
    _("Apache ActiveMQ Queue lengths"),
    Dictionary(
        elements = [
            ("size",
            Tuple(
               title = _("Levels for the queue length"),
               help = _("Set the maximum and minimum length for the queue size"),
               elements = [
                  Integer(title="Warning at a size of"),
                  Integer(title="Critical at a size of"),
               ]
            )),
            ("consumerCount",
            Tuple(
               title = _("Levels for the consumer count"),
               help = _("Consumer Count is the size of connected consumers to a queue"),
               elements = [
                  Integer(title="Warning less then"),
                  Integer(title="Critical less then"),
               ]
            )),
        ]
    ),
    TextAscii( title=_("Queue Name"),
    help=_("The name of the queue like in the Apache queue manager")),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "sshd_config",
    _("SSH daemon configuration"),
    Dictionary(
        elements = [
            ("PermitRootLogin",
            DropdownChoice(
                title = _("Permit root login"),
                choices = [
                    ('yes',                     _('Yes')),
                    ('without-password',        _('Without password')),
                    ('forced-commands-only',    _('Forced commands only')),
                    ('no',                      _('No')),
                ],
                default_value = "without-password",
            )),
            ("Protocol",
            DropdownChoice(
                title = _("Allowed protocols"),
                choices = [
                    ('1',   _('Version 1')),
                    ('2',   _('Version 2')),
                    ('1,2', _('Version 1 and 2')),
                ],
                default_value = "2",
            )),
            ("Port",
            ListOfIntegers(
                title = _("Allowed Ports"),
                minvalue = 0,
                maxvalue = 65535,
                orientation = "horizontal",
                default_value = [22],
            )),
            ("PasswordAuthentication",
            DropdownChoice(
                title = _("Allow password authentication"),
                help = _("Specifies whether password authentication is allowed"),
                choices = [
                    ('yes', _('Yes')),
                    ('no',  _('No')),
                ],
                default_value = "no",
            )),
            ("PermitEmptyPasswords",
            DropdownChoice(
                title = _("Permit empty passwords"),
                help = _("If password authentication is used this option "
                       "specifies wheter the server allows login to accounts "
                       "with empty passwords"),
                choices = [
                    ('yes', _('Yes')),
                    ('no',  _('No')),
                ],
                default_value = "no",
            )),
            ("ChallengeResponseAuthentication",
            DropdownChoice(
                title = _("Allow challenge-response authentication"),
                choices = [
                    ('yes', _('Yes')),
                    ('no',  _('No')),
                ],
                default_value = "no",
            )),
            ("X11Forwarding",
            DropdownChoice(
                title = _("Permit X11 forwarding"),
                choices = [
                    ('yes', _('Yes')),
                    ('no',  _('No')),
                ],
                default_value = "no",
            )),
            ("UsePAM",
            DropdownChoice(
                title = _("Use pluggable authentication module"),
                choices = [
                    ('yes', _('Yes')),
                    ('no',  _('No')),
                ],
                default_value = "no",
            )),
            ("Ciphers",
            ListOfStrings(
                title = _("Allowed Ciphers"),
                orientation = "horizontal",
            )),
        ]
    ),
    None,
    match_type = "dict",
)

websphere_mq_common_elements = [
    ("message_count",
        OptionalDropdownChoice(
            title      = _('Maximum number of messages'),
            choices    = [ (None, _("Ignore these levels")) ],
            otherlabel = _("Set absolute levels"),
            explicit   = \
                Tuple(
                    title = _('Maximum number of messages'),
                    elements = [
                        Integer(title = _("Warning at")),
                        Integer(title = _("Critical at")),
                    ]
                ),
            default_value = (1000, 1200)
        )
    ),
    ("message_count_perc",
        OptionalDropdownChoice(
            title      = _('Percentage of queue length'),
            help       = _('This setting only applies if the WebSphere MQ reports the queue length'),
            choices    = [ (None, _("Ignore these levels")) ],
            otherlabel = _("Set relative levels"),
            explicit   = \
                Tuple(
                    title = _('Percentage of queue length'),
                    elements = [
                        Percentage(title = _("Warning at")),
                        Percentage(title = _("Critical at")),
                    ]
                ),
            default_value = (80.0, 90.0)
    )),
]

def transform_websphere_mq_queues(source):
    if isinstance(source, tuple):
        return {"message_count": source}

    elif "messages_not_processed_age" in source:
        age_params = source["messages_not_processed_age"]
        source["messages_not_processed"] = {}
        source["messages_not_processed"]["age"] = age_params
        del source["messages_not_processed_age"]
        return source

    else:
        return source

register_check_parameters(
    subgroup_applications,
    "websphere_mq",
    _("Websphere MQ"),
    Transform(
        Dictionary(
            elements = websphere_mq_common_elements + [
                ("messages_not_processed",
                    Dictionary(
                        title = _("Settings for messages not processed"),
                        help  = _("With this rule you can determine the warn and crit age "
                                  "if LGETTIME and LGETDATE is available in the agent data. "
                                  "Note that if LGETTIME and LGETDATE are available but not set "
                                  "you can set the service state which is default WARN. "
                                  "This rule applies only if the current depth is greater than zero."),
                        elements = [
                            ("age",
                                Tuple(
                                    title    = _("Upper levels for the age"),
                                    elements = [
                                        Age(title = _("Warning at")),
                                        Age(title = _("Critical at")),
                                    ],
                                )
                            ),
                            ("state",
                                MonitoringState(
                                    title = _("State if LGETTIME and LGETDATE are available but not set"),
                                    default_value = 1)
                            ),
                        ]
                    )),
                ],
        ),
        forth = transform_websphere_mq_queues
    ),
    TextAscii(title = _("Name of queue")),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "websphere_mq_channels",
    _("Websphere MQ Channels"),
    Dictionary(
        elements = websphere_mq_common_elements + [
            ("status",
                Dictionary(
                     title = _('Override check state based on channel state'),
                     elements = [
                         ("INACTIVE",  MonitoringState(
                             title = _("State when channel is inactive"),
                             default_value = 2)),
                         ("INITIALIZING",  MonitoringState(
                             title = _("State when channel is initializing"),
                             default_value = 2)),
                         ("BINDING",  MonitoringState(
                             title = _("State when channel is binding"),
                             default_value = 2)),
                         ("STARTING",  MonitoringState(
                             title = _("State when channel is starting"),
                             default_value = 2)),
                         ("RUNNING",  MonitoringState(
                             title = _("State when channel is running"),
                             default_value = 0)),
                         ("RETRYING", MonitoringState(
                             title = _("State when channel is retrying"),
                             default_value = 2)),
                         ("STOPPING", MonitoringState(
                             title = _("State when channel is stopping"),
                             default_value = 2)),
                         ("STOPPED",  MonitoringState(
                             title = _("State when channel is stopped"),
                             default_value = 1)),
                         ("other",    MonitoringState(
                             title = _("State when channel status is unknown"),
                             default_value = 2)),
                     ],
                     optional_keys = []
            )),
        ],
    ),
    TextAscii(title = _("Name of channel")),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    'websphere_mq_manager',
    _("Websphere MQ Manager"),
    Dictionary(
        elements = [
            ("map_manager_states", ListOf(Tuple(
                orientation = "horizontal",
                elements = [
                    DropdownChoice(
                        choices = [
                            ('starting',             _('Starting')),
                            ('running',              _('Running')),
                            ('running_as_stanby',    _('Running as standby')),
                            ('running_elsewhere',    _('Running elsewhere')),
                            ('quiescing',            _('Quiescing')),
                            ('ending_immediately',   _('Ending immedtiately')),
                            ('ending_pre_emptively', _('Ending pre-emptivley')),
                            ('ended_normally',       _('Ended normally')),
                            ('ended_immediately',    _('Ended immediately')),
                            ('ended_unexpectedly',   _('Ended unexpectedly')),
                            ('ended_pre_emptively',  _('Ended pre-emptively')),
                            ('status_not_available', _('Status not available')),
                        ]
                    ), MonitoringState(),
                ]),
                title = _('Map manager state'),
            )),
            ("map_standby_states", ListOf(Tuple(
                orientation = "horizontal",
                elements = [
                    DropdownChoice(
                        choices = [
                            ('permitted',      _('Permitted')),
                            ('not_permitted',  _('Not permitted')),
                            ('not_applicable', _('Not applicable')),
                        ]
                    ), MonitoringState(),
                ]),
                title = _('Map standby state'),
            )),
        ]
    ),
    TextAscii(title = _("Name of manager")),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    'websphere_mq_instance',
    _("Websphere MQ Instance"),
    Dictionary(
        elements = [
            ("map_instance_states", ListOf(Tuple(
                orientation = "horizontal",
                elements = [
                    DropdownChoice(
                        choices = [
                            ('active',  _('Active')),
                            ('standby', _('Standby')),
                        ]
                    ), MonitoringState(),
                ]),
                title = _('Map instance state'),
            )),
        ]
    ),
    TextAscii(title = _("Name of manager or instance")),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "plesk_backups",
    _("Plesk Backups"),
    Dictionary(
         help = _("This check monitors backups configured for domains in plesk."),
         elements = [
             ("no_backup_configured_state", MonitoringState(
                 title = _("State when no backup is configured"),
                 default_value = 1)
             ),
             ("no_backup_found_state", MonitoringState(
                 title = _("State when no backup can be found"),
                 default_value = 1)
             ),
             ("backup_age",
               Tuple(
                   title = _("Maximum age of backups"),
                   help = _("The maximum age of the last backup."),
                   elements = [
                       Age(title = _("Warning at")),
                       Age(title = _("Critical at")),
                    ],
               ),
             ),
             ("total_size",
               Tuple(
                   title = _("Maximum size of all files on backup space"),
                   help = _("The maximum size of all files on the backup space. "
                            "This might be set to the allowed quotas on the configured "
                            "FTP server to be notified if the space limit is reached."),
                   elements = [
                       Filesize(title = _("Warning at")),
                       Filesize(title = _("Critical at")),
                    ],
               ),
             ),
         ],
         optional_keys = ['backup_age', 'total_size']
    ),
    TextAscii(
        title = _("Service descriptions"),
        allow_empty = False
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "firewall_if",
    _("Firewall Interfaces"),
    Dictionary(
        elements = [
            ( "ipv4_in_blocked",
                Levels(
                    title = _("Levels for rate of incoming IPv4 packets blocked"),
                    unit = _("pkts/s"),
                    default_levels = (100.0, 10000.0),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "average",
              Integer(
                  title = _("Averaging"),
                  help = _("When this option is activated then the block rate is being "
                           "averaged <b>before</b> the levels are being applied."),
                  unit = _("minutes"),
                  default_value = 3,
                  minvalue = 1,
                  label = _("Compute average over last "),
            )),
        ],
    ),
    TextAscii(
        title = _("Interface"),
        help = _("The description of the interface as provided by the device"),
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "kaspersky_av_client",
    _("Kaspersky Anti-Virus Time Settings"),
    Dictionary(
        elements = [
            ( "signature_age",
                Tuple( title = _("Time Settings for Signature"),
                    elements = [
                        Age(title=_("Warning at"), default_value = 86400),
                        Age(title=_("Critical at"), default_value = 7*86400),
                    ],
                ),
            ),
            ( "fullscan_age",
                Tuple( title = _("Time Settings for Fullscan"),
                    elements = [
                        Age(title=_("Warning at"), default_value = 86400),
                        Age(title=_("Critical at"), default_value = 7*86400),
                    ],
                ),
            ),
        ],
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "mcafee_av_client",
    _("McAfee Anti-Virus Time Settings"),
    Tuple(
        title = _('Time Settings for Signature'),
        elements = [
            Age(title = _("Warning at"), default_value = 86400 ),
            Age(title = _("Critical at"), default_value = 7*86400 ),
        ],
    ),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_applications,
    "mcafee_web_gateway",
    _("McAfee web gateway statistics"),
    Dictionary(
        elements = [
            ("infections",
                Tuple(
                    title = _("Upper levels for infections"),
                    help  = _("Here you can specify upper levels for the number of "
                              "infections detected by the McAfee Gateway Antimalware Engine."),
                    elements = [
                        Float(title = _("Warning at")),
                        Float(title = _("Critical at")),
                    ]
                )
            ),
            ("connections_blocked",
                Tuple(
                    title = _("Upper levels for blocked connections"),
                    elements = [
                        Float(title = _("Warning at")),
                        Float(title = _("Critical at")),
                    ]
                )
            ),
        ]
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "mcafee_web_gateway_misc",
    _("McAfee web gateway miscellaneous"),
    Dictionary(
        elements = [
            ("clients",
                Tuple(
                    title = _("Upper levels for clients"),
                    elements = [
                        Integer(title = _("Warning at")),
                        Integer(title = _("Critical at")),
                    ]
                )
            ),
            ("network_sockets",
                Tuple(
                    title = _("Upper levels for open network sockets"),
                    elements = [
                        Integer(title = _("Warning at")),
                        Integer(title = _("Critical at")),
                    ]
                )
            ),
        ]
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "mcafee_emailgateway_bridge",
    _("McAfee email gateway bridge"),
    Dictionary(
        elements = [
            ("tcp", Tuple(
                title = _("TCP packets"),
                elements = [
                    Float(title = _("Warning at"),
                          unit = _("packets/s")),
                    Float(title = _("Critical at"),
                          unit = _("packets/s")),
                ]
            )),
            ("udp", Tuple(
                title = _("UDP packets"),
                elements = [
                    Float(title = _("Warning at"),
                          unit = _("packets/s")),
                    Float(title = _("Critical at"),
                          unit = _("packets/s")),
                ]
            )),
            ("icmp", Tuple(
                title = _("ICMP packets"),
                elements = [
                    Float(title = _("Warning at"),
                          unit = _("packets/s")),
                    Float(title = _("Critical at"),
                          unit = _("packets/s")),
                ]
            )),
        ]
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
     subgroup_applications,
     "pfsense_counter",
     _("pfSense Firewall Packet Rates"),
     Dictionary(
         help = _("This rule set is for configuring levels for global packet counters."),
         elements = [
             ("average", Integer(
                  title = _("Averaging"),
                  help = _("When this option is activated then the packet rates are being "
                           "averaged <b>before</b> the levels are being applied. Setting this to zero will "
                           "deactivate averaging."),
                  unit = _("minutes"),
                  default_value = 3,
                  minvalue = 1,
                  label = _("Compute average over last "),
                  )),
             ( "fragment",
               Tuple(
                   title = _("Levels for rate of fragmented packets"),
                   elements = [
                      Float(title = _("Warning at"), unit = _("pkts/s"), default_value = 100.0),
                      Float(title = _("Critical at"), unit = _("pkts/s"), default_value = 10000.0),
                   ],
             )),
             ( "normalized",
               Tuple(
                   title = _("Levels for rate of normalized packets"),
                   elements = [
                      Float(title = _("Warning at"), unit = _("pkts/s"), default_value = 100.0),
                      Float(title = _("Critical at"), unit = _("pkts/s"), default_value = 10000.0),
                   ],
             )),
             ( "badoffset",
               Tuple(
                   title = _("Levels for rate of packets with bad offset"),
                   elements = [
                      Float(title = _("Warning at"), unit = _("pkts/s"), default_value = 100.0),
                      Float(title = _("Critical at"), unit = _("pkts/s"), default_value = 10000.0),
                   ],
             )),
             ( "short",
               Tuple(
                   title = _("Levels for rate of short packets"),
                   elements = [
                      Float(title = _("Warning at"), unit = _("pkts/s"), default_value = 100.0),
                      Float(title = _("Critical at"), unit = _("pkts/s"), default_value = 10000.0),
                   ],
             )),
             ( "memdrop", Tuple(
                    title = _("Levels for rate of packets dropped due to memory limitations"),
                    elements = [
                       Float(title = _("Warning at"), unit = _("pkts/s"), default_value = 100.0),
                       Float(title = _("Critical at"), unit = _("pkts/s"), default_value = 10000.0),
                   ],
             )),
         ],
     ),
     None,
     match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "lnx_quota",
    _("Linux quota check"),
    Dictionary(
        optional_keys = None,
        elements = [
            ( "user",
                Checkbox(
                    title = _("Monitor user quotas"),
                    label = _("Enable"),
                    default_value = True,
                ),
            ),
            ( "group",
                Checkbox(
                    title = _("Monitor group quotas"),
                    label = _("Enable"),
                ),
            ),
        ]
    ),
    TextAscii(
        title = _("filesystem"),
        help = _("Name of filesystem with quotas enabled"),
    ),
    match_type = 'dict',
)


register_check_parameters(
    subgroup_applications,
    "ruckus_mac",
    _("Ruckus Spot Unique MAC addresses"),
    Dictionary(
        elements = [
            ("inside", Dictionary(
                title = _("Inside unique MACs"),
                elements = [
                    ( "levels_upper",
                        Tuple(
                            title = _("Upper levels"),
                            elements = [
                                Integer(title = _("Warning at") ),
                                Integer(title = _("Critical at")),
                            ],
                        ),
                    ),
                    ( "levels_lower",
                        Tuple(
                            title = _("Lower levels"),
                            elements = [
                                Integer(title = _("Warning if below")),
                                Integer(title = _("Critical if below")),
                            ],
                        ),
                    ),
                ]
            )),
            ("outside", Dictionary(
                title = _("Outside unique MACs"),
                elements = [
                    ( "levels_upper",
                        Tuple(
                            title = _("Upper levels"),
                            elements = [
                                Integer(title = _("Warning at") ),
                                Integer(title = _("Critical at")),
                            ],
                        ),
                    ),
                    ( "levels_lower",
                        Tuple(
                            title = _("Lower levels"),
                            elements = [
                                Integer(title = _("Warning if below")),
                                Integer(title = _("Critical if below")),
                            ],
                        ),
                    ),
                ]
            )),
        ],
    ),
    None,
    "dict"
)


register_check_parameters(
    subgroup_applications,
    "ruckus_ap",
    _("Ruckus Spot Access Points"),
    Tuple(
        elements = [
            Optional(
                Tuple(
                    elements = [
                        Integer(title = _("Warning at"),  default_value = 1, unit = _("devices")),
                        Integer(title = _("Critical at"), default_value = 1, unit = _("devices")),
                    ],
                ),
                sameline   = True,
                label      = _("Levels for <i>device time drifted</i>"),
                none_label = _("No levels set"),
                none_value = (None, None)
            ),
            Optional(
                Tuple(
                    elements = [
                        Integer(title = _("Warning at"),  default_value = 1, unit = _("devices")),
                        Integer(title = _("Critical at"), default_value = 1, unit = _("devices")),
                    ],
                ),
                sameline   = True,
                label      = _("Levels for <i>device not responding</i>"),
                none_label = _("No levels set"),
                none_value = (None, None)
            ),
        ],
    ),
    TextAscii(
        title = _("Band"),
        help = _("Name of the band, e.g. 5 GHz"),
    ),
    "first"
)

vs_license = Alternative(
        title = _("Levels for Number of Licenses"),
        style = "dropdown",
        default_value = None,
        elements = [
              Tuple(
                  title = _("Absolute levels for unused licenses"),
                  elements = [
                      Integer(title = _("Warning below"), default_value = 5, unit = _("unused licenses")),
                      Integer(title = _("Critical below"), default_value = 0, unit = _("unused licenses")),
                  ]
              ),
              Tuple(
                  title = _("Percentual levels for unused licenses"),
                  elements = [
                      Percentage(title = _("Warning below"), default_value = 10.0),
                      Percentage(title = _("Critical below"), default_value = 0),
                  ]
             ),
             FixedValue(
                 None,
                 totext = _("Critical when all licenses are used"),
                 title = _("Go critical if all licenses are used"),
             ),
             FixedValue(
                False,
                title = _("Always report OK"),
                totext = _("Alerting depending on the number of used licenses is disabled"),
             )
          ]
        )

register_check_parameters(
    subgroup_applications,
    "esx_licenses",
    _("Number of used VMware licenses"),
    vs_license,
    TextAscii(
       title = _("Name of the license"),
       help  = _("For example <tt>VMware vSphere 5 Standard</tt>"),
       allow_empty = False,
    ),
    "first"
)

register_check_parameters(
    subgroup_applications,
    "ibmsvc_licenses",
    _("Number of used IBM SVC licenses"),
    vs_license,
    TextAscii(
       title = _("ID of the license, e.g. <tt>virtualization</tt>"),
       allow_empty = False,
    ),
    "first"
)

register_check_parameters(
    subgroup_applications,
    "citrix_licenses",
    _("Number of used Citrix licenses"),
    vs_license,
    TextAscii(
       title = _("ID of the license, e.g. <tt>PVSD_STD_CCS</tt>"),
       allow_empty = False,
    ),
    "first"
)

register_check_parameters(
    subgroup_applications,
    "rds_licenses",
    _("Number of used Remote Desktop Licenses"),
    vs_license,
    TextAscii(
       title = _("ID of the license, e.g. <tt>Windows Server 2008 R2</tt>"),
       allow_empty = False,
    ),
    "first"
)

register_check_parameters(
    subgroup_applications,
    "citrix_sessions",
    _("Citrix Terminal Server Sessions"),
    Dictionary(
        elements = [
            ( "total",
              Tuple(
                  title = _("Total number of Sessions"),
                  elements = [
                      Integer(title = _("warning at"), unit = "Sessions" ),
                      Integer(title = _("critical at"), unit = "Session" ),
                  ])
            ),
            ( "active",
              Tuple(
                  title = _("Number of Active Sessions"),
                  elements = [
                      Integer(title = _("warning at"), unit = "Sessions" ),
                      Integer(title = _("critical at"), unit = "Session" ),
                  ])
            ),
            ( "inactive",
              Tuple(
                  title = _("Number of Inactive Sessions"),
                  elements = [
                      Integer(title = _("warning at"), unit = "Sessions" ),
                      Integer(title = _("critical at"), unit = "Session" ),
                  ])
            ),
        ]
    ),
    None, "dict"
)

register_check_parameters(
    subgroup_applications,
    "citrix_state",
    _("State of Citrix VMs"),
    Dictionary(
        elements = [
            ( "registrationstate",
              Dictionary(
                title = _("Interpretation of Registration States"),
                elements = [
                    ( "Unregistered", MonitoringState(title = _("Unregistered"), default_value = 2) ),
                    ( "Initializing", MonitoringState(title = _("Initializing"), default_value = 1) ),
                    ( "Registered",   MonitoringState(title = _("Registered"), default_value = 0) ),
                    ( "AgentError",   MonitoringState(title = _("Agent Error"), default_value = 2) ),
                ],
                optional_keys = False,
              ),
            )
        ]),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "mssql_stats",
    _("MSSQL Statistics"),
    Dictionary(
        elements = [
            ( "batch_requests/sec", Tuple(title = _("Batch Requests/sec"),
                elements = [ Float(title = _("warning at"), unit = _("/sec"), default_value = 100000.0 ),
                             Float(title = _("critical at"), unit = _("/sec"), default_value = 200000.0 ),])),
            ( "sql_compilations/sec", Tuple(title = _("SQL Compilations/sec"),
                elements = [ Float(title = _("warning at"), unit = _("/sec"), default_value = 10000.0),
                             Float(title = _("critical at"), unit = _("/sec"), default_value = 20000.0),])),
            ( "sql_re-compilations/sec", Tuple(title = _("SQL Re-Compilations/sec"),
                elements = [ Float(title = _("warning at"), unit = _("/sec"), default_value = 10000.0),
                             Float(title = _("critical at"), unit = _("/sec"), default_value = 200.0),])),
            ( "locks_per_batch", Tuple(title = _("Locks/Batch"),
                elements = [ Float(title = _("warning at"), default_value = 1000.0),
                             Float(title = _("critical at"), default_value = 3000.0),])),
        ],
    ),
    TextAscii(
       title = _("Counter ID"),
    ),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "mssql_instance",
    _("MSSQL Instance"),
    Dictionary(
        elements = [
            ("map_connection_state", MonitoringState(
                title = _("Connection status"),
                default_value = 2))
        ],
    ),
    TextAscii(
       title = _("Instance identifier"),
    ),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "mssql_databases",
    _("MSSQL Databases properties"),
    Dictionary(
        elements = [
            ("map_db_states", Dictionary(
                elements = [
                    ("ONLINE",  MonitoringState(title=_("Database Online"))),
                    ("OFFLINE", MonitoringState(title=_("Database Offline"))),
                    ("RESTORING", MonitoringState(title=_("Database Files are restored"))),
                    ("RECOVERING", MonitoringState(title=_("Database is being recovered"))),
                    ("RECOVERY_PENDING", MonitoringState(title=_("Database must be recovered"))),
                    ("SUSPECT", MonitoringState(title=_("Database Suspect"))),
                    ("EMERGENCY", MonitoringState(title=_("Database changed to emergency"))),
                ],
                title = _('Map Database States'),
                optional_keys = [],
            )),
            ("map_auto_close_state", Dictionary(
                elements = [
                    ( "on",  MonitoringState(title=_("Auto close on"), default_value=1) ),
                    ( "off", MonitoringState(title=_("Auto close off")) ),
                ],
                title = _('Map auto close status'),
                optional_keys = [],
            )),
            ("map_auto_shrink_state", Dictionary(
                elements = [
                    ( "on",  MonitoringState(title=_("Auto shrink on"), default_value=1) ),
                    ( "off", MonitoringState(title=_("Auto shrink off")) ),
                ],
                title = _('Map auto shrink status'),
                optional_keys = [],
            )),
        ]
    ),
    TextAscii(
       title = _("Database identifier"),
    ),
    "dict",
)


register_check_parameters(
    subgroup_applications,
    "mssql_connections",
    _("MSSQL Connections"),
    Dictionary(
        elements = [
            ( "levels",
                Tuple(
                    title = _("Upper levels for the number of active database connections"),
                    elements = [
                        Integer(title = _("Warning if over"), default_value=20),
                        Integer(title = _("Critical if over"), default_value=50),
                    ]
            ),)
        ]
    ),
    TextAscii(
        title = _("Database identifier"),
        allow_empty = True
    ),
    'dict',
)


register_check_parameters(
    subgroup_applications,
    "varnish_cache",
    _("Varnish Cache"),
    Dictionary(
        elements = [
            ("miss",
                Tuple(
                    title = _("Upper levels for \"cache misses\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
            ),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "varnish_client",
    _("Varnish Client"),
    Dictionary(
        elements = [
                ("drop",
                Tuple(
                    title = _("Upper levels for \"clients dropped\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
                ("req",
                Tuple(
                    title = _("Upper levels for \"client requests\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "varnish_backend",
    _("Varnish Backend"),
    Dictionary(
        elements = [
                ("busy",
                Tuple(
                    title = _("Upper levels for \"backend connections busy/too many\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
                ("fail",
                Tuple(
                    title = _("Upper levels for \"backend connections failures\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
                ("unhealthy",
                Tuple(
                    title = _("Upper levels for \"backend connections unhealthy/not attempted\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "varnish_fetch",
    _("Varnish Fetch"),
    Dictionary(
        elements = [
                ("1xx",
                Tuple(
                    title = _("Upper levels for \"fetch no body (1xx)\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
                ("204",
                Tuple(
                    title = _("Upper levels for \"fetch no body (204)\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
                ("304",
                Tuple(
                    title = _("Upper levels for \"fetch no body (304)\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
                ("bad",
                Tuple(
                    title = _("Upper levels for \"fetch had bad headers\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
                ("eof",
                Tuple(
                    title = _("Upper levels for \"fetch EOF\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
                ("failed",
                Tuple(
                    title = _("Upper levels for \"fetch failed\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
                ("zero",
                Tuple(
                    title = _("Upper levels for \"fetch zero length\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "varnish_esi",
    _("Varnish ESI"),
    Dictionary(
        elements = [
                ("errors",
                Tuple(
                    title = _("Upper levels for \"ESI errors\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
                ("warnings",
                Tuple(
                    title = _("Upper levels for \"ESI warnings\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "varnish_objects",
    _("Varnish Objects"),
    Dictionary(
        elements = [
                ("expired",
                Tuple(
                    title = _("Upper levels for \"expired objects\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
                ("lru_nuked",
                Tuple(
                    title = _("Upper levels for \"LRU nuked objects\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "varnish_worker",
    _("Varnish Worker"),
    Dictionary(
        elements = [
                ("wrk_drop",
                Tuple(
                    title = _("Upper levels for \"dropped work requests\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
                ("wrk_failed",
                Tuple(
                    title = _("Upper levels for \"worker threads not created\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
                ("wrk_queued",
                Tuple(
                    title = _("Upper levels for \"queued work requests\" per second"),
                    elements = [
                    Float(title = _("Warning at"), default_value = 1.0, allow_empty = False),
                    Float(title = _("Critical at"), default_value = 2.0, allow_empty = False)]),
                ),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "varnish_cache_hit_ratio",
    _("Varnish Cache Hit Ratio"),
    Dictionary(
        elements = [
            ("levels_lower",
                Tuple(
                    title = _("Lower levels"),
                    elements = [
                       Percentage(title = _("Warning if below"), default_value = 70.0, allow_empty = False),
                       Percentage(title = _("Critical if below"), default_value = 60.0, allow_empty = False)
                    ]
                ),
            ),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "varnish_backend_success_ratio",
    _("Varnish Backend Success Ratio"),
    Dictionary(
        elements = [
            ("levels_lower",
                Tuple(
                    title = _("Lower levels"),
                    elements = [
                        Percentage(title = _("Warning if below"), default_value = 70.0, allow_empty = False),
                        Percentage(title = _("Critical if below"), default_value = 60.0, allow_empty = False)
                    ]
                ),
            ),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "varnish_worker_thread_ratio",
    _("Varnish Worker Thread Ratio"),
    Dictionary(
        elements = [
            ("levels_lower",
                Tuple(
                    title = _("Lower levels"),
                    elements = [
                       Percentage(title = _("Warning if below"), default_value = 70.0, allow_empty = False),
                       Percentage(title = _("Critical if below"), default_value = 60.0, allow_empty = False)
                    ]
                ),
            ),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "clr_memory",
    _("DotNet (.Net) runtime memory levels"),
    Dictionary(
        help = _("This rule allows to set the warn and crit levels of the memory "
                 "metrics of the DotNet (.Net) Runtime"),
        elements = [
            ( "upper",
             Tuple(
                 title = _("Percent time spent in garbage collection"),
                 elements = [
                     Percentage(title = _("Warning at"), label = _("% time"), default_value = 10.0),
                     Percentage(title = _("Critical at"), label = _("% time"), default_value = 15.0),
                 ]
             )),
        ],
    ),
    TextAscii(
        title = _("Name of the Application"),
        help = _("The name of the DotNet (.Net) application or _Global_"),
        allow_empty = False,
    ),
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "skype_mobile",
    _("Skype for Business Mobile"),
    Dictionary(
        elements = [
            ('requests_processing',
            Dictionary(
                title = _("Requests in Processing"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Integer(title = _("Warning at"), unit = _("per second"), default_value = 10000),
                            Integer(title = _("Critical at"), unit = _("per second"), default_value = 20000),
                        ]
                    )),
                ],
                optional_keys = []
            ))
        ],
        optional_keys = []
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "skype_conferencing",
    _("Skype for Business Conferencing"),
    Dictionary(
        elements = [
            ('incomplete_calls',
             Dictionary(
                title = _("Incomplete Calls"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("per second"), default_value = 20.0),
                            Float(title = _("Critical at"), unit = _("per second"), default_value = 40.0),
                        ]
                    )),
                ],
                optional_keys = []
             )),
            ('create_conference_latency',
            Dictionary(
                title = _("Create Conference Latency"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("seconds"), default_value = 5.0),
                            Float(title = _("Critical at"), unit = _("seconds"), default_value = 10.0),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('allocation_latency',
            Dictionary(
                title = _("Conference Allocation Latency"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("seconds"), default_value = 5.0),
                            Float(title = _("Critical at"), unit = _("seconds"), default_value = 10.0),
                        ]
                    )),
                ],
                optional_keys = []
            )),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "skype_sip",
    _("Skype for Business SIP Stack"),
    Dictionary(
        elements = [
            ('message_processing_time',
            Dictionary(
                title = _("Average Incoming Message Processing Time"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("seconds"), default_value = 1.0),
                            Float(title = _("Critical at"), unit = _("seconds"), default_value = 2.0),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('incoming_responses_dropped',
            Dictionary(
                title = _("Incoming Responses Dropped"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("per second"), default_value = 1.0),
                            Float(title = _("Critical at"), unit = _("per second"), default_value = 2.0),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('incoming_requests_dropped',
            Dictionary(
                title = _("Incoming Requests Dropped"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("per second"), default_value = 1.0),
                            Float(title = _("Critical at"), unit = _("per second"), default_value = 2.0),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('queue_latency',
            Dictionary(
                title = _("Queue Latency"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("seconds"), default_value = 0.1),
                            Float(title = _("Critical at"), unit = _("seconds"), default_value = 0.2),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('sproc_latency',
            Dictionary(
                title = _("Sproc Latency"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("seconds"), default_value = 0.1),
                            Float(title = _("Critical at"), unit = _("seconds"), default_value = 0.2),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('throttled_requests',
            Dictionary(
                title = _("Throttled requests"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("per second"), default_value = 0.2),
                            Float(title = _("Critical at"), unit = _("per second"), default_value = 0.4),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('local_503_responses',
             Dictionary(
                 title = _("Local HTTP 503 Responses"),
                 elements = [
                     ("upper",
                      Tuple(
                          elements = [
                              Float(title = _("Warning at"), unit = _("per second"), default_value = 1.0),
                              Float(title = _("Critical at"), unit = _("per second"), default_value = 2.0),
                          ]
                      )),
                 ],
                 optional_keys = []
             )),
            ('timedout_incoming_messages',
            Dictionary(
                title = _("Incoming Messages Timed out"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Integer(title = _("Warning at"), default_value = 2),
                            Integer(title = _("Critical at"), default_value = 4),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('holding_time_incoming',
            Dictionary(
                title = _("Average Holding Time For Incoming Messages"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("seconds"), default_value = 1.0),
                            Float(title = _("Critical at"), unit = _("seconds"), default_value = 2.0),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('flow_controlled_connections',
            Dictionary(
                title = _("Flow-controlled Connections"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Integer(title = _("Warning at"), default_value = 1),
                            Integer(title = _("Critical at"), default_value = 2),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('outgoing_queue_delay',
            Dictionary(
                title = _("Average Outgoing Queue Delay"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("seconds"), default_value = 2.0),
                            Float(title = _("Critical at"), unit = _("seconds"), default_value = 4.0),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('timedout_sends',
            Dictionary(
                title = _("Sends Timed-Out"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("per second"), default_value = 0.01),
                            Float(title = _("Critical at"), unit = _("per second"), default_value = 0.02),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('authentication_errors',
            Dictionary(
                title = _("Authentication System Errors"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("per second"), default_value = 1.0),
                            Float(title = _("Critical at"), unit = _("per second"), default_value = 2.0),
                        ]
                    )),
                ],
                optional_keys = []
            )),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "skype_mediation_server",
    _("Skype for Business Mediation Server"),
    Dictionary(
        elements = [
            ('load_call_failure_index',
            Dictionary(
                title = _("Load Call Failure Index"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Integer(title = _("Warning at"), default_value = 10),
                            Integer(title = _("Critical at"), default_value = 20),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('failed_calls_because_of_proxy',
            Dictionary(
                title = _("Failed calls caused by unexpected interaction from proxy"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Integer(title = _("Warning at"), default_value = 10),
                            Integer(title = _("Critical at"), default_value = 20),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('failed_calls_because_of_gateway',
            Dictionary(
                title = _("Failed calls caused by unexpected interaction from gateway"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Integer(title = _("Warning at"), default_value = 10),
                            Integer(title = _("Critical at"), default_value = 20),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('media_connectivity_failure',
            Dictionary(
                title = _("Media Connectivity Check Failure"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Integer(title = _("Warning at"), default_value = 1),
                            Integer(title = _("Critical at"), default_value = 2),
                        ]
                    )),
                ],
                optional_keys = []
            )),

        ],
    ),
    None,
    "dict"
)


register_check_parameters(
    subgroup_applications,
    "skype_xmpp",
    _("Skype for Business XMPP"),
    Dictionary(
        elements = [
            ('failed_outbound_streams',
            Dictionary(
                title = _("XMPP Failed outbound stream establishes"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("per second"), default_value = 0.01),
                            Float(title = _("Critical at"), unit = _("per second"), default_value = 0.02),
                        ]
                    )),
                ],
                optional_keys = []
            )),
            ('failed_inbound_streams',
            Dictionary(
                title = _("XMPP Failed inbound stream establishes"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Float(title = _("Warning at"), unit = _("per second"), default_value = 0.01),
                            Float(title = _("Critical at"), unit = _("per second"), default_value = 0.02),
                        ]
                    )),
                ],
                optional_keys = []
            )),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "skype_edgeauth",
    _("Skype for Business Edge Auth"),
    Dictionary(
        elements = [
            ('bad_requests',
            Dictionary(
                title = _("Bad Requests Received"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Integer(title = _("Warning at"), unit = _("per second"), default_value = 20),
                            Integer(title = _("Critical at"), unit = _("per second"), default_value = 40),
                        ]
                    )),
                ],
                optional_keys = []
            )),
        ],
        optional_keys = []
    ),
    None,
    "dict"
)


register_check_parameters(
    subgroup_applications,
    "acme_certificates",
    _("ACME certificates"),
    Dictionary(
        elements = [
            ("expire_lower", Tuple(
                title    = _("Lower age levels for expire date"),
                elements = [
                    Age(title = _("Warning if below"),  default_value = 604800),
                    Age(title = _("Critical if below"), default_value = 2592000),
            ]))
        ],
    ),
    TextAscii(
        title       = _("Name of certificate"),
        allow_empty = False,
    ),
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "skype",
    _("Skype for Business"),
    Dictionary(
        elements = [
            ('failed_search_requests',
             Dictionary(
                 title = _("Failed search requests"),
                 elements = [
                     ("upper",
                      Tuple(
                          elements = [
                              Float(title = _("Warning at"), unit = _("per second"), default_value = 1.0),
                              Float(title = _("Critical at"), unit = _("per second"), default_value = 2.0),
                          ]
                      )),
                 ],
                 optional_keys = []
             )),
            ('failed_locations_requests',
             Dictionary(
                 title = _("Failed Get Locations Requests"),
                 elements = [
                     ("upper",
                      Tuple(
                          elements = [
                              Float(title = _("Warning at"), unit = _("per second"), default_value = 1.0),
                              Float(title = _("Critical at"), unit = _("per second"), default_value = 2.0),
                          ]
                      )),
                 ],
                 optional_keys = []
             )),
            ('failed_file_requests',
             Dictionary(
                 title = _("Failed requests to Adressbook files"),
                 elements = [
                    ("upper",
                     Tuple(
                          elements = [
                              Float(title = _("Warning at"), unit = _("per second"), default_value = 1.0),
                              Float(title = _("Critical at"), unit = _("per second"), default_value = 2.0),
                          ]
                     ))
                 ],
                 optional_keys = []
             )),
            ('join_failures',
             Dictionary(
                 title = _("Failures of the join launcher service"),
                 elements = [
                    ("upper",
                     Tuple(
                          elements = [
                              Integer(title = _("Warning at"), default_value = 1),
                              Integer(title = _("Critical at"), default_value = 2),
                          ]
                     ))
                 ],
                 optional_keys = []
             )),
            ('failed_validate_cert',
             Dictionary(
                 title = _("Failed certificate validations"),
                 elements = [
                    ("upper",
                     Tuple(
                          elements = [
                              Integer(title = _("Warning at"), default_value = 1),
                              Integer(title = _("Critical at"), default_value = 2),
                          ]
                     ))
                 ],
                 optional_keys = []
             )),
            ('timedout_ad_requests',
             Dictionary(
                 title = _("Timed out Active Directory Requests"),
                 elements = [
                     ("upper",
                      Tuple(
                          elements = [
                              Float(title = _("Warning at"), unit = _("per second"), default_value = 0.01),
                              Float(title = _("Critical at"), unit = _("per second"), default_value = 0.02),
                          ]
                      )),
                 ],
                 optional_keys = []
             )),
            ('5xx_responses',
             Dictionary(
                 title = _("HTTP 5xx Responses"),
                 elements = [
                     ("upper",
                      Tuple(
                          elements = [
                              Float(title = _("Warning at"), unit = _("per second"), default_value = 1.0),
                              Float(title = _("Critical at"), unit = _("per second"), default_value = 2.0),
                          ]
                      )),
                 ],
                 optional_keys = []
             )),
            ('asp_requests_rejected',
            Dictionary(
                title = _("ASP Requests Rejected"),
                elements = [
                    ("upper",
                    Tuple(
                        elements = [
                            Integer(title = _("Warning at"), default_value = 1),
                            Integer(title = _("Critical at"), default_value = 2),
                        ]
                    )),
                ],
                optional_keys = []
            )),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "skype_proxy",
    _("Skype for Business Data Proxy"),
    Dictionary(
        help = _("Warn/Crit levels for various Skype for Business "
                 "(formerly known as Lync) metrics"),
        elements = [
            ('throttled_connections',
             Dictionary(
                 title = _("Throttled Server Connections"),
                 elements = [
                     ("upper",
                      Tuple(
                          elements = [
                              Integer(title = _("Warning at"), default_value = 3),
                              Integer(title = _("Critical at"), default_value = 6),
                          ]
                      )),
                 ],
                 optional_keys = []
             )),
        ],
        optional_keys = []
    ),
    TextAscii(
        title = _("Name of the Proxy"),
        help = _("The name of the Data Proxy"),
        allow_empty = False,
    ),
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "skype_edge",
    _("Skype for Business Edge"),
    Dictionary(
        elements = [
            ('authentication_failures',
             Dictionary(
                 title = _("Authentication Failures"),
                 elements = [
                     ("upper",
                      Tuple(
                          elements = [
                              Integer(title = _("Warning at"), unit = _("per second"), default_value = 20),
                              Integer(title = _("Critical at"), unit = _("per second"), default_value = 40),
                          ]
                      )),
                 ],
                 optional_keys = []
             )),
            ('allocate_requests_exceeding',
             Dictionary(
                 title = _("Allocate Requests Exceeding Port Limit"),
                 elements = [
                     ("upper",
                      Tuple(
                          elements = [
                              Integer(title = _("Warning at"), unit = _("per second"), default_value = 20),
                              Integer(title = _("Critical at"), unit = _("per second"), default_value = 40),
                          ]
                      )),
                 ],
                 optional_keys = []
             )),
            ('packets_dropped',
             Dictionary(
                 title = _("Packets Dropped"),
                 elements = [
                     ("upper",
                      Tuple(
                          elements = [
                              Integer(title = _("Warning at"), unit = _("per second"), default_value = 200),
                              Integer(title = _("Critical at"), unit = _("per second"), default_value = 400),
                          ]
                      )),
                 ],
                 optional_keys = []
             )),
        ]
    ),
    TextAscii(
        title = _("Interface"),
        help = _("The name of the interface (Public/Private IPv4/IPv6 Network Interface)"),
    ),
    "dict"
)

# Rule for disovered process checks
register_check_parameters(
    subgroup_applications,
    "ps",
    _("State and count of processes"),
    Transform(
        Dictionary(
            elements = process_level_elements + [
                ('icon', UserIconOrAction(
                    title = _("Add custom icon or action"),
                    help = _("You can assign icons or actions to the found services in the status GUI."),
                ))
            ],
            ignored_keys=['match_groups'],
        ),
        forth = ps_convert_inventorized_from_singlekeys,
    ),
    TextAscii(
        title = _("Process name as defined at discovery"),
    ),
    "dict",
    has_inventory = True,
    register_static_check = False,
)

# Rule for static process checks
register_check_parameters(
    subgroup_applications,
    "ps",
    _("State and count of processes"),
    Transform(
        Dictionary(
            elements = [
                ( "process", Alternative(
                    title = _("Process Matching"),
                    style = "dropdown",
                    elements = [
                        TextAscii(
                            title = _("Exact name of the process without argments"),
                            size = 50,
                        ),
                        Transform(
                            RegExp(
                                size = 50,
                                mode = RegExp.prefix,
                            ),
                            title = _("Regular expression matching command line"),
                            help = _("This regex must match the <i>beginning</i> of the complete "
                                     "command line of the process including arguments"),
                            forth = lambda x: x[1:],   # remove ~
                            back  = lambda x: "~" + x, # prefix ~
                        ),
                        FixedValue(
                            None,
                            totext = "",
                            title = _("Match all processes"),
                        )
                    ],
                    match = lambda x: (not x and 2) or (x[0] == '~' and 1 or 0)
                )),
                ( "user", Alternative(
                    title = _("Name of operating system user"),
                    style = "dropdown",
                    elements = [
                        TextAscii(
                            title = _("Exact name of the operating system user")
                        ),
                        Transform(
                            RegExp(
                                size = 50,
                                mode = RegExp.prefix,
                            ),
                            title = _("Regular expression matching username"),
                            help = _("This regex must match the <i>beginning</i> of the complete "
                                     "username"),
                            forth = lambda x: x[1:],   # remove ~
                            back  = lambda x: "~" + x, # prefix ~
                        ),
                        FixedValue(
                            None,
                            totext = "",
                            title = _("Match all users"),
                        )

                    ],
                    match = lambda x: (not x and 2) or (x[0] == '~' and 1 or 0)

                )),
                ('icon', UserIconOrAction(
                    title = _("Add custom icon or action"),
                    help = _("You can assign icons or actions to the found services in the status GUI."),
                )),
            ] + process_level_elements,
            # required_keys = [ "process" ],
            ignored_keys=['match_groups'],
        ),
        forth = ps_convert_from_singlekeys,
    ),
    TextAscii(
        title = _("Process Name"),
        help = _("This name will be used in the description of the service"),
        allow_empty = False,
        regex = "^[a-zA-Z_0-9 _./-]*$",
        regex_error = _("Please use only a-z, A-Z, 0-9, space, underscore, "
                        "dot, hyphen and slash for your service description"),
    ),
    "dict",
    has_inventory = False,
)


register_check_parameters(
    subgroup_applications,
    "generic_number",
    _("Generic numeric value"),
    Dictionary(
        elements = [
            ( "levels",
              Tuple(
                    title = _("Upper levels"),
                    elements = [
                        Float(title = "Warning at"),
                        Float(title = "Critical at"),
                    ])),
            ( "levels_lower",
              Tuple(
                    title = _("Lower levels"),
                    elements = [
                        Float(title = "Warning below"),
                        Float(title = "Critical below"),
                    ])),
        ]),
    TextAscii(
        title = _("Item"),
    ),
    "dict"
)


register_check_parameters(
    subgroup_applications,
    "generic_rate",
    _("Generic rate"),
    Dictionary(
        elements = [
            ( "levels",
              Tuple(
                    title = _("Upper levels"),
                    elements = [
                        Float(title = "Warning at", unit = "/s"),
                        Float(title = "Critical at", unit = "/s"),
                    ])),
            ( "levels_lower",
              Tuple(
                    title = _("Lower levels"),
                    elements = [
                        Float(title = "Warning below", unit = "/s"),
                        Float(title = "Critical below", unit = "/s"),
                    ])),
        ]),
    TextAscii(
        title = _("Item"),
    ),
    "dict"
)


register_check_parameters(
    subgroup_applications,
    "generic_string",
    _("Generic string"),
    Dictionary(
        elements = [
            ( "default_status", MonitoringState(title = _("Default Status"))),
            ( "match_strings",
            ListOf(
                Tuple(
                    elements = [
                        TextAscii(title=_("Search string")),
                        MonitoringState(),
                    ])
            )),
         ]
    ),
    TextAscii(
        title = _("Item"),
    ),
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "jvm_uptime",
    _("JVM uptime (since last reboot)"),
    Dictionary(
        help = _("This rule sets the warn and crit levels for the uptime of a JVM. "
                 "Other keywords for this rule: Tomcat, Jolokia, JMX. "),
        elements = [
        ( "min",
          Tuple(
              title = _("Minimum required uptime"),
              elements = [
              Age(title = _("Warning if below")),
              Age(title = _("Critical if below")),
              ]
              )),
        ( "max",
          Tuple(
              title = _("Maximum allowed uptime"),
              elements = [
              Age(title = _("Warning at")),
              Age(title = _("Critical at")),
              ]
              )),
        ]
    ),
    TextAscii(
            title = _("Name of the virtual machine"),
            help = _("The name of the application server"),
            allow_empty = False,
            ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "netapp_systemtime",
    _("Netapp systemtime"),
    Dictionary(
        elements = [
            ( "levels", Tuple(
                title    = _("Set upper levels for the time difference"),
                help     = _("Here you can Set upper levels for the time difference "
                             "between agent and system time."),
                elements = [
                    Age(title = _("Warning if at")),
                    Age(title = _("Critical if at")),
            ])),
    ]),
    TextAscii(
        title = _("Name of the node"),
        allow_empty = False,
    ),
    match_type = "dict",
)

register_check_parameters(
   subgroup_applications,
    "jvm_sessions",
    _("JVM session count"),
    Tuple(
        help = _("This rule sets the warn and crit levels for the number of current "
                 "connections to a JVM application on the servlet level."),
        elements = [
            Integer(
                title = _("Warning if below"),
                unit = _("sessions"),
                default_value = -1,
            ),
            Integer(
                title = _("Critical if below"),
                unit = _("sessions"),
                default_value = -1,
            ),
            Integer(
                title = _("Warning at"),
                unit = _("sessions"),
                default_value = 800,
            ),
            Integer(
                title = _("Critical at"),
                unit = _("sessions"),
                default_value = 1000,
            ),
        ]
    ),
    TextAscii(
        title = _("Name of the virtual machine"),
        help = _("The name of the application server"),
        allow_empty = False,
    ),
    "first"
)

register_check_parameters(
   subgroup_applications,
    "jvm_requests",
    _("JVM request count"),
    Tuple(
        help = _("This rule sets the warn and crit levels for the number "
                 "of incoming requests to a JVM application server."),
        elements = [
            Integer(
                title = _("Warning if below"),
                unit = _("requests/sec"),
                default_value = -1,
            ),
            Integer(
                title = _("Critical if below"),
                unit = _("requests/sec"),
                default_value = -1,
            ),
            Integer(
                title = _("Warning at"),
                unit = _("requests/sec"),
                default_value = 800,
            ),
            Integer(
                title = _("Critical at"),
                unit = _("requests/sec"),
                default_value = 1000,
            ),
        ]
    ),
    TextAscii(
        title = _("Name of the virtual machine"),
        help = _("The name of the application server"),
        allow_empty = False,
    ),
    "first"
)

register_check_parameters(
   subgroup_applications,
    "jvm_queue",
    _("JVM Execute Queue Count"),
    Tuple(
        help = _("The BEA application servers have 'Execute Queues' "
                 "in which requests are processed. This rule allows to set "
                 "warn and crit levels for the number of requests that are "
                 "being queued for processing."),
        elements = [
            Integer(
                title = _("Warning at"),
                unit = _("requests"),
                default_value = 20,
            ),
            Integer(
                title = _("Critical at"),
                unit = _("requests"),
                default_value = 50,
            ),
        ]
    ),
    TextAscii(
        title = _("Name of the virtual machine"),
        help = _("The name of the application server"),
        allow_empty = False,
    ),
    "first"
)


register_check_parameters(
    subgroup_applications,
    "jvm_memory",
    _("JVM memory levels"),
    Dictionary(
            help = _("This rule allows to set the warn and crit levels of the heap / "
                     "non-heap and total memory area usage on web application servers. "
                     "Other keywords for this rule: Tomcat, Jolokia, JMX. "),
            elements = [
                ( "totalheap",
                   Alternative(
                       title = _("Total Memory Levels"),
                       elements = [
                           Tuple(
                               title = _("Percentage levels of used space"),
                               elements = [
                                   Percentage(title = _("Warning at"), label = _("% usage")),
                                   Percentage(title = _("Critical at"), label = _("% usage")),
                               ]
                           ),
                           Tuple(
                               title = _("Absolute free space in MB"),
                               elements = [
                                    Integer(title = _("Warning if below"), unit = _("MB")),
                                    Integer(title = _("Critical if below"), unit = _("MB")),
                               ]
                            )
                       ])),
                ( "heap",
                   Alternative(
                       title = _("Heap Memory Levels"),
                       elements = [
                           Tuple(
                               title = _("Percentage levels of used space"),
                               elements = [
                                   Percentage(title = _("Warning at"), label = _("% usage")),
                                   Percentage(title = _("Critical at"), label = _("% usage")),
                               ]
                           ),
                           Tuple(
                               title = _("Absolute free space in MB"),
                               elements = [
                                    Integer(title = _("Warning if below"), unit = _("MB")),
                                    Integer(title = _("Critical if below"), unit = _("MB")),
                               ]
                            )
                       ])),
                ( "nonheap",
                   Alternative(
                       title = _("Nonheap Memory Levels"),
                       elements = [
                           Tuple(
                               title = _("Percentage levels of used space"),
                               elements = [
                                   Percentage(title = _("Warning at"), label = _("% usage")),
                                   Percentage(title = _("Critical at"), label = _("% usage")),
                               ]
                           ),
                           Tuple(
                               title = _("Absolute free space in MB"),
                               elements = [
                                    Integer(title = _("Warning if below"), unit = _("MB")),
                                    Integer(title = _("Critical if below"), unit = _("MB")),
                               ]
                            )
                       ])),
                ( "perm",
                    Tuple(
                        title = _("Perm Memory usage"),
                        elements = [
                            Percentage(title = _("Warning at"), label = _("% usage")),
                            Percentage(title = _("Critical at"), label = _("% usage")),
                        ]
                    )
                ),
            ]),
        TextAscii(
            title = _("Name of the virtual machine"),
            help = _("The name of the application server"),
            allow_empty = False,
        ),
        "dict"
   )

register_check_parameters(
    subgroup_applications,
    "safenet_hsm_operstats",
    _("Safenet HSM Operation Stats"),
    Dictionary(
        elements=[
            ("error_rate", Tuple(
                title=_(u"Error rate"),
                elements=[
                    Float(title=_("Warning at"), default_value=0.01, unit=_("1/s")),
                    Float(title=_("Critical at"), default_value=0.05, unit=_("1/s")),
                ])),
            ("request_rate", Levels(
                title = _(u"Request rate"),
                unit = _("1/s"),
                default_value = None,
                )),
            ("operation_errors", Tuple(
                title=_("Operation errors"),
                help=_("Sets levels on total operation errors since last counter reset."),
                elements=[
                    Integer(title=_("Warning at"), default_value=0),
                    Integer(title=_("Critical at"), default_value=1),
                ])),
        ]
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "safenet_hsm_eventstats",
    _("Safenet HSM Event Stats"),
    Dictionary(
        elements=[
            ("critical_events", Tuple(
                title=_(u"Critical events"),
                help=_(u"Sets levels on total critical events since last counter reset."),
                elements=[
                    Integer(title=_("Warning at"), default_value=0),
                    Integer(title=_("Critical at"), default_value=1),
                ])),
            ("noncritical_events", Tuple(
                title=_(u"Noncritical events"),
                help=_(u"Sets levels on total noncritical events since last counter reset."),
                elements=[
                    Integer(title=_("Warning at"), default_value=0),
                    Integer(title=_("Critical at"), default_value=1),
                ])),
            ("critical_event_rate", Tuple(
                title=_(u"Critical event rate"),
                elements=[
                    Float(title=_("Warning at"), default_value=0.0001, unit=_("1/s")),
                    Float(title=_("Critical at"), default_value=0.0005, unit=_("1/s")),
                ])),
            ("noncritical_event_rate", Tuple(
                title=_(u"Noncritical event rate"),
                elements=[
                    Float(title=_("Warning at"), default_value=0.0001, unit=_("1/s")),
                    Float(title=_("Critical at"), default_value=0.0005, unit=_("1/s")),
                ])),
        ]
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "safenet_ntls_links",
    _(u"Safenet NTLS Links"),
    Levels(
        title=_(u"NTLS Links"),
        default_value=None,
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "safenet_ntls_clients",
    _(u"Safenet NTLS Clients"),
    Levels(
        title=_(u"NTLS Clients"),
        help=_(u"Number of connected clients"),
        default_value=None,
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "fireeye_active_vms",
        _("Fireeye Active VMs"),
        Dictionary(
            elements = [
                ( "vms",
                    Tuple(
                    title    = _("Levels for active VMs"),
                        elements = [
                            Integer( title = "Warning at", default_value=60, unit = "VMs"),
                            Integer( title = "Critical at", default_value=70, unit = "VMs"),
                        ]
                ),
            )]),
        None,
        match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "fireeye_lic",
        _("Fireeye Licenses"),
        Dictionary(
            elements = [
                ( "days",
                    Tuple(
                    title    = _("Levels for Fireeye License Expiration"),
                        elements = [
                            Integer( title = "Warning at", default_value=90, unit = "days"),
                            Integer( title = "Critical at", default_value=120, unit = "days"),
                        ]
                ),
            )]),
        TextAscii(
            title = _("License Feature")),
        match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "fireeye_quarantine",
        _("Fireeye Quarantine Usage"),
        Dictionary(
            elements = [
                ( "usage",
                    Tuple(
                    title    = _("Levels for Quarantine Usage"),
                        elements = [
                            Integer( title = "Warning at", default_value=70, unit = "%"),
                            Integer( title = "Critical at", default_value=80, unit = "%"),
                        ]
                ),
            )]),
        None,
        match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "fireeye_mailq",
        _("Fireeye Mail Queues"),
        Dictionary(
            elements = [
                ( "deferred",
                    Tuple(
                    title    = _("Levels for Deferred Queue length"),
                        elements = [
                            Integer( title = "Warning at", default_value=10, unit = "Mails"),
                            Integer( title = "Critical at", default_value=15, unit = "Mails"),
                        ]
                )),
                ( "hold",
                    Tuple(
                    title    = _("Levels for Hold Queue length"),
                        elements = [
                            Integer( title = "Warning at", default_value=500, unit = "Mails"),
                            Integer( title = "Critical at", default_value=700, unit = "Mails"),
                        ]
                )),
                ( "drop",
                    Tuple(
                    title    = _("Levels for Drop Queue length"),
                        elements = [
                            Integer( title = "Warning at", default_value=10, unit = "Mails"),
                            Integer( title = "Critical at", default_value=15, unit = "Mails"),
                        ]
                    )),
            ]),
        None,
        match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "fireeye_mail",
        _("Fireeye Mail Rate Average"),
        Dictionary(
            elements = [
                ( "interval",
                    Integer( title = "Timespan for mail rate computation", default_value=60, unit = "minutes"),
                ),
            ]),
        None,
        match_type = "dict",
)

#.
#   .--Environment---------------------------------------------------------.
#   |     _____            _                                      _        |
#   |    | ____|_ ____   _(_)_ __ ___  _ __  _ __ ___   ___ _ __ | |_      |
#   |    |  _| | '_ \ \ / / | '__/ _ \| '_ \| '_ ` _ \ / _ \ '_ \| __|     |
#   |    | |___| | | \ V /| | | | (_) | | | | | | | | |  __/ | | | |_      |
#   |    |_____|_| |_|\_/ |_|_|  \___/|_| |_|_| |_| |_|\___|_| |_|\__|     |
#   |                                                                      |
#   '----------------------------------------------------------------------'

register_check_parameters(
    subgroup_environment,
    "fan_failures",
    _("Number of fan failures"),
    Tuple(
        title=_("Number of fan failures"),
        elements = [
            Integer(title="Warning at", default_value=1),
            Integer(title="Critical at", default_value=2),
        ]
    ),
    None,
    "first",
)

register_check_parameters(
    subgroup_environment,
    "pll_lock_voltage",
    _("Lock Voltage for PLLs"),
    Dictionary(
        help = _("PLL lock voltages by freqency"),
        elements = [
            ( "rx",
                ListOf(
                    Tuple(
                        elements = [
                            Float(title = _("Frequencies up to"), unit = u"MHz"),
                            Float(title = _("Warning below"), unit = u"V"),
                            Float(title = _("Critical below"), unit = u"V"),
                            Float(title = _("Warning at or above"), unit = u"V"),
                            Float(title = _("Critical at or above"), unit = u"V"),
                        ],
                    ),
                    title = _("Lock voltages for RX PLL"),
                    help = _("Specify frequency ranges by the upper boundary of the range "
                             "to which the voltage levels are to apply. The list is sorted "
                             "automatically when saving."),
                    movable = False
                    )),
            ( "tx",
                ListOf(
                    Tuple(
                        elements = [
                            Float(title = _("Frequencies up to"), unit = u"MHz"),
                            Float(title = _("Warning below"), unit = u"V"),
                            Float(title = _("Critical below"), unit = u"V"),
                            Float(title = _("Warning at or above"), unit = u"V"),
                            Float(title = _("Critical at or above"), unit = u"V"),
                        ],
                    ),
                    title = _("Lock voltages for TX PLL"),
                    help = _("Specify frequency ranges by the upper boundary of the range "
                             "to which the voltage levels are to apply. The list is sorted "
                             "automatically when saving."),
                    movable = False
                    )),
        ],
        optional_keys = ["rx", "tx"],
    ),
    DropdownChoice( title = _("RX/TX"),
        choices = [ ("RX", _("RX")), ("TX", _("TX")) ]
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_environment,
    "ipmi",
    _("IPMI sensors"),
    Dictionary(
        elements = [
            ("sensor_states",
                ListOf(
                    Tuple( elements = [ TextAscii(), MonitoringState() ] ),
                    title = _("Set states of IPMI sensor status texts"),
                    help  = _("The pattern specified here must match exactly the beginning of "
                              "the sensor state (case sensitive)."),
                    orientation = "horizontal",
                )
            ),
            ( "ignored_sensors",
                ListOfStrings(
                    title = _("Ignore the following IPMI sensors"),
                    help  = _("Names of IPMI sensors that should be ignored during discovery "
                              "and when summarizing."
                              "The pattern specified here must match exactly the beginning of "
                              "the actual sensor name (case sensitive)."),
                    orientation = "horizontal"
                    )
                ),
            ( "ignored_sensorstates",
                ListOfStrings(
                    title = _("Ignore the following IPMI sensor states"),
                    help  = _("IPMI sensors with these states that should be ignored during discovery "
                              "and when summarizing."
                              "The pattern specified here must match exactly the beginning of "
                              "the actual sensor name (case sensitive)."),
                    orientation = "horizontal",
                    default_value = [ "nr", "ns" ]
                    )
            ),
            ( "numerical_sensor_levels", ListOf(Tuple(
                elements = [
                    TextAscii(title = _("Sensor name (only summary)"),
                              help  = _("In summary mode you have to state the sensor name. "
                                        "In single mode the sensor name comes from service description.")
                    ),
                    Dictionary(
                        elements = [
                            ("lower", Tuple(
                                title    = _("Lower levels"),
                                elements = [ Float(), Float() ])),
                            ("upper", Tuple(
                                title    = _("Upper levels"),
                                elements = [ Float(), Float() ])),
                    ]),
                ],
            ), title = _("Set lower and upper levels for numerical sensors"))),
        ],
        ignored_keys = ["ignored_sensors", "ignored_sensor_states"],
    ),
    TextAscii(title = _("The sensor name")),
    "dict",
)

register_check_parameters(
    subgroup_environment,
    "ps_voltage",
    _("Output Voltage of Power Supplies"),
    Tuple(
        elements = [
            Float(title = _("Warning below"), unit = u"V"),
            Float(title = _("Critical below"), unit = u"V"),
            Float(title = _("Warning at or above"), unit = u"V"),
            Float(title = _("Critical at or above"), unit = u"V"),
        ],
    ),
    None,
    match_type = "first",
)

bvip_link_states = [
  ( 0 , "No Link"),
  ( 1 , "10 MBit - HalfDuplex"),
  ( 2 , "10 MBit - FullDuplex"),
  ( 3 , "100 Mbit - HalfDuplex"),
  ( 4 , "100 Mbit - FullDuplex"),
  ( 5 , "1 Gbit - FullDuplex"),
  ( 7, "Wifi"),
]

register_check_parameters(
    subgroup_environment,
    "bvip_link",
    _("Allowed Network states on Bosch IP Cameras"),
    Dictionary(
        title = _("Update State"),
        elements = [
            ("ok_states", ListChoice(
              title = _("States which result in OK"),
              choices = bvip_link_states,
              default_value = [ 0, 4, 5 ]
            )),
            ("warn_states", ListChoice(
              title = _("States which result in Warning"),
              choices = bvip_link_states,
              default_value = [ 7 ]
            )),
            ("crit_states", ListChoice(
              title = _("States which result in Critical"),
              choices = bvip_link_states,
              default_value = [ 1, 2, 3 ]
            )),
        ],
        optional_keys = None,
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_environment,
    "ocprot_current",
    _("Electrical Current of Overcurrent Protectors"),
    Tuple(
        elements = [
            Float(title = _("Warning at"), unit = u"A", default_value = 14.0),
            Float(title = _("Critical at"), unit = u"A", default_value = 15.0),
        ],
    ),
    TextAscii(title = _("The Index of the Overcurrent Protector")),
    match_type = "first",
)


register_check_parameters(
    subgroup_environment,
    'brightness',
    _("Brightness Levels"),
    Levels(
        title = _("Brightness"),
        unit = _("lx"),
        default_value = None,
        default_difference = (2.0, 4.0),
        default_levels = (50.0, 100.0),
    ),
    TextAscii(
        title = _("Sensor name"),
        help = _("The identifier of the sensor."),
    ),
    match_type = "dict",
)


register_check_parameters(
    subgroup_environment,
    'motion',
    _("Motion Detectors"),
    Dictionary(
        elements = [
            ("time_periods",
             Dictionary(
                 title = _("Time periods"),
                 help = _("Specifiy time ranges during which no motion is expected. "
                          "Outside these times, the motion detector will always be in "
                          "state OK"),
                 elements = [
                     (day_id, TimeofdayRanges(count = 3, title = day_str))
                     for day_id,       day_str in [
                         ("monday",    _("Monday")),
                         ("tuesday",   _("Tuesday")),
                         ("wednesday", _("Wednesday")),
                         ("thursday",  _("Thursday")),
                         ("friday",    _("Friday")),
                         ("saturday",  _("Saturday")),
                         ("sunday",    _("Sunday"))
                     ]
                 ],
                 optional_keys = []
             )
             ),
        ]
    ),
    TextAscii(
        title = _("Sensor name"),
        help = _("The identifier of the sensor."),
    ),
    match_type = "dict"
)


register_check_parameters(
    subgroup_environment,
    'ewon',
    _("eWON SNMP Proxy"),
    Dictionary(
        title = _("Device Type"),
        help = _("The eWON router can act as a proxy to metrics from a secondary non-snmp device."
                 "Here you can make settings to the monitoring of the proxied device."),
        elements = [
            ("oxyreduct", Dictionary(
                title = _("Wagner OxyReduct"),
                elements = [
                    ("o2_levels", Tuple(
                        title = _("O2 levels"),
                        elements = [
                            Percentage(title = _("Warning at"), default_value = 16.0),
                            Percentage(title = _("Critical at"), default_value = 17.0),
                            Percentage(title = _("Warning below"), default_value = 14.0),
                            Percentage(title = _("Critical below"), default_value = 13.0),
                        ]
                    )
                    )
                ]
            )
            )
        ]
    ),
    TextAscii(
        title = _("Item name"),
        help = _("The item name. The meaning of this depends on the proxied device: "
                 "- Wagner OxyReduct: Name of the room/protection zone")
    ),
    match_type = "dict"
)


register_check_parameters(
    subgroup_environment,
    "lamp_operation_time",
    _("Beamer lamp operation time"),
    Tuple(
        elements = [
            Age(title = _("Warning at"), default_value = 1000*3600, display = [ "hours" ]),
            Age(title = _("Critical at"), default_value = 1500*3600, display = [ "hours" ]),
        ]),
    None,
    match_type = "first",
)

#.
#   .--Storage-------------------------------------------------------------.
#   |                 ____  _                                              |
#   |                / ___|| |_ ___  _ __ __ _  __ _  ___                  |
#   |                \___ \| __/ _ \| '__/ _` |/ _` |/ _ \                 |
#   |                 ___) | || (_) | | | (_| | (_| |  __/                 |
#   |                |____/ \__\___/|_|  \__,_|\__, |\___|                 |
#   |                                          |___/                       |
#   '----------------------------------------------------------------------'

register_check_parameters(
    subgroup_storage,
    "disk_failures",
    _("Number of disk failures"),
    Tuple(
        title=_("Number of disk failures"),
        elements = [
            Integer(title="Warning at", default_value=1),
            Integer(title="Critical at", default_value=2),
        ]
    ),
    None,
    "first",
)

register_check_parameters(
    subgroup_storage,
    "ddn_s2a_port_errors",
    _("Port errors of DDN S2A devices"),
    Dictionary(
        elements=[
            ("link_failure_errs", Tuple(
                title=_(u"Link failure errors"),
                elements=[
                    Integer(title=_(u"Warning at")),
                    Integer(title=_(u"Critical at")),
                ])),
            ("lost_sync_errs", Tuple(
                title=_(u"Lost synchronization errors"),
                elements=[
                    Integer(title=_(u"Warning at")),
                    Integer(title=_(u"Critical at")),
                ])),
            ("loss_of_signal_errs", Tuple(
                title=_(u"Loss of signal errors"),
                elements=[
                    Integer(title=_(u"Warning at")),
                    Integer(title=_(u"Critical at")),
                ])),
            ("prim_seq_errs", Tuple(
                title=_(u"PrimSeq erros"),
                elements=[
                    Integer(title=_(u"Warning at")),
                    Integer(title=_(u"Critical at")),
                ])),
            ("crc_errs", Tuple(
                title=_(u"CRC errors"),
                elements=[
                    Integer(title=_(u"Warning at")),
                    Integer(title=_(u"Critical at")),
                ])),
            ("receive_errs", Tuple(
                title=_(u"Receive errors"),
                elements=[
                    Integer(title=_(u"Warning at")),
                    Integer(title=_(u"Critical at")),
                ])),
            ("ctio_timeouts", Tuple(
                title=_(u"CTIO timeouts"),
                elements=[
                    Integer(title=_(u"Warning at")),
                    Integer(title=_(u"Critical at")),
                ])),
            ("ctio_xmit_errs", Tuple(
                title=_(u"CTIO transmission errors"),
                elements=[
                    Integer(title=_(u"Warning at")),
                    Integer(title=_(u"Critical at")),
                ])),
            ("ctio_other_errs", Tuple(
                title=_(u"other CTIO errors"),
                elements=[
                    Integer(title=_(u"Warning at")),
                    Integer(title=_(u"Critical at")),
                ])),
        ],
    ),
    TextAscii(title="Port index"),
    "dict"
)

register_check_parameters(
    subgroup_storage,
    "read_hits",
    _(u"Read prefetch hits for DDN S2A devices"),
    Tuple(
        title=_(u"Prefetch hits"),
        elements=[
            Float(title=_(u"Warning below"), default_value=95.0),
            Float(title=_(u"Critical below"), default_value=90.0),
        ]),
    TextAscii(title=_(u"Port index or 'Total'")),
    "first"
)

register_check_parameters(
    subgroup_storage,
    "storage_iops",
    _(u"I/O operations for DDN S2A devices"),
    Dictionary(
        elements=[
            ("read", Tuple(
                title=_(u"Read IO operations per second"),
                elements=[
                    Float(title=_(u"Warning at"), unit="1/s"),
                    Float(title=_(u"Critical at"), unit="1/s"),
                ])),
            ("write", Tuple(
                title=_(u"Write IO operations per second"),
                elements=[
                    Float(title=_(u"Warning at"), unit="1/s"),
                    Float(title=_(u"Critical at"), unit="1/s"),
                ])),
            ("total", Tuple(
                title=_(u"Total IO operations per second"),
                elements=[
                    Float(title=_(u"Warning at"), unit="1/s"),
                    Float(title=_(u"Critical at"), unit="1/s"),
                ])),
            ]),
    TextAscii(title=_(u"Port index or 'Total'")),
    "dict"
)

register_check_parameters(
    subgroup_storage,
    "storage_throughput",
    _(u"Throughput for DDN S2A devices"),
    Dictionary(
        elements=[
            ("read", Tuple(
                title=_(u"Read throughput per second"),
                elements=[
                    Filesize(title=_(u"Warning at")),
                    Filesize(title=_(u"Critical at")),
                ])),
            ("write", Tuple(
                title=_(u"Write throughput per second"),
                elements=[
                    Filesize(title=_(u"Warning at")),
                    Filesize(title=_(u"Critical at")),
                ])),
            ("total", Tuple(
                title=_(u"Total throughput per second"),
                elements=[
                    Filesize(title=_(u"Warning at")),
                    Filesize(title=_(u"Critical at")),
                ])),
            ]),
    TextAscii(title=_(u"Port index or 'Total'")),
    "dict"
)

register_check_parameters(
    subgroup_storage,
    "ddn_s2a_wait",
    _(u"Read/write wait for DDN S2A devices"),
    Dictionary(
        elements=[
            ("read_avg", Tuple(
                title=_(u"Read wait average"),
                elements=[
                    Float(title=_(u"Warning at"), unit="s"),
                    Float(title=_(u"Critical at"), unit="s"),
                ])),
            ("read_min", Tuple(
                title=_(u"Read wait minimum"),
                elements=[
                    Float(title=_(u"Warning at"), unit="s"),
                    Float(title=_(u"Critical at"), unit="s"),
                ])),
            ("read_max", Tuple(
                title=_(u"Read wait maximum"),
                elements=[
                    Float(title=_(u"Warning at"), unit="s"),
                    Float(title=_(u"Critical at"), unit="s"),
                ])),
            ("write_avg", Tuple(
                title=_(u"Write wait average"),
                elements=[
                    Float(title=_(u"Warning at"), unit="s"),
                    Float(title=_(u"Critical at"), unit="s"),
                ])),
            ("write_min", Tuple(
                title=_(u"Write wait minimum"),
                elements=[
                    Float(title=_(u"Warning at"), unit="s"),
                    Float(title=_(u"Critical at"), unit="s"),
                ])),
            ("write_max", Tuple(
                title=_(u"Write wait maximum"),
                elements=[
                    Float(title=_(u"Warning at"), unit="s"),
                    Float(title=_(u"Critical at"), unit="s"),
                ])),
            ]),
    DropdownChoice(
        title=_(u"Host or Disk"),
        choices=[
            ("Disk", _(u"Disk")),
            ("Host", _(u"Host")),
        ]
    ),
    "dict"
)

register_check_parameters(
    subgroup_storage,
    "blank_tapes",
    _("Remaining blank tapes in DIVA CSM Devices"),
    Tuple(
        elements = [
            Integer(title = _("Warning below"), default_value = 5),
            Integer(title = _("Critical below"), default_value = 1),
        ],
    ),
    None,
    match_type = "first",
)


register_check_parameters(
    subgroup_storage,
    "mongodb_flushing",
    _("MongoDB Flushes"),
    Dictionary(
        elements = [
            ("average_time",  Tuple(
                                title = _("Average flush time"),
                                elements = [
                                    Integer(title = _("Warning at"), unit = "ms", default_value = 50),
                                    Integer(title = _("Critical at"), unit = "ms", default_value = 100),
                                    Integer(title = _("Time interval"), unit = "minutes", default_value = 10),
                                ]),
            ),
            ("last_time",  Tuple(
                                title = _("Last flush time"),
                                elements = [
                                    Integer(title = _("Warning at"), unit = "ms", default_value = 50),
                                    Integer(title = _("Critical at"), unit = "ms", default_value = 100),
                                ]),
            ),
        ]
    ),
    None,
    match_type = "dict"
)

register_check_parameters(
    subgroup_storage,
    "mongodb_asserts",
    _("MongoDB Assert Rates"),
    Dictionary(
        elements = [
            ("%s_assert_rate" % what, Tuple(
                                title = _("%s rate") % what.title(),
                                elements = [
                                    Float(title = _("Warning at"), unit = _("Asserts / s"),  default_value = 1.0),
                                    Float(title = _("Critical at"), unit = _("Asserts / s"), default_value = 2.0),
                                ])
            ) for what in ["msg", "rollovers", "regular", "warning", "user"]
        ],
    ),
    None,
    match_type = "dict"
)

register_check_parameters(
    subgroup_storage,
    "mongodb_mem",
    _("MongoDB Memory"),
    Dictionary(
        title = _("MongoDB Memory"),
        elements = [
            ( "resident_levels",
               Tuple(
                 title = _("Resident memory usage"),
                 help = _("The value of resident is roughly equivalent to the amount of RAM, "
                          "currently used by the database process. In normal use this value tends to grow. "
                          "In dedicated database servers this number tends to approach the total amount of system memory."),
                 elements = [
                     Filesize(title = _("Warning at"), default_value = 1 * 1024**3),
                     Filesize(title = _("Critical at"), default_value = 2 * 1024**3),
                 ],
            )),
            ( "mapped_levels",
               Tuple(
                 title = _("Mapped memory usage"),
                 help = _("The value of mapped shows the amount of mapped memory by the database. "
                          "Because MongoDB uses memory-mapped files, this value is likely to be to be "
                          "roughly equivalent to the total size of your database or databases."),
                 elements = [
                     Filesize(title = _("Warning at"), default_value = 1 * 1024**3),
                     Filesize(title = _("Critical at"), default_value = 2 * 1024**3),
                 ],
            )),
            ( "virtual_levels",
               Tuple(
                 title = _("Virtual memory usage"),
                 help = _("Virtual displays the quantity of virtual memory used by the mongod process. "),
                 elements = [
                     Filesize(title = _("Warning at"), default_value = 2 * 1024**3),
                     Filesize(title = _("Critical at"), default_value = 4 * 1024**3),
                 ],
            )),
        ]
    ),
    None,
    match_type = "dict"
)


register_check_parameters(
    subgroup_storage,
    "openhardwaremonitor_smart",
    _("OpenHardwareMonitor S.M.A.R.T."),
    Dictionary(
        elements = [
            ( "remaining_life",
             Tuple(
                 title = _("Remaining Life"),
                 help = _("Estimated remaining health of the disk based on other readings."),
                 elements = [
                     Percentage(title = _("Warning below"),  default_value = 30),
                     Percentage(title = _("Critical below"), default_value = 10),
                 ],
             )
             ),
        ]
    ),
    TextAscii(
        title = _("Device Name"),
        help = _("Name of the Hard Disk as reported by OHM: hdd0, hdd1, ..."),
    ),
    match_type = "dict"
)


register_check_parameters(
    subgroup_storage,
    "mongodb_locks",
    _("MongoDB Locks"),
    Dictionary(
        elements = [
            ("%s_locks" % what, Tuple(
                title = _("%s Locks") % what.title().replace("_", " "),
                elements = [
                    Integer(title = _("Warning at"),  minvalue = 0),
                    Integer(title = _("Critical at"), minvalue = 0),
            ])) for what in ["clients_readers", "clients_writers", "clients_total",
                             "queue_readers", "queue_writers", "queue_total"]],
    ),
    None,
    match_type = "dict"
)


register_check_parameters(
    subgroup_storage,
    "prism_container",
    _("Nutanix Prism"),
    Dictionary(
        elements = [
            ("levels",
             Alternative(
                 title = _("Usage levels"),
                 default_value = (80.0, 90.0),
                 elements = [
                     Tuple(
                         title = _("Specify levels in percentage of total space"),
                         elements = [
                             Percentage(title = _("Warning at"), unit = _("%")),
                             Percentage(title = _("Critical at"), unit = _("%"))
                         ]
                     ),
                     Tuple(
                         title = _("Specify levels in absolute usage"),
                         elements = [
                             Filesize(title = _("Warning at"), default_value = 1000 * 1024 * 1024),
                             Filesize(title = _("Critical at"), default_value = 5000 * 1024 * 1024)
                         ]
                     ),
                 ]
             ))
        ],
        optional_keys = []
    ),
    TextAscii(
        title = _("Container Name"),
        help = _("Name of the container"),
    ),
    match_type = "dict"
)

register_check_parameters(
    subgroup_storage,
    "inotify",
    _("INotify Levels"),
    Dictionary(
        help = _("This rule allows you to set levels for specific Inotify changes. "
                 "Keep in mind that you can only monitor operations which are actually "
                 "enabled in the Inotify plugin. So it might be a good idea to cross check "
                 "these levels here with the configuration rule in the agent bakery. "),
        elements = [
            ('age_last_operation',
                ListOf(
                    Tuple(
                        elements = [
                            DropdownChoice( title = _("INotify Operation"),
                                choices = [
                                            ("create",    _("Create")),
                                            ("delete",    _("Delete")),
                                            ("open",      _("Open")),
                                            ("modify",    _("Modify")),
                                            ("access",    _("Access")),
                                            ("movedfrom", _("Moved from")),
                                            ("movedto",   _("Moved to")),
                                            ("moveself",  _("Move self")),
                                          ]
                            ),
                            Age(title=_("Warning at")),
                            Age(title=_("Critical at")),
                        ],
                    ),
                    title = _("Age of last operation"),
                    movable = False
             )),
        ],
        optional_keys = None,
    ),
    TextAscii(
        title = _("The filesystem path, prefixed with <i>File </i> or <i>Folder </i>"),
    ),
    match_type = "dict"
)

register_check_parameters(
    subgroup_storage,
    "emcvnx_disks",
    _("EMC VNX Enclosures"),
    Dictionary(
        elements = [
            ("state_read_error",
             Tuple(
                title = _("State on hard read error"),
                elements = [
                    MonitoringState(
                        title = _("State"),
                        default_value = 2,
                    ),
                    Integer(
                        title = _("Minimum error count"),
                        default_value = 2,
                    ),
                ]
             )
            ),
            ("state_write_error",
             Tuple(
                title = _("State on hard write error"),
                elements = [
                    MonitoringState(
                        title = _("State"),
                        default_value = 2,
                    ),
                    Integer(
                        title = _("Minimum error count"),
                        default_value = 2,
                    ),
                ]
             )
            ),
            ("state_rebuilding",
             MonitoringState(
                    default_value = 1,
                    title = _("State when rebuildung enclosure")
             )
            ),
        ]
    ),
    TextAscii(
        title = _("Enclosure ID"),
        allow_empty = True),
    match_type = "dict",
)

register_check_parameters(
    subgroup_storage,
    "lvm_lvs_pools",
    _("Logical Volume Pools (LVM)"),
    Dictionary(
        elements = [
            ( "levels_meta", Tuple(
                 title = _("Levels for Meta"),
                 default_value = (80.0, 90.0),
                     elements = [
                         Percentage(title = _("Warning at"), unit = _("%")),
                         Percentage(title = _("Critical at"), unit = _("%"))
                     ]
                 ),
            ),
            ( "levels_data", Tuple(
                 title = _("Levels for Data"),
                 default_value = (80.0, 90.0),
                     elements = [
                         Percentage(title = _("Warning at"), unit = _("%")),
                         Percentage(title = _("Critical at"), unit = _("%"))
                     ]
                 ),
            ),
        ]
    ),
    TextAscii(
        title = _("Logical Volume Pool"),
        allow_empty = True,
    ),
    match_type = "dict"
)

register_check_parameters(
    subgroup_storage,
    "emcvnx_storage_pools",
    _("EMC VNX storage pools"),
    Dictionary(
        elements = [
            ("percent_full",
             Tuple(
                title = _("Upper levels for physical capacity in percent"),
                elements = [
                    Percentage(title = _("Warning at"),  default_value = 70.0),
                    Percentage(title = _("Critical at"), default_value = 90.0),
                ]
            )),
        ]
    ),
    TextAscii(title = _("Pool name")),
    match_type = "dict",
)

register_check_parameters(
    subgroup_storage,
    "emcvnx_storage_pools_tiering",
    _("EMC VNX storage pools tiering"),
    Dictionary(
        elements = [
            ("time_to_complete",
             Tuple(
                title = _("Upper levels for estimated time to complete"),
                elements = [
                    Age(title = _("Warning at"),  default_value = 300*60*60),
                    Age(title = _("Critical at"), default_value = 350*60*60),
                ]
            )),
        ]
    ),
    TextAscii(title = _("Pool name")),
    match_type = "dict",
)

register_check_parameters(
    subgroup_storage,
    "filehandler",
    _("Filehandler"),
    Dictionary(
        elements = [
            ( "levels", Tuple(
                 title = _("Levels"),
                 default_value = (80.0, 90.0),
                     elements = [
                         Percentage(title = _("Warning at"), unit = _("%")),
                         Percentage(title = _("Critical at"), unit = _("%"))
                     ]
                 ),
            ),
        ]
    ),
    None,
    match_type = "dict"
)

register_check_parameters(
    subgroup_storage,
    "brocade_fcport",
    _("Brocade FibreChannel ports"),
    Dictionary(
        elements = [
            ("bw",
              Alternative(
                  title = _("Throughput levels"),
                  help = _("Please note: in a few cases the automatic detection of the link speed "
                           "does not work. In these cases you have to set the link speed manually "
                           "below if you want to monitor percentage values"),
                  elements = [
                      Tuple(
                        title = _("Used bandwidth of port relative to the link speed"),
                        elements = [
                            Percentage(title = _("Warning at"), unit = _("percent")),
                            Percentage(title = _("Critical at"), unit = _("percent")),
                        ]
                    ),
                    Tuple(
                        title = _("Used Bandwidth of port in megabyte/s"),
                        elements = [
                            Integer(title = _("Warning at"), unit = _("MByte/s")),
                            Integer(title = _("Critical at"), unit = _("MByte/s")),
                        ]
                    )
                  ])
            ),
            ("assumed_speed",
                Float(
                    title = _("Assumed link speed"),
                    help = _("If the automatic detection of the link speed does "
                             "not work you can set the link speed here."),
                    unit = _("GByte/s")
                )
            ),
            ("rxcrcs",
                Tuple (
                    title = _("CRC errors rate"),
                    elements = [
                        Percentage( title = _("Warning at"), unit = _("percent")),
                        Percentage( title = _("Critical at"), unit = _("percent")),
                    ]
               )
            ),
            ("rxencoutframes",
                Tuple (
                    title = _("Enc-Out frames rate"),
                    elements = [
                        Percentage( title = _("Warning at"), unit = _("percent")),
                        Percentage( title = _("Critical at"), unit = _("percent")),
                    ]
                )
            ),
            ("rxencinframes",
                Tuple (
                    title = _("Enc-In frames rate"),
                    elements = [
                        Percentage( title = _("Warning at"), unit = _("percent")),
                        Percentage( title = _("Critical at"), unit = _("percent")),
                    ]
                )
            ),
            ("notxcredits",
                Tuple (
                    title = _("No-TxCredits errors"),
                    elements = [
                        Percentage( title = _("Warning at"), unit = _("percent")),
                        Percentage( title = _("Critical at"), unit = _("percent")),
                    ]
                )
            ),
            ("c3discards",
                Tuple (
                    title = _("C3 discards"),
                    elements = [
                        Percentage( title = _("Warning at"), unit = _("percent")),
                        Percentage( title = _("Critical at"), unit = _("percent")),
                    ]
                )
            ),
            ("average",
                Integer (
                    title = _("Averaging"),
                    help = _("If this parameter is set, all throughputs will be averaged "
                           "over the specified time interval before levels are being applied. Per "
                           "default, averaging is turned off. "),
                   unit = _("minutes"),
                   minvalue = 1,
                   default_value = 60,
                )
            ),
            ("phystate",
                Optional(
                    ListChoice(
                        title = _("Allowed states (otherwise check will be critical)"),
                        choices = [ (1, _("noCard") ),
                                    (2, _("noTransceiver") ),
                                    (3, _("laserFault") ),
                                    (4, _("noLight") ),
                                    (5, _("noSync") ),
                                    (6, _("inSync") ),
                                    (7, _("portFault") ),
                                    (8, _("diagFault") ),
                                    (9, _("lockRef") ),
                                  ]
                    ),
                    title = _("Physical state of port") ,
                    negate = True,
                    label = _("ignore physical state"),
                )
            ),
            ("opstate",
                Optional(
                    ListChoice(
                        title = _("Allowed states (otherwise check will be critical)"),
                        choices = [ (0, _("unknown") ),
                                    (1, _("online") ),
                                    (2, _("offline") ),
                                    (3, _("testing") ),
                                    (4, _("faulty") ),
                                  ]
                    ),
                    title = _("Operational state") ,
                    negate = True,
                    label = _("ignore operational state"),
                )
            ),
            ("admstate",
                Optional(
                    ListChoice(
                        title = _("Allowed states (otherwise check will be critical)"),
                        choices = [ (1, _("online") ),
                                    (2, _("offline") ),
                                    (3, _("testing") ),
                                    (4, _("faulty") ),
                                  ]
                    ),
                    title = _("Administrative state") ,
                    negate = True,
                    label = _("ignore administrative state"),
                )
            )
        ]
      ),
    TextAscii(
        title = _("port name"),
        help = _("The name of the switch port"),
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_storage,
    "brocade_sfp",
    _("Brocade SFPs"),
    Dictionary(
        elements = [
            ("rx_power", Tuple(
                            title=_("Rx power level"),
                            elements=[
                                Float(title=_("Critical below"), unit=_("dBm")),
                                Float(title=_("Warning below"), unit=_("dBm")),
                                Float(title=_("Warning at"), unit=_("dBm")),
                                Float(title=_("Critical at"), unit=_("dBm"))
                            ])),
            ("tx_power", Tuple(
                            title=_("Tx power level"),
                            elements=[
                                Float(title=_("Critical below"), unit=_("dBm")),
                                Float(title=_("Warning below"), unit=_("dBm")),
                                Float(title=_("Warning at"), unit=_("dBm")),
                                Float(title=_("Critical at"), unit=_("dBm"))
                            ])),
        ]),
    TextAscii(title=_("Port index")),
    "dict"
)

register_check_parameters(
    subgroup_storage,
    "fcport_words",
    _("Atto Fibrebridge FC port"),
    Dictionary(
        title = _("Levels for transmitted and received words"),
        elements = [
            ("fc_tx_words", Levels(title=_("Tx"), unit=_("words/s"))),
            ("fc_rx_words", Levels(title=_("Rx"), unit=_("words/s"))),
        ],
    ),
    TextAscii(
        title = _("Port index"),
    ),
    "dict"
)


register_check_parameters(
    subgroup_storage,
    "fs_mount_options",
    _("Filesystem mount options (Linux/UNIX)"),
    ListOfStrings(
       title = _("Expected mount options"),
       help = _("Specify all expected mount options here. If the list of "
         "actually found options differs from this list, the check will go "
         "warning or critical. Just the option <tt>commit</tt> is being "
         "ignored since it is modified by the power saving algorithms."),
       valuespec = TextUnicode(),
    ),
    TextAscii(
        title = _("Mount point"),
        allow_empty = False),
    "first"
)

register_check_parameters(
    subgroup_storage,
    "storcli_vdrives",
    _("LSI RAID VDrives (StorCLI)"),
    Dictionary(
        title = _("Evaluation of VDrive States"),
        elements = [
            ( "Optimal",
              MonitoringState(
                    title = _("State for <i>Optimal</i>"),
                    default_value = 0,
            )),
            ( "Partially Degraded",
              MonitoringState(
                    title = _("State for <i>Partially Degraded</i>"),
                    default_value = 1,
            )),
            ( "Degraded",
              MonitoringState(
                    title = _("State for <i>Degraded</i>"),
                    default_value = 2,
            )),
            ( "Offline",
              MonitoringState(
                    title = _("State for <i>Offline</i>"),
                    default_value = 1,
            )),
            ( "Recovery",
              MonitoringState(
                    title = _("State for <i>Recovery</i>"),
                    default_value = 1,
            )),
        ]),
    TextAscii(
        title = _("Virtual Drive"),
        allow_empty = False,
    ),
    "dict"
)

register_check_parameters(
    subgroup_storage,
    "storcli_pdisks",
    _("LSI RAID physical disks (StorCLI)"),
    Dictionary(
        title = _("Evaluation of PDisk States"),
        elements = [
            ( "Dedicated Hot Spare",
              MonitoringState(
                    title = _("State for <i>Dedicated Hot Spare</i>"),
                    default_value = 0,
            )),
            ( "Global Hot Spare",
              MonitoringState(
                    title = _("State for <i>Global Hot Spare</i>"),
                    default_value = 0,
            )),
            ( "Unconfigured Good",
              MonitoringState(
                    title = _("State for <i>Unconfigured Good</i>"),
                    default_value = 0,
            )),
            ( "Unconfigured Bad",
              MonitoringState(
                    title = _("State for <i>Unconfigured Bad</i>"),
                    default_value = 1,
            )),
            ( "Online",
              MonitoringState(
                    title = _("State for <i>Online</i>"),
                    default_value = 0,
            )),
            ( "Offline",
              MonitoringState(
                    title = _("State for <i>Offline</i>"),
                    default_value = 2,
            )),
        ]),
    TextAscii(
        title = _("PDisk EID:Slot-Device"),
        allow_empty = False,
    ),
    "dict"
)

register_check_parameters(
    subgroup_storage,
    "veeam_tapejobs",
    _("VEEAM tape backup jobs"),
    Tuple(
        title = _("Levels for duration of backup job"),
        elements = [
            Age(title = "Warning at"),
            Age(title = "Critical at"),
        ],
    ),
    TextAscii(
        title = _("Name of the tape job"),
    ),
    "first",
)

def ceph_epoch_element(title):
    return  [("epoch", Tuple(
        title    = title,
        elements = [
            Float(title=_("Warning at")),
            Float(title=_("Critical at")),
            Integer(title=_("Average interval"), unit=_("minutes")),
        ])
    )]

register_check_parameters(
    subgroup_storage,
    "ceph_status",
    _("Ceph Status"),
    Dictionary(
        elements = ceph_epoch_element(_("Status epoch levels and average")),
    ),
    None,
    "dict",
)

register_check_parameters(
    subgroup_storage,
    "ceph_osds",
    _("Ceph OSDs"),
    Dictionary(
        elements = [
            ("num_out_osds", Tuple(
                title    = _("Upper levels for number of OSDs which are out"),
                elements = [
                    Percentage(title = _("Warning at")),
                    Percentage(title = _("Critical at")),
            ])),
            ("num_down_osds", Tuple(
                title    = _("Upper levels for number of OSDs which are down"),
                elements = [
                    Percentage(title = _("Warning at")),
                    Percentage(title = _("Critical at")),
            ])),
        ] + ceph_epoch_element(_("OSDs epoch levels and average")),
    ),
    None,
    "dict",
)

register_check_parameters(
    subgroup_storage,
    "ceph_mgrs",
    _("Ceph MGRs"),
    Dictionary(
        elements = ceph_epoch_element(_("MGRs epoch levels and average")),
    ),
    None,
    "dict",
)

register_check_parameters(
    subgroup_environment,
    "apc_system_events",
    _("APC Inrow System Events"),
    Dictionary(
        title = _("System Events on APX Inrow Devices"),
        elements = [
            ( "state",
              MonitoringState(
                    title = _("State during active system events"),
                    default_value = 2,
            )),
        ]),
    None,
    "dict"
)

#.
#   .--Printing------------------------------------------------------------.
#   |                ____       _       _   _                              |
#   |               |  _ \ _ __(_)_ __ | |_(_)_ __   __ _                  |
#   |               | |_) | '__| | '_ \| __| | '_ \ / _` |                 |
#   |               |  __/| |  | | | | | |_| | | | | (_| |                 |
#   |               |_|   |_|  |_|_| |_|\__|_|_| |_|\__, |                 |
#   |                                               |___/                  |
#   '----------------------------------------------------------------------'

def transform_printer_supply(params):
    if isinstance(params, tuple):
        if len(params) == 2:
            return {"levels" : params}
        return {"levels": params[:2], "upturn_toner": params[2]}
    return params

register_check_parameters(
    subgroup_printing,
    "printer_supply",
    _("Printer cartridge levels"),
    Transform(
        Dictionary(
            elements = [
                ( "levels",
                    Tuple(
                        title = _("Levels for remaining supply"),
                        elements = [
                            Percentage(
                                title = _("Warning level for remaining"),
                                allow_int = True,
                                default_value = 20.0,
                                help = _("For consumable supplies, this is configured as the percentage of "
                                         "remaining capacity. For supplies that fill up, this is configured "
                                         "as remaining space."),
                            ),
                            Percentage(
                                title = _("Critical level for remaining"),
                                allow_int = True,
                                default_value = 10.0,
                                help = _("For consumable supplies, this is configured as the percentage of "
                                         "remaining capacity. For supplies that fill up, this is configured "
                                         "as remaining space."),
                            ),
                        ]
                )),
                ( "some_remaining",
                   MonitoringState(
                    title = _("State for <i>some remaining</i>"),
                    help = _("Some printers do not report a precise percentage but "
                             "just <i>some remaining</i> at a low fill state. Here you "
                             "can set the monitoring state for that situation"),
                    default_value = 1,
                )),
                ( "upturn_toner",
                    Checkbox(
                        title = _("Upturn toner levels"),
                        label = _("Printer sends <i>used</i> material instead of <i>remaining</i>"),
                        help =  _("Some Printers (eg. Konica for Drum Cartdiges) returning the available"
                                  " fuel instead of what is left. In this case it's possible"
                                  " to upturn the levels to handle this behavior"),
                )),
            ]
        ),
        forth = transform_printer_supply,
    ),
    TextAscii(
        title = _("cartridge specification"),
        allow_empty = True
    ),
    match_type = "first",
)

register_check_parameters(
    subgroup_printing,
    "printer_input",
    _("Printer Input Units"),
    Dictionary(
        elements =  [
            ('capacity_levels', Tuple(
                title = _('Capacity remaining'),
                elements = [
                    Percentage(title = _("Warning at"), default_value = 0.0),
                    Percentage(title = _("Critical at"), default_value = 0.0),
                ],
            )),
        ],
        default_keys = ['capacity_levels'],
    ),
    TextAscii(
        title = _('Unit Name'),
        allow_empty = True
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_printing,
    "printer_output",
    _("Printer Output Units"),
    Dictionary(
        elements =  [
            ('capacity_levels', Tuple(
                title = _('Capacity filled'),
                elements = [
                    Percentage(title = _("Warning at"), default_value = 0.0),
                    Percentage(title = _("Critical at"), default_value = 0.0),
                ],
            )),
        ],
        default_keys = ['capacity_levels'],
    ),
    TextAscii(
        title = _('Unit Name'),
        allow_empty = True
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_printing,
    "cups_queues",
    _("CUPS Queue"),
    Dictionary(
        elements = [
            ( "job_count", Tuple(
                title = _("Levels of current jobs"),
                default_value = (5, 10),
                    elements = [
                        Integer(title = _("Warning at")),
                        Integer(title = _("Critical at"))
                    ]
                ),
            ),
            ( "job_age", Tuple(
                title = _("Levels for age of jobs"),
                help = _("A value in seconds"),
                default_value = (360, 720),
                    elements = [
                        Integer(title = _("Warning at")),
                        Integer(title = _("Critical at"))
                    ]
                ),
            ),
            ( "is_idle", MonitoringState(
                title = _("State for 'is idle'"),
                default_value = 0,
                )
            ),
            ( "now_printing", MonitoringState(
                title = _("State for 'now printing'"),
                default_value = 0,
                )
            ),
            ( "disabled_since", MonitoringState(
                title = _("State for 'disabled since'"),
                default_value = 2,
               )
            ),
        ],
    ),
    TextAscii(
        title = _("CUPS Queue") ),
    "dict",
)

#.
#   .--Os------------------------------------------------------------------.
#   |                               ___                                    |
#   |                              / _ \ ___                               |
#   |                             | | | / __|                              |
#   |                             | |_| \__ \                              |
#   |                              \___/|___/                              |
#   |                                                                      |
#   '----------------------------------------------------------------------'

register_check_parameters(
    subgroup_os,
    "fortigate_node_memory",
    _("Fortigate node memory"),
   Dictionary(
        elements = [
            ("levels", Tuple (
                title = _("Levels"),
                elements = [
                    Percentage(title = _("Warning at"),  default_value = 70.0, ),
                    Percentage(title = _("Critical at"), default_value = 80.0, ),
                ],
            ))
        ],
    ),
    TextAscii(
        title = _("node"),
    ),
    "dict",
)

register_check_parameters(
    subgroup_os,
    "uptime",
    _("Uptime since last reboot"),
    Dictionary(
        elements = [
            ( "min",
              Tuple(
                  title = _("Minimum required uptime"),
                  elements = [
                      Age(title = _("Warning if below")),
                      Age(title = _("Critical if below")),
                  ]
            )),
            ( "max",
              Tuple(
                  title = _("Maximum allowed uptime"),
                  elements = [
                      Age(title = _("Warning at")),
                      Age(title = _("Critical at")),
                  ]
            )),
        ]
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
   subgroup_os,
    "systemtime",
    _("Windows system time offset"),
    Tuple(
        title = _("Time offset"),
        elements = [
           Integer(title = _("Warning at"), unit = _("Seconds")),
           Integer(title = _("Critical at"), unit = _("Seconds")),
        ]
    ),
    None,
    "first"
)


#.
#   .--Unsorted--(Don't create new stuff here!)----------------------------.
#   |              _   _                      _           _                |
#   |             | | | |_ __  ___  ___  _ __| |_ ___  __| |               |
#   |             | | | | '_ \/ __|/ _ \| '__| __/ _ \/ _` |               |
#   |             | |_| | | | \__ \ (_) | |  | ||  __/ (_| |               |
#   |              \___/|_| |_|___/\___/|_|   \__\___|\__,_|               |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  All these rules have not been moved into their according sections.  |
#   |  Please move them as you come along - but beware of dependecies!     |
#   |  Remove this section as soon as it's empty.                          |
#   '----------------------------------------------------------------------'


register_check_parameters(
   subgroup_environment,
    "ups_test",
    _("Time since last UPS selftest"),
    Tuple(
        title = _("Time since last UPS selftest"),
        elements = [
            Integer(
                title = _("Warning Level for time since last self test"),
                help = _("Warning Level for time since last diagnostic test of the device. "
                         "For a value of 0 the warning level will not be used"),
                unit = _("days"),
                default_value = 0,
            ),
            Integer(
                title = _("Critical Level for time since last self test"),
                help = _("Critical Level for time since last diagnostic test of the device. "
                         "For a value of 0 the critical level will not be used"),
                unit = _("days"),
                default_value = 0,
            ),
        ]
    ),
    None,
    "first"
)

register_check_parameters(
   subgroup_environment,
    "apc_power",
    _("APC Power Consumption"),
    Tuple(
        title = _("Power Comsumption of APC Devices"),
        elements = [
            Integer(
                title = _("Warning below"),
                unit = _("W"),
                default_value = 20,
            ),
            Integer(
                title = _("Critical below"),
                unit = _("W"),
                default_value = 1,
            ),
        ]
    ),
    TextAscii(
        title = _("Phase"),
        help = _("The identifier of the phase the power is related to."),
    ),
    match_type = "first"
)

register_check_parameters(
    subgroup_storage,
    "fileinfo",
    _("Size and age of single files"),
    Dictionary(
        elements = [
            ( "minage",
                Tuple(
                    title = _("Minimal age"),
                    elements = [
                      Age(title = _("Warning if younger than")),
                      Age(title = _("Critical if younger than")),
                    ]
                )
            ),
            ( "maxage",
                Tuple(
                    title = _("Maximal age"),
                    elements = [
                      Age(title = _("Warning if older than")),
                      Age(title = _("Critical if older than")),
                    ]
                )
            ),
            ("minsize",
                Tuple(
                    title = _("Minimal size"),
                    elements = [
                      Filesize(title = _("Warning if below")),
                      Filesize(title = _("Critical if below")),
                    ]
                )
            ),
            ("maxsize",
                Tuple(
                    title = _("Maximal size"),
                    elements = [
                      Filesize(title = _("Warning at")),
                      Filesize(title = _("Critical at")),
                    ]
                )
            ),
            ("timeofday",
                TimeofdayRanges(
                    title = _("Only check during the following times of the day"),
                    help = _("Outside these ranges the check will always be OK"),
                    count = 3,
            )),
            ("state_missing",
                MonitoringState(
                    default_value = 3,
                    title = _("State when file is missing")
                )
            ),
        ]
    ),
    TextAscii(
        title = _("File name"),
        allow_empty = True),
    match_type = "dict",
)

register_rule(group + '/' + subgroup_storage,
    varname   = "filesystem_groups",
    title     = _('Filesystem grouping patterns'),
    help      = _('Normally the filesystem checks (<tt>df</tt>, <tt>hr_fs</tt> and others) '
                  'will create a single service for each filesystem. '
                  'By defining grouping '
                  'patterns you can handle groups of filesystems like one filesystem. '
                  'For each group you can define one or several patterns. '
                  'The filesystems matching one of the patterns '
                  'will be monitored like one big filesystem in a single service.'),
    valuespec = ListOf(
      Tuple(
          show_titles = True,
          orientation = "horizontal",
          elements = [
             TextAscii(
                 title = _("Name of group"),
             ),
             TextAscii(
                 title = _("Pattern for mount point (using * and ?)"),
                 help  = _("You can specify one or several patterns containing "
                           "<tt>*</tt> and <tt>?</tt>, for example <tt>/spool/tmpspace*</tt>. "
                           "The filesystems matching the patterns will be monitored "
                           "like one big filesystem in a single service."),
             ),
          ]
      ),
      add_label = _("Add pattern"),
    ),
    match = 'all',
)

register_rule(group + '/' + subgroup_storage,
    varname   = "fileinfo_groups",
    title     = _('File Grouping Patterns'),
    help      = _('The check <tt>fileinfo</tt> monitors the age and size of '
                  'a single file. Each file information that is sent '
                  'by the agent will create one service. By defining grouping '
                  'patterns you can switch to the check <tt>fileinfo.groups</tt>. '
                  'That check monitors a list of files at once. You can set levels '
                  'not only for the total size and the age of the oldest/youngest '
                  'file but also on the count. You can define one or several '
                  'patterns for a group containing <tt>*</tt> and <tt>?</tt>, for example '
                  '<tt>/var/log/apache/*.log</tt>. Please see Python\'s fnmatch for more '
                  'information regarding globbing patterns and special characters. '
                  'If the pattern begins with a tilde then this pattern is interpreted as '
                  'a regular expression instead of as a filename globbing pattern and '
                  '<tt>*</tt> and <tt>?</tt> are treated differently. '
                  'For files contained in a group '
                  'the discovery will automatically create a group service instead '
                  'of single services for each file. This rule also applies when '
                  'you use manually configured checks instead of inventorized ones. '
                  'Furthermore, the current time/date in a configurable format '
                  'may be included in the include pattern. The syntax is as follows: '
                  '$DATE:format-spec$ or $YESTERDAY:format-spec$, where format-spec '
                  'is a list of time format directives of the unix date command. '
                  'Example: $DATE:%Y%m%d$ is todays date, e.g. 20140127. A pattern '
                  'of /var/tmp/backups/$DATE:%Y%m%d$.txt would search for .txt files '
                  'with todays date  as name in the directory /var/tmp/backups. '
                  'The YESTERDAY syntax simply subtracts one day from the reference time.'),
    valuespec = ListOf(
        Tuple(
            help = _("This defines one file grouping pattern."),
            show_titles = True,
            orientation = "horizontal",
            elements = [
                TextAscii(
                     title = _("Name of group"),
                ),
                Transform(
                    Tuple(
                        show_titles = True,
                        orientation = "vertical",
                        elements = [
                            TextAscii(title = _("Include Pattern"), size=80),
                            TextAscii(title = _("Exclude Pattern"), size=80),
                        ],
                    ),
                    forth = lambda params: type(params) == str and ( params, '' ) or params
                ),
            ],
        ),
        add_label = _("Add pattern group"),
    ),
    match = 'all',
)


register_check_parameters(
    subgroup_storage,
    "fileinfo-groups",
    _("Size, age and count of file groups"),
    Dictionary(
        elements = [
            ( "minage_oldest",
                Tuple(
                    title = _("Minimal age of oldest file"),
                    elements = [
                      Age(title = _("Warning if younger than")),
                      Age(title = _("Critical if younger than")),
                    ]
                )
            ),
            ( "maxage_oldest",
                Tuple(
                    title = _("Maximal age of oldest file"),
                    elements = [
                      Age(title = _("Warning if older than")),
                      Age(title = _("Critical if older than")),
                    ]
                )
            ),
            ( "minage_newest",
                Tuple(
                    title = _("Minimal age of newest file"),
                    elements = [
                      Age(title = _("Warning if younger than")),
                      Age(title = _("Critical if younger than")),
                    ]
                )
            ),
            ( "maxage_newest",
                Tuple(
                    title = _("Maximal age of newest file"),
                    elements = [
                      Age(title = _("Warning if older than")),
                      Age(title = _("Critical if older than")),
                    ]
                )
            ),
            ("minsize_smallest",
                Tuple(
                    title = _("Minimal size of smallest file"),
                    elements = [
                      Filesize(title = _("Warning if below")),
                      Filesize(title = _("Critical if below")),
                    ]
                )
            ),
            ("maxsize_smallest",
                Tuple(
                    title = _("Maximal size of smallest file"),
                    elements = [
                      Filesize(title = _("Warning if above")),
                      Filesize(title = _("Critical if above")),
                    ]
                )
            ),
            ("minsize_largest",
                Tuple(
                    title = _("Minimal size of largest file"),
                    elements = [
                      Filesize(title = _("Warning if below")),
                      Filesize(title = _("Critical if below")),
                    ]
                )
            ),
            ("maxsize_largest",
                Tuple(
                    title = _("Maximal size of largest file"),
                    elements = [
                      Filesize(title = _("Warning if above")),
                      Filesize(title = _("Critical if above")),
                    ]
                )
            ),
            ("minsize",
                Tuple(
                    title = _("Minimal size"),
                    elements = [
                      Filesize(title = _("Warning if below")),
                      Filesize(title = _("Critical if below")),
                    ]
                )
            ),
            ("maxsize",
                Tuple(
                    title = _("Maximal size"),
                    elements = [
                      Filesize(title = _("Warning if above")),
                      Filesize(title = _("Critical if above")),
                    ]
                )
            ),
            ("mincount",
                Tuple(
                    title = _("Minimal file count"),
                    elements = [
                      Integer(title = _("Warning if below")),
                      Integer(title = _("Critical if below")),
                    ]
                )
            ),
            ("maxcount",
                Tuple(
                    title = _("Maximal file count"),
                    elements = [
                      Integer(title = _("Warning if above")),
                      Integer(title = _("Critical if above")),
                    ]
                )
            ),
            ("timeofday",
                TimeofdayRanges(
                    title = _("Only check during the following times of the day"),
                    help = _("Outside these ranges the check will always be OK"),
                    count = 3,
            )),
        ],
        ignored_keys = ["precompiled_patterns", "group_patterns"]
    ),
    TextAscii(
        title = _("File Group Name"),
        help = _("This name must match the name of the group defined "
                 "in the <a href=\"wato.py?mode=edit_ruleset&varname=fileinfo_groups\">%s</a> ruleset.") % \
                    (_('File Grouping Patterns')),
        allow_empty = True),
    match_type = "dict",
)

register_check_parameters(
    subgroup_storage,
    "netapp_fcportio",
    _("Netapp FC Port throughput"),
    Dictionary(
        elements = [
            ("read",
                Tuple(
                    title = _("Read"),
                    elements = [
                      Filesize(title = _("Warning if below")),
                      Filesize(title = _("Critical if below")),
                    ]
                )
            ),
            ("write",
                Tuple(
                    title = _("Write"),
                    elements = [
                      Filesize(title = _("Warning at")),
                      Filesize(title = _("Critical at")),
                    ]
                )
            )

        ]
    ),
    TextAscii(
        title = _("File name"),
        allow_empty = True),
    match_type = "dict",
)


register_check_parameters(
    subgroup_os,
    "memory_pagefile_win",
    _("Memory levels for Windows"),
    Dictionary(
        elements = [
            ( "memory",
               Alternative(
                   title = _("Memory Levels"),
                   style = "dropdown",
                   elements = [
                       Tuple(
                           title = _("Memory usage in percent"),
                           elements = [
                               Percentage(title = _("Warning at")),
                               Percentage(title = _("Critical at")),
                           ],
                       ),
                       Transform(
                            Tuple(
                                title = _("Absolute free memory"),
                                elements = [
                                     Filesize(title = _("Warning if less than")),
                                     Filesize(title = _("Critical if less than")),
                                ]
                            ),
                            # Note: Filesize values lesser 1MB will not work
                            # -> need hide option in filesize valuespec
                            back  = lambda x: (x[0] / 1024 / 1024, x[1] / 1024 / 1024),
                            forth = lambda x: (x[0] * 1024 * 1024, x[1] * 1024 * 1024)
                       ),
                       PredictiveLevels(
                           unit = _("GB"),
                           default_difference = (0.5, 1.0)
                       )
                   ],
                   default_value = (80.0, 90.0))),
            ( "pagefile",
               Alternative(
                   title = _("Commit charge Levels"),
                   style = "dropdown",
                   elements = [
                       Tuple(
                           title = _("Commit charge in percent (relative to commit limit)"),
                           elements = [
                               Percentage(title = _("Warning at")),
                               Percentage(title = _("Critical at")),
                           ]
                       ),
                       Transform(
                            Tuple(
                                title = _("Absolute commitable memory"),
                                elements = [
                                     Filesize(title = _("Warning if less than")),
                                     Filesize(title = _("Critical if less than")),
                                ]
                            ),
                            # Note: Filesize values lesser 1MB will not work
                            # -> need hide option in filesize valuespec
                            back  = lambda x: (x[0] / 1024 / 1024, x[1] / 1024 / 1024),
                            forth = lambda x: (x[0] * 1024 * 1024, x[1] * 1024 * 1024)
                       ),
                       PredictiveLevels(
                           unit = _("GB"),
                           default_difference = (0.5, 1.0)
                       )
                   ],
                   default_value = (80.0, 90.0))
            ),
            ("average",
                Integer (
                    title = _("Averaging"),
                    help = _("If this parameter is set, all measured values will be averaged "
                           "over the specified time interval before levels are being applied. Per "
                           "default, averaging is turned off. "),
                   unit = _("minutes"),
                   minvalue = 1,
                   default_value = 60,
                )
            ),

        ]),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "apache_status",
    ("Apache Status"),
    Dictionary(
        elements = [
            ( "OpenSlots",
                Tuple(
                    title = _("Remaining Open Slots"),
                    help  = _("Here you can set the number of remaining open slots"),
                    elements = [
                        Integer(title = _("Warning below"),  label = _("slots")),
                        Integer(title = _("Critical below"), label = _("slots"))
                    ]
                )
            ),
            ( "BusyWorkers",
                Tuple(
                    title = _("Busy workers"),
                    help  = _("Here you can set upper levels of busy workers"),
                    elements = [
                        Integer(title = _("Warning at"),  label = _("busy workers")),
                        Integer(title = _("Critical at"), label = _("busy workers"))
                    ]
                )
            ),
        ]
    ),
    TextAscii(
        title = _("Apache Server"),
        help  = _("A string-combination of servername and port, e.g. 127.0.0.1:5000.")
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "saprouter_cert_age",
    _("SAP router certificate time settings"),
    Dictionary(
        elements = [
            ("validity_age",
             Tuple(
                title = _('Lower levels for certificate age'),
                elements = [
                    Age( title = _("Warning below"),  default_value = 30*86400 ),
                    Age( title = _("Critical below"), default_value = 7*86400 ),
                ]
            )),
        ]
    ),
    None,
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "sap_dialog",
    ("SAP Dialog"),
    Dictionary(
        elements = [
            ( "UsersLoggedIn",
              Tuple(
                  title = _("Number of Loggedin Users"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("Users")),
                      Integer(title = _("Critical at"), label = _("Users"))
                  ]
              )
            ),
            ( "FrontEndNetTime",
              Tuple(
                  title = _("Frontend net time"),
                  elements = [
                     Float(title = _("Warning at"),  unit = _('ms') ),
                     Float(title = _("Critical at"), unit = _('ms') )
                  ]
              )
            ),
            ( "ResponseTime",
              Tuple(
                  title = _("Response Time"),
                  elements = [
                     Float(title = _("Warning at"),  unit = _('ms') ),
                     Float(title = _("Critical at"), unit = _('ms') )
                  ]
              )
            ),
        ]
    ),
    TextAscii(
        title = _("System ID"),
        help  = _("The SAP system ID."),
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "nginx_status",
    ("Nginx Status"),
    Dictionary(
        elements = [
            ( "active_connections",
              Tuple(
                  title = _("Active Connections"),
                  help = _("You can configure upper thresholds for the currently active "
                           "connections handled by the web server."),
                  elements = [
                      Integer(title = _("Warning at"),  unit = _("connections")),
                      Integer(title = _("Critical at"), unit = _("connections"))
                  ]
              )
            )
        ]
    ),
    TextAscii(
        title = _("Nginx Server"),
        help  = _("A string-combination of servername and port, e.g. 127.0.0.1:80.")
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "sles_license",
    ("SLES License"),
    Dictionary(
        elements = [
            ( "status",
              DropdownChoice(
                  title = _("Status"),
                  help = _("Status of the SLES license"),
                  choices = [
                      ('Registered', _('Registered')),
                      ('Ignore', _('Do not check')),
                  ]
              )
            ),
            ( "subscription_status",
              DropdownChoice(
                  title = _("Subscription"),
                  help = _("Status of the SLES subscription"),
                  choices = [
                      ('ACTIVE', _('ACTIVE')),
                      ('Ignore', _('Do not check')),
                  ]
              )
            ),
            ( "days_left",
              Tuple(
                  title = _("Time until license expiration"),
                  help = _("Remaining days until the SLES license expires"),
                  elements = [
                      Integer(title = _("Warning at"),  unit = _("days")),
                      Integer(title = _("Critical at"), unit = _("days"))
                  ]
              )
            ),
        ]
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_networking,
    "viprinet_router",
    _("Viprinet router"),
    Dictionary(
        elements = [
            ( "expect_mode",
              DropdownChoice(
                  title = _("Set expected router mode"),
                  choices = [
                        ( "inv", _("Mode found during inventory") ),
                        ( "0"  , _("Node") ),
                        ( "1"  , _("Hub") ),
                        ( "2"  , _("Hub running as HotSpare") ),
                        ( "3"  , _("Hotspare-Hub replacing another router") ),
                  ]
              )
            ),
        ]
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_networking,
    'docsis_channels_upstream',
    _("Docsis Upstream Channels"),
    Dictionary(
        elements = [
            ( 'signal_noise', Tuple(
                title = _("Levels for signal/noise ratio"),
                elements = [
                    Float(title = _("Warning at or below"), unit = "dB", default_value = 10.0),
                    Float(title = _("Critical at or below"), unit = "dB",  default_value = 5.0 ),
                ]
            )),
            ( 'correcteds', Tuple(
                title = _("Levels for rate of corrected errors"),
                elements = [
                    Percentage(title = _("Warning at"), default_value = 5.0),
                    Percentage(title = _("Critical at"), default_value = 8.0),
                ]
            )),
            ( 'uncorrectables', Tuple(
                title = _("Levels for rate of uncorrectable errors"),
                elements = [
                    Percentage(title = _("Warning at"), default_value = 1.0),
                    Percentage(title = _("Critical at"), default_value = 2.0),
                ]
            )),
        ]
    ),
    TextAscii(title = _("ID of the channel (usually ranging from 1)")),
    "dict"
)

register_check_parameters(
    subgroup_networking,
    "docsis_channels_downstream",
    _("Docsis Downstream Channels"),
    Dictionary(
        elements = [
            ( "power", Tuple(
                title = _("Transmit Power"),
                help = _("The operational transmit power"),
                elements = [
                    Float(title = _("warning at or below"), unit = "dBmV", default_value = 5.0 ),
                    Float(title = _("critical at or below"), unit = "dBmV", default_value = 1.0 ),
                ])
            ),
        ]
    ),
    TextAscii(title = _("ID of the channel (usually ranging from 1)")),
    "dict"
)

register_check_parameters(
    subgroup_networking,
    "docsis_cm_status",
    _("Docsis Cable Modem Status"),
    Dictionary(
        elements = [
            ( "error_states", ListChoice(
                title = _("Modem States that lead to a critical state"),
                help = _("If one of the selected states occurs the check will repsond with a critical state "),
                choices = [
                  ( 1,   "other" ),
                  ( 2,   "notReady" ),
                  ( 3,   "notSynchronized" ),
                  ( 4,   "phySynchronized" ),
                  ( 5,   "usParametersAcquired" ),
                  ( 6,   "rangingComplete" ),
                  ( 7,   "ipComplete" ),
                  ( 8,   "todEstablished" ),
                  ( 9,   "securityEstablished" ),
                  ( 10,  "paramTransferComplete"),
                  ( 11,  "registrationComplete"),
                  ( 12,  "operational"),
                  ( 13,  "accessDenied"),
                ],
                default_value = [ 1, 2, 13 ],
                )),
            ( "tx_power", Tuple(
                title = _("Transmit Power"),
                help = _("The operational transmit power"),
                elements = [
                    Float(title = _("warning at"), unit = "dBmV", default_value = 20.0 ),
                    Float(title = _("critical at"), unit = "dBmV", default_value = 10.0 ),
                ])),
        ]
    ),
    TextAscii( title = _("ID of the Entry")),
    "dict"
)

register_check_parameters(
    subgroup_networking,
    "vpn_tunnel",
    _("VPN Tunnel"),
    Dictionary(
        elements = [
            ( "tunnels",
              ListOf(
                  Tuple(
                      title = ("VPN Tunnel Endpoints"),
                      elements = [
                      IPv4Address(
                          title = _("IP-Address or Name of Tunnel Endpoint"),
                          help = _("The configured value must match a tunnel reported by the monitored "
                                   "device."),
                          allow_empty = False,
                      ),
                      TextUnicode(
                          title = _("Tunnel Alias"),
                          help = _("You can configure an individual alias here for the tunnel matching "
                                   "the IP-Address or Name configured in the field above."),
                      ),
                      MonitoringState(
                          default_value = 2,
                          title = _("State if tunnel is not found"),
                          )]),
                  add_label = _("Add tunnel"),
                  movable = False,
                  title = _("VPN tunnel specific configuration"),
                  )),
            ( "state",
              MonitoringState(
                  title = _("Default state to report when tunnel can not be found anymore"),
                  help = _("Default state if a tunnel, which is not listed above in this rule, "
                           "can no longer be found."),
                  ),
            ),
        ],
    ),
    TextAscii( title = _("IP-Address of Tunnel Endpoint")),
    match_type = "dict",
)

register_check_parameters(
    subgroup_networking,
    "lsnat",
    _("Enterasys LSNAT Bindings"),
    Dictionary(
        elements = [
                ( "current_bindings",
                    Tuple(
                        title = _("Number of current LSNAT bindings"),
                              elements = [
                                Integer(title = _("Warning at"),  size = 10, unit=_("bindings")),
                                Integer(title = _("Critical at"), size = 10, unit=_("bindings")),
                              ]
                   )
                ),
        ],
        optional_keys = False,
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_networking,
    "enterasys_powersupply",
    _("Enterasys Power Supply Settings"),
    Dictionary(
        elements = [
                ( "redundancy_ok_states",
                    ListChoice(
                        title = _("States treated as OK"),
                        choices = [
                            (1, 'redundant'),
                            (2, 'notRedundant'),
                            (3, 'notSupported'),
                        ],
                        default_value = [ 1 ],
                        )
                ),
        ],
        optional_keys = False,
    ),
    TextAscii(
        title = _("Number of Powersupply"),
    ),
    "dict"
)

hivemanger_states = [
 ( "Critical" , "Critical" ),
 ( "Maybe" , "Maybe" ),
 ( "Major" , "Major" ),
 ( "Minor" , "Minor" ),
]
register_check_parameters(
    subgroup_networking,
    "hivemanager_devices",
    _("Hivemanager Devices"),
    Dictionary(
        elements = [
            ( 'max_clients',
                Tuple(
                    title = _("Number of clients"),
                    help  = _("Number of clients connected to a Device."),
                          elements = [
                              Integer(title = _("Warning at"),  unit=_("clients")),
                              Integer(title = _("Critical at"), unit=_("clients")),
                          ]
                )),
            ( 'max_uptime',
                Tuple(
                    title = _("Maximum uptime of Device"),
                          elements = [
                              Age(title = _("Warning at")),
                              Age(title = _("Critical at")),
                          ]
                )),
            ( 'alert_on_loss',
                FixedValue(
                  False,
                  totext = "",
                  title = _("Do not alert on connection loss"),
                )),
                ( "warn_states",
                    ListChoice(
                        title = _("States treated as warning"),
                        choices = hivemanger_states,
                        default_value = ['Maybe', 'Major', 'Minor'],
                        )
                ),
                ( "crit_states",
                    ListChoice(
                        title = _("States treated as critical"),
                        choices = hivemanger_states,
                        default_value = ['Critical'],
                        )
                ),
        ]),
    TextAscii(
       title = _("Hostname of the Device")
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_networking,
    "hivemanager_ng_devices",
    _("HiveManager NG Devices"),
    Dictionary(
        elements = [
            ('max_clients',
             Tuple(
                title = _("Number of clients"),
                help  = _("Number of clients connected to a Device."),
                elements = [
                    Integer(title = _("Warning at"),  unit=_("clients")),
                    Integer(title = _("Critical at"), unit=_("clients")),
                ]
             )
            ),
        ]),
    TextAscii(
       title = _("Hostname of the Device")
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_networking,
    "wlc_clients",
    _("WLC WiFi client connections"),
    Transform(
        Dictionary(
            title = _("Number of connections"),
            elements = [
                ("levels",
                    Tuple(
                        title = _("Upper levels"),
                        elements = [
                            Integer(title = _("Warning at"),  unit=_("connections")),
                            Integer(title = _("Critical at"), unit=_("connections")),
                        ]
                )),
                ("levels_lower",
                    Tuple(
                        title = _("Lower levels"),
                        elements= [
                            Integer(title = _("Critical if below"), unit=_("connections")),
                            Integer(title = _("Warning if below"),  unit=_("connections")),
                        ]
                )),
            ]
        ),
        # old params = (crit_low, warn_low, warn, crit)
        forth = lambda v: type(v) == tuple and { "levels" : (v[2], v[3]), "levels_lower" : (v[1], v[0]) } or v,
    ),
    TextAscii( title = _("Name of Wifi")),
    "first"
)

register_check_parameters(
   subgroup_networking,
   "cisco_wlc",
   _("Cisco WLAN AP"),
   Dictionary(
       help = _("Here you can set which alert type is set when the given "
                "access point is missing (might be powered off). The access point "
                "can be specified by the AP name or the AP model"),
        elements = [
           ( "ap_name",
            ListOf(
                Tuple(
                    elements = [
                        TextAscii(title = _("AP name")),
                        MonitoringState( title=_("State when missing"), default_value = 2)
                    ]
                ),
                title = _("Access point name"),
            add_label = _("Add name"))
           )
        ]
    ),
   TextAscii(title = _("Access Point")),
   match_type = "dict",
)

register_check_parameters(
    subgroup_networking,
    "tcp_conn_stats",
    _("TCP connection statistics"),
    Dictionary(
        elements = [
            ( "ESTABLISHED",
              Tuple(
                  title = _("ESTABLISHED"),
                  help = _("connection up and passing data"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("connections")),
                      Integer(title = _("Critical at"), label = _("connections"))
                  ]
              )
            ),
            ( "SYN_SENT",
              Tuple(
                  title = _("SYN_SENT"),
                  help = _("session has been requested by us; waiting for reply from remote endpoint"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("connections")),
                      Integer(title = _("Critical at"), label = _("connections"))
                  ]
              )
            ),
            ( "SYN_RECV",
              Tuple(
                  title = _("SYN_RECV"),
                  help = _("session has been requested by a remote endpoint "
                           "for a socket on which we were listening"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("connections")),
                      Integer(title = _("Critical at"), label = _("connections"))
                  ]
              )
            ),
            ( "LAST_ACK",
              Tuple(
                  title = _("LAST_ACK"),
                  help = _("our socket is closed; remote endpoint has also shut down; "
                           " we are waiting for a final acknowledgement"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("connections")),
                      Integer(title = _("Critical at"), label = _("connections"))
                  ]
              )
            ),
            ( "CLOSE_WAIT",
              Tuple(
                  title = _("CLOSE_WAIT"),
                  help = _("remote endpoint has shut down; the kernel is waiting "
                           "for the application to close the socket"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("connections")),
                      Integer(title = _("Critical at"), label = _("connections"))
                  ]
              )
            ),
            ( "TIME_WAIT",
              Tuple(
                  title = _("TIME_WAIT"),
                  help = _("socket is waiting after closing for any packets left on the network"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("connections")),
                      Integer(title = _("Critical at"), label = _("connections"))
                  ]
              )
            ),
            ( "CLOSED",
              Tuple(
                  title = _("CLOSED"),
                  help = _("socket is not being used"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("connections")),
                      Integer(title = _("Critical at"), label = _("connections"))
                  ]
              )
            ),
            ( "CLOSING",
              Tuple(
                  title = _("CLOSING"),
                  help = _("our socket is shut down; remote endpoint is shut down; "
                           "not all data has been sent"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("connections")),
                      Integer(title = _("Critical at"), label = _("connections"))
                  ]
              )
            ),
            ( "FIN_WAIT1",
              Tuple(
                  title = _("FIN_WAIT1"),
                  help = _("our socket has closed; we are in the process of "
                           "tearing down the connection"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("connections")),
                      Integer(title = _("Critical at"), label = _("connections"))
                  ]
              )
            ),
            ( "FIN_WAIT2",
              Tuple(
                  title = _("FIN_WAIT2"),
                  help = _("the connection has been closed; our socket is waiting "
                           "for the remote endpoint to shutdown"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("connections")),
                      Integer(title = _("Critical at"), label = _("connections"))
                  ]
              )
            ),
            ( "LISTEN",
              Tuple(
                  title = _("LISTEN"),
                  help = _("represents waiting for a connection request from any remote TCP and port"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("connections")),
                      Integer(title = _("Critical at"), label = _("connections"))
                  ]
              )
            ),
            ( "BOUND",
              Tuple(
                  title = _("BOUND"),
                  help = _("the socket has been created and an address assigned "
                           "to with bind(). The TCP stack is not active yet. "
                           "This state is only reported on Solaris."),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("connections")),
                      Integer(title = _("Critical at"), label = _("connections"))
                  ]
              )
            ),
            ( "IDLE",
              Tuple(
                  title = _("IDLE"),
                  help = _("a TCP session that is active but that has no data being "
                           "transmitted by either device for a prolonged period of time"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("connections")),
                      Integer(title = _("Critical at"), label = _("connections"))
                  ]
              )
            ),
        ]
    ),
    None,
    match_type = "dict",
)


register_check_parameters(
    subgroup_networking,
    "tcp_connections",
    _("Monitor specific TCP/UDP connections and listeners"),
    Dictionary(
        help = _("This rule allows to monitor the existence of specific TCP connections or "
                 "TCP/UDP listeners."),
        elements = [
            ( "proto",
              DropdownChoice(
                  title = _("Protocol"),
                  choices = [ ("TCP", _("TCP")), ("UDP", _("UDP")) ],
                  default_value = "TCP",
              ),
            ),
            ( "state",
              DropdownChoice(
                  title = _("State"),
                  choices = [
                            ( "ESTABLISHED", "ESTABLISHED" ),
                            ( "LISTENING", "LISTENING" ),
                            ( "SYN_SENT", "SYN_SENT" ),
                            ( "SYN_RECV", "SYN_RECV" ),
                            ( "LAST_ACK", "LAST_ACK" ),
                            ( "CLOSE_WAIT", "CLOSE_WAIT" ),
                            ( "TIME_WAIT", "TIME_WAIT" ),
                            ( "CLOSED", "CLOSED" ),
                            ( "CLOSING", "CLOSING" ),
                            ( "FIN_WAIT1", "FIN_WAIT1" ),
                            ( "FIN_WAIT2", "FIN_WAIT2" ),
                            ( "BOUND", "BOUND" ),
                  ]
              ),
            ),
            ( "local_ip", IPv4Address(title = _("Local IP address"))),
            ( "local_port", Integer(title = _("Local port number"), minvalue = 1, maxvalue = 65535, )),
            ( "remote_ip", IPv4Address(title = _("Remote IP address"))),
            ( "remote_port", Integer(title = _("Remote port number"), minvalue = 1, maxvalue = 65535, )),
            ( "max_states",
               Tuple(
                   title = _("Maximum number of connections or listeners"),
                   elements = [
                       Integer(title = _("Warning at")),
                       Integer(title = _("Critical at")),
                    ],
               ),
            ),
            ( "min_states",
               Tuple(
                   title = _("Minimum number of connections or listeners"),
                   elements = [
                       Integer(title = _("Warning if below")),
                       Integer(title = _("Critical if below")),
                    ],
               ),
            ),
        ]
    ),
    TextAscii(title = _("Connection name"), help = _("Specify an arbitrary name of this connection here"), allow_empty = False),
    "dict",
    has_inventory = False,
)


register_check_parameters(
    subgroup_applications,
    'msx_info_store',
    _("MS Exchange Information Store"),
    Dictionary(
        title = _("Set Levels"),
        elements = [
            ('store_latency',
             Tuple(
                 title = _("Average latency for store requests"),
                 elements = [
                     Float(title = _("Warning at"),  unit = _('ms'), default_value = 40.0),
                     Float(title = _("Critical at"), unit = _('ms'), default_value = 50.0)
                 ]
             )
            ),
            ('clienttype_latency',
             Tuple(
                 title = _("Average latency for client type requests"),
                 elements = [
                     Float(title = _("Warning at"),  unit = _('ms'), default_value = 40.0),
                     Float(title = _("Critical at"), unit = _('ms'), default_value = 50.0)
                 ]
             )
            ),
            ('clienttype_requests',
             Tuple(
                 title = _("Maximum number of client type requests per second"),
                 elements = [
                     Integer(title = _("Warning at"),  unit = _('requests'), default_value = 60),
                     Integer(title = _("Critical at"), unit = _('requests'), default_value = 70)
                 ]
             )
             )
        ],
        optional_keys=[]
    ),
    TextAscii(title = _("Store"), help = _("Specify the name of a store (This is either a mailbox or public folder)")),
    match_type = 'dict'
)


register_check_parameters(
    subgroup_applications,
    'msx_rpcclientaccess',
    _("MS Exchange RPC Client Access"),
    Dictionary(
        title = _("Set Levels"),
        elements = [
            ('latency',
             Tuple(
                 title = _("Average latency for RPC requests"),
                 elements = [
                     Float(title = _("Warning at"),  unit = _('ms'), default_value = 200.0),
                     Float(title = _("Critical at"), unit = _('ms'), default_value = 250.0)
                 ]
             )
            ),
            ('requests',
             Tuple(
                 title = _("Maximum number of RPC requests per second"),
                 elements = [
                     Integer(title = _("Warning at"),  unit = _('requests'), default_value = 30),
                     Integer(title = _("Critical at"), unit = _('requests'), default_value = 40)
                 ]
             )
             )
        ],
        optional_keys=[]
    ),
    None,
    match_type = 'dict'
)


register_check_parameters(
    subgroup_applications,
    'msx_database',
    _("MS Exchange Database"),
    Dictionary(
        title = _("Set Levels"),
        elements = [
            ('read_attached_latency',
             Tuple(
                 title = _("I/O Database Reads (Attached) Average Latency"),
                 elements = [
                     Float(title = _("Warning at"),  unit = _('ms'), default_value = 200.0),
                     Float(title = _("Critical at"), unit = _('ms'), default_value = 250.0)
                 ]
             )
             ),
            ('read_recovery_latency',
             Tuple(
                 title = _("I/O Database Reads (Recovery) Average Latency"),
                 elements = [
                     Float(title = _("Warning at"),  unit = _('ms'), default_value = 150.0),
                     Float(title = _("Critical at"), unit = _('ms'), default_value = 200.0)
                 ]
             )
             ),
            ('write_latency',
             Tuple(
                 title = _("I/O Database Writes (Attached) Average Latency"),
                 elements = [
                     Float(title = _("Warning at"),  unit = _('ms'), default_value = 40.0),
                     Float(title = _("Critical at"), unit = _('ms'), default_value = 50.0)
                 ]
             )
             ),
            ('log_latency',
             Tuple(
                 title = _("I/O Log Writes Average Latency"),
                 elements = [
                     Float(title = _("Warning at"),  unit = _('ms'), default_value = 5.0),
                     Float(title = _("Critical at"), unit = _('ms'), default_value = 10.0)
                 ]
             )
             ),
        ],
        optional_keys=[]
    ),
    TextAscii(
        title = _("Database Name"),
        help = _("Specify database names that the rule should apply to"),
    ),
    match_type = 'dict'
)


def transform_msx_queues(params):
    if type(params) == tuple:
        return { "levels" : ( params[0], params[1] ) }
    return params


register_check_parameters(
    subgroup_applications,
    "msx_queues",
    _("MS Exchange Message Queues"),
         Transform(
              Dictionary(
                  title = _("Set Levels"),
                  elements = [
                     ( 'levels',
                            Tuple(
                                title = _("Maximum Number of E-Mails in Queue"),
                                elements = [
                                    Integer(title = _("Warning at"), unit = _("E-Mails")),
                                    Integer(title = _("Critical at"), unit = _("E-Mails"))
                                ]),
                     ),
                     ('offset',
                        Integer(
                            title = _("Offset"),
                            help = _("Use this only if you want to overwrite the postion of the information in the agent "
                                     "output. Also refer to the rule <i>Microsoft Exchange Queues Discovery</i> ")
                        )
                    ),
                  ],
                optional_keys = [ "offset" ],
              ),
              forth = transform_msx_queues,
         ),
    TextAscii(
        title = _("Explicit Queue Names"),
        help = _("Specify queue names that the rule should apply to"),
    ),
    "first"
)

register_check_parameters(
    subgroup_applications,
    "msexch_copyqueue",
    _("MS Exchange DAG CopyQueue"),
          Tuple(
              title = _("Upper Levels for CopyQueue Length"),
              help = _("This rule sets upper levels to the number of transaction logs waiting to be copied "
                       "and inspected on your Exchange Mailbox Servers in a Database Availability Group "
                       "(DAG). This is also known as the CopyQueue length."),
              elements = [
                  Integer(title = _("Warning at")),
                  Integer(title = _("Critical at"))
              ],
          ),
    TextAscii(
        title = _("Database Name"),
        help = _("The database name on the Mailbox Server."),
    ),
    "first"
)

def get_free_used_dynamic_valuespec(what, name, default_value = (80.0, 90.0)):
    if what == "used":
        title  = _("used space")
        course = _("above")
    else:
        title  = _("free space")
        course = _("below")


    vs_subgroup =  [
        Tuple( title = _("Percentage %s") % title,
            elements = [
                Percentage(title = _("Warning if %s") % course, unit = "%", minvalue = 0.0),
                Percentage(title = _("Critical if %s") % course, unit = "%", minvalue = 0.0),
            ]
        ),
        Tuple( title = _("Absolute %s") % title,
            elements = [
                Integer(title = _("Warning if %s") % course, unit = _("MB"), minvalue = 0),
                Integer(title = _("Critical if %s") % course, unit = _("MB"), minvalue = 0),
            ]
        )
    ]

    def validate_dynamic_levels(value, varprefix):
        if [ v for v in value if v[0] < 0 ]:
            raise MKUserError(varprefix, _("You need to specify levels "
                                           "of at least 0 bytes."))

    return Alternative(
        title = _("Levels for %s %s") % (name, title),
        style = "dropdown",
        show_alternative_title = True,
        default_value = default_value,
        elements = vs_subgroup + [
            ListOf(
                Tuple(
                    orientation = "horizontal",
                    elements = [
                        Filesize(title = _("%s larger than") % name.title()),
                        Alternative(
                            elements = vs_subgroup
                        )
                    ]
                ),
                title = _('Dynamic levels'),
                allow_empty = False,
                validate = validate_dynamic_levels,
            )],
        )


# Match and transform functions for level configurations like
# -- used absolute,        positive int   (2, 4)
# -- used percentage,      positive float (2.0, 4.0)
# -- available absolute,   negative int   (-2, -4)
# -- available percentage, negative float (-2.0, -4.0)
# (4 alternatives)
def match_dual_level_type(value):
    if type(value) == list:
        for entry in value:
            if entry[1][0] < 0 or entry[1][1] < 0:
                return 1
        else:
            return 0
    else:
        if value[0] < 0 or value[1] < 0:
            return 1
        else:
            return 0

def transform_filesystem_free(value):
    tuple_convert = lambda val: tuple(map(lambda x: -x, val))

    if type(value) == tuple:
        return tuple_convert(value)
    else:
        result = []
        for item in value:
            result.append((item[0], tuple_convert(item[1])))
        return result

fs_inodes_elements = [
    ( "inodes_levels",
        Alternative(
            title = _("Levels for Inodes"),
            help  = _("The number of remaining inodes on the filesystem. "
                      "Please note that this setting has no effect on some filesystem checks."),
            elements = [
                    Tuple(title = _("Percentage free"),
                          elements = [
                               Percentage(title = _("Warning if less than")),
                               Percentage(title = _("Critical if less than")),
                          ]
                    ),
                    Tuple(title = _("Absolute free"),
                          elements = [
                               Integer(title = _("Warning if less than"),  size = 10, unit = _("inodes"), minvalue = 0, default_value = 10000),
                               Integer(title = _("Critical if less than"), size = 10, unit = _("inodes"), minvalue = 0, default_value = 5000),
                          ]
                    )
            ],
            default_value = (10.0, 5.0),
        )
    ),
    ( "show_inodes",
      DropdownChoice(
          title = _("Display inode usage in check output..."),
          choices = [
            ( "onproblem", _("Only in case of a problem")),
            ( "onlow",     _("Only in case of a problem or if inodes are below 50%")),
            ( "always",    _("Always")),
          ],
          default_value = "onlow",
    ))
]

fs_magic_elements = [
    (  "magic",
       Float(
          title = _("Magic factor (automatic level adaptation for large filesystems)"),
          default_value = 0.8,
          minvalue = 0.1,
          maxvalue = 1.0)),
    (  "magic_normsize",
       Integer(
           title = _("Reference size for magic factor"),
           default_value = 20,
           minvalue = 1,
           unit = _("GB"))),
    ( "levels_low",
      Tuple(
          title = _("Minimum levels if using magic factor"),
          help = _("The filesystem levels will never fall below these values, when using "
                   "the magic factor and the filesystem is very small."),
          elements = [
              Percentage(title = _("Warning at"),  unit = _("% usage"), allow_int = True, default_value=50),
              Percentage(title = _("Critical at"), unit = _("% usage"), allow_int = True, default_value=60)]))
]

size_trend_elements = [
    (  "trend_range",
       Optional(
           Integer(
               title = _("Time Range for trend computation"),
               default_value = 24,
               minvalue = 1,
               unit= _("hours")),
           title = _("Trend computation"),
           label = _("Enable trend computation"))),
    (  "trend_mb",
       Tuple(
           title = _("Levels on trends in MB per time range"),
           elements = [
               Integer(title = _("Warning at"), unit = _("MB / range"), default_value = 100),
               Integer(title = _("Critical at"), unit = _("MB / range"), default_value = 200)
           ])),
    (  "trend_perc",
       Tuple(
           title = _("Levels for the percentual growth per time range"),
           elements = [
               Percentage(title = _("Warning at"), unit = _("% / range"), default_value = 5,),
               Percentage(title = _("Critical at"), unit = _("% / range"), default_value = 10,),
           ])),
    (  "trend_timeleft",
       Tuple(
           title = _("Levels on the time left until full"),
           elements = [
               Integer(title = _("Warning if below"), unit = _("hours"), default_value = 12,),
               Integer(title = _("Critical if below"), unit = _("hours"), default_value = 6, ),
            ])),
    ( "trend_showtimeleft",
            Checkbox( title = _("Display time left in check output"), label = _("Enable"),
                       help = _("Normally, the time left until the disk is full is only displayed when "
                                "the configured levels have been breached. If you set this option "
                                "the check always reports this information"))
    ),
    ( "trend_perfdata",
      Checkbox(
          title = _("Trend performance data"),
          label = _("Enable generation of performance data from trends"))),
]

# Note: This hack is only required on very old filesystem checks (prior August 2013)
fs_levels_elements_hack = [
    # Beware: this is a nasty hack that helps us to detect new-style parameters.
    # Something hat has todo with float/int conversion and has not been documented
    # by the one who implemented this.
    ( "flex_levels",
      FixedValue(
          None,
          totext = "",
          title = "",
          )),
]

fs_levels_elements = [
    ("levels",
        Alternative(
            title = _("Levels for filesystem"),
            show_alternative_title = True,
            default_value = (80.0, 90.0),
            match = match_dual_level_type,
            elements = [
                   get_free_used_dynamic_valuespec("used", "filesystem"),
                   Transform(
                            get_free_used_dynamic_valuespec("free", "filesystem", default_value = (20.0, 10.0)),
                            title = _("Levels for filesystem free space"),
                            allow_empty = False,
                            forth = transform_filesystem_free,
                            back  = transform_filesystem_free
                    )
                ]
                )
    ),
    ( "show_levels",
      DropdownChoice(
          title = _("Display warn/crit levels in check output..."),
          choices = [
            ( "onproblem", _("Only if the status is non-OK")),
            ( "onmagic",   _("If the status is non-OK or a magic factor is set")),
            ( "always",    _("Always") ),
          ],
          default_value = "onmagic",
    ))]

fs_reserved_elements = [
    ( "show_reserved",
      DropdownChoice(
          title = _("Show space reserved for the <tt>root</tt> user"),
          help = _("Check_MK treats space that is reserved for the <tt>root</tt> user on Linux and Unix as "
                   "used space. Usually, 5% are being reserved for root when a new filesystem is being created. "
                   "With this option you can have Check_MK display the current amount of reserved but yet unused "
                   "space."),
          choices = [
            ( True, _("Show reserved space") ),
            ( False, _("Do now show reserved space") ),
         ]
    ))
]

filesystem_elements = fs_levels_elements + fs_levels_elements_hack + fs_reserved_elements +\
                      fs_inodes_elements + fs_magic_elements + size_trend_elements

register_check_parameters(
    subgroup_storage,
    "filesystem",
    _("Filesystems (used space and growth)"),
    Dictionary(
        help=_("This ruleset allows to set parameters for space and inodes usage"),
        elements = filesystem_elements,
        hidden_keys = ["flex_levels"],
        ignored_keys = ["patterns"],
    ),
    TextAscii(
        title = _("Mount point"),
        help = _("For Linux/UNIX systems, specify the mount point, for Windows systems "
                 "the drive letter uppercase followed by a colon and a slash, e.g. <tt>C:/</tt>"),
        allow_empty = False),
    "dict"
)

register_check_parameters(
    subgroup_storage,
    "mongodb_collections",
    _("MongoDB Collection Size"),
    Dictionary(
        elements = fs_levels_elements + size_trend_elements
    ),
    TextAscii(
        title = _("Collection name"),
    ),
    "dict"
)

register_check_parameters(
    subgroup_storage,
    "volume_groups",
    _("Volume Groups (LVM)"),
    Dictionary(
        elements = [
             ("levels",
            Alternative(
                title = _("Levels for volume group"),
                show_alternative_title = True,
                default_value = (80.0, 90.0),
                match = match_dual_level_type,
                elements = [
                    get_free_used_dynamic_valuespec("used", "volume group"),
                    Transform(
                             get_free_used_dynamic_valuespec("free", "volume group", default_value = (20.0, 10.0)),
                             title = _("Levels for volume group free space"),
                             allow_empty = False,
                             forth = transform_filesystem_free,
                             back  = transform_filesystem_free
                    )
                 ]
            )),
       ],
    optional_keys = False
    ),
    TextAscii(
        title = _("Volume Group"),
        allow_empty = False),
    "dict"
)

register_check_parameters(
    subgroup_storage,
    "ibm_svc_mdiskgrp",
    _("IBM SVC Pool Capacity"),
    Dictionary(
        elements = filesystem_elements + [
            ( "provisioning_levels", Tuple(
                title = _("Provisioning Levels"),
                help = _("A provisioning of over 100% means over provisioning."),
                elements = [
                    Percentage(title = _("Warning at a provisioning of"), default_value = 110.0, maxvalue = None),
                    Percentage(title = _("Critical at a provisioning of"), default_value = 120.0, maxvalue = None),
                ]
            )),
        ],
        hidden_keys = ["flex_levels"],
    ),
    TextAscii(
        title = _("Name of the pool"),
        allow_empty = False
    ),
    "dict"
)

register_check_parameters(
    subgroup_os,
    "sp_util",
    _("Storage Processor Utilization"),
    Tuple(
        title = _("Specify levels in percentage of storage processor usage"),
        elements = [
            Percentage(title = _("Warning at"), default_value = 50.0),
            Percentage(title = _("Critical at"), default_value = 60.0),
        ]
    ),
    None,
    "first",
)

register_check_parameters(
    subgroup_storage,
    "esx_vsphere_datastores",
    _("ESX Datastores (used space and growth)"),
    Dictionary(
        elements = filesystem_elements + [
            ("provisioning_levels", Tuple(
                title = _("Provisioning Levels"),
                help = _("A provisioning of more than 100% is called "
                         "over provisioning and can be a useful strategy for saving disk space. But you cannot guarantee "
                         "any longer that every VM can really use all space that it was assigned. Here you can "
                         "set levels for the maximum provisioning. A warning level of 150% will warn at 50% over provisioning."),
                elements = [
                  Percentage(title = _("Warning at a provisioning of"), maxvalue = None, default_value = 120.0),
                  Percentage(title = _("Critical at a provisioning of"), maxvalue = None, default_value = 150.0),
                ]
            )),
        ],
        hidden_keys = ["flex_levels"],
    ),
    TextAscii(
        title = _("Datastore Name"),
        help = _("The name of the Datastore"),
        allow_empty = False
    ),
    "dict"
)

register_check_parameters(
    subgroup_storage,
    "esx_hostystem_maintenance",
    _("ESX Hostsystem Maintenance Mode"),
    Dictionary(
        elements = [
            ("target_state", DropdownChoice(
                title = _("Target State"),
                help = _("Configure the target mode for the system."),
                choices = [
                 ('true', "System should be in Maintenance Mode"),
                 ('false', "System not should be in Maintenance Mode"),
                ]
            )),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_networking,
    "bonding",
    _("Status of Linux bonding interfaces"),
    Dictionary(
        elements = [
            ( "expect_active",
              DropdownChoice(
                  title = _("Warn on unexpected active interface"),
                  choices = [
                     ( "ignore",   _("ignore which one is active") ),
                     ( "primary", _("require primary interface to be active") ),
                     ( "lowest",   _("require interface that sorts lowest alphabetically") ),
                  ]
              )
            ),
        ]
    ),
    TextAscii(
        title = _("Name of the bonding interface"),
    ),
    "dict"
)

def vs_interface_traffic():
    def vs_abs_perc():
        return CascadingDropdown(
            orientation = "horizontal",
            choices = [
                ("perc", _("Percentual levels (in relation to port speed)"), Tuple(
                    orientation = "float",
                    show_titles = False,
                    elements = [
                        Percentage(label = _("Warning at")),
                        Percentage(label = _("Critical at")),
                    ]
                )),
                ("abs", _("Absolute levels in bits or bytes per second"), Tuple(
                    orientation = "float",
                    show_titles = False,
                    elements = [
                        Integer(label = _("Warning at")),
                        Integer(label = _("Critical at")),
                    ]
                )),
                ("predictive", _("Predictive Levels (only on CMC)"), PredictiveLevels())
            ]
        )

    return CascadingDropdown(
        orientation = "horizontal",
        choices = [
            ("upper", _("Upper"), vs_abs_perc()),
            ("lower", _("Lower"), vs_abs_perc()),
        ]
    )

def transform_if(v):
    new_traffic = []

    if 'traffic' in v and type(v['traffic']) != list:
        warn, crit = v['traffic']
        if type(warn) == int:
            new_traffic.append(('both', ('upper', ('abs', (warn, crit)))))
        elif type(warn) == float:
            new_traffic.append(('both', ('upper', ('perc', (warn, crit)))))

    if 'traffic_minimum' in v:
        warn, crit = v['traffic_minimum']
        if type(warn) == int:
            new_traffic.append(('both', ('lower', ('abs', (warn, crit)))))
        elif type(warn) == float:
            new_traffic.append(('both', ('lower', ('perc', (warn, crit)))))
        del v['traffic_minimum']

    if new_traffic:
        v['traffic'] = new_traffic

    return v

register_check_parameters(
    subgroup_networking,
    "if",
    _("Network interfaces and switch ports"),
    # Transform old traffic related levels which used "traffic" and "traffic_minimum"
    # keys where each was configured with an Alternative valuespec
    Transform(Dictionary(
        ignored_keys = [ "aggregate" ], # Created by discovery when using interface grouping
        elements = [
             ( "errors",
               Alternative(
                  title = _("Levels for error rates"),
                  help = _("These levels make the check go warning or critical whenever the "
                           "<b>percentual error rate</b> or the <b>absolute error rate</b> of the monitored interface reaches "
                           "the given bounds. The percentual error rate is computed by dividing number of "
                           "errors by the total number of packets (successful plus errors)."),
                  elements = [
                      Tuple(
                          title = _("Percentual levels for error rates"),
                          elements = [
                              Percentage(title = _("Warning at"), unit = _("percent errors"), default_value = 0.01, display_format = '%.3f' ),
                              Percentage(title = _("Critical at"), unit = _("percent errors"), default_value = 0.1, display_format = '%.3f' )
                          ]
                      ),
                      Tuple(
                          title = _("Absolute levels for error rates"),
                          elements = [
                              Integer(title = _("Warning at"), unit= _("errors") ),
                              Integer(title = _("Critical at"), unit = _("errors") )
                          ]
                      )
                    ]
                )
             ),
             ( "speed",
               OptionalDropdownChoice(
                   title = _("Operating speed"),
                   help = _("If you use this parameter then the check goes warning if the "
                            "interface is not operating at the expected speed (e.g. it "
                            "is working with 100Mbit/s instead of 1Gbit/s.<b>Note:</b> "
                            "some interfaces do not provide speed information. In such cases "
                            "this setting is used as the assumed speed when it comes to "
                            "traffic monitoring (see below)."),
                  choices = [
                     ( None,       _("ignore speed") ),
                     ( 10000000,    "10 Mbit/s" ),
                     ( 100000000,   "100 Mbit/s" ),
                     ( 1000000000,  "1 Gbit/s" ),
                     ( 10000000000, "10 Gbit/s" ) ],
                  otherlabel = _("specify manually ->"),
                  explicit = \
                      Integer(title = _("Other speed in bits per second"),
                              label = _("Bits per second")))
             ),
             ( "state",
                Optional(
                    ListChoice(
                        title = _("Allowed states:"),
                        choices = defines.interface_oper_states()),
                    title = _("Operational state"),
                    help = _("If you activate the monitoring of the operational state (<tt>ifOperStatus</tt>) "
                             "the check will get warning or critical if the current state "
                             "of the interface does not match one of the expected states. Note: the status 9 (<i>admin down</i>) "
                             "is only visible if you activate this status during switch port inventory or if you manually "
                             "use the check plugin <tt>if64adm</tt> instead of <tt>if64</tt>."),
                    label = _("Ignore the operational state"),
                    none_label = _("ignore"),
                    negate = True)
             ),
             ( "map_operstates",
                ListOf(
                    Tuple(
                        orientation = "horizontal",
                        elements = [
                            DropdownChoice(choices = defines.interface_oper_states()),
                            MonitoringState()
                        ]),
                    title = _('Map operational states'),
                )
             ),
             ( "assumed_speed_in",
               OptionalDropdownChoice(
                        title = _("Assumed input speed"),
                        help = _("If the automatic detection of the link speed does not work "
                                 "or the switch's capabilities are throttled because of the network setup "
                                 "you can set the assumed speed here."),
                  choices = [
                     ( None,       _("ignore speed") ),
                     ( 10000000,    "10 Mbit/s" ),
                     ( 100000000,   "100 Mbit/s" ),
                     ( 1000000000,  "1 Gbit/s" ),
                     ( 10000000000, "10 Gbit/s" ) ],
                  otherlabel = _("specify manually ->"),
                  default_value = 16000000,
                  explicit = \
                      Integer(title = _("Other speed in bits per second"),
                              label = _("Bits per second"),
                              size = 10))
             ),
             ( "assumed_speed_out",
               OptionalDropdownChoice(
                        title = _("Assumed output speed"),
                        help = _("If the automatic detection of the link speed does not work "
                                 "or the switch's capabilities are throttled because of the network setup "
                                 "you can set the assumed speed here."),
                  choices = [
                     ( None,       _("ignore speed") ),
                     ( 10000000,    "10 Mbit/s" ),
                     ( 100000000,   "100 Mbit/s" ),
                     ( 1000000000,  "1 Gbit/s" ),
                     ( 10000000000, "10 Gbit/s" ) ],
                  otherlabel = _("specify manually ->"),
                  default_value = 1500000,
                  explicit = \
                      Integer(title = _("Other speed in bits per second"),
                              label = _("Bits per second"),
                              size = 12))
             ),
             ( "unit",
               RadioChoice(
                   title = _("Measurement unit"),
                   help = _("Here you can specifiy the measurement unit of the network interface"),
                   default_value = "byte",
                   choices = [
                       ( "bit",  _("Bits") ),
                       ( "byte", _("Bytes") ),],
               )),
              ( "infotext_format",
                   DropdownChoice(
                        title = _("Change infotext in check output"),
                        help = _("This setting allows you to modify the information text which is displayed between "
                                 "the two brackets in the check output. Please note that this setting does not work for "
                                 "grouped interfaces, since the additional information of grouped interfaces is different"),
                        choices = [
                            ("alias",                 _("Show alias")),
                            ("description",           _("Show description")),
                            ("alias_and_description", _("Show alias and description")),
                            ("alias_or_description",  _("Show alias if set, else description")),
                            ("desription_or_alias",   _("Show description if set, else alias")),
                            ("hide",                  _("Hide infotext")),
                        ]
                   )
              ),
              ( "traffic",
                ListOf(CascadingDropdown(
                        title = _("Direction"),
                        orientation = "horizontal",
                        choices = [
                            ('both', _("In / Out"), vs_interface_traffic()),
                            ('in',   _("In"),       vs_interface_traffic()),
                            ('out',  _("Out"),      vs_interface_traffic()),
                        ]
                    ),
                    title = _("Used bandwidth (minimum or maximum traffic)"),
                    help = _("Setting levels on the used bandwidth is optional. If you do set "
                             "levels you might also consider using averaging."),
                )
              ),
             ( "nucasts",
                   Tuple(
                       title = _("Non-unicast packet rates"),
                       help = _("Setting levels on non-unicast packet rates is optional. This may help "
                            "to detect broadcast storms and other unwanted traffic."),
                       elements = [
                           Integer(title = _("Warning at"), unit = _("pkts / sec")),
                           Integer(title = _("Critical at"), unit = _("pkts / sec")),
                       ]
                   ),
             ),
             ( "discards",
               Tuple(
                   title = _("Absolute levels for discards rates"),
                   elements = [
                       Integer(title = _("Warning at"), unit= _("discards") ),
                       Integer(title = _("Critical at"), unit = _("discards") )
                   ]
               )
             ),
             ( "average",
                 Integer(
                     title = _("Average values"),
                     help = _("By activating the computation of averages, the levels on "
                              "errors and traffic are applied to the averaged value. That "
                              "way you can make the check react only on long-time changes, "
                              "not on one-minute events."),
                     unit = _("minutes"),
                     minvalue = 1,
                     default_value = 15,
                 )
             ),

         ]),
        forth = transform_if,
    ),
    TextAscii(
        title = _("port specification"),
        allow_empty = False),
    "dict",
)

register_check_parameters(
    subgroup_networking,
    "k8s_if",
    _("Kubernetes Network interfaces"),
    Dictionary(elements=[
        ("errors",
         Alternative(
             title=_("Levels for error rates"),
             help=
             _("These levels make the check go warning or critical whenever the "
               "<b>percentual error rate</b> or the <b>absolute error rate</b> of the monitored interface reaches "
               "the given bounds. The percentual error rate is computed by dividing number of "
               "errors by the total number of packets (successful plus errors)."),
             elements=[
                 Tuple(
                     title=_("Percentual levels for error rates"),
                     elements=[
                         Percentage(
                             title=_("Warning at"),
                             unit=_("percent errors"),
                             default_value=0.01,
                             display_format='%.3f'),
                         Percentage(
                             title=_("Critical at"),
                             unit=_("percent errors"),
                             default_value=0.1,
                             display_format='%.3f')
                     ]),
                 Tuple(
                     title=_("Absolute levels for error rates"),
                     elements=[
                         Integer(title=_("Warning at"), unit=_("errors")),
                         Integer(title=_("Critical at"), unit=_("errors"))
                     ])
             ])),
        ("discards",
         Tuple(
             title=_("Absolute levels for discards rates"),
             elements=[
                 Integer(title=_("Warning at"), unit=_("discards")),
                 Integer(title=_("Critical at"), unit=_("discards"))
             ])),
    ]),
    TextAscii(title=_("port specification"), allow_empty=False),
    "dict",
)

register_check_parameters(
    subgroup_networking,
    "fcp",
    _("Fibrechannel Interfaces"),
    Dictionary(
        elements = [
            ( "speed",
              OptionalDropdownChoice(
                  title = _("Operating speed"),
                  help = _("If you use this parameter then the check goes warning if the "
                           "interface is not operating at the expected speed (e.g. it "
                           "is working with 8Gbit/s instead of 16Gbit/s)."),
                 choices = [
                    ( None,       _("ignore speed") ),
                    ( 4000000000,   "4 Gbit/s" ),
                    ( 8000000000,   "8 Gbit/s" ),
                    ( 16000000000,  "16 Gbit/s" ) ],
                 otherlabel = _("specify manually ->"),
                 explicit = \
                     Integer(title = _("Other speed in bits per second"),
                             label = _("Bits per second")))
            ),
            ( "traffic",
              ListOf(CascadingDropdown(
                      title = _("Direction"),
                      orientation = "horizontal",
                      choices = [
                          ('both', _("In / Out"), vs_interface_traffic()),
                          ('in',   _("In"),       vs_interface_traffic()),
                          ('out',  _("Out"),      vs_interface_traffic()),
                      ]
                  ),
                  title = _("Used bandwidth (minimum or maximum traffic)"),
                  help = _("Setting levels on the used bandwidth is optional. If you do set "
                           "levels you might also consider using averaging."),
              )
            ),
            ( "read_latency",
              Levels(
                  title = _("Read latency"),
                  unit = _("ms"),
                  default_value = None,
                  default_levels = (50.0, 100.0))),
            ( "write_latency",
              Levels(
                  title = _("Write latency"),
                  unit = _("ms"),
                  default_value = None,
                  default_levels = (50.0, 100.0))),
            ( "latency",
              Levels(
                  title = _("Overall latency"),
                  unit = _("ms"),
                  default_value = None,
                  default_levels = (50.0, 100.0))),
        ]
    ),
    TextAscii(
        title = _("Port specification"),
        allow_empty = False),
    "dict",
)


register_check_parameters(
    subgroup_networking,
    "signal_quality",
    _("Signal quality of Wireless device"),
    Tuple(
        elements=[
            Percentage(title = _("Warning if under"), maxvalue=100 ),
            Percentage(title = _("Critical if under"), maxvalue=100 ),
    ]),
    TextAscii(
        title = _("Network specification"),
        allow_empty = True),
    "first",
)


register_check_parameters(
    subgroup_networking,
    "cisco_ip_sla",
    _("Cisco IP SLA"),
    Dictionary(
        elements = [
            ("rtt_type",
             DropdownChoice(
                 title = _("RTT type"),
                 choices = [
                     ( 'echo',  _("echo")),
                     ( 'path echo', _("path echo")),
                     ( 'file IO',  _("file IO")),
                     ( 'UDP echo',  _("UDP echo")),
                     ( 'TCP connect',  _("TCP connect")),
                     ( 'HTTP',  _("HTTP")),
                     ( 'DNS',  _("DNS")),
                     ( 'jitter',  _("jitter")),
                     ( 'DLSw',  _("DLSw")),
                     ( 'DHCP',  _("DHCP")),
                     ( 'FTP',  _("FTP")),
                     ( 'VoIP',  _("VoIP")),
                     ( 'RTP',  _("RTP")),
                     ( 'LSP group',  _("LSP group")),
                     ( 'ICMP jitter',  _("ICMP jitter")),
                     ( 'LSP ping',  _("LSP ping")),
                     ( 'LSP trace',  _("LSP trace")),
                     ( 'ethernet ping',  _("ethernet ping")),
                     ( 'ethernet jitter',  _("ethernet jitter")),
                     ( 'LSP ping pseudowire',  _("LSP ping pseudowire")),
                 ],
                 default_value = "echo",
            )),
            ("threshold",
             Integer(
                 title = _("Treshold"),
                 help = _("Depending on the precision the unit can be "
                          "either milliseconds or micoseconds."),
                 unit = _("ms/us"),
                 minvalue = 1,
                 default_value = 5000,
            )),
            ("state",
             DropdownChoice(
                 title = _("State"),
                 choices = [
                     ( 'active',  _("active")),
                     ( 'inactive',  _("inactive")),
                     ( 'reset',  _("reset")),
                     ( 'orderly stop',  _("orderly stop")),
                     ( 'immediate stop',  _("immediate stop")),
                     ( 'pending',  _("pending")),
                     ( 'restart',  _("restart")),
                 ],
                 default_value = "active",
            )),
            ("connection_lost_occured",
             DropdownChoice(
                 title = _("Connection lost occured"),
                 choices = [
                     ( "yes",  _("yes")),
                     ( "no", _("no")),
                 ],
                 default_value = "no",
            )),
            ("timeout_occured",
             DropdownChoice(
                 title = _("Timeout occured"),
                 choices = [
                     ( "yes",  _("yes")),
                     ( "no", _("no")),
                 ],
                 default_value = "no",
            )),
            ("completion_time_over_treshold_occured",
             DropdownChoice(
                 title = _("Completion time over treshold occured"),
                 choices = [
                     ( "yes",  _("yes")),
                     ( "no", _("no")),
                 ],
                 default_value = "no",
            )),
            ("latest_rtt_completion_time",
                 Tuple(
                     title = _("Latest RTT completion time"),
                     help = _("Depending on the precision the unit can be "
                              "either milliseconds or micoseconds."),
                     elements = [
                         Integer(
                             title = _("Warning at"),
                             unit = _("ms/us"),
                             minvalue=1,
                             default_value = 100,
                         ),
                         Integer(
                             title = _("Critical at"),
                             unit = _("ms/us"),
                             minvalue=1,
                             default_value = 200,
                         ),
                     ]
            )),
            ("latest_rtt_state",
             DropdownChoice(
                 title = _("Latest RTT state"),
                 choices = [
                     ( 'ok',  _("OK")),
                     ( 'disconnected',  _("disconnected")),
                     ( 'over treshold',  _("over treshold")),
                     ( 'timeout',  _("timeout")),
                     ( 'other',  _("other")),
                 ],
                 default_value = "ok",
            )),
        ]
    ),
    TextAscii(
        title = _("RTT row index of the service"),
        allow_empty = True,
    ),
    "dict",
)


register_check_parameters(
    subgroup_networking,
    "cisco_qos",
    _("Cisco quality of service"),
    Dictionary(
        elements = [
             ( "unit",
               RadioChoice(
                   title = _("Measurement unit"),
                   help = _("Here you can specifiy the measurement unit of the network interface"),
                   default_value = "bit",
                   choices = [
                       ( "bit",  _("Bits") ),
                       ( "byte", _("Bytes") ),],
               )),
             ( "post",
               Alternative(
                   title = _("Used bandwidth (traffic)"),
                   help = _("Settings levels on the used bandwidth is optional. If you do set "
                            "levels you might also consider using averaging."),
                   elements = [
                       Tuple(
                           title = _("Percentual levels (in relation to policy speed)"),
                           elements = [
                               Percentage(title = _("Warning at"), maxvalue=1000, label = _("% of port speed")),
                               Percentage(title = _("Critical at"), maxvalue=1000, label = _("% of port speed")),
                           ]
                       ),
                       Tuple(
                           title = _("Absolute levels in bits or bytes per second"),
                           help = _("Depending on the measurement unit (defaults to bit) the absolute levels are set in bit or byte"),
                           elements = [
                               Integer(title = _("Warning at"), size = 10, label = _("bits / bytes per second")),
                               Integer(title = _("Critical at"), size = 10, label = _("bits / bytes per second")),
                           ]
                        )
                   ])
               ),
               ( "average",
                 Integer(
                     title = _("Average values"),
                     help = _("By activating the computation of averages, the levels on "
                              "errors and traffic are applied to the averaged value. That "
                              "way you can make the check react only on long-time changes, "
                              "not on one-minute events."),
                     unit = _("minutes"),
                     minvalue = 1,
                 )
               ),
               ( "drop",
                 Alternative(
                     title = _("Number of dropped bits or bytes per second"),
                     help = _("Depending on the measurement unit (defaults to bit) you can set the warn and crit "
                              "levels for the number of dropped bits or bytes"),
                     elements = [
                         Tuple(
                             title = _("Percentual levels (in relation to policy speed)"),
                             elements = [
                                 Percentage(title = _("Warning at"), maxvalue=1000, label = _("% of port speed")),
                                 Percentage(title = _("Critical at"), maxvalue=1000, label = _("% of port speed")),
                             ]
                         ),
                         Tuple(
                             elements = [
                                 Integer(title = _("Warning at"), size = 8, label = _("bits / bytes per second")),
                                 Integer(title = _("Critical at"), size = 8, label = _("bits / bytes per second")),
                             ]
                          )
                     ])
               ),
           ]),
    TextAscii(
        title = _("port specification"),
        allow_empty = False),
    "dict",
)

register_check_parameters(
    subgroup_os,
    "innovaphone_mem",
    _("Innovaphone Memory Usage"),
    Tuple(
       title = _("Specify levels in percentage of total RAM"),
       elements = [
          Percentage(title = _("Warning at a usage of"), unit = _("% of RAM") ),
          Percentage(title = _("Critical at a usage of"), unit = _("% of RAM") ),
       ]
    ),
    None,
    "first"
)

register_check_parameters(
    subgroup_os,
    "mem_pages",
    _("Memory Pages Statistics"),
    Dictionary(
        elements = [
            ("pages_per_second",
                Tuple(
                   title = _("Pages per second"),
                   elements = [
                      Integer(title = _("Warning at"), unit = _("pages/s") ),
                      Integer(title = _("Critical at"), unit = _("pages/s") ),
                   ]
                ),
            )
        ]
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_os,
    "statgrab_mem",
    _("Statgrab Memory Usage"),
    Alternative(
        elements = [
            Tuple(
                title = _("Specify levels in percentage of total RAM"),
                elements = [
                  Percentage(title = _("Warning at a usage of"), unit = _("% of RAM"), maxvalue = None),
                  Percentage(title = _("Critical at a usage of"), unit = _("% of RAM"), maxvalue = None)
                ]
            ),
            Tuple(
                title = _("Specify levels in absolute usage values"),
                elements = [
                  Integer(title = _("Warning at"), unit = _("MB")),
                  Integer(title = _("Critical at"), unit = _("MB"))
                ]
            ),
        ]
    ),
    None,
    "first",
    deprecated=True,
)

register_check_parameters(
    subgroup_os,
    "cisco_mem",
    _("Cisco Memory Usage"),
    Transform(
        Dictionary(
            elements = [
                ("levels",
                 Alternative(
                     title = _("Levels for memory usage"),
                     elements = [
                         Tuple(
                             title = _("Specify levels in percentage of total RAM"),
                             elements = [
                             Percentage(title = _("Warning at a usage of"), unit = _("% of RAM"), maxvalue = None),
                             Percentage(title = _("Critical at a usage of"), unit = _("% of RAM"), maxvalue = None)
                             ]
                         ),
                         Tuple(
                             title = _("Specify levels in absolute usage values"),
                             elements = [
                             Integer(title = _("Warning at"), unit = _("MB")),
                             Integer(title = _("Critical at"), unit = _("MB"))
                             ]
                         ),
                     ]
                )),
            ] + size_trend_elements
        ),
        forth = lambda spec: spec if type(spec) == dict else {"levels": spec},
    ),
    TextAscii(
        title = _("Memory Pool Name"),
        allow_empty = False
    ),
    match_type = "first",
)

register_check_parameters(
    subgroup_os,
    "juniper_mem",
    _("Juniper Memory Usage"),
    Tuple(
        title = _("Specify levels in percentage of total memory usage"),
        elements = [
            Percentage(title = _("Warning at a usage of"), unit =_("% of RAM"), default_value = 80.0, maxvalue = 100.0 ),
            Percentage(title = _("Critical at a usage of"), unit =_("% of RAM"), default_value = 90.0, maxvalue = 100.0 )
        ]
    ),
    None,
    "first"
)

# TODO: Remove situations where a rule is used once with and once without items
register_check_parameters(
    subgroup_os,
    "juniper_mem_modules",
    _("Juniper Modules Memory Usage"),
    Tuple(
        title = _("Specify levels in percentage of total memory usage"),
        elements = [
            Percentage(title = _("Warning at a usage of"), unit =_("% of RAM"), default_value = 80.0, maxvalue = 100.0 ),
            Percentage(title = _("Critical at a usage of"), unit =_("% of RAM"), default_value = 90.0, maxvalue = 100.0 )
        ]
    ),
    TextAscii(
        title = _("Module Name"),
        help = _("The identificator of the module."),
    ),
    "first",
)

register_check_parameters(
    subgroup_os,
    "juniper_cpu_util",
    _("Juniper Processor Utilization of Routing Engine"),
    Transform(
        Dictionary(
            help = _("CPU utilization of routing engine."),
            optional_keys = [],
            elements = [
                ("levels",
                    Tuple(
                        title = _("Specify levels in percentage of processor routing engine usage"),
                        elements = [
                            Percentage(title = _("Warning at"), default_value = 80.0),
                            Percentage(title = _("Critical at"), default_value = 90.0),
                        ],
                    ),
                ),
            ]
        ),
        forth = lambda old: not old and { 'levels': (80.0, 90.0) } or old,
    ),
    TextAscii(
        title = _("Routing Engine"),
    ),
    "dict",
)

register_check_parameters(
    subgroup_os,
    "netscaler_mem",
    _("Netscaler Memory Usage"),
    Tuple(
        title = _("Specify levels in percentage of total memory usage"),
        elements = [
            Percentage(title = _("Warning at a usage of"), unit =_("% of RAM"), default_value = 80.0, maxvalue = 100.0 ),
            Percentage(title = _("Critical at a usage of"), unit =_("% of RAM"), default_value = 90.0, maxvalue = 100.0 )
        ]
    ),
    None,
    "first"
)

register_check_parameters(
    subgroup_os,
    "netscaler_vserver",
    _("Netscaler VServer States"),
    Dictionary(
        elements = [
            ("health_levels", Tuple(title = _("Lower health levels"), elements = [
                Percentage(title = _("Warning below"),  default_value = 100.0),
                Percentage(title = _("Critical below"), default_value = 0.1),
            ])),
        ]
    ),
    TextAscii( title = _("Name of VServer") ),
    "dict"
)


register_check_parameters(
    subgroup_os,
    "general_flash_usage",
    _("Flash Space Usage"),
    Alternative(
        elements = [
            Tuple(
                title = _("Specify levels in percentage of total Flash"),
                elements = [
                  Percentage(title = _("Warning at a usage of"), label = _("% of Flash"), maxvalue = None),
                  Percentage(title = _("Critical at a usage of"), label = _("% of Flash"), maxvalue = None)
                ]
            ),
            Tuple(
                title = _("Specify levels in absolute usage values"),
                elements = [
                  Integer(title = _("Warning at"), unit = _("MB")),
                  Integer(title = _("Critical at"), unit = _("MB"))
                ]
            ),
        ]
    ),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_os,
    "cisco_supervisor_mem",
    _("Cisco Nexus Supervisor Memory Usage"),
    Tuple(
        title = _("The average utilization of memory on the active supervisor"),
        elements = [
          Percentage(title = _("Warning at a usage of"), default_value = 80.0, maxvalue = 100.0 ),
          Percentage(title = _("Critical at a usage of"), default_value = 90.0, maxvalue = 100.0 )
        ]
    ),
    None,
    match_type = "first",
)


def UsedSize(**args):
    GB = 1024 * 1024 * 1024
    return Tuple(
        elements = [
            Filesize(title = _("Warning at"), default_value = 1 * GB),
            Filesize(title = _("Critical at"), default_value = 2 * GB),
        ],
        **args)

def FreeSize(**args):
    GB = 1024 * 1024 * 1024
    return Tuple(
        elements = [
            Filesize(title = _("Warning below"), default_value = 2 * GB),
            Filesize(title = _("Critical below"), default_value = 1 * GB),
        ],
        **args)

def UsedPercentage(default_percents=None, of_what=None):
    if of_what:
        unit = _("%% of %s") % of_what
        maxvalue = None
    else:
        unit = "%"
        maxvalue = 101.0
    return Tuple(
        elements = [
            Percentage(title = _("Warning at"),
                       default_value = default_percents and default_percents[0] or 80.0,
                       unit = unit,
                       maxvalue = maxvalue,
                       ),
            Percentage(title = _("Critical at"),
                       default_value = default_percents and default_percents[1] or 90.0,
                       unit = unit,
                       maxvalue = maxvalue),
        ])

def FreePercentage(default_percents=None, of_what=None):
    if of_what:
        unit = _("%% of %s") % of_what
    else:
        unit = "%"
    return Tuple(
        elements = [
            Percentage(title = _("Warning below"),
                       default_value = default_percents and default_percents[0] or 20.0,
                       unit = unit),
            Percentage(title = _("Critical below"),
                       default_value = default_percents and default_percents[1] or 10.0,
                       unit = unit),
        ])

def DualMemoryLevels(what, default_percents=None):
    return CascadingDropdown(
        title = _("Levels for %s") % what,
        choices = [
            ( "perc_used",  _("Percentual levels for used %s") % what, UsedPercentage(default_percents) ),
            ( "perc_free",  _("Percentual levels for free %s") % what, FreePercentage() ),
            ( "abs_used",   _("Absolute levels for used %s") % what,   UsedSize() ),
            ( "abs_free",   _("Absolute levels for free %s") % what,   FreeSize() ),
            # PredictiveMemoryChoice(_("used %s") % what), # not yet implemented
            ( "ignore",     _("Do not impose levels") ),
        ]
    )

def UpperMemoryLevels(what, default_percents=None, of_what=None):
    return CascadingDropdown(
        title = _("Upper levels for %s") % what,
        choices = [
            ( "perc_used",  _("Percentual levels%s") % (of_what and (_(" in relation to %s") % of_what) or ""),
              UsedPercentage(default_percents, of_what) ),
            ( "abs_used",   _("Absolute levels"),   UsedSize() ),
            # PredictiveMemoryChoice(what), # not yet implemented
            ( "ignore",     _("Do not impose levels") ),
        ]
    )

def LowerMemoryLevels(what, default_percents=None, of_what=None, help_text=None):
    return CascadingDropdown(
        title = _("Lower levels for %s") % what,
        help = help_text,
        choices = [
            ( "perc_free",  _("Percentual levels"), FreePercentage(default_percents, of_what) ),
            ( "abs_free",   _("Absolute levels"),   FreeSize() ),
            # PredictiveMemoryChoice(what), # not yet implemented
            ( "ignore",     _("Do not impose levels") ),
        ]
    )

# Beware: This is not yet implemented in the check.
# def PredictiveMemoryChoice(what):
#     return ( "predictive", _("Predictive levels for %s") % what,
#         PredictiveLevels(
#            unit = _("GB"),
#            default_difference = (0.5, 1.0)
#     ))


register_check_parameters(
    subgroup_os,
    "memory_linux",
    _("Memory and Swap usage on Linux"),
    Dictionary(
        elements = [
            ( "levels_ram",         DualMemoryLevels(_("RAM"))),
            ( "levels_swap",        DualMemoryLevels(_("Swap"))),
            ( "levels_virtual",     DualMemoryLevels(_("Total virtual memory"), ( 80.0, 90.0))),
            ( "levels_total",       UpperMemoryLevels(_("Total Data in relation to RAM"), (120.0, 150.0), _("RAM"))),
            ( "levels_shm",         UpperMemoryLevels(_("Shared memory"),       ( 20.0,  30.0), _("RAM"))),
            ( "levels_pagetables",  UpperMemoryLevels(_("Page tables"),         (  8.0,  16.0), _("RAM"))),
            ( "levels_writeback",   UpperMemoryLevels(_("Disk Writeback"))),
            ( "levels_committed",   UpperMemoryLevels(_("Committed memory"),    (100.0, 150.0), _("RAM + Swap"))),
            ( "levels_commitlimit", LowerMemoryLevels(_("Commit Limit"),        ( 20.0,  10.0), _("RAM + Swap"))),
            ( "levels_available",   LowerMemoryLevels(_("Estimated RAM for new processes"),       ( 20.0,  10.0), _("RAM"),
                                    _("If the host has a kernel of version 3.14 or newer, the information MemAvailable is provided: "
                                      "\"An estimate of how much memory is available for starting new "
                                      "applications, without swapping. Calculated from MemFree, "
                                      "SReclaimable, the size of the file LRU lists, and the low "
                                      "watermarks in each zone. "
                                      "The estimate takes into account that the system needs some "
                                      "page cache to function well, and that not all reclaimable "
                                      "slab will be reclaimable, due to items being in use. The "
                                      "impact of those factors will vary from system to system.\" "
                                      "(https://www.kernel.org/doc/Documentation/filesystems/proc.txt)"))),
            ( "levels_vmalloc",     LowerMemoryLevels(_("Largest Free VMalloc Chunk"))),
            ( "handle_hw_corrupted_error", MonitoringState(
                title = _("Handle Hardware Corrupted Error"),
                default_value = 2,
            )),
        ],
    ),
    None,
    "dict",
)



register_check_parameters(
    subgroup_os,
    "memory",
    _("Main memory usage (UNIX / Other Devices)"),
    Transform(
        Dictionary(
            elements = [
                ( "levels",
                    Alternative(
                        title = _("Levels for memory"),
                        show_alternative_title = True,
                        default_value = (150.0, 200.0),
                        match = match_dual_level_type,
                        help = _("The used and free levels for the memory on UNIX systems take into account the "
                               "currently used memory (RAM or SWAP) by all processes and sets this in relation "
                               "to the total RAM of the system. This means that the memory usage can exceed 100%. "
                               "A usage of 200% means that the total size of all processes is twice as large as "
                               "the main memory, so <b>at least</b> half of it is currently swapped out. For systems "
                               "without Swap space you should choose levels below 100%."),
                        elements = [
                            Alternative(
                                title = _("Levels for used memory"),
                                style = "dropdown",
                                elements = [
                                    Tuple(
                                        title = _("Specify levels in percentage of total RAM"),
                                        elements = [
                                          Percentage(title = _("Warning at a usage of"),  maxvalue = None),
                                          Percentage(title = _("Critical at a usage of"), maxvalue = None)
                                        ]
                                    ),
                                    Tuple(
                                        title = _("Specify levels in absolute values"),
                                        elements = [
                                          Integer(title = _("Warning at"), unit = _("MB")),
                                          Integer(title = _("Critical at"), unit = _("MB"))
                                        ]
                                    ),
                                ]
                            ),
                            Transform(
                                    Alternative(
                                        style = "dropdown",
                                        elements = [
                                            Tuple(
                                                title = _("Specify levels in percentage of total RAM"),
                                                elements = [
                                                  Percentage(title = _("Warning if less than"),  maxvalue = None),
                                                  Percentage(title = _("Critical if less than"), maxvalue = None)
                                                ]
                                            ),
                                            Tuple(
                                                title = _("Specify levels in absolute values"),
                                                elements = [
                                                  Integer(title = _("Warning if below"), unit = _("MB")),
                                                  Integer(title = _("Critical if below"), unit = _("MB"))
                                                ]
                                            ),
                                        ]
                                    ),
                                    title = _("Levels for free memory"),
                                    help = _("Keep in mind that if you have 1GB RAM and 1GB SWAP you need to "
                                             "specify 120% or 1200MB to get an alert if there is only 20% free RAM available. "
                                             "The free memory levels do not work with the fortigate check, because it does "
                                             "not provide total memory data."),
                                    allow_empty = False,
                                    forth = lambda val: tuple(map(lambda x: -x, val)),
                                    back  = lambda val: tuple(map(lambda x: -x, val))
                             )
                        ]
                    ),
                ),
                ("average",
                    Integer(
                        title = _("Averaging"),
                        help = _("If this parameter is set, all measured values will be averaged "
                               "over the specified time interval before levels are being applied. Per "
                               "default, averaging is turned off."),
                       unit = _("minutes"),
                       minvalue = 1,
                       default_value = 60,
                    )
                ),
            ],
            optional_keys = [ "average" ],
        ),
        forth = lambda t: type(t) == tuple and { "levels" : t } or t,
    ),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_os,
    "memory_relative",
    _("Main memory usage for Brocade fibre channel switches"),
    OptionalDropdownChoice(
        title = _("Memory usage"),
        choices = [
            ( None, _("Do not impose levels"))
        ],
        otherlabel = _("Percentual levels ->"),
        explicit = \
            Tuple(
                elements = [
                    Integer(title=_("Warning at"), default_value=85, unit="%"),
                    Integer(title=_("Critical at"), default_value=90, unit="%"),
                ]
            )
    ),
    None,
    "first"
)

register_check_parameters(
    subgroup_os,
    "memory_simple",
    _("Main memory usage of simple devices"),
    Transform(
        Dictionary(
            help = _("Memory levels for simple devices not running more complex OSs"),
            elements = [
                ("levels", CascadingDropdown(
                    title = _("Levels for memory usage"),
                    choices = [
                        ( "perc_used",
                          _("Percentual levels for used memory"),
                          Tuple(
                              elements = [
                                   Percentage(title = _("Warning at a memory usage of"), default_value = 80.0, maxvalue = None),
                                   Percentage(title = _("Critical at a memory usage of"), default_value = 90.0, maxvalue = None)
                              ]
                        )),
                        ( "abs_free",
                          _("Absolute levels for free memory"),
                          Tuple(
                              elements = [
                                 Filesize(title = _("Warning below")),
                                 Filesize(title = _("Critical below"))
                              ]
                        )),
                        ( "ignore", _("Do not impose levels")),
                    ])
                ),
            ],
            optional_keys = [],
        ),
        # Convert default levels from discovered checks
        forth = lambda v: type(v) != dict and { "levels" : ( "perc_used", v) } or v,
    ),
    TextAscii(
        title = _("Module name or empty"),
        help = _("Leave this empty for systems without modules, which just "
                 "have one global memory usage."),
        allow_empty = True,
    ),
    "dict",
)

register_check_parameters(
    subgroup_os,
    "memory_multiitem",
    _("Main memory usage of devices with modules"),
    Dictionary(
        help = _("The memory levels for one specific module of this host. This is relevant for hosts that have "
                 "several distinct memory areas, e.g. pluggable cards"),
        elements = [
            ("levels", Alternative(
                title = _("Memory levels"),
                elements = [
                     Tuple(
                         title = _("Specify levels in percentage of total RAM"),
                         elements = [
                             Percentage(title = _("Warning at a memory usage of"), default_value = 80.0, maxvalue = None),
                             Percentage(title = _("Critical at a memory usage of"), default_value = 90.0, maxvalue = None)]),
                     Tuple(
                         title = _("Specify levels in absolute usage values"),
                         elements = [
                           Filesize(title = _("Warning at")),
                           Filesize(title = _("Critical at"))]),
                ])),
            ],
        optional_keys = []),
    TextAscii(
        title = _("Module name"),
        allow_empty = False
    ),
    "dict",
)

register_check_parameters(
    subgroup_os,
    "memory_arbor",
    _("Memory and Swap usage on Arbor devices"),
    Dictionary(
        elements = [
            ( "levels_ram",  DualMemoryLevels(_("RAM"))),
            ( "levels_swap", DualMemoryLevels(_("Swap"))),
        ],
    ),
    None,
    "dict",
)

register_check_parameters(
   subgroup_networking,
   "mem_cluster",
   _("Memory Usage of Clusters"),
    ListOf(
        Tuple(
            elements = [
                Integer(title = _("Equal or more than"), unit = _("nodes")),
                Tuple(
                    title = _("Percentage of total RAM"),
                    elements = [
                      Percentage(title = _("Warning at a RAM usage of"), default_value = 80.0),
                      Percentage(title = _("Critical at a RAM usage of"), default_value = 90.0),
                    ])
            ]
        ),
        help = _("Here you can specify the total memory usage levels for clustered hosts."),
        title = _("Memory Usage"),
        add_label = _("Add limits")
    ),
    None,
   "first",
   False
)

register_check_parameters(
   subgroup_networking,
   "cpu_utilization_cluster",
   _("CPU Utilization of Clusters"),
    ListOf(
        Tuple(
            elements = [
                Integer(title = _("Equal or more than"), unit = _("nodes")),
                Tuple(
                      elements = [
                          Percentage(title = _("Warning at a utilization of"), default_value = 90.0),
                          Percentage(title = _("Critical at a utilization of"), default_value = 95.0)
                      ],
                      title = _("Alert on too high CPU utilization"),
                )
            ]
        ),
        help = _("Configure levels for averaged CPU utilization depending on number of cluster nodes. "
                 "The CPU utilization sums up the percentages of CPU time that is used "
                 "for user processes and kernel routines over all available cores within "
                 "the last check interval. The possible range is from 0% to 100%"),
        title = _("Memory Usage"),
        add_label = _("Add limits")
    ),
   None,
   "first",
   False
)

register_check_parameters(
    subgroup_os,
    "esx_host_memory",
    _("Main memory usage of ESX host system"),
    Tuple(
        title = _("Specify levels in percentage of total RAM"),
        elements = [
          Percentage(title = _("Warning at a RAM usage of"), default_value = 80.0),
          Percentage(title = _("Critical at a RAM usage of"), default_value = 90.0),
        ]),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_os,
    "vm_guest_tools",
    _("Virtual machine (for example ESX) guest tools status"),
     Dictionary(
         optional_keys = False,
         elements = [
            ( "guestToolsCurrent",
               MonitoringState(
                   title = _("VMware Tools is installed, and the version is current"),
                   default_value = 0,
               )
            ),
            ( "guestToolsNeedUpgrade",
               MonitoringState(
                   title = _("VMware Tools is installed, but the version is not current"),
                   default_value = 1,
               )
            ),
             ( "guestToolsNotInstalled",
               MonitoringState(
                   title = _("VMware Tools have never been installed"),
                   default_value = 2,
               )
            ),
            ( "guestToolsUnmanaged",
               MonitoringState(
                   title = _("VMware Tools is installed, but it is not managed by VMWare"),
                   default_value = 1,
               )
            ),
         ]
      ),
    None,
    "dict",
)
register_check_parameters(
    subgroup_os,
    "vm_heartbeat",
    _("Virtual machine (for example ESX) heartbeat status"),
     Dictionary(
         optional_keys = False,
         elements = [
            ( "heartbeat_missing",
               MonitoringState(
                   title = _("No heartbeat"),
                   help = _("Guest operating system may have stopped responding."),
                   default_value = 2,
               )
            ),
            ( "heartbeat_intermittend",
               MonitoringState(
                   title = _("Intermittent heartbeat"),
                   help = _("May be due to high guest load."),
                   default_value = 1,
               )
            ),
             ( "heartbeat_no_tools",
               MonitoringState(
                   title = _("Heartbeat tools missing or not installed"),
                   help = _("No VMWare Tools installed."),
                   default_value = 1,
               )
            ),
            ( "heartbeat_ok",
               MonitoringState(
                   title = _("Heartbeat OK"),
                   help = _("Guest operating system is responding normally."),
                   default_value = 0,
               )
            ),
         ]
      ),
    None,
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "services_summary",
    _("Windows Service Summary"),
    Dictionary(
        title = _('Autostart Services'),
        elements = [
            ('ignored',
            ListOfStrings(
                title = _("Ignored autostart services"),
                help  = _('Regular expressions matching the begining of the internal name '
                          'or the description of the service. '
                          'If no name is given then this rule will match all services. The '
                          'match is done on the <i>beginning</i> of the service name. It '
                          'is done <i>case sensitive</i>. You can do a case insensitive match '
                          'by prefixing the regular expression with <tt>(?i)</tt>. Example: '
                          '<tt>(?i).*mssql</tt> matches all services which contain <tt>MSSQL</tt> '
                          'or <tt>MsSQL</tt> or <tt>mssql</tt> or...'),
                orientation = "horizontal",
            )),
            ('state_if_stopped',
            MonitoringState(
                title = _("Default state if stopped autostart services are found"),
                default_value = 0,
            )),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "solaris_services_summary",
    _("Solaris Services Summary"),
    Dictionary(
        elements = [
            ('maintenance_state',
                MonitoringState(
                    title = _("State if 'maintenance' services are found"),
                    default_value = 0,
            )),
        ],
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "esx_vsphere_objects",
    _("State of ESX hosts and virtual machines"),
    Dictionary(
        help = _("Usually the check goes to WARN if a VM or host is powered off and OK otherwise. "
                 "You can change this behaviour on a per-state-basis here."),
        optional_keys = False,
        elements = [
           ( "states",
             Dictionary(
                 title = _("Target states"),
                 optional_keys = False,
                 elements = [
                     ( "poweredOn",
                       MonitoringState(
                           title = _("Powered ON"),
                           help = _("Check result if the host or VM is powered on"),
                           default_value = 0,
                       )
                    ),
                    ( "poweredOff",
                       MonitoringState(
                           title = _("Powered OFF"),
                           help = _("Check result if the host or VM is powered off"),
                           default_value = 1,
                       )
                    ),
                    ( "suspended",
                       MonitoringState(
                           title = _("Suspended"),
                           help = _("Check result if the host or VM is suspended"),
                           default_value = 1,
                       )
                    ),
                    ( "unknown",
                       MonitoringState(
                           title = _("Unknown"),
                           help = _("Check result if the host or VM state is reported as <i>unknown</i>"),
                           default_value = 3,
                       )
                    ),
                 ]
              )
           ),
        ]
    ),
    TextAscii(
        title = _("Name of the VM/HostSystem"),
        help = _("Please do not forget to specify either <tt>VM</tt> or <tt>HostSystem</tt>. Example: <tt>VM abcsrv123</tt>. Also note, "
                 "that we match the <i>beginning</i> of the name."),
        regex = "(^VM|HostSystem)( .*|$)",
        regex_error = _("The name of the system must begin with <tt>VM</tt> or <tt>HostSystem</tt>."),
        allow_empty = False,
    ),
    "dict",
)

def windows_printer_queues_forth(old):
    default = {
        "warn_states"   : [ 8, 11 ],
        "crit_states"   : [ 9, 10 ],
      }
    if type(old) == tuple:
        default['levels'] = old
    if type(old) == dict:
        return old
    return default

register_check_parameters(
    subgroup_printing,
    "windows_printer_queues",
    _("Number of open jobs of a printer on windows" ),
    Transform(
        Dictionary(
            title = _("Windows Printer Configuration"),
            elements = [
                ( "levels",
                    Tuple(
                        title = _("Levels for the number of print jobs"),
                        help = _("This rule is applied to the number of print jobs "
                                 "currently waiting in windows printer queue."),
                        elements = [
                            Integer(title = _("Warning at"), unit = _("jobs"), default_value = 40),
                            Integer(title = _("Critical at"), unit = _("jobs"), default_value = 60),
                        ]
                    ),
                ),
                ("crit_states",
                    ListChoice(
                        title = _("States who should lead to critical"),
                        choices = [
                            ( 0,  "Unkown"),
                            ( 1,  "Other"),
                            ( 2,  "No Error"),
                            ( 3,  "Low Paper"),
                            ( 4,  "No Paper"),
                            ( 5,  "Low Toner"),
                            ( 6,  "No Toner"),
                            ( 7,  "Door Open"),
                            ( 8,  "Jammed"),
                            ( 9,  "Offline"),
                            ( 10, "Service Requested"),
                            ( 11, "Output Bin Full"),
                            ],
                        default_value = [9, 10],
                        )
                 ),
                ("warn_states",
                    ListChoice(
                        title = _("States who should lead to warning"),
                        choices = [
                            ( 0,  "Unkown"),
                            ( 1,  "Other"),
                            ( 2,  "No Error"),
                            ( 3,  "Low Paper"),
                            ( 4,  "No Paper"),
                            ( 5,  "Low Toner"),
                            ( 6,  "No Toner"),
                            ( 7,  "Door Open"),
                            ( 8,  "Jammed"),
                            ( 9,  "Offline"),
                            ( 10, "Service Requested"),
                            ( 11, "Output Bin Full"),
                            ],
                        default_value = [8, 11],
                        )
                 ),
                ]
        ),
        forth = windows_printer_queues_forth,
    ),
    TextAscii(
        title = _("Printer Name"),
        allow_empty = True
    ),
    match_type = "first",
)

register_check_parameters(
    subgroup_printing,
    "printer_input",
    _("Printer Input Units"),
    Dictionary(
        elements =  [
            ('capacity_levels', Tuple(
                title = _('Capacity remaining'),
                elements = [
                    Percentage(title = _("Warning at"), default_value = 0.0),
                    Percentage(title = _("Critical at"), default_value = 0.0),
                ],
            )),
        ],
        default_keys = ['capacity_levels'],
    ),
    TextAscii(
        title = _('Unit Name'),
        allow_empty = True
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_printing,
    "printer_output",
    _("Printer Output Units"),
    Dictionary(
        elements =  [
            ('capacity_levels', Tuple(
                title = _('Capacity filled'),
                elements = [
                    Percentage(title = _("Warning at"), default_value = 0.0),
                    Percentage(title = _("Critical at"), default_value = 0.0),
                ],
            )),
        ],
        default_keys = ['capacity_levels'],
    ),
    TextAscii(
        title = _('Unit Name'),
        allow_empty = True
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_os,
    "cpu_load",
    _("CPU load (not utilization!)"),
    Levels(
          help = _("The CPU load of a system is the number of processes currently being "
                   "in the state <u>running</u>, i.e. either they occupy a CPU or wait "
                   "for one. The <u>load average</u> is the averaged CPU load over the last 1, "
                   "5 or 15 minutes. The following levels will be applied on the average "
                   "load. On Linux system the 15-minute average load is used when applying "
                   "those levels. The configured levels are multiplied with the number of "
                   "CPUs, so you should configure the levels based on the value you want to "
                   "be warned \"per CPU\"."),
          unit = "per core",
          default_difference = (2.0, 4.0),
          default_levels = (5.0, 10.0),
    ),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_os,
    "cpu_utilization",
    _("CPU utilization for Appliances"),
    Optional(
        Tuple(
              elements = [
                  Percentage(title = _("Warning at a utilization of")),
                  Percentage(title = _("Critical at a utilization of"))]),
        label = _("Alert on too high CPU utilization"),
        help = _("The CPU utilization sums up the percentages of CPU time that is used "
                 "for user processes and kernel routines over all available cores within "
                 "the last check interval. The possible range is from 0% to 100%"),
        default_value = (90.0, 95.0)),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_os,
    "cpu_utilization_multiitem",
    _("CPU utilization of Devices with Modules"),
    Dictionary(
        help = _("The CPU utilization sums up the percentages of CPU time that is used "
                 "for user processes and kernel routines over all available cores within "
                 "the last check interval. The possible range is from 0% to 100%"),
        elements =  [
                        ("levels", Tuple(
                            title = _("Alert on too high CPU utilization"),
                            elements = [
                                Percentage(title = _("Warning at a utilization of"), default_value=90.0),
                                Percentage(title = _("Critical at a utilization of"), default_value=95.0)],
                            ),
                        ),
                    ]
                ),
    TextAscii(
        title = _("Module name"),
        allow_empty = False
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_os,
    "fpga_utilization",
    _("FPGA utilization"),
    Dictionary(
        help = _("Give FPGA utilization levels in percent. The possible range is from 0% to 100%."),
        elements =  [
                        ("levels", Tuple(
                            title = _("Alert on too high FPGA utilization"),
                            elements = [
                                Percentage(title = _("Warning at a utilization of"), default_value = 80.0),
                                Percentage(title = _("Critical at a utilization of"), default_value = 90.0)],
                            ),
                        ),
                    ]
                ),
    TextAscii(
        title = _("FPGA"),
        allow_empty = False
    ),
    match_type = "dict",
)

cpu_util_common_elements = [
    ( "levels_single",
       Tuple(
           title = _("Levels on single cores"),
           elements = [
                 Percentage(title = _("Warning at"), default_value = 90.0),
                 Percentage(title = _("Critical at"), default_value = 95.0)],
           help = _("Here you can set levels on the CPU utilization on single cores"),
        )
    ),
    ( "core_util_time_total",
      Tuple(
          title = _("Levels over an extended time period on total CPU utilization"),
          elements = [
              Percentage(title = _("High utilization at "), default_value = 100.0),
              Age(title = _("Warning after "), default_value = 5 * 60),
              Age(title = _("Critical after "), default_value = 15 * 60),
          ],
          help = _("With this configuration, check_mk will alert if the total CPU is "
                   "exceeding a utilization threshold over an extended period of time. "
                   "ATTENTION: This configuration cannot be used for check <i>lparstat_aix.cpu_util</i>!")
        )
    ),
    ( "core_util_time",
        Tuple(
            title = _("Levels over an extended time period on a single core CPU utilization"),
            elements = [
                Percentage(title = _("High utilization at "), default_value = 100.0),
                Age(title = _("Warning after "), default_value = 5 * 60),
                Age(title = _("Critical after "), default_value = 15 * 60),
            ],
            help = _("A single thread fully utilizing a single core (potentially due to a bug) "
                    "may go unnoticed when only monitoring the total utilization of the CPU. "
                    "With this configuration, check_mk will alert if a single core is "
                    "exceeding a utilization threshold over an extended period of time."
                    "This is currently only supported on linux and windows agents "
                    "as well as devices monitored through the host-resource mib")
        )
    ),
    ( "core_util_graph",
        Checkbox(
            title = _("Graphs for individual cores"),
            label = _("Enable performance graph for utilization of individual cores"),
            help  = _("This adds another graph to the performance CPU utilization "
                    "details page, showing utilization of individual cores. "
                    "Please note that this graph may be impractical on "
                    "device with very many cores. "
                    "This is currently only supported on linux and windows agents "
                    "as well as devices monitored through the host-resource mib")
        ),
    ),
]

register_check_parameters(
    subgroup_os,
    "cpu_utilization_os",
    _("CPU utilization for simple devices"),
    Dictionary(
        help = _("This rule configures levels for the CPU utilization (not load) for "
                 "the operating systems Windows and VMWare ESX host systems, as well as devices "
                 "implementing the Host Resources MIB. The utilization "
                 "ranges from 0 to 100 - regardless of the number of CPUs."),
        elements = [
            ( "average",
              Integer(
                  title = _("Averaging for total CPU utilization"),
                  help = _("When this option is activated then the CPU utilization is being "
                           "averaged <b>before</b> the levels are being applied."),
                  unit = _("minutes"),
                  minvalue = 1,
                  default_value = 15,
                  label = _("Compute average over last "),
            )),
            ( "levels",
                Levels(
                    title = _("Levels on total CPU utilization"),
                    unit = "%",
                    default_levels = (85, 90),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
        ] + cpu_util_common_elements,
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_os,
    "cpu_iowait",
    _("CPU utilization on Linux/UNIX"),
    Transform(
        Dictionary(
            elements = [
                ( "iowait",
                   Tuple(
                       title = _("Levels on disk wait (IO wait)"),
                       elements = [
                             Percentage(title = _("Warning at a disk wait of"), default_value = 30.0),
                             Percentage(title = _("Critical at a disk wait of"), default_value = 50.0)],
                       help = _("The CPU utilization sums up the percentages of CPU time that is used "
                                "for user processes, kernel routines (system), disk wait (sometimes also "
                                "called IO wait) or nothing (idle). "
                                "Currently you can only set warning/critical levels to the disk wait. This "
                                "is the total percentage of time all CPUs have nothing else to do then waiting "
                                "for data coming from or going to disk. If you have a significant disk wait "
                                "the the bottleneck of your server is IO. Please note that depending on the "
                                "applications being run this might or might not be totally normal.")),
                ),
                ( "util",
                   Tuple(
                       title = _("Levels on total CPU utilization"),
                       elements = [
                             Percentage(title = _("Warning at a utilization of"), default_value = 90.0),
                             Percentage(title = _("Critical at a utilization of"), default_value = 95.0)],
                       help = _("Here you can set levels on the total CPU utilization, i.e. the sum of "
                                "<i>system</i>, <i>user</i> and <i>iowait</i>. The levels are always applied "
                                "on the average utiliazation since the last check - which is usually one minute."),
                    )
                ),
            ] + cpu_util_common_elements,
        ),
        forth = lambda old: type(old) != dict and { "iowait" : old } or old,
    ),
    None,
    "dict",
)

def transform_humidity(p):
    if type(p) in [ list, tuple ]:
        p = {
            "levels_lower" : (float(p[1]), float(p[0])),
            "levels"       : (float(p[2]), float(p[3])),
        }
    return p

register_check_parameters(
    subgroup_environment,
    "humidity",
    _("Humidity Levels"),
    Transform(
        Dictionary(
            help = _("This Ruleset sets the threshold limits for humidity sensors"),
            elements = [
                ("levels", Tuple(
                    title    = _("Upper levels"),
                    elements = [
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ]
                )),
                ("levels_lower", Tuple(
                    title    = _("Lower levels"),
                    elements = [
                        Percentage(title=_("Warning below")),
                        Percentage(title=_("Critical below")),
                    ]
                )),
            ]
        ),
        forth = transform_humidity,
    ),
    TextAscii(
        title = _("Sensor name"),
        help = _("The identifier of the sensor."),
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_environment,
    "single_humidity",
    _("Humidity Levels for devices with a single sensor"),
    Tuple(
          help = _("This Ruleset sets the threshold limits for humidity sensors"),
          elements = [
              Integer(title = _("Critical at or below"), unit="%" ),
              Integer(title = _("Warning at or below"), unit="%" ),
              Integer(title = _("Warning at or above"), unit="%" ),
              Integer(title = _("Critical at or above"), unit="%" ),
              ]),
     None,
     match_type = "first",
)

db_levels_common = [
    ("levels",
        Alternative(
            title = _("Levels for the Tablespace usage"),
            default_value = (10.0, 5.0),
            elements = [
                Tuple(
                    title = _("Percentage free space"),
                    elements = [
                        Percentage(title = _("Warning if below"), unit = _("% free")),
                        Percentage(title = _("Critical if below"), unit = _("% free")),
                    ]
                ),
                Tuple(
                    title = _("Absolute free space"),
                    elements = [
                         Integer(title = _("Warning if below"), unit = _("MB"), default_value = 1000),
                         Integer(title = _("Critical if below"), unit = _("MB"), default_value = 500),
                    ]
                ),
                ListOf(
                    Tuple(
                        orientation = "horizontal",
                        elements = [
                            Filesize(title = _("Tablespace larger than")),
                            Alternative(
                                title = _("Levels for the Tablespace size"),
                                elements = [
                                    Tuple(
                                        title = _("Percentage free space"),
                                        elements = [
                                            Percentage(title = _("Warning if below"), unit = _("% free")),
                                            Percentage(title = _("Critical if below"), unit = _("% free")),
                                        ]
                                    ),
                                    Tuple(
                                        title = _("Absolute free space"),
                                        elements = [
                                             Integer(title = _("Warning if below"), unit = _("MB")),
                                             Integer(title = _("Critical if below"), unit = _("MB")),
                                        ]
                                    ),
                                ]
                            ),
                        ],
                    ),
                    title = _('Dynamic levels'),
                ),
            ]
        )
    ),
    ("magic",
       Float(
          title = _("Magic factor (automatic level adaptation for large tablespaces)"),
          help = _("This is only be used in case of percentual levels"),
          minvalue = 0.1,
          maxvalue = 1.0,
          default_value = 0.9)),
    (  "magic_normsize",
       Integer(
           title = _("Reference size for magic factor"),
           minvalue = 1,
           default_value = 1000,
           unit = _("MB"))),
    ( "magic_maxlevels",
      Tuple(
          title = _("Maximum levels if using magic factor"),
          help = _("The tablespace levels will never be raise above these values, when using "
                   "the magic factor and the tablespace is very small."),
          elements = [
              Percentage(title = _("Maximum warning level"),  unit = _("% free"), allow_int = True, default_value = 60.0),
              Percentage(title = _("Maximum critical level"), unit = _("% free"), allow_int = True, default_value = 50.0)])
    )
]

register_check_parameters(
    subgroup_applications,
    "oracle_tablespaces",
    _("Oracle Tablespaces"),
    Dictionary(
        help = _("A tablespace is a container for segments (tables, indexes, etc). A "
                 "database consists of one or more tablespaces, each made up of one or "
                 "more data files. Tables and indexes are created within a particular "
                 "tablespace. "
                 "This rule allows you to define checks on the size of tablespaces."),
        elements = db_levels_common + [
            ( "autoextend",
                DropdownChoice(
                  title = _("Expected autoextend setting"),
                  choices = [
                     ( True,  _("Autoextend is expected to be ON")),
                     ( False, _("Autoextend is expected to be OFF")),
                     ( None,  _("Autoextend will be ignored")),
                  ]
            )),
            ( "autoextend_severity",
              MonitoringState(
                  title = _("Severity of invalid autoextend setting"),
                  default_value = 2,
            )),
            ( "defaultincrement",
                DropdownChoice(
                  title   = _("Default Increment"),
                  choices = [
                     ( True, _("State is WARNING in case the next extent has the default size.")),
                     ( False, _("Ignore default increment")),
                  ]
                )
            ),
            ( "map_file_online_states",
                ListOf(
                    Tuple(
                        orientation = "horizontal",
                        elements = [
                            DropdownChoice(choices = [
                                ("RECOVER", _("Recover")),
                                ("OFFLINE", _("Offline")),
                            ]),
                            MonitoringState()
                        ]),
                    title = _('Map file online states'),
                )
            ),
        ],
    ),
    TextAscii(
        title = _("Explicit tablespaces"),
        help = _("Here you can set explicit tablespaces by defining them via SID and the tablespace name, separated by a dot, for example <b>pengt.TEMP</b>"),
        regex = '.+\..+',
        allow_empty = False),
     match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "oracle_processes",
    _("Oracle Processes"),
    Dictionary(
          help = _("Here you can override the default levels for the ORACLE Processes check. The levels "
                   "are applied on the number of used processes in percentage of the configured limit."),
          elements = [
              ( "levels",
                Tuple(
                    title = _("Levels for used processes"),
                    elements = [
                        Percentage(title = _("Warning if more than"), default_value = 70.0),
                        Percentage(title = _("Critical if more than"), default_value = 90.0)
                    ]
                )
             ),
          ],
          optional_keys = False,
    ),
    TextAscii(
        title = _("Database SID"),
        size = 12,
        allow_empty = False),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "oracle_logswitches",
    _("Oracle Logswitches"),
    Tuple(
          help = _("This check monitors the number of log switches of an ORACLE "
                   "database instance in the last 60 minutes. You can set levels for upper and lower bounds."),
          elements = [
              Integer(title = _("Critical at or below"), unit=_("log switches / hour"), default_value = -1),
              Integer(title = _("Warning at or below"),  unit=_("log switches / hour"), default_value = -1),
              Integer(title = _("Warning at or above"),  unit=_("log switches / hour"), default_value = 50),
              Integer(title = _("Critical at or above"), unit=_("log switches / hour"), default_value = 100),
              ]),
    TextAscii(
        title = _("Database SID"),
        size = 12,
        allow_empty = False),
    "first",
)

register_check_parameters(
    subgroup_applications,
    "oracle_recovery_area",
    _("Oracle Recovery Area"),
    Dictionary(
         elements = [
             ("levels",
                 Tuple(
                     title = _("Levels for used space (reclaimable is considered as free)"),
                     elements = [
                       Percentage(title = _("warning at"), default_value = 70.0),
                       Percentage(title = _("critical at"), default_value = 90.0),
                     ]
                 )
             )
         ]
    ),
    TextAscii(
        title = _("Database SID"),
        size = 12,
        allow_empty = False),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "oracle_dataguard_stats",
    _("Oracle Data-Guard Stats"),
    Dictionary(
        help = _("The Data-Guard statistics are available in Oracle Enterprise Edition with enabled Data-Guard. "
                 "The <tt>init.ora</tt> parameter <tt>dg_broker_start</tt> must be <tt>TRUE</tt> for this check. "
                 "The apply and transport lag can be configured with this rule."),
        elements = [
            ( "apply_lag",
              Tuple(
                  title = _("Apply Lag Maximum Time"),
                  help = _( "The maximum limit for the apply lag in <tt>v$dataguard_stats</tt>."),
                  elements = [
                      Age(title = _("Warning at"),),
                      Age(title = _("Critical at"),)])),
            ( "apply_lag_min",
              Tuple(
                  title = _("Apply Lag Minimum Time"),
                  help = _( "The minimum limit for the apply lag in <tt>v$dataguard_stats</tt>. "
                            "This is only useful if also <i>Apply Lag Maximum Time</i> has been configured."),
                  elements = [
                      Age(title = _("Warning at"),),
                      Age(title = _("Critical at"),)])),
            ( "transport_lag",
              Tuple(
                  title = _("Transport Lag"),
                  help = _( "The limit for the transport lag in <tt>v$dataguard_stats</tt>"),
                  elements = [
                      Age(title = _("Warning at"),),
                      Age(title = _("Critical at"),)])),
                   ]),
    TextAscii(
        title = _("Database SID"),
        size = 12,
        allow_empty = False),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "oracle_undostat",
    _("Oracle Undo Retention"),
    Dictionary(
         elements = [
             ("levels",
                 Tuple(
                     title = _("Levels for remaining undo retention"),
                     elements = [
                          Age(title = _("warning if less then"), default_value = 600),
                          Age(title = _("critical if less then"), default_value = 300),
                     ]
                 )
             ),(
            'nospaceerrcnt_state',
                MonitoringState(
                    default_value = 2,
                    title = _("State in case of non space error count is greater then 0: "),
                ),
            ),
         ]
    ),
    TextAscii(
        title = _("Database SID"),
        size = 12,
        allow_empty = False),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "oracle_rman",
    _("Oracle RMAN Backups"),
    Dictionary(
         elements = [
             ("levels",
                 Tuple(
                     title = _("Maximum Age for RMAN backups"),
                     elements = [
                          Age(title = _("warning if older than"),  default_value = 1800),
                          Age(title = _("critical if older than"), default_value = 3600),
                     ]
                 )
             )
         ]
    ),
    TextAscii(
        title = _("Database SID"),
        size = 12,
        allow_empty = False),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "oracle_recovery_status",
    _("Oracle Recovery Status"),
    Dictionary(
         elements = [
             ("levels",
                 Tuple(
                     title = _("Levels for checkpoint time"),
                     elements = [
                          Age(title = _("warning if higher then"), default_value = 1800),
                          Age(title = _("critical if higher then"), default_value = 3600),
                     ]
                 )
             ),
             ("backup_age",
                 Tuple(
                     title = _("Levels for user managed backup files"),
                     help = _( "Important! This checks is only for monitoring of datafiles "
                               "who were left in backup mode. "
                               "(alter database datafile ... begin backup;) "),
                     elements = [
                          Age(title = _("warning if higher then"), default_value = 1800),
                          Age(title = _("critical if higher then"), default_value = 3600),
                     ]
                 )
             )
         ]
    ),
    TextAscii(
        title = _("Database SID"),
        size = 12,
        allow_empty = False),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "oracle_jobs",
    _("Oracle Scheduler Job"),
    Dictionary(
        help = _("A scheduler job is an object in an ORACLE database which could be "
                 "compared to a cron job on Unix. "),
        elements = [
            ( "run_duration",
                Tuple(
                    title = _("Maximum run duration for last execution"),
                    help  = _("Here you can define an upper limit for the run duration of "
                              "last execution of the job."),
                    elements = [
                         Age(title = _("warning at")),
                         Age(title = _("critical at")),
                    ]
            )),
            ( "disabled",
                DropdownChoice(
                    title   = _("Job State"),
                    help    = _("The state of the job is ignored per default."),
                    totext  = "",
                    choices = [
                        ( True, _("Ignore the state of the Job")),
                        ( False, _("Consider the state of the job")),
                    ],
            )),
            ( "status_disabled_jobs",
                MonitoringState(
                    title = "Status of service in case of disabled job",
                    default_value = 0
            )),
            ( "status_missing_jobs",
                MonitoringState(
                    title = _("Status of service in case of missing job."),
                    default_value = 2,
            )),

        ]
    ),
    TextAscii(
        title = _("Scheduler Job Name"),
        help = _("Here you can set explicit Scheduler-Jobs by defining them via SID, Job-Owner "
                 "and Job-Name, separated by a dot, for example <tt>TUX12C.SYS.PURGE_LOG</tt>"),
        regex = '.+\..+',
        allow_empty = False),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "oracle_instance",
    _("Oracle Instance"),
    Dictionary(
        title = _("Consider state of Archivelogmode: "),
        elements = [(
            'archivelog',
                MonitoringState(
                    default_value = 0,
                    title = _("State in case of Archivelogmode is enabled: "),
                )
            ),(
            'noarchivelog',
                MonitoringState(
                    default_value = 1,
                    title = _("State in case of Archivelogmode is disabled: "),
                ),
            ),(
            'forcelogging',
                MonitoringState(
                    default_value = 0,
                    title = _("State in case of Force Logging is enabled: "),
                ),
            ),(
            'noforcelogging',
                MonitoringState(
                    default_value = 1,
                    title = _("State in case of Force Logging is disabled: "),
                ),
            ),(
            'logins',
                MonitoringState(
                    default_value = 2,
                    title = _("State in case of logins are not possible: "),
                ),
            ),(
            'primarynotopen',
                MonitoringState(
                    default_value = 2,
                    title = _("State in case of Database is PRIMARY and not OPEN: "),
                ),
            ),(
            'uptime_min',
             Tuple(
                 title = _("Minimum required uptime"),
                 elements = [
                     Age(title = _("Warning if below")),
                     Age(title = _("Critical if below")),
                 ]
           )),(
            'ignore_noarchivelog',
                Checkbox(
                    title = _("Ignore state of no-archive log"),
                    label = _("Enable"),
                    help  = _("If active, only a single summary item is displayed. The summary "
                              "will explicitly mention sensors in warn/crit state but the "
                              "sensors that are ok are aggregated."),
                    default_value = False)
            ),
        ],
    ),
    TextAscii(
        title = _("Database SID"),
        size = 12,
        allow_empty = False),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "asm_diskgroup",
    _("ASM Disk Group (used space and growth)"),
    Dictionary(
        elements = filesystem_elements + [
            ("req_mir_free", DropdownChoice(
             title = _("Handling for required mirror space"),
             totext = "",
             choices = [
                 ( False, _("Do not regard required mirror space as free space")),
                 ( True, _("Regard required mirror space as free space")),],
             help = _("ASM calculates the free space depending on free_mb or required mirror "
                      "free space. Enable this option to set the check against required "
                      "mirror free space. This only works for normal or high redundancy Disk Groups."))
            ),
        ],
        hidden_keys = ["flex_levels"],
    ),
    TextAscii(
        title = _("ASM Disk Group"),
        help = _("Specify the name of the ASM Disk Group "),
        allow_empty = False),
    "dict"
)

def _vs_mssql_backup_age(title):
    return Alternative(
        title=_("%s" % title),
        style="dropdown",
        elements=[
            Tuple(
                title=_("Set levels"),
                elements=[
                    Age(title=_("Warning if older than")),
                    Age(title=_("Critical if older than")),
            ]),
            Tuple(
                title=_("No levels"),
                elements=[
                    FixedValue(None, totext=""),
                    FixedValue(None, totext=""),
            ]),
        ]
    )

register_check_parameters(
    subgroup_applications,
    "mssql_backup",
    _("MSSQL Time since last Backup"),
    Transform(
        Dictionary(
            help = _("This rule allows you to set limits on the age of backups for "
                     "different backup types. If your agent does not support "
                     "backup types (e.g. <i>Log Backup</i>, <i>Database Diff "
                     "Backup</i>, etc.) you can use the option <i>Database Backup"
                     "</i> to set a general limit"),
            elements = [
                ("database", _vs_mssql_backup_age("Database backup")),
                ("database_diff", _vs_mssql_backup_age("Database diff backup")),
                ("log", _vs_mssql_backup_age("Log backup")),
                ("file_or_filegroup", _vs_mssql_backup_age("File or filegroup backup")),
                ("file_diff", _vs_mssql_backup_age("File diff backup")),
                ("partial", _vs_mssql_backup_age("Partial backup")),
                ("partial_diff", _vs_mssql_backup_age("Partial diff backup")),
                ("unspecific", _vs_mssql_backup_age("Unspecific backup")),
            ]
        ),
        forth = lambda params: (params if isinstance(params, dict)
                                else {'database': (params[0], params[1])})
    ),
    TextAscii(
        title = _("Service descriptions"),
        allow_empty = False),
    "first",
)

register_check_parameters(
    subgroup_applications,
    "mssql_file_sizes",
    _("MSSQL Log and Data File Sizes"),
    Dictionary(
        title = _("File Size Levels"),
        elements = [
            ("data_files",
                Tuple(
                    title = _("Levels for Datafiles"),
                    elements = [
                      Filesize(title = _("Warning at")),
                      Filesize(title = _("Critical at")),
                    ]
            )),
            ("log_files",
                Tuple(
                    title = _("Levels for Logfiles"),
                    elements = [
                      Filesize(title = _("Warning at")),
                      Filesize(title = _("Critical at")),
                    ]
            )),
            ("log_files_used",
                Tuple(
                    title = _("Levels for used Logfiles"),
                    elements = [
                      Filesize(title = _("Warning at")),
                      Filesize(title = _("Critical at")),
                    ]
            )),
        ]
    ),
    TextAscii(
        title = _("Service descriptions"),
        allow_empty = False),
     "dict"
)

register_check_parameters(
    subgroup_applications,
    "mssql_tablespaces",
    _("MSSQL Size of Tablespace"),
    Dictionary(
        elements = [
            ("size",
            Tuple(
                title = _("Size"),
                elements = [
                  Filesize(title = _("Warning at")),
                  Filesize(title = _("Critical at"))
                ]
            )),
            ("unallocated",
            Tuple(
                title = _("Unallocated Space"),
                elements = [
                  Filesize(title = _("Warning below")),
                  Filesize(title = _("Critical below"))
                ]
            )),
            ("reserved",
            Tuple(
                title = _("Reserved Space"),
                elements = [
                  Filesize(title = _("Warning at")),
                  Filesize(title = _("Critical at"))
                ]
            )),
            ("data",
            Tuple(
                title = _("Data"),
                elements = [
                  Filesize(title = _("Warning at")),
                  Filesize(title = _("Critical at"))
                ]
            )),
            ("indexes",
            Tuple(
                title = _("Indexes"),
                elements = [
                  Filesize(title = _("Warning at")),
                  Filesize(title = _("Critical at"))
                ]
            )),
            ("unused",
            Tuple(
                title = _("Unused"),
                elements = [
                  Filesize(title = _("Warning at")),
                  Filesize(title = _("Critical at"))
                ]
            )),

        ],
    ),
    TextAscii(
        title = _("Tablespace name"),
        allow_empty = False),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "mssql_page_activity",
    _("MSSQL Page Activity"),
    Dictionary(
        title = _("Page Activity Levels"),
        elements = [
            ("page_reads/sec",
             Tuple(
                 title = _("Reads/sec"),
                 elements = [
                     Float(title = _("warning at"), unit = _("/sec") ),
                     Float(title = _("critical at"), unit = _("/sec") ),
                 ])
             ),
            ("page_writes/sec",
             Tuple(
                 title = _("Writes/sec"),
                 elements = [
                     Float(title = _("warning at"), unit = _("/sec") ),
                     Float(title = _("critical at"), unit = _("/sec") ),
                 ])
             ),
            ("page_lookups/sec",
             Tuple(
                 title = _("Lookups/sec"),
                 elements = [
                     Float(title = _("warning at"), unit = _("/sec") ),
                     Float(title = _("critical at"), unit = _("/sec") ),
                 ])
             ),
        ]
    ),
    TextAscii(
        title = _("Service descriptions"),
        allow_empty = False),
    match_type = "dict"
)

def levels_absolute_or_dynamic(name, value):
    return Alternative(
        title = _("Levels of %s %s") % (name, value),
        default_value = (80.0, 90.0),
        elements = [
            Tuple(
                title = _("Percentage %s space") % value,
                elements = [
                    Percentage(title = _("Warning at"), unit = _("% used")),
                    Percentage(title = _("Critical at"), unit = _("% used")),
                ]
            ),
            Tuple(
                title = _("Absolute %s space") % value,
                elements = [
                    Integer(title = _("Warning at"), unit = _("MB"), default_value = 500),
                    Integer(title = _("Critical at"), unit = _("MB"), default_value = 1000),
                ]
            ),
            ListOf(
                Tuple(
                    orientation = "horizontal",
                    elements = [
                        Filesize(title = _(" larger than")),
                        Alternative(
                            title = _("Levels for the %s %s size") % (name, value),
                            elements = [
                                Tuple(
                                    title = _("Percentage %s space") % value,
                                    elements = [
                                        Percentage(title = _("Warning at"), unit = _("% used")),
                                        Percentage(title = _("Critical at"), unit = _("% used")),
                                    ]
                                ),
                                Tuple(
                                    title = _("Absolute free space"),
                                    elements = [
                                        Integer(title = _("Warning at"), unit = _("MB")),
                                        Integer(title = _("Critical at"), unit = _("MB")),
                                    ]
                                ),
                            ]
                        ),
                    ],
                ),
                title = _('Dynamic levels'),
            ),
        ]
    )

register_check_parameters(
    subgroup_applications,
    "mssql_transactionlogs",
    _("MSSQL Transactionlog Sizes"),
    Dictionary(
        title = _("File Size Levels"),
        help = _("Specify levels for transactionlogs of a database. Please note that relative "
                 "levels will only work if there is a max_size set for the file on the database "
                 "side."),
        elements = [
            ("used_levels", levels_absolute_or_dynamic(_("Transactionlog"), _("used"))),
            ("allocated_used_levels", levels_absolute_or_dynamic(_("Transactionlog"), _("used of allocation"))),
            ("allocated_levels", levels_absolute_or_dynamic(_("Transactionlog"), _("allocated"))),
        ]
    ),
    TextAscii(
        title = _("Database Name"),
        allow_empty = False),
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "mssql_datafiles",
    _("MSSQL Datafile Sizes"),
    Dictionary(
        title = _("File Size Levels"),
        help = _("Specify levels for datafiles of a database. Please note that relative "
                 "levels will only work if there is a max_size set for the file on the database "
                 "side."),
        elements = [
            ("used_levels", levels_absolute_or_dynamic(_("Datafile"), _("used"))),
            ("allocated_used_levels", levels_absolute_or_dynamic(_("Datafile"), _("used of allocation"))),
            ("allocated_levels", levels_absolute_or_dynamic(_("Datafile"), _("allocated"))),
        ]
    ),
    TextAscii(
        title = _("Database Name"),
        allow_empty = False),
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "vm_snapshots",
    _("Virtual Machine Snapshots"),
    Dictionary(
        elements = [
        ("age",
          Tuple(
            title = _("Age of the last snapshot"),
            elements = [
                Age(title = _("Warning if older than")),
                Age(title = _("Critical if older than"))
            ]
          )
        ),
        ("age_oldest",
          Tuple(
            title = _("Age of the oldest snapshot"),
            elements = [
                Age(title = _("Warning if older than")),
                Age(title = _("Critical if older than"))
            ]
          )
        ),
        ]
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "veeam_backup",
    _("Veeam: Time since last Backup"),
    Dictionary(
        elements = [
        ("age",
          Tuple(
            title = _("Time since end of last backup"),
            elements = [
                Age(title = _("Warning if older than"), default_value = 108000),
                Age(title = _("Critical if older than"), default_value = 172800)
            ]
          )
        )]
    ),
    TextAscii(title=_("Job name")),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "backup_timemachine",
    _("Age of timemachine backup"),
    Dictionary(
        elements = [
        ("age",
          Tuple(
            title = _("Maximum age of latest timemachine backup"),
            elements = [
                Age(title = _("Warning if older than"), default_value = 86400),
                Age(title = _("Critical if older than"), default_value = 172800)
            ]
          )
        )]
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "job",
    _("Age of jobs controlled by mk-job"),
    Dictionary(
        elements = [
        ("age", Tuple(
            title = _("Maximum time since last start of job execution"),
            elements = [
                Age(title = _("Warning at"), default_value = 0),
                Age(title = _("Critical at"), default_value = 0)
        ])),
        ("outcome_on_cluster", DropdownChoice(
            title = _("Clusters: Prefered check result of local checks"),
            help  = _("If you're running local checks on clusters via clustered services rule "
                      "you can influence the check result with this rule. You can choose between "
                      "best or worst state. Default setting is worst state."),
            choices = [
                ("worst", _("Worst state")),
                ("best",  _("Best state")),
            ],
            default_value = "worst")),
        ]
    ),
    TextAscii(
        title = _("Job name"),
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "mssql_counters_locks",
    _("MSSQL Locks"),
    Dictionary(
         help = _("This check monitors locking related information of MSSQL tablespaces."),
         elements = [
             ("lock_requests/sec",
               Tuple(
                   title = _("Lock Requests / sec"),
                   help = _("Number of new locks and lock conversions per second requested from the lock manager."),
                   elements = [
                       Float(title = _("Warning at"),  unit = _("requests/sec")),
                       Float(title = _("Critical at"), unit = _("requests/sec")),
                    ],
               ),
            ),
            ( "lock_timeouts/sec",
               Tuple(
                   title = _("Lock Timeouts / sec"),
                   help = _("Number of lock requests per second that timed out, including requests for NOWAIT locks."),
                   elements = [
                       Float(title = _("Warning at"),  unit = _("timeouts/sec")),
                       Float(title = _("Critical at"), unit = _("timeouts/sec")),
                    ],
               ),
            ),
            ( "number_of_deadlocks/sec",
               Tuple(
                   title = _("Number of Deadlocks / sec"),
                   help = _("Number of lock requests per second that resulted in a deadlock."),
                   elements = [
                       Float(title = _("Warning at"),  unit = _("deadlocks/sec")),
                       Float(title = _("Critical at"), unit = _("deadlocks/sec")),
                    ],
               ),
            ),
            ( "lock_waits/sec",
               Tuple(
                   title = _("Lock Waits / sec"),
                   help = _("Number of lock requests per second that required the caller to wait."),
                   elements = [
                       Float(title = _("Warning at"),  unit = _("waits/sec")),
                       Float(title = _("Critical at"), unit = _("waits/sec")),
                    ],
               ),
            ),
         ]
    ),
    TextAscii(
        title = _("Service descriptions"),
        allow_empty = False
    ),
    match_type = "dict",
)

mssql_waittypes = [
    "ABR", "ASSEMBLY_LOAD", "ASYNC_DISKPOOL_LOCK", "ASYNC_IO_COMPLETION", "ASYNC_NETWORK_IO","AUDIT_GROUPCACHE_LOCK",
    "AUDIT_LOGINCACHE_LOCK", "AUDIT_ON_DEMAND_TARGET_LOCK", "AUDIT_XE_SESSION_MGR", "BACKUP", "BACKUP_OPERATOR",
    "BACKUPBUFFER", "BACKUPIO", "BACKUPTHREAD", "BAD_PAGE_PROCESS", "BROKER_CONNECTION_RECEIVE_TASK",
    "BROKER_ENDPOINT_STATE_MUTEX", "BROKER_EVENTHANDLER", "BROKER_INIT", "BROKER_MASTERSTART", "BROKER_RECEIVE_WAITFOR",
    "BROKER_REGISTERALLENDPOINTS", "BROKER_SERVICE", "BROKER_SHUTDOWN", "BROKER_TASK_STOP", "BROKER_TO_FLUSH",
    "BROKER_TRANSMITTER", "BUILTIN_HASHKEY_MUTEX", "CHECK_PRINT_RECORD", "CHECKPOINT_QUEUE", "CHKPT",
    "CLEAR_DB", "CLR_AUTO_EVENT", "CLR_CRST", "CLR_JOIN", "CLR_MANUAL_EVENT", "CLR_MEMORY_SPY", "CLR_MONITOR",
    "CLR_RWLOCK_READER", "CLR_RWLOCK_WRITER", "CLR_SEMAPHORE", "CLR_TASK_START", "CLRHOST_STATE_ACCESS", "CMEMTHREAD", "CXCONSUMER",
    "CXPACKET", "CXROWSET_SYNC", "DAC_INIT", "DBMIRROR_DBM_EVENT", "DBMIRROR_DBM_MUTEX", "DBMIRROR_EVENTS_QUEUE",
    "DBMIRROR_SEND", "DBMIRROR_WORKER_QUEUE", "DBMIRRORING_CMD", "DEADLOCK_ENUM_MUTEX", "DEADLOCK_TASK_SEARCH",
    "DEBUG", "DISABLE_VERSIONING", "DISKIO_SUSPEND", "DISPATCHER_QUEUE_SEMAPHORE", "DLL_LOADING_MUTEX",
    "DROPTEMP", "DTC", "DTC_ABORT_REQUEST",  "DTC_RESOLVE", "DTC_STATE", "DTC_TMDOWN_REQUEST", "DTC_WAITFOR_OUTCOME",
    "DUMP_LOG_COORDINATOR", "DUMPTRIGGER", "EC", "EE_PMOLOCK", "EE_SPECPROC_MAP_INIT", "ENABLE_VERSIONING",
    "ERROR_REPORTING_MANAGER", "EXCHANGE",  "EXECSYNC", "EXECUTION_PIPE_EVENT_INTERNAL", "FAILPOINT","FCB_REPLICA_READ",
    "FCB_REPLICA_WRITE", "FS_FC_RWLOCK", "FS_GARBAGE_COLLECTOR_SHUTDOWN", "FS_HEADER_RWLOCK","FS_LOGTRUNC_RWLOCK",
    "FSA_FORCE_OWN_XACT", "FSAGENT", "FSTR_CONFIG_MUTEX", "FSTR_CONFIG_RWLOCK", "FT_COMPROWSET_RWLOCK",
    "FT_IFTS_RWLOCK", "FT_IFTS_SCHEDULER_IDLE_WAIT", "FT_IFTSHC_MUTEX", "FT_IFTSISM_MUTEX", "FT_MASTER_MERGE",
    "FT_METADATA_MUTEX", "FT_RESTART_CRAWL", "FULLTEXT", "GUARDIAN", "HADR_AG_MUTEX", "HADR_AR_CRITICAL_SECTION_ENTRY",
    "HADR_AR_MANAGER_MUTEX", "HADR_ARCONTROLLER_NOTIFICATIONS_SUBSCRIBER_LIST", "HADR_BACKUP_BULK_LOCK", "HADR_BACKUP_QUEUE",
    "HADR_CLUSAPI_CALL", "HADR_COMPRESSED_CACHE_SYNC", "HADR_DATABASE_FLOW_CONTROL", "HADR_DATABASE_VERSIONING_STATE",
    "HADR_DATABASE_WAIT_FOR_RESTART", "HADR_DATABASE_WAIT_FOR_TRANSITION_TO_VERSIONING", "HADR_DB_COMMAND",
    "HADR_DB_OP_COMPLETION_SYNC", "HADR_DB_OP_START_SYNC", "HADR_DBR_SUBSCRIBER", "HADR_DBR_SUBSCRIBER_FILTER_LIST",
    "HADR_DBSTATECHANGE_SYNC", "HADR_FILESTREAM_BLOCK_FLUSH", "HADR_FILESTREAM_FILE_CLOSE", "HADR_FILESTREAM_FILE_REQUEST",
    "HADR_FILESTREAM_IOMGR", "HADR_FILESTREAM_IOMGR_IOCOMPLETION", "HADR_FILESTREAM_MANAGER", "HADR_GROUP_COMMIT",
    "HADR_LOGCAPTURE_SYNC", "HADR_LOGCAPTURE_WAIT", "HADR_LOGPROGRESS_SYNC", "HADR_NOTIFICATION_DEQUEUE",
    "HADR_NOTIFICATION_WORKER_EXCLUSIVE_ACCESS", "HADR_NOTIFICATION_WORKER_STARTUP_SYNC",
    "HADR_NOTIFICATION_WORKER_TERMINATION_SYNC", "HADR_PARTNER_SYNC", "HADR_READ_ALL_NETWORKS", "HADR_RECOVERY_WAIT_FOR_CONNECTION",
    "HADR_RECOVERY_WAIT_FOR_UNDO", "HADR_REPLICAINFO_SYNC", "HADR_SYNC_COMMIT", "HADR_SYNCHRONIZING_THROTTLE",
    "HADR_TDS_LISTENER_SYNC", "HADR_TDS_LISTENER_SYNC_PROCESSING", "HADR_TIMER_TASK", "HADR_TRANSPORT_DBRLIST",
    "HADR_TRANSPORT_FLOW_CONTROL", "HADR_TRANSPORT_SESSION", "HADR_WORK_POOL", "HADR_WORK_QUEUE", "HADR_XRF_STACK_ACCESS",
    "HTTP_ENUMERATION", "HTTP_START", "IMPPROV_IOWAIT", "INTERNAL_TESTING", "IO_AUDIT_MUTEX", "IO_COMPLETION",
    "IO_RETRY", "IOAFF_RANGE_QUEUE", "KSOURCE_WAKEUP", "KTM_ENLISTMENT", "KTM_RECOVERY_MANAGER", "KTM_RECOVERY_RESOLUTION",
    "LATCH_DT", "LATCH_EX", "LATCH_KP", "LATCH_NL", "LATCH_SH", "LATCH_UP", "LAZYWRITER_SLEEP", "LCK_M_BU",
    "LCK_M_BU_ABORT_BLOCKERS", "LCK_M_BU_LOW_PRIORITY", "LCK_M_IS", "LCK_M_IS_ABORT_BLOCKERS", "LCK_M_IS_LOW_PRIORITY",
    "LCK_M_IU", "LCK_M_IU_ABORT_BLOCKERS",  "LCK_M_IU_LOW_PRIORITY", "LCK_M_IX", "LCK_M_IX_ABORT_BLOCKERS", "LCK_M_IX_LOW_PRIORITY",
    "LCK_M_RIn_NL", "LCK_M_RIn_NL_ABORT_BLOCKERS", "LCK_M_RIn_NL_LOW_PRIORITY", "LCK_M_RIn_S", "LCK_M_RIn_S_ABORT_BLOCKERS",
    "LCK_M_RIn_S_LOW_PRIORITY", "LCK_M_RIn_U", "LCK_M_RIn_U_ABORT_BLOCKERS", "LCK_M_RIn_U_LOW_PRIORITY", "LCK_M_RIn_X",
    "LCK_M_RIn_X_ABORT_BLOCKERS", "LCK_M_RIn_X_LOW_PRIORITY", "LCK_M_RS_S", "LCK_M_RS_S_ABORT_BLOCKERS", "LCK_M_RS_S_LOW_PRIORITY",
    "LCK_M_RS_U", "LCK_M_RS_U_ABORT_BLOCKERS", "LCK_M_RS_U_LOW_PRIORITY", "LCK_M_RX_S", "LCK_M_RX_S_ABORT_BLOCKERS", "LCK_M_RX_S_LOW_PRIORITY",
    "LCK_M_RX_U", "LCK_M_RX_U_ABORT_BLOCKERS", "LCK_M_RX_U_LOW_PRIORITY", "LCK_M_RX_X", "LCK_M_RX_X_ABORT_BLOCKERS",
    "LCK_M_RX_X_LOW_PRIORITY", "LCK_M_S", "LCK_M_S_ABORT_BLOCKERS", "LCK_M_S_LOW_PRIORITY", "LCK_M_SCH_M", "LCK_M_SCH_M_ABORT_BLOCKERS",
    "LCK_M_SCH_M_LOW_PRIORITY", "LCK_M_SCH_S", "LCK_M_SCH_S_ABORT_BLOCKERS", "LCK_M_SCH_S_LOW_PRIORITY", "LCK_M_SIU", "LCK_M_SIU_ABORT_BLOCKERS",
    "LCK_M_SIU_LOW_PRIORITY", "LCK_M_SIX", "LCK_M_SIX_ABORT_BLOCKERS", "LCK_M_SIX_LOW_PRIORITY", "LCK_M_U", "LCK_M_U_ABORT_BLOCKERS",
    "LCK_M_U_LOW_PRIORITY", "LCK_M_UIX", "LCK_M_UIX_ABORT_BLOCKERS", "LCK_M_UIX_LOW_PRIORITY", "LCK_M_X", "LCK_M_X_ABORT_BLOCKERS",
    "LCK_M_X_LOW_PRIORITY", "LOGBUFFER", "LOGGENERATION", "LOGMGR", "LOGMGR_FLUSH", "LOGMGR_QUEUE", "LOGMGR_RESERVE_APPEND",
    "LOWFAIL_MEMMGR_QUEUE", "MEMORY_ALLOCATION_EXT", "MISCELLANEOUS", "MSQL_DQ", "MSQL_XACT_MGR_MUTEX", "MSQL_XACT_MUTEX",
    "MSQL_XP", "MSSEARCH", "NET_WAITFOR_PACKET", "OLEDB", "ONDEMAND_TASK_QUEUE", "PAGEIOLATCH_DT", "PAGEIOLATCH_EX",
    "PAGEIOLATCH_KP", "PAGEIOLATCH_NL", "PAGEIOLATCH_SH", "PAGEIOLATCH_UP", "PAGELATCH_DT", "PAGELATCH_EX", "PAGELATCH_KP",
    "PAGELATCH_NL", "PAGELATCH_SH", "PAGELATCH_UP", "PARALLEL_BACKUP_QUEUE", "PREEMPTIVE_ABR", "PREEMPTIVE_AUDIT_ACCESS_EVENTLOG",
    "PREEMPTIVE_AUDIT_ACCESS_SECLOG", "PREEMPTIVE_CLOSEBACKUPMEDIA", "PREEMPTIVE_CLOSEBACKUPTAPE", "PREEMPTIVE_CLOSEBACKUPVDIDEVICE",
    "PREEMPTIVE_CLUSAPI_CLUSTERRESOURCECONTROL", "PREEMPTIVE_COM_COCREATEINSTANCE", "PREEMPTIVE_HADR_LEASE_MECHANISM",
    "PREEMPTIVE_SOSTESTING", "PREEMPTIVE_STRESSDRIVER", "PREEMPTIVE_TESTING", "PREEMPTIVE_XETESTING", "PRINT_ROLLBACK_PROGRESS",
    "PWAIT_HADR_CHANGE_NOTIFIER_TERMINATION_SYNC", "PWAIT_HADR_CLUSTER_INTEGRATION", "PWAIT_HADR_OFFLINE_COMPLETED",
    "PWAIT_HADR_ONLINE_COMPLETED", "PWAIT_HADR_POST_ONLINE_COMPLETED", "PWAIT_HADR_WORKITEM_COMPLETED", "PWAIT_MD_LOGIN_STATS",
    "PWAIT_MD_RELATION_CACHE", "PWAIT_MD_SERVER_CACHE", "PWAIT_MD_UPGRADE_CONFIG", "PWAIT_METADATA_LAZYCACHE_RWLOCk",
    "QPJOB_KILL", "QPJOB_WAITFOR_ABORT", "QRY_MEM_GRANT_INFO_MUTEX", "QUERY_ERRHDL_SERVICE_DONE", "QUERY_EXECUTION_INDEX_SORT_EVENT_OPEN",
    "QUERY_NOTIFICATION_MGR_MUTEX", "QUERY_NOTIFICATION_SUBSCRIPTION_MUTEX", "QUERY_NOTIFICATION_TABLE_MGR_MUTEX",
    "QUERY_NOTIFICATION_UNITTEST_MUTEX", "QUERY_OPTIMIZER_PRINT_MUTEX", "QUERY_TRACEOUT", "QUERY_WAIT_ERRHDL_SERVICE", "RECOVER_CHANGEDB",
    "REPL_CACHE_ACCESS", "REPL_SCHEMA_ACCESS", "REPLICA_WRITES", "REQUEST_DISPENSER_PAUSE", "REQUEST_FOR_DEADLOCK_SEARCH",
    "RESMGR_THROTTLED", "RESOURCE_QUEUE", "RESOURCE_SEMAPHORE", "RESOURCE_SEMAPHORE_MUTEX", "RESOURCE_SEMAPHORE_QUERY_COMPILE",
    "RESOURCE_SEMAPHORE_SMALL_QUERY", "SEC_DROP_TEMP_KEY", "SECURITY_MUTEX", "SEQUENTIAL_GUID", "SERVER_IDLE_CHECK",
    "SHUTDOWN", "SLEEP_BPOOL_FLUSH", "SLEEP_DBSTARTUP", "SLEEP_DCOMSTARTUP", "SLEEP_MSDBSTARTUP", "SLEEP_SYSTEMTASK",
    "SLEEP_TASK", "SLEEP_TEMPDBSTARTUP", "SNI_CRITICAL_SECTION", "SNI_HTTP_WAITFOR_", "SNI_LISTENER_ACCESS",
    "SNI_TASK_COMPLETION", "SOAP_READ", "SOAP_WRITE", "SOS_CALLBACK_REMOVAL", "SOS_DISPATCHER_MUTEX", "SOS_LOCALALLOCATORLIST",
    "SOS_MEMORY_USAGE_ADJUSTMENT", "SOS_OBJECT_STORE_DESTROY_MUTEX", "SOS_PHYS_PAGE_CACHE", "SOS_PROCESS_AFFINITY_MUTEX",
    "SOS_RESERVEDMEMBLOCKLIST", "SOS_SCHEDULER_YIELD", "SOS_SMALL_PAGE_ALLOC", "SOS_STACKSTORE_INIT_MUTEX", "SOS_SYNC_TASK_ENQUEUE_EVENT",
    "SOS_VIRTUALMEMORY_LOW", "SOSHOST_EVENT", "SOSHOST_INTERNAL", "SOSHOST_MUTEX", "SOSHOST_RWLOCK", "SOSHOST_SEMAPHORE",
    "SOSHOST_SLEEP", "SOSHOST_TRACELOCK", "SOSHOST_WAITFORDONE", "SQLCLR_APPDOMAIN", "SQLCLR_ASSEMBLY", "SQLCLR_DEADLOCK_DETECTION",
    "SQLCLR_QUANTUM_PUNISHMENT", "SQLSORT_NORMMUTEX", "SQLSORT_SORTMUTEX", "SQLTRACE_BUFFER_FLUSH", "SQLTRACE_FILE_BUFFER",
    "SQLTRACE_SHUTDOWN", "SQLTRACE_WAIT_ENTRIES", "SRVPROC_SHUTDOWN", "TEMPOBJ", "THREADPOOL", "TIMEPRIV_TIMEPERIOD",
    "TRACEWRITE", "TRAN_MARKLATCH_DT", "TRAN_MARKLATCH_EX", "TRAN_MARKLATCH_KP", "TRAN_MARKLATCH_NL", "TRAN_MARKLATCH_SH",
    "TRAN_MARKLATCH_UP", "TRANSACTION_MUTEX", "UTIL_PAGE_ALLOC", "VIA_ACCEPT", "VIEW_DEFINITION_MUTEX", "WAIT_FOR_RESULTS",
    "WAIT_XTP_CKPT_CLOSE", "WAIT_XTP_CKPT_ENABLED", "WAIT_XTP_CKPT_STATE_LOCK", "WAIT_XTP_GUEST", "WAIT_XTP_HOST_WAIT",
    "WAIT_XTP_OFFLINE_CKPT_LOG_IO", "WAIT_XTP_OFFLINE_CKPT_NEW_LOG", "WAIT_XTP_PROCEDURE_ENTRY", "WAIT_XTP_RECOVERY",
    "WAIT_XTP_TASK_SHUTDOWN", "WAIT_XTP_TRAN_COMMIT", "WAIT_XTP_TRAN_DEPENDENCY", "WAITFOR", "WAITFOR_TASKSHUTDOWN",
    "WAITSTAT_MUTEX", "WCC", "WORKTBL_DROP", "WRITE_COMPLETION", "WRITELOG", "XACT_OWN_TRANSACTION", "XACT_RECLAIM_SESSION",
    "XACTLOCKINFO", "XACTWORKSPACE_MUTEX", "XE_BUFFERMGR_ALLPROCESSED_EVENT", "XE_BUFFERMGR_FREEBUF_EVENT",
    "XE_DISPATCHER_CONFIG_SESSION_LIST",  "XE_DISPATCHER_JOIN", "XE_DISPATCHER_WAIT", "XE_MODULEMGR_SYNC", "XE_OLS_LOCK",
    "XE_PACKAGE_LOCK_BACKOFF", "XTPPROC_CACHE_ACCESS", "XTPPROC_PARTITIONED_STACK_CREATE", ]

register_check_parameters(
    subgroup_applications,
    "mssql_blocked_sessions",
    _("MSSQL Blocked Sessions"),
    Dictionary(
        elements = [
            (   "state",
                MonitoringState(
                    title           = _("State of MSSQL Blocked Sessions is treated as"),
                    help            = _("The default state if there is at least one "
                                        "blocked session."),
                    default_value   = 2,
            )),
            (   "waittime", Tuple(
                    title           = _("Levels for wait"),
                    help            = _("The threshholds for wait_duration_ms. Will "
                                        "overwrite the default state set above."),
                    default_value   = (0, 0),
                    elements = [
                        Float(title = _("Warning at"),  unit = _("seconds"), display_format = "%.3f"),
                        Float(title = _("Critical at"), unit = _("seconds"), display_format = "%.3f"),
                    ]
            )),
            ("ignore_waittypes", DualListChoice(
                title   = _("Ignore wait types"),
                rows    = 40,
                choices = [ (entry, entry) for entry in mssql_waittypes ],
            )),
        ],
    ),
    None,
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "mysql_sessions",
    _("MySQL Sessions & Connections"),
    Dictionary(
         help = _("This check monitors the current number of active sessions to the MySQL "
                  "database server as well as the connection rate."),
         elements = [
             ( "total",
               Tuple(
                   title = _("Number of current sessions"),
                   elements = [
                       Integer(title = _("Warning at"),  unit = _("sessions"), default_value = 100),
                       Integer(title = _("Critical at"), unit = _("sessions"), default_value = 200),
                    ],
               ),
            ),
            ( "running",
               Tuple(
                   title = _("Number of currently running sessions"),
                   help = _("Levels for the number of sessions that are currently active"),
                   elements = [
                       Integer(title = _("Warning at"),  unit = _("sessions"), default_value = 10),
                       Integer(title = _("Critical at"), unit = _("sessions"), default_value = 20),
                    ],
               ),
            ),
            ( "connections",
               Tuple(
                   title = _("Number of new connections per second"),
                   elements = [
                       Integer(title = _("Warning at"),  unit = _("connection/sec"), default_value = 20),
                       Integer(title = _("Critical at"), unit = _("connection/sec"), default_value = 40),
                    ],
               ),
            ),
         ]
    ),
    TextAscii(
        title = _("Instance"),
        help = _("Only needed if you have multiple MySQL Instances on one server"),
    ),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "mysql_innodb_io",
    _("MySQL InnoDB Throughput"),
    Dictionary(
        elements = [
            ( "read",
              Tuple(
                  title = _("Read throughput"),
                  elements = [
                      Float(title = _("warning at"), unit = _("MB/s")),
                      Float(title = _("critical at"), unit = _("MB/s"))
                  ])),
            ( "write",
              Tuple(
                  title = _("Write throughput"),
                  elements = [
                      Float(title = _("warning at"), unit = _("MB/s")),
                      Float(title = _("critical at"), unit = _("MB/s"))
                  ])),
            ( "average",
              Integer(
                  title = _("Average"),
                  help = _("When averaging is set, a floating average value "
                           "of the disk throughput is computed and the levels for read "
                           "and write will be applied to the average instead of the current "
                           "value."),
                  minvalue = 1,
                  default_value = 5,
                  unit = _("minutes")))
        ]),
    TextAscii(
        title = _("Instance"),
        help = _("Only needed if you have multiple MySQL Instances on one server"),
    ),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "mysql_connections",
    _("MySQL Connections"),
    Dictionary(
        elements = [
            ( "perc_used",
                Tuple(
                    title = _("Max. parallel connections"),
                    help = _("Compares the maximum number of connections that have been "
                             "in use simultaneously since the server started with the maximum simultaneous "
                             "connections allowed by the configuration of the server. This threshold "
                             "makes the check raise warning/critical states if the percentage is equal to "
                             "or above the configured levels."),
                    elements = [
                       Percentage(title = _("Warning at")),
                       Percentage(title = _("Critical at")),
                    ]
                )
            ),
        ]),
    TextAscii(
        title = _("Instance"),
        help = _("Only needed if you have multiple MySQL Instances on one server"),
    ),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "mysql_slave",
    _("MySQL Slave"),
    Dictionary(
        elements = [
            ( "seconds_behind_master",
                Tuple(
                    title = _("Max. time behind the master"),
                    help = _("Compares the time which the slave can be behind the master. "
                             "This rule makes the check raise warning/critical states if the time is equal to "
                             "or above the configured levels."),
                    elements = [
                       Age(title = _("Warning at")),
                       Age(title = _("Critical at")),
                    ]
                )
            ),
        ],
        optional_keys = None),
    TextAscii(
        title = _("Instance"),
        help = _("Only needed if you have multiple MySQL Instances on one server"),
    ),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "db_bloat",
    _("Database Bloat (PostgreSQL)"),
    Dictionary(
        help = _("This rule allows you to configure bloat levels for a databases tablespace and "
                 "indexspace."),
        elements = [
            ("table_bloat_abs", Tuple(
                title = _("Table absolute bloat levels"),
                elements = [
                    Filesize(title = _("Warning at")),
                    Filesize(title = _("Critical at")),
            ])),
            ("table_bloat_perc", Tuple(
                title = _("Table percentage bloat levels"),
                help = _("Percentage in respect to the optimal utilization. "
                         "For example if an alarm should raise at 50% wasted space, you need "
                         "to configure 150%"),
                elements = [
                    Percentage(title = _("Warning at"), maxvalue = None),
                    Percentage(title = _("Critical at"), maxvalue = None),
            ])),
            ("index_bloat_abs", Tuple(
                title = _("Index absolute levels"),
                elements = [
                    Filesize(title = _("Warning at")),
                    Filesize(title = _("Critical at")),
            ])),
            ("index_bloat_perc", Tuple(
                title = _("Index percentage bloat levels"),
                help = _("Percentage in respect to the optimal utilization. "
                         "For example if an alarm should raise at 50% wasted space, you need "
                         "to configure 150%"),
                elements = [
                    Percentage(title = _("Warning at"), maxvalue = None),
                    Percentage(title = _("Critical at"), maxvalue = None),
            ])),
        ]
    ),
    TextAscii(
        title = _("Name of the database"),
    ),
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "db_connections",
    _("Database Connections (PostgreSQL/MongoDB)"),
    Dictionary(
        help = _("This rule allows you to configure the number of maximum concurrent "
                "connections for a given database."),
        elements = [
            ("levels_perc", Tuple(
                title = _("Percentage of maximum available connections"),
                elements = [
                    Percentage(title = _("Warning at"),  unit=_("% of maximum connections")),
                    Percentage(title = _("Critical at"), unit=_("% of maximum connections")),
            ])),
            ("levels_abs", Tuple(
                title = _("Absolute number of connections"),
                elements = [
                    Integer(title = _("Warning at"),  minvalue = 0, unit=_("connections")),
                    Integer(title = _("Critical at"), minvalue = 0, unit=_("connections")),
            ])),
        ]
    ),
    TextAscii(
        title = _("Name of the database"),
    ),
    "dict"
)


register_check_parameters(
    subgroup_applications,
    "postgres_locks",
    _("PostgreSQL Locks"),
    Dictionary(
        help = _("This rule allows you to configure the limits for the SharedAccess and Exclusive Locks "
                 "for a PostgreSQL database."),
        elements = [
            ("levels_shared", Tuple(
                title = _("Shared Access Locks"),
                elements = [
                    Integer(title = _("Warning at"),  minvalue = 0),
                    Integer(title = _("Critical at"), minvalue = 0),
            ])),
            ("levels_exclusive", Tuple(
                title = _("Exclusive Locks"),
                elements = [
                    Integer(title = _("Warning at"),  minvalue = 0),
                    Integer(title = _("Critical at"), minvalue = 0),
            ])),
        ]
    ),
    TextAscii(
        title = _("Name of the database"),
    ),
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "postgres_maintenance",
    _("PostgreSQL VACUUM and ANALYZE"),
    Dictionary(
        help = _("With this rule you can set limits for the VACUUM and ANALYZE operation of "
                 "a PostgreSQL database. Keep in mind that each table within a database is checked "
                 "with this limits."),
        elements = [
            ("last_vacuum", Tuple(
                title = _("Time since the last VACUUM"),
                elements = [
                    Age(title = _("Warning if older than"), default_value = 86400 * 7),
                    Age(title = _("Critical if older than"), default_value = 86400 * 14)
            ])),
            ("last_analyze", Tuple(
                title = _("Time since the last ANALYZE"),
                elements = [
                    Age(title = _("Warning if older than"), default_value = 86400 * 7),
                    Age(title = _("Critical if older than"), default_value = 86400 * 14)
            ])),
            ("never_analyze_vacuum", Tuple(
                title = _("Age of never analyzed/vacuumed tables"),
                elements = [
                    Age(title = _("Warning if older than"), default_value = 86400 * 7),
                    Age(title = _("Critical if older than"), default_value = 86400 * 14)
            ])),
        ]
    ),
    TextAscii(
        title = _("Name of the database"),
    ),
    "dict"
)


register_check_parameters(
    subgroup_applications,
    "f5_connections",
    _("F5 Loadbalancer Connections"),
    Dictionary(
        elements = [
            ( "conns",
                Levels(
                     title = _("Max. number of connections"),
                     default_value = None,
                     default_levels = (25000, 30000)
                )
            ),
            ( "ssl_conns",
                Levels(
                     title = _("Max. number of SSL connections"),
                     default_value = None,
                     default_levels = (25000, 30000)
                )
            ),
            ( "connections_rate",
                Levels(
                     title = _("Maximum connections per second"),
                     default_value = None,
                     default_levels = (500, 1000)
                )
            ),
            ( "connections_rate_lower",
                Tuple(
                    title=_("Minimum connections per second"),
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                )
            ),
            ( "http_req_rate",
                Levels(
                     title = _("HTTP requests per second"),
                     default_value = None,
                     default_levels = (500, 1000)
                )
            ),
        ]),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "cisco_fw_connections",
    _("Cisco ASA Firewall Connections"),
    Dictionary(
        elements = [
            ("connections", Tuple(
                help = _("This rule sets limits to the current number of connections through "
                         "a Cisco ASA firewall."),
                title = _("Maximum number of firewall connections"),
                elements = [
                    Integer(title=_("Warning at")),
                    Integer(title=_("Critical at")),
                ],
            )),
    ]),
    None,
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "checkpoint_connections",
    _("Checkpoint Firewall Connections"),
    Tuple(
       help = _("This rule sets limits to the current number of connections through "
                "a Checkpoint firewall."),
       title = _("Maximum number of firewall connections"),
       elements = [
           Integer( title = _("Warning at"), default_value = 40000),
           Integer( title = _("Critical at"), default_value = 50000),
       ],
    ),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_applications,
    "checkpoint_packets",
    _("Checkpoint Firewall Packet Rates"),
    Dictionary(
        elements = [
            ( "accepted",
                Levels(
                     title = _("Maximum Rate of Accepted Packets"),
                     default_value = None,
                     default_levels = (100000, 200000),
                     unit = "pkts/sec"
                )
            ),
            ( "rejected",
                Levels(
                     title = _("Maximum Rate of Rejected Packets"),
                     default_value = None,
                     default_levels = (100000, 200000),
                     unit = "pkts/sec"
                )
            ),
            ( "dropped",
                Levels(
                     title = _("Maximum Rate of Dropped Packets"),
                     default_value = None,
                     default_levels = (100000, 200000),
                     unit = "pkts/sec"
                )
            ),
            ( "logged",
                Levels(
                     title = _("Maximum Rate of Logged Packets"),
                     default_value = None,
                     default_levels = (100000, 200000),
                     unit = "pkts/sec"
                )
            ),
        ]),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "f5_pools",
    _("F5 Loadbalancer Pools"),
    Tuple(
       title = _("Minimum number of pool members"),
       elements = [
           Integer( title = _("Warning if below"), unit=_("Members ")),
           Integer( title = _("Critical if below"), unit=_("Members")),
       ],
    ),
    TextAscii(title = _("Name of pool")),
    "first"
)

register_check_parameters(
    subgroup_applications,
    "mysql_db_size",
    _("Size of MySQL databases"),
    Optional(
        Tuple(
            elements = [
                Filesize(title = _("warning at")),
                Filesize(title = _("critical at")),
            ]),
        help = _("The check will trigger a warning or critical state if the size of the "
                 "database exceeds these levels."),
        title = _("Impose limits on the size of the database"),
    ),
    TextAscii(
        title = _("Name of the database"),
        help = _("Don't forget the instance: instance:dbname"),
    ),
    "first"
)

register_check_parameters(
    subgroup_applications,
    "postgres_sessions",
    _("PostgreSQL Sessions"),
    Dictionary(
         help = _("This check monitors the current number of active and idle sessions on PostgreSQL"),
         elements = [
             ( "total",
               Tuple(
                   title = _("Number of current sessions"),
                   elements = [
                       Integer(title = _("Warning at"),  unit = _("sessions"), default_value = 100),
                       Integer(title = _("Critical at"), unit = _("sessions"), default_value = 200),
                    ],
               ),
            ),
            ( "running",
               Tuple(
                   title = _("Number of currently running sessions"),
                   help = _("Levels for the number of sessions that are currently active"),
                   elements = [
                       Integer(title = _("Warning at"),  unit = _("sessions"), default_value = 10),
                       Integer(title = _("Critical at"), unit = _("sessions"), default_value = 20),
                    ],
               ),
            ),
         ]
    ),
    None,
    match_type = "dict",
    deprecated=True,
)

register_check_parameters(
    subgroup_applications,
    "postgres_instance_sessions",
    _("PostgreSQL Sessions"),
    Dictionary(
         help = _("This check monitors the current number of active and idle sessions on PostgreSQL"),
         elements = [
             ( "total",
               Tuple(
                   title = _("Number of current sessions"),
                   elements = [
                       Integer(title = _("Warning at"),  unit = _("sessions"), default_value = 100),
                       Integer(title = _("Critical at"), unit = _("sessions"), default_value = 200),
                    ],
               ),
            ),
            ( "running",
               Tuple(
                   title = _("Number of currently running sessions"),
                   help = _("Levels for the number of sessions that are currently active"),
                   elements = [
                       Integer(title = _("Warning at"),  unit = _("sessions"), default_value = 10),
                       Integer(title = _("Critical at"), unit = _("sessions"), default_value = 20),
                    ],
               ),
            ),
         ]
    ),
    TextAscii( title = _("Instance") ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "asa_svc_sessions",
    _("Cisco SSl VPN Client Sessions"),
    Tuple(
         title = _("Number of active sessions"),
         help = _("This check monitors the current number of active sessions"),
         elements = [
             Integer(title = _("Warning at"),  unit = _("sessions"), default_value = 100),
             Integer(title = _("Critical at"), unit = _("sessions"), default_value = 200),
          ],
     ),
    None,
    match_type = "first",
)

def convert_oracle_sessions(value):
    if isinstance(value, tuple):
        return {'sessions_abs' : value }
    if 'sessions_abs' not in value:
        value['sessions_abs'] = (100, 200)
    return value

register_check_parameters(
    subgroup_applications,
    "oracle_sessions",
    _("Oracle Sessions"),
    Transform(
        Dictionary(
            elements = [
                ("sessions_abs",
                    Alternative(
                        title = _("Absolute levels of active sessions"),
                        style = "dropdown",
                        help = _("This check monitors the current number of active sessions on Oracle"),
                        elements = [
                            FixedValue(None, title = _("Do not use absolute levels"), totext = ""),
                            Tuple(
                                title = _("Number of active sessions"),
                                elements = [
                                    Integer(title = _("Warning at"),  unit = _("sessions"), default_value = 100),
                                    Integer(title = _("Critical at"), unit = _("sessions"), default_value = 200),
                                    ],
                                ),
                            ],
                        )),
                ("sessions_perc",
                    Tuple(
                         title = _("Relative levels of active sessions."),
                         help =  _("Set upper levels of active sessions relative to max. number of sessions. This is optional."),
                         elements = [
                             Percentage(title = _("Warning at")),
                             Percentage(title = _("Critical at")),
                          ],
                    ),
                ),
            ],
            optional_keys = ["sessions_perc"],
        ),
        forth = convert_oracle_sessions
    ),
    TextAscii(
        title = _("Database name"),
        allow_empty = False),
    match_type = "first",
)

register_check_parameters(
    subgroup_applications,
    "oracle_locks",
    _("Oracle Locks"),
    Dictionary(
         elements = [
             ("levels",
                 Tuple(
                     title = _("Levels for minimum wait time for a lock"),
                     elements = [
                          Age(title = _("warning if higher then"), default_value = 1800),
                          Age(title = _("critical if higher then"), default_value = 3600),
                     ]
                 )
             )
         ]
    ),
    TextAscii(
        title = _("Database SID"),
        size = 12,
        allow_empty = False),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "oracle_longactivesessions",
    _("Oracle Long Active Sessions"),
    Dictionary(
         elements = [
             ("levels",
                 Tuple(
                     title = _("Levels of active sessions"),
                     elements = [
                          Integer(title = _("Warning if more than"), unit=_("sessions")),
                          Integer(title = _("Critical if more than"), unit=_("sessions")),
                     ]
                 )
             )
         ]
    ),
    TextAscii(
        title = _("Database SID"),
        size = 12,
        allow_empty = False),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "postgres_stat_database",
    _("PostgreSQL Database Statistics"),
    Dictionary(
        help = _("This check monitors how often database objects in a PostgreSQL Database are accessed"),
        elements = [
            ( "blocks_read",
                Tuple(
                   title = _("Blocks read"),
                   elements = [
                      Float(title = _("Warning at"), unit = _("blocks/s")),
                      Float(title = _("Critical at"), unit = _("blocks/s")),
                   ],
                ),
            ),
            ( "xact_commit",
                Tuple(
                   title = _("Commits"),
                   elements = [
                      Float(title = _("Warning at"), unit = _("/s")),
                      Float(title = _("Critical at"), unit = _("/s")),
                   ],
                ),
            ),
            ( "tup_fetched",
                Tuple(
                   title = _("Fetches"),
                   elements = [
                      Float(title = _("Warning at"), unit = _("/s")),
                      Float(title = _("Critical at"), unit = _("/s")),
                   ],
                ),
            ),
            ( "tup_deleted",
                Tuple(
                   title = _("Deletes"),
                   elements = [
                      Float(title = _("Warning at"), unit = _("/s")),
                      Float(title = _("Critical at"), unit = _("/s")),
                   ],
                ),
            ),
            ( "tup_updated",
                Tuple(
                   title = _("Updates"),
                   elements = [
                      Float(title = _("Warning at"), unit = _("/s")),
                      Float(title = _("Critical at"), unit = _("/s")),
                   ],
                ),
            ),
            ( "tup_inserted",
                Tuple(
                   title = _("Inserts"),
                   elements = [
                      Float(title = _("Warning at"), unit = _("/s")),
                      Float(title = _("Critical at"), unit = _("/s")),
                   ],
                ),
            ),
        ],
    ),
    TextAscii(
        title = _("Database name"),
        allow_empty = False),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "win_dhcp_pools",
    _("DHCP Pools for Windows and Linux"),
    Transform(
        Dictionary(
            elements = [
                ("free_leases",
                    Alternative(
                        title = _("Free leases levels"),
                        elements = [
                            Tuple(
                                title = _("Free leases levels in percent"),
                                elements = [
                                    Percentage(title = _("Warning if below"),  default_value = 10.0),
                                    Percentage(title = _("Critical if below"), default_value = 5.0)
                                ]
                            ),
                            Tuple(
                                title = _("Absolute free leases levels"),
                                elements = [
                                    Integer(title = _("Warning if below"),  unit = _("free leases")),
                                    Integer(title = _("Critical if below"), unit = _("free leases"))
                                ]
                            )
                        ]
                    )
                ),
                ("used_leases",
                    Alternative(
                        title = _("Used leases levels"),
                        elements = [
                            Tuple(
                                title = _("Used leases levels in percent"),
                                elements = [
                                    Percentage(title = _("Warning if below")),
                                    Percentage(title = _("Critical if below"))
                                ]
                            ),
                            Tuple(
                                title = _("Absolute used leases levels"),
                                elements = [
                                    Integer(title = _("Warning if below"),  unit = _("used leases")),
                                    Integer(title = _("Critical if below"), unit = _("used leases"))
                                ]
                            )
                        ]
                    )
                ),
            ]
        ),
        forth = lambda params: type(params) == tuple and {"free_leases" : (float(params[0]), float(params[1]))} or params,
    ),
    TextAscii(
        title = _("Pool name"),
        allow_empty = False,
    ),
    match_type = "first",
)

register_check_parameters(
    subgroup_os,
    "threads",
    _("Number of threads"),
    Tuple(
          help = _("These levels check the number of currently existing threads on the system. Each process has at "
                   "least one thread."),
          elements = [
              Integer(title = _("Warning at"), unit = _("threads"), default_value = 1000),
              Integer(title = _("Critical at"), unit = _("threads"), default_value = 2000)]),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_os,
    "logins",
    _("Number of Logins on System"),
    Tuple(
          help = _("This rule defines upper limits for the number of logins on a system."),
          elements = [
              Integer(title = _("Warning at"), unit = _("users"), default_value = 20),
              Integer(title = _("Critical at"), unit = _("users"), default_value = 30)]),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_applications,
    "vms_procs",
    _("Number of processes on OpenVMS"),
    Optional(
        Tuple(
              elements = [
                  Integer(title = _("Warning at"), unit = _("processes"), default_value = 100),
                  Integer(title = _("Critical at"), unit = _("processes"), default_value = 200)]),
        title = _("Impose levels on number of processes"),
    ),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_os,
    "vm_counter",
    _("Number of kernel events per second"),
    Levels(
          help = _("This ruleset applies to several similar checks measing various kernel "
                   "events like context switches, process creations and major page faults. "
                   "Please create separate rules for each type of kernel counter you "
                   "want to set levels for."),
          unit = _("events per second"),
          default_levels = (1000, 5000),
          default_difference = (500.0, 1000.0),
          default_value = None,
    ),
    DropdownChoice(
        title = _("kernel counter"),
        choices = [
           ( "Context Switches",  _("Context Switches") ),
           ( "Process Creations", _("Process Creations") ),
           ( "Major Page Faults", _("Major Page Faults") )]),
    "first"
)

register_check_parameters(
    subgroup_storage,
    "ibm_svc_total_latency",
    _("IBM SVC: Levels for total disk latency"),
    Dictionary(
        elements = [
            ( "read",
              Levels(
                  title = _("Read latency"),
                  unit = _("ms"),
                  default_value = None,
                  default_levels = (50.0, 100.0))),
            ( "write",
              Levels(
                  title = _("Write latency"),
                  unit = _("ms"),
                  default_value = None,
                  default_levels = (50.0, 100.0))),
        ]
    ),
    DropdownChoice(
        choices = [ ( "Drives",  _("Total latency for all drives") ),
                    ( "MDisks",  _("Total latency for all MDisks") ),
                    ( "VDisks",  _("Total latency for all VDisks") ),
                  ],
        title = _("Disk/Drive type"),
        help = _("Please enter <tt>Drives</tt>, <tt>Mdisks</tt> or <tt>VDisks</tt> here.")),
    match_type = "dict",
)

def transform_ibm_svc_host(params):
    if params == None:
        # Old inventory rule until version 1.2.7
        # params were None instead of emtpy dictionary
        params = { 'always_ok': False }

    if 'always_ok' in params:
        if params['always_ok'] == False:
            params = { 'degraded_hosts': (1,1), 'offline_hosts': (1,1), 'other_hosts': (1,1) }
        else:
            params = {}
    return params

register_check_parameters(
    subgroup_storage,
    "ibm_svc_host",
    _("IBM SVC: Options for SVC Hosts Check"),
    Transform(
        Dictionary(
            elements = [
                ( "active_hosts",
                    Tuple(
                        title = _("Count of active hosts"),
                        elements = [
                            Integer(title = _("Warning at or below"), minvalue = 0, unit = _("active hosts")),
                            Integer(title = _("Critical at or below"), minvalue = 0, unit = _("active hosts")),
                        ]
                    ),
                ),
                ( "inactive_hosts",
                    Tuple(
                        title = _("Count of inactive hosts"),
                        elements = [
                            Integer(title = _("Warning at or above"), minvalue = 0, unit = _("inactive hosts")),
                            Integer(title = _("Critical at or above"), minvalue = 0, unit = _("inactive hosts")),
                        ]
                    ),
                ),
                ( "degraded_hosts",
                    Tuple(
                        title = _("Count of degraded hosts"),
                        elements = [
                            Integer(title = _("Warning at or above"), minvalue = 0, unit = _("degraded hosts")),
                            Integer(title = _("Critical at or above"), minvalue = 0, unit = _("degraded hosts")),
                        ]
                    ),
                ),
                ( "offline_hosts",
                    Tuple(
                        title = _("Count of offline hosts"),
                        elements = [
                            Integer(title = _("Warning at or above"), minvalue = 0, unit = _("offline hosts")),
                            Integer(title = _("Critical at or above"), minvalue = 0, unit = _("offline hosts")),
                        ]
                    ),
                ),
                ( "other_hosts",
                    Tuple(
                        title = _("Count of other hosts"),
                        elements = [
                            Integer(title = _("Warning at or above"), minvalue = 0, unit = _("other hosts")),
                            Integer(title = _("Critical at or above"), minvalue = 0, unit = _("other hosts")),
                        ]
                    ),
                ),
            ]
        ),
        forth = transform_ibm_svc_host,
    ),
    None,
    "dict",
)

register_check_parameters(
    subgroup_storage,
    "ibm_svc_mdisk",
    _("IBM SVC: Options for SVC Disk Check"),
    Dictionary(
        optional_keys = False,
        elements = [
            ( "online_state",
                MonitoringState(
                    title = _("Resulting state if disk is online"),
                    default_value = 0,
                ),
            ),
            ( "degraded_state",
                MonitoringState(
                    title = _("Resulting state if disk is degraded"),
                    default_value = 1,
                ),
            ),
            ( "offline_state",
                MonitoringState(
                    title = _("Resulting state if disk is offline"),
                    default_value = 2,
                ),
            ),
            ( "excluded_state",
                MonitoringState(
                    title = _("Resulting state if disk is excluded"),
                    default_value = 2,
                ),
            ),
            ( "managed_mode",
                MonitoringState(
                    title= _("Resulting state if disk is in managed mode"),
                    default_value = 0,
                ),
            ),
            ( "array_mode",
                MonitoringState(
                    title = _("Resulting state if disk is in array mode"),
                    default_value = 0,
                ),
            ),
            ( "image_mode",
                MonitoringState(
                    title = _("Resulting state if disk is in image mode"),
                    default_value = 0,
                ),
            ),
            ( "unmanaged_mode",
                MonitoringState(
                    title = _("Resulting state if disk is in unmanaged mode"),
                    default_value = 1,
                ),
            ),
        ]
    ),
    TextAscii(
        title = _("IBM SVC disk"),
        help = _("Name of the disk, e.g. mdisk0"),
    ),
    "dict",
)



register_check_parameters(
    subgroup_storage,
    "diskstat",
    _("Levels for disk IO"),
    Dictionary(
        help     = _("With this rule you can set limits for various disk IO statistics. "
                     "Keep in mind that not all of these settings may be applicable for the actual "
                     "check. For example, if the check doesn't provide a <i>Read wait</i> information in its "
                     "output, any configuration setting referring to <i>Read wait</i> will have no effect."),
        elements = [
            ( "read",
              Levels(
                  title = _("Read throughput"),
                  unit = _("MB/s"),
                  default_levels = (50.0, 100.0),
            )),
            ( "write",
              Levels(
                  title = _("Write throughput"),
                  unit = _("MB/s"),
                  default_levels = (50.0, 100.0),
            )),
            ( "utilization",
              Levels(
                  title = _("Disk Utilization"),
                  unit = _("%"),
                  default_levels = (80.0, 90.0),
            )),
            ( "latency",
              Levels(
                  title = _("Disk Latency"),
                  unit = _("ms"),
                  default_levels = (80.0, 160.0),
            )),
            ("read_latency",
             Levels(
                 title=_("Disk Read Latency"),
                 unit=_("ms"),
                 default_levels=(80.0, 160.0),
             )),
            ("write_latency",
             Levels(
                 title=_("Disk Write Latency"),
                 unit=_("ms"),
                 default_levels=(80.0, 160.0),
             )),
            ( "read_wait",
              Levels(
                  title = _("Read wait"),
                  unit = _("ms"),
                  default_levels = (30.0, 50.0))),
            ( "write_wait",
              Levels(
                  title = _("Write wait"),
                  unit = _("ms"),
                  default_levels = (30.0, 50.0))),
            ( "average",
              Age(
                  title = _("Averaging"),
                  help = _("When averaging is set, then all of the disk's metrics are averaged "
                           "over the selected interval - rather then the check interval. This allows "
                           "you to make your monitoring less reactive to short peaks. But it will also "
                           "introduce a loss of accuracy in your graphs. "),
                  default_value = 300,
            )),
        ]),
    TextAscii(
        title = _("Device"),
        help = _("For a summarized throughput of all disks, specify <tt>SUMMARY</tt>,  "
                 "a per-disk IO is specified by the drive letter, a colon and a slash on Windows "
                 "(e.g. <tt>C:/</tt>) or by the device name on Linux/UNIX (e.g. <tt>/dev/sda</tt>).")
    ),
    "dict",
)


register_check_parameters(
    subgroup_storage,
    "disk_io",
    _("Levels on disk IO (old style checks)"),
    Dictionary(
        elements = [
            ( "read",
              Levels(
                  title = _("Read throughput"),
                  unit = _("MB/s"),
                  default_value = None,
                  default_levels = (50.0, 100.0))),
            ( "write",
              Levels(
                  title = _("Write throughput"),
                  unit = _("MB/s"),
                  default_value = None,
                  default_levels = (50.0, 100.0))),
            ( "average",
              Integer(
                  title = _("Average"),
                  help = _("When averaging is set, a floating average value "
                           "of the disk throughput is computed and the levels for read "
                           "and write will be applied to the average instead of the current "
                           "value."),
                  default_value = 5,
                  minvalue = 1,
                  unit = _("minutes"))),
            ( "latency",
              Tuple(
                  title = _("IO Latency"),
                  elements = [
                      Float(title = _("warning at"),  unit = _("ms"), default_value = 80.0),
                      Float(title = _("critical at"), unit = _("ms"), default_value = 160.0),
             ])),
            ( "latency_perfdata",
              Checkbox(
                  title = _("Performance Data for Latency"),
                  label = _("Collect performance data for disk latency"),
                  help = _("Note: enabling performance data for the latency might "
                           "cause incompatibilities with existing historical data "
                           "if you are running PNP4Nagios in SINGLE mode.")),
            ),
            ( "read_ql",
              Tuple(
                  title = _("Read Queue-Length"),
                  elements = [
                      Float(title = _("warning at"),  default_value = 80.0),
                      Float(title = _("critical at"), default_value = 90.0),
             ])),
            ( "write_ql",
              Tuple(
                  title = _("Write Queue-Length"),
                  elements = [
                      Float(title = _("warning at"),  default_value = 80.0),
                      Float(title = _("critical at"), default_value = 90.0),
             ])),
            ( "ql_perfdata",
              Checkbox(
                  title = _("Performance Data for Queue Length"),
                  label = _("Collect performance data for disk latency"),
                  help = _("Note: enabling performance data for the latency might "
                           "cause incompatibilities with existing historical data "
                           "if you are running PNP4Nagios in SINGLE mode.")),
            ),
        ]),
    TextAscii(
        title = _("Device"),
        help = _("For a summarized throughput of all disks, specify <tt>SUMMARY</tt>, for a "
                 "sum of read or write throughput write <tt>read</tt> or <tt>write</tt> resp. "
                 "A per-disk IO is specified by the drive letter, a colon and a slash on Windows "
                 "(e.g. <tt>C:/</tt>) or by the device name on Linux/UNIX (e.g. <tt>/dev/sda</tt>).")),
    "dict"
)


register_rule(
    group + '/' + subgroup_storage,
    "diskstat_inventory",
    ListChoice(
        title = _("Discovery mode for Disk IO check"),
        help = _("This rule controls which and how many checks will be created "
                 "for monitoring individual physical and logical disks. "
                 "Note: the option <i>Create a summary for all read, one for "
                 "write</i> has been removed. Some checks will still support "
                 "this settings, but it will be removed there soon."),
        choices = [
           ( "summary",  _("Create a summary over all physical disks") ),
           # This option is still supported by some checks, but is deprecated and
           # we fade it out...
           # ( "legacy",   _("Create a summary for all read, one for write") ),
           ( "physical", _("Create a separate check for each physical disk") ),
           ( "lvm",      _("Create a separate check for each LVM volume (Linux)") ),
           ( "vxvm",     _("Creata a separate check for each VxVM volume (Linux)") ),
           ( "diskless", _("Creata a separate check for each partition (XEN)") ),
        ],
        default_value = [ 'summary' ],
    ),
    match="first")


def transform_if_groups_forth(params):
    for param in params:
        if param.get("name"):
            param["group_name"] = param["name"]
            del param["name"]
        if param.get("include_items"):
            param["items"] = param["include_items"]
            del param["include_items"]
        if param.get("single") is not None:
            if param["single"]:
                param["group_presence"] = "instead"
            else:
                param["group_presence"] = "separate"
            del param["single"]
    return params


vs_elements_if_groups_matches = [
    ("iftype", Transform(
        DropdownChoice(
            title = _("Select interface port type"),
            choices = defines.interface_port_types(),
            help = _("Only interfaces with the given port type are put into this group. "
                     "For example 53 (propVirtual)."),
        ), forth = lambda x: str(x),
           back  = lambda x: int(x),
    )),
    ("items", ListOfStrings(
        title = _("Restrict interface items"),
        help =  _("Only interface with these item names are put into this group."),
    )),
]


vs_elements_if_groups_group = [
    ("group_name", TextAscii(
        title = _("Group name"),
        help  = _("Name of group in service description"),
        allow_empty = False,
    )),
    ("group_presence", DropdownChoice(
        title   = _("Group interface presence"),
        help    = _("Determine whether the group interface is created as an "
                    "separate service or not. In second case the choosen interface "
                    "services disapear."),
        choices = [
            ("separate", _("List grouped interfaces separately")),
            ("instead",  _("List grouped interfaces instead")),
        ],
        default_value = "instead",
    )),
]


register_rule(group + '/' + subgroup_networking,
    varname   = "if_groups",
    title     = _('Network interface groups'),
    help      = _('Normally the Interface checks create a single service for interface. '
                  'By defining if-group patterns multiple interfaces can be combined together. '
                  'A single service is created for this interface group showing the total traffic amount '
                  'of its members. You can configure if interfaces which are identified as group interfaces '
                  'should not show up as single service. You can restrict grouped interfaces by iftype and the '
                  'item name of the single interface.'),
    valuespec = Transform(Alternative(
        style    = "dropdown",
        elements = [
            ListOf(
                title     = _("Groups on single host"),
                add_label = _("Add pattern"),
                valuespec = Dictionary(
                    elements = vs_elements_if_groups_group + \
                               vs_elements_if_groups_matches,
                    required_keys = [ "group_name", "group_presence" ]
                ),
            ),
            ListOf(
                magic     = "@!!",
                title     = _("Groups on cluster"),
                add_label = _("Add pattern"),
                valuespec = Dictionary(
                    elements = vs_elements_if_groups_group + [
                        ("node_patterns", ListOf(
                            title     = _("Patterns for each node"),
                            add_label = _("Add pattern"),
                            valuespec = Dictionary(
                                elements = [
                                    ( "node_name", TextAscii(
                                        title = _("Node name") ) )
                                ] + vs_elements_if_groups_matches,
                                required_keys = [ "node_name" ]
                            ),
                            allow_empty = False,
                        ))
                    ],
                    optional_keys = []
            )),
        ],
    ), forth = transform_if_groups_forth ),
    match = 'all',
)

register_rule(group + '/' + subgroup_inventory,
    varname   = "winperf_msx_queues_inventory",
    title     = _('MS Exchange Message Queues Discovery'),
    help      = _('Per default the offsets of all Windows performance counters are preconfigured in the check. '
                  'If the format of your counters object is not compatible then you can adapt the counter '
                  'offsets manually.'),
    valuespec = ListOf(
                    Tuple(
                        orientation = "horizontal",
                        elements = [
                            TextAscii(
                                title = _("Name of Counter"),
                                help  = _("Name of the Counter to be monitored."),
                                size = 50,
                                allow_empty = False,
                            ),
                            Integer(
                                title = _("Offset"),
                                help  = _("The offset of the information relative to counter base"),
                                allow_empty = False,
                            ),
                        ]),
                    movable = False,
                    add_label = _("Add Counter")),
    match = 'all',
)

mailqueue_params = Dictionary(
    elements = [
        ( "deferred",
            Tuple(
                title = _("Mails in outgoing mail queue/deferred mails"),
                help = _("This rule is applied to the number of E-Mails currently "
                         "in the deferred mail queue, or in the general outgoing mail "
                         "queue, if such a distinction is not available."),
                elements = [
                    Integer(title = _("Warning at"), unit = _("mails"), default_value = 10),
                    Integer(title = _("Critical at"), unit = _("mails"), default_value = 20),
                ],
            ),
        ),
        ( "active",
            Tuple(
                title = _("Mails in active mail queue"),
                help = _("This rule is applied to the number of E-Mails currently "
                         "in the active mail queue"),
                elements = [
                    Integer(title = _("Warning at"), unit = _("mails"), default_value = 800),
                    Integer(title = _("Critical at"), unit = _("mails"), default_value = 1000),
                ],
            ),
        ),
    ],
    optional_keys = [ "active" ],
)

register_check_parameters(
    subgroup_applications,
    "mailqueue_length",
    _("Number of mails in outgoing mail queue"),
    Transform(
        mailqueue_params,
        forth = lambda old: type(old) != dict and { "deferred" : old } or old,
    ),
    None,
    match_type = "dict",
    deprecated=True,
)

register_check_parameters(
    subgroup_applications,
    "mail_queue_length",
    _("Number of mails in outgoing mail queue"),
    Transform(
        mailqueue_params,
        forth = lambda old: type(old) != dict and { "deferred" : old } or old,
    ),
    TextAscii(title = _("Mail queue name")),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "mail_latency",
    _("Mail Latency"),
    Tuple(
        title = _("Upper levels for Mail Latency"),
        elements = [
            Age(title = _("Warning at"),  default_value = 40),
            Age(title = _("Critical at"), default_value = 60),
        ]),
    None,
    "first"
)


register_check_parameters(
    subgroup_storage,
    "zpool_status",
    _("ZFS storage pool status"),
    None,
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_virt,
    "vm_state",
    _("Overall state of a virtual machine (for example ESX VMs)"),
    None,
    None,
    match_type = "first",
)


register_check_parameters(
    subgroup_hardware,
    "hw_errors",
    _("Simple checks for BIOS/Hardware errors"),
    None,
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_applications,
    "omd_status",
    _("OMD site status"),
    None,
    TextAscii(
        title = _("Name of the OMD site"),
        help = _("The name of the OMD site to check the status for")),
    "first"
)

register_check_parameters(
    subgroup_storage,
    "network_fs",
    _("Network filesystem - overall status (e.g. NFS)"),
    Dictionary(
        elements = [
            ("has_perfdata",
                DropdownChoice(
                    title = _("Performance data settings"),
                    choices = [
                         (True,  _("Enable performance data")),
                         (False, _("Disable performance data")),
                    ],
                    default_value = False
                ),
            ),
        ],
    ),
    TextAscii(
        title = _("Name of the mount point"),
        help = _("For NFS enter the name of the mount point.")),
    "dict"
)

register_check_parameters(
    subgroup_storage,
    "windows_multipath",
    _("Windows Multipath Count"),
    Alternative(
        help = _("This rules sets the expected number of active paths for a multipath LUN."),
        title = _("Expected number of active paths"),
        elements = [
            Integer(
                title = _("Expected number of active paths")),
            Tuple(
                title = _("Expected percentage of active paths"),
                elements = [
                    Integer(
                        title = _("Expected number of active paths")),
                    Percentage(
                        title = _("Warning if less then")),
                    Percentage(
                        title = _("Critical if less then")),
                    ]),
        ]
    ),
    None,
    "first",
)

register_check_parameters(
    subgroup_storage,
    "multipath",
    _("Linux and Solaris Multipath Count"),
    Alternative(
        help = _("This rules sets the expected number of active paths for a multipath LUN "
                 "on Linux and Solaris hosts"),
        title = _("Expected number of active paths"),
        elements = [
            Integer(
                title = _("Expected number of active paths")),
            Tuple(
                title = _("Expected percentage of active paths"),
                elements = [
                    Percentage(
                        title = _("Warning if less then")),
                    Percentage(
                        title = _("Critical if less then")),
                    ]),
        ]
    ),
    TextAscii(
        title = _("Name of the MP LUN"),
        help = _("For Linux multipathing this is either the UUID (e.g. "
                 "60a9800043346937686f456f59386741), or the configured "
                 "alias.")),
    "first"
)

register_rule(
    "checkparams/" + subgroup_storage,
    varname   = "inventory_multipath_rules",
    title     = _("Linux Multipath Inventory"),
    valuespec = Dictionary(
        elements = [
            ("use_alias", Checkbox(
                     title = _("Use the multipath alias as service name, if one is set"),
                         label = _("use alias"),
                         help = _("If a multipath device has an alias then you can use it for specifying "
                                  "the device instead of the UUID. The alias will then be part of the service "
                                  "description. The UUID will be displayed in the plugin output."))
            ),
        ],
        help = _("This rule controls whether the UUID or the alias is used in the service description during "
                 "discovery of Multipath devices on Linux."),
    ),
    match = 'dict',
)

register_check_parameters(
     subgroup_storage,
    "multipath_count",
    _("ESX Multipath Count"),
    Alternative(
            help = _("This rules sets the expected number of active paths for a multipath LUN "
                     "on ESX servers"),
            title = _("Match type"),
            elements = [
                    FixedValue(
                        None,
                        title = _("OK if standby count is zero or equals active paths."),
                        totext  = "",
                    ),
                    Dictionary(
                        title = _("Custom settings"),
                        elements = [ (element,
                                      Transform(
                                            Tuple(
                                                title = description,
                                                elements = [
                                                    Integer(title = _("Critical if less than")),
                                                    Integer(title = _("Warning if less than")),
                                                    Integer(title = _("Warning if more than")),
                                                    Integer(title = _("Critical if more than")),
                                                ]
                                            ),
                                            forth = lambda x: len(x) == 2 and (0, 0, x[0], x[1]) or x
                                         )
                                         ) for (element, description) in [
                                                 ("active",   _("Active paths")),
                                                 ("dead",     _("Dead paths")),
                                                 ("disabled", _("Disabled paths")),
                                                 ("standby",  _("Standby paths")),
                                                 ("unknown",  _("Unknown paths"))
                                                ]
                                        ]
                        ),
                    ]
    ),
    TextAscii(
        title = _("Path ID")),
    "first"
)



register_check_parameters(
     subgroup_storage,
    "hpux_multipath",
    _("HP-UX Multipath Count"),
    Tuple(
        title = _("Expected path situation"),
        help = _("This rules sets the expected number of various paths for a multipath LUN "
                 "on HPUX servers"),
        elements = [
            Integer(title = _("Number of active paths")),
            Integer(title = _("Number of standby paths")),
            Integer(title = _("Number of failed paths")),
            Integer(title = _("Number of unopen paths")),
        ]),
    TextAscii(
        title = _("WWID of the LUN")),
    "first"
)

register_check_parameters(
    subgroup_storage,
    "drbd",
    _("DR:BD roles and diskstates"),
    Dictionary(
        elements = [
            ( "roles",
              Alternative(
                  title = _("Roles"),
                  elements = [
                        FixedValue(None, totext = "", title = _("Do not monitor")),
                        ListOf(
                          Tuple(
                              orientation = "horizontal",
                              elements = [
                                  DropdownChoice(
                                      title = _("DRBD shows up as"),
                                      default_value = "running",
                                      choices = [
                                          ( "primary_secondary",   _("Primary / Secondary")   ),
                                          ( "primary_primary",     _("Primary / Primary")     ),
                                          ( "secondary_primary",   _("Secondary / Primary")   ),
                                          ( "secondary_secondary", _("Secondary / Secondary") )
                                      ]
                                  ),
                                  MonitoringState(
                                      title = _("Resulting state"),
                                  ),
                              ],
                              default_value = ( "ignore",  0)
                          ),
                          title = _("Set roles"),
                          add_label = _("Add role rule")
                        )
                    ]
                )
            ),
            ( "diskstates",
                Alternative(
                    title = _("Diskstates"),
                    elements = [
                            FixedValue(None, totext = "", title = _("Do not monitor")),
                            ListOf(
                                Tuple(
                                    elements = [
                                    DropdownChoice(
                                        title = _("Diskstate"),
                                        choices = [
                                              ( "primary_Diskless",       _("Primary - Diskless") ),
                                              ( "primary_Attaching",      _("Primary - Attaching") ),
                                              ( "primary_Failed",         _("Primary - Failed") ),
                                              ( "primary_Negotiating",    _("Primary - Negotiating") ),
                                              ( "primary_Inconsistent",   _("Primary - Inconsistent") ),
                                              ( "primary_Outdated",       _("Primary - Outdated") ),
                                              ( "primary_DUnknown",       _("Primary - DUnknown") ),
                                              ( "primary_Consistent",     _("Primary - Consistent") ),
                                              ( "primary_UpToDate",       _("Primary - UpToDate") ),
                                              ( "secondary_Diskless",     _("Secondary - Diskless") ),
                                              ( "secondary_Attaching",    _("Secondary - Attaching") ),
                                              ( "secondary_Failed",       _("Secondary - Failed") ),
                                              ( "secondary_Negotiating",  _("Secondary - Negotiating") ),
                                              ( "secondary_Inconsistent", _("Secondary - Inconsistent") ),
                                              ( "secondary_Outdated",     _("Secondary - Outdated") ),
                                              ( "secondary_DUnknown",     _("Secondary - DUnknown") ),
                                              ( "secondary_Consistent",   _("Secondary - Consistent") ),
                                              ( "secondary_UpToDate",     _("Secondary - UpToDate") ),
                                        ]
                                    ),
                                    MonitoringState( title = _("Resulting state") )
                                    ],
                                    orientation = "horizontal",
                                ),
                                title     = _("Set diskstates"),
                                add_label = _("Add diskstate rule")
                            )
                    ]
                ),
            )
        ]
    ),
    TextAscii( title = _("DRBD device") ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_storage,
    "snapvault",
    _("NetApp Snapvaults / Snapmirror Lag Time"),
    Dictionary(
         elements = [
             ("lag_time",
               Tuple(
                   title = _("Default levels"),
                   elements = [
                       Age(title = _("Warning at")),
                       Age(title = _("Critical at")),
                    ],
               ),
             ),
             ("policy_lag_time",
               ListOf(
                   Tuple(
                       orientation = "horizontal",
                       elements = [
                           TextAscii(title = _("Policy name")),
                                Tuple(
                                    title = _("Maximum age"),
                                    elements = [
                                        Age(title = _("Warning at")),
                                        Age(title = _("Critical at")),
                                     ],
                                ),
                       ]
                   ),
                   title = _('Policy specific levels (Clustermode only)'),
                   help = _("Here you can specify levels for different policies which overrule the levels "
                            "from the <i>Default levels</i> parameter. This setting only works in NetApp Clustermode setups."),
                   allow_empty = False,
               )
            )
         ],
    ),
    TextAscii(
        title = _("Source Path"),
        allow_empty = False
    ),
    "dict",
)

register_check_parameters(
    subgroup_storage,
    "netapp_snapshots",
    _("NetApp Snapshot Reserve"),
    Dictionary(
        elements = [
            ( "levels",
            Tuple(
                title = _("Levels for used configured reserve"),
                elements = [
                    Percentage(title = _("Warning at or above"),  unit = "%", default_value = 85.0),
                    Percentage(title = _("Critical at or above"), unit = "%", default_value = 90.0),
                ]
            )),
            ( "state_noreserve",
               MonitoringState(
                   title = _("State if no reserve is configured"),
            )),
        ],
    ),
    TextAscii(title = _("Volume name")),
    match_type = "dict",
)

register_check_parameters(
    subgroup_storage,
    "netapp_disks",
    _("Filer Disk Levels (NetApp, IBM SVC)"),
    Transform(
        Dictionary(
            elements = [
                ( "failed_spare_ratio",
                Tuple(
                    title = _("Failed to spare ratio"),
                    help  = _("You can set a limit to the failed to spare disk ratio. "
                              "The ratio is calculated with <i>spare / (failed + spare)</i>."),
                    elements = [
                        Percentage(title = _("Warning at or above"), default_value = 1.0),
                        Percentage(title = _("Critical at or above"), default_value = 50.0),
                    ]
                )),
                ( "offline_spare_ratio",
                Tuple(
                    title = _("Offline to spare ratio"),
                    help  = _("You can set a limit to the offline to spare disk ratio. "
                              "The ratio is calculated with <i>spare / (offline + spare)</i>."),
                    elements = [
                        Percentage(title = _("Warning at or above"), default_value = 1.0),
                        Percentage(title = _("Critical at or above"), default_value = 50.0),
                    ]
                )),
            ],
        ),
        forth = lambda a: "broken_spare_ratio" in a and {"failed_spare_ratio": a["broken_spare_ratio"]} or a
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_storage,
    "netapp_volumes",
    _("NetApp Volumes"),
    Dictionary(
        elements = [
             ("levels",
                Alternative(
                    title = _("Levels for volume"),
                    show_alternative_title = True,
                    default_value = (80.0, 90.0),
                    match = match_dual_level_type,
                    elements = [
                           get_free_used_dynamic_valuespec("used", "volume"),
                           Transform(
                                    get_free_used_dynamic_valuespec("free", "volume", default_value = (20.0, 10.0)),
                                    allow_empty = False,
                                    forth = transform_filesystem_free,
                                    back  = transform_filesystem_free
                           )
                    ]
                 )
            ),
            ("perfdata",
                ListChoice(
                    title = _("Performance data for protocols"),
                    help = _("Specify for which protocol performance data should get recorded."),
                    choices = [
                       ( "", _("Summarized data of all protocols") ),
                       ( "nfs",    _("NFS") ),
                       ( "cifs",   _("CIFS") ),
                       ( "san",    _("SAN") ),
                       ( "fcp",    _("FCP") ),
                       ( "iscsi",  _("iSCSI") ),
                    ],
                )),
            (  "magic",
               Float(
                  title = _("Magic factor (automatic level adaptation for large volumes)"),
                  default_value = 0.8,
                  minvalue = 0.1,
                  maxvalue = 1.0)),
            (  "magic_normsize",
               Integer(
                   title = _("Reference size for magic factor"),
                   default_value = 20,
                   minvalue = 1,
                   unit = _("GB"))),
            ( "levels_low",
              Tuple(
                  title = _("Minimum levels if using magic factor"),
                  help = _("The volume levels will never fall below these values, when using "
                           "the magic factor and the volume is very small."),
                  elements = [
                      Percentage(title = _("Warning if above"),  unit = _("% usage"), allow_int = True, default_value=50),
                      Percentage(title = _("Critical if above"), unit = _("% usage"), allow_int = True, default_value=60)])),
            ( "inodes_levels",
                Alternative(
                    title = _("Levels for Inodes"),
                    help  = _("The number of remaining inodes on the filesystem. "
                              "Please note that this setting has no effect on some filesystem checks."),
                    elements = [
                            Tuple(title = _("Percentage free"),
                                  elements = [
                                       Percentage(title = _("Warning if less than")),
                                       Percentage(title = _("Critical if less than")),
                                  ]
                            ),
                            Tuple(title = _("Absolute free"),
                                  elements = [
                                       Integer(title = _("Warning if less than"),  size = 10, unit = _("inodes"), minvalue = 0, default_value = 10000),
                                       Integer(title = _("Critical if less than"), size = 10, unit = _("inodes"), minvalue = 0, default_value = 5000),
                                  ]
                            )
                    ],
                    default_value = (10.0, 5.0),
                )
            ),
            ( "show_inodes",
              DropdownChoice(
                  title = _("Display inode usage in check output..."),
                  choices = [
                    ( "onproblem", _("Only in case of a problem")),
                    ( "onlow",     _("Only in case of a problem or if inodes are below 50%")),
                    ( "always",    _("Always")),
                  ],
                  default_value = "onlow",
            )),
            (  "trend_range",
               Optional(
                   Integer(
                       title = _("Time Range for filesystem trend computation"),
                       default_value = 24,
                       minvalue = 1,
                       unit= _("hours")),
                   title = _("Trend computation"),
                   label = _("Enable trend computation"))),
            (  "trend_mb",
               Tuple(
                   title = _("Levels on trends in MB per time range"),
                   elements = [
                       Integer(title = _("Warning at"), unit = _("MB / range"), default_value = 100),
                       Integer(title = _("Critical at"), unit = _("MB / range"), default_value = 200)
                   ])),
            (  "trend_perc",
               Tuple(
                   title = _("Levels for the percentual growth per time range"),
                   elements = [
                       Percentage(title = _("Warning at"), unit = _("% / range"), default_value = 5,),
                       Percentage(title = _("Critical at"), unit = _("% / range"), default_value = 10,),
                   ])),
            (  "trend_timeleft",
               Tuple(
                   title = _("Levels on the time left until the filesystem gets full"),
                   elements = [
                       Integer(title = _("Warning if below"), unit = _("hours"), default_value = 12,),
                       Integer(title = _("Critical if below"), unit = _("hours"), default_value = 6, ),
                    ])),
            ( "trend_showtimeleft",
                    Checkbox( title = _("Display time left in check output"), label = _("Enable"),
                               help = _("Normally, the time left until the disk is full is only displayed when "
                                        "the configured levels have been breached. If you set this option "
                                        "the check always reports this information"))
            ),
            ( "trend_perfdata",
              Checkbox(
                  title = _("Trend performance data"),
                  label = _("Enable generation of performance data from trends"))),


        ]
    ),
    TextAscii(title = _("Volume name")),
    match_type = "dict",
)

register_check_parameters(
    subgroup_storage,
    "netapp_luns",
    _("NetApp LUNs"),
       Dictionary(
           title = _("Configure levels for used space"),
           elements = [
                ("ignore_levels",
                   FixedValue(
                          title = _("Ignore used space (this option disables any other options)"),
                          help  = _("Some luns, e.g. jfs formatted, tend to report incorrect used space values"),
                          label = _("Ignore used space"),
                          value = True,
                          totext = "",)
                ),
                ("levels",
                   Alternative(
                       title = _("Levels for LUN"),
                       show_alternative_title = True,
                       default_value = (80.0, 90.0),
                       match = match_dual_level_type,
                       elements = [
                              get_free_used_dynamic_valuespec("used", "LUN"),
                              Transform(
                                       get_free_used_dynamic_valuespec("free", "LUN", default_value = (20.0, 10.0)),
                                       allow_empty = False,
                                       forth = transform_filesystem_free,
                                       back  = transform_filesystem_free,
                              )
                       ]
                    )
               ),
               (  "trend_range",
                  Optional(
                      Integer(
                          title = _("Time Range for lun filesystem trend computation"),
                          default_value = 24,
                          minvalue = 1,
                          unit= _("hours")),
                      title = _("Trend computation"),
                      label = _("Enable trend computation"))),
               (  "trend_mb",
                  Tuple(
                      title = _("Levels on trends in MB per time range"),
                      elements = [
                          Integer(title = _("Warning at"), unit = _("MB / range"), default_value = 100),
                          Integer(title = _("Critical at"), unit = _("MB / range"), default_value = 200)
                      ])),
               (  "trend_perc",
                  Tuple(
                      title = _("Levels for the percentual growth per time range"),
                      elements = [
                          Percentage(title = _("Warning at"), unit = _("% / range"), default_value = 5,),
                          Percentage(title = _("Critical at"), unit = _("% / range"), default_value = 10,),
                      ])),
               (  "trend_timeleft",
                  Tuple(
                      title = _("Levels on the time left until the lun filesystem gets full"),
                      elements = [
                          Integer(title = _("Warning if below"), unit = _("hours"), default_value = 12,),
                          Integer(title = _("Critical if below"), unit = _("hours"), default_value = 6, ),
                       ])),
               ( "trend_showtimeleft",
                       Checkbox( title = _("Display time left in check output"), label = _("Enable"),
                                  help = _("Normally, the time left until the lun filesystem is full is only displayed when "
                                           "the configured levels have been breached. If you set this option "
                                           "the check always reports this information"))
               ),
               ( "trend_perfdata",
                 Checkbox(
                     title = _("Trend performance data"),
                     label = _("Enable generation of performance data from trends"))
               ),
               ( "read_only",
                 Checkbox(
                     title = _("LUN is read-only"),
                     help = _("Display a warning if a LUN is not read-only. Without "
                              "this setting a warning will be displayed if a LUN is "
                              "read-only."),
                     label = _("Enable"))
               ),
      ]
    ),
    TextAscii(title = _("LUN name")),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "services",
    _("Windows Services"),
    Dictionary(
        elements = [
            ( "additional_servicenames",
                ListOfStrings(
                    title = _("Alternative names for the service"),
                    help = _("Here you can specify alternative names that the service might have. "
                             "This helps when the exact spelling of the services can changed from "
                             "one version to another."),
                )
            ),
            ( "states",
              ListOf(
                Tuple(
                    orientation = "horizontal",
                    elements = [
                        DropdownChoice(
                            title = _("Expected state"),
                            default_value = "running",
                            choices = [
                                ( None, _("ignore the state") ),
                                ( "running", _("running") ),
                                ( "stopped", _("stopped") )]),
                        DropdownChoice(
                            title = _("Start type"),
                            default_value = "auto",
                            choices = [
                                ( None, _("ignore the start type") ),
                                ( "demand", _("demand") ),
                                ( "disabled", _("disabled") ),
                                ( "auto", _("auto") ),
                                ( "unknown", _("unknown (old agent)") ),
                            ]),
                        MonitoringState(
                            title = _("Resulting state"),
                        ),
                    ],
                    default_value = ( "running", "auto", 0)
                ),
                title = _("Services states"),
                help = _("You can specify a separate monitoring state for each possible "
                         "combination of service state and start type. If you do not use "
                         "this parameter, then only running/auto will be assumed to be OK."),
            )),
        ( "else",
           MonitoringState(
               title = _("State if no entry matches"),
               default_value = 2,
           ),
        ),
        ('icon', UserIconOrAction(
            title = _("Add custom icon or action"),
            help = _("You can assign icons or actions to the found services in the status GUI."),
        ))
        ]
    ),
    TextAscii(
        title = _("Name of the service"),
        help = _("Please Please note, that the agent replaces spaces in "
         "the service names with underscores. If you are unsure about the "
         "correct spelling of the name then please look at the output of "
         "the agent (cmk -d HOSTNAME). The service names  are in the first "
         "column of the section &lt;&lt;&lt;services&gt;&gt;&gt;. Please "
         "do not mix up the service name with the display name of the service."
         "The latter one is just being displayed as a further information."),
        allow_empty = False),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "solaris_services",
    _("Solaris Services"),
    Dictionary(
        elements=[
            ("additional_servicenames",
                ListOfStrings(
                    title = _("Alternative names for the service"),
                    help = _("Here you can specify alternative names that the service might have. "
                             "This helps when the exact spelling of the services can changed from "
                             "one version to another."),
            )),
            ("states", ListOf(
                Tuple(
                    orientation="horizontal",
                    elements=[
                        DropdownChoice(
                            title=_("Expected state"),
                            choices=[
                                (None, _("Ignore the state")),
                                ("online", _("Online")),
                                ("disabled", _("Disabled")),
                                ("maintenance", _("Maintenance")),
                                ("legacy_run", _("Legacy run")),
                        ]),
                        DropdownChoice(
                            title=_("STIME"),
                            choices=[
                                (None, _("Ignore")),
                                (True, _("Has changed")),
                                (False, _("Did not changed")),
                        ]),
                        MonitoringState(
                            title=_("Resulting state"),
                        ),
                    ],
                ),
                title=_("Services states"),
                help=_("You can specify a separate monitoring state for each possible "
                       "combination of service state. If you do not use this parameter, "
                       "then only online/legacy_run will be assumed to be OK."),
            )),
            ("else",
               MonitoringState(
                   title = _("State if no entry matches"),
                   default_value = 2,
            )),
        ],
    ),
    TextAscii(
        title = _("Name of the service"),
        allow_empty = False),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "winperf_ts_sessions",
    _("Windows Terminal Server Sessions"),
    Dictionary(
         help = _("This check monitors number of active and inactive terminal "
                  "server sessions."),
         elements = [
             ( "active",
               Tuple(
                   title = _("Number of active sessions"),
                   elements = [
                       Integer(title = _("Warning at"),  unit = _("sessions"), default_value = 100),
                       Integer(title = _("Critical at"), unit = _("sessions"), default_value = 200),
                    ],
               ),
            ),
            ( "inactive",
               Tuple(
                   title = _("Number of inactive sessions"),
                   help = _("Levels for the number of sessions that are currently inactive"),
                   elements = [
                       Integer(title = _("Warning at"),  unit = _("sessions"), default_value = 10),
                       Integer(title = _("Critical at"), unit = _("sessions"), default_value = 20),
                    ],
               ),
            ),
         ]
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_storage,
    "raid",
    _("RAID: overall state"),
    None,
    TextAscii(
        title = _("Name of the device"),
        help = _("For Linux MD specify the device name without the "
                 "<tt>/dev/</tt>, e.g. <tt>md0</tt>, for hardware raids "
                 "please refer to the manual of the actual check being used.")),
    "first"
)

register_check_parameters(
    subgroup_storage,
    "raid_summary",
    _("RAID: summary state"),
    Dictionary(
        elements=[
            ("use_device_states", DropdownChoice(
                title=_("Use device states and overwrite expected status"),
                choices=[
                    (False, _("Ignore")),
                    (True, _("Use device states")),
                ],
                default_value=True,
            )),
        ]
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_storage,
    "raid_disk",
    _("RAID: state of a single disk"),
    Transform(Dictionary(
        elements=[
            ("expected_state",
                TextAscii(
                    title=_("Expected state"),
                    help=_("State the disk is expected to be in. Typical good states "
                           "are online, host spare, OK and the like. The exact way of how "
                           "to specify a state depends on the check and hard type being used. "
                           "Please take examples from discovered checks for reference.")),
            ),
            ("use_device_states", DropdownChoice(
                title=_("Use device states and overwrite expected status"),
                choices=[
                    (False, _("Ignore")),
                    (True, _("Use device states")),
                ],
                default_value=True,
            )),
        ]), forth = lambda x: type(x) is str and {"expected_state": x} or x,
    ),
    TextAscii(
        title = _("Number or ID of the disk"),
        help = _("How the disks are named depends on the type of hardware being "
                 "used. Please look at already discovered checks for examples.")),
    "first"
)

register_check_parameters(
    subgroup_storage,
    "pfm_health",
    _("PCIe flash module"),
    Dictionary(
        elements = [
            ( "health_lifetime_perc",
                Tuple(
                    title    = _("Lower levels for health lifetime"),
                    elements = [
                        Percentage(title = _("Warning if below"),  default_value = 10),
                        Percentage(title = _("Critical if below"), default_value = 5)
                    ],
                ),
            ),
        ],
    ),
    TextAscii(
        title = _("Number or ID of the disk"),
        help = _("How the disks are named depends on the type of hardware being "
                 "used. Please look at already discovered checks for examples.")),
    "dict"
)

register_check_parameters(
    subgroup_environment,
    "switch_contact",
    _("Switch contact state"),
    DropdownChoice(
          help = _("This rule sets the required state of a switch contact"),
          label = _("Required switch contact state"),
          choices = [
                    ( "open", "Switch contact is <b>open</b>" ),
                    ( "closed", "Switch contact is <b>closed</b>" ),
                    ( "ignore", "Ignore switch contact state" ),
                    ],
    ),
    TextAscii(
        title = _("Sensor"),
        allow_empty = False),
    match_type = "first",
)

register_check_parameters(
    subgroup_environment,
    "plugs",
    _("State of PDU Plugs"),
    DropdownChoice(
        help = _("This rule sets the required state of a PDU plug. It is meant to "
                 "be independent of the hardware manufacturer."),
        title = _("Required plug state"),
        choices = [
             ( "on", _("Plug is ON") ),
             ( "off", _("Plug is OFF") ),
        ],
        default_value = "on"
    ),
    TextAscii(
        title = _("Plug item number or name"),
        help = _("Whether you need the number or the name depends on the check. Just take a look to the service description."),
        allow_empty = True),
    match_type = "first",
)


# New temperature rule for modern temperature checks that have the
# sensor type (e.g. "CPU", "Chassis", etc.) as the beginning of their
# item (e.g. "CPU 1", "Chassis 17/11"). This will replace all other
# temperature rulesets in future. Note: those few temperature checks
# that do *not* use an item, need to be converted to use one single
# item (other than None).
register_check_parameters(
    subgroup_environment,
    "temperature",
    _("Temperature"),
    Transform(
        Dictionary(
            elements = [
                ( "levels",
                  Tuple(
                      title = _("Upper Temperature Levels"),
                      elements = [
                          Float(title = _("Warning at"), unit = u"°C", default_value = 26),
                          Float(title = _("Critical at"), unit = u"°C", default_value = 30),
                      ]
                )),
                ( "levels_lower",
                  Tuple(
                      title = _("Lower Temperature Levels"),
                      elements = [
                          Float(title = _("Warning below"), unit = u"°C", default_value = 0),
                          Float(title = _("Critical below"), unit = u"°C", default_value = -10),
                      ]
                )),
                ( "output_unit",
                  DropdownChoice(
                      title = _("Display values in "),
                      choices = [
                        ( "c", _("Celsius") ),
                        ( "f", _("Fahrenheit") ),
                        ( "k", _("Kelvin") ),
                      ]
                )),
                ( "input_unit",
                  DropdownChoice(
                      title = _("Override unit of sensor"),
                      help = _("In some rare cases the unit that is signalled by the sensor "
                               "is wrong and e.g. the sensor sends values in Fahrenheit while "
                               "they are misinterpreted as Celsius. With this setting you can "
                               "force the reading of the sensor to be interpreted as customized. "),
                      choices = [
                        ( "c", _("Celsius") ),
                        ( "f", _("Fahrenheit") ),
                        ( "k", _("Kelvin") ),
                      ]
                )),
                ( "device_levels_handling",
                  DropdownChoice(
                      title = _("Interpretation of the device's own temperature status"),
                      choices = [
                          ( "usr", _("Ignore device's own levels") ),
                          ( "dev", _("Only use device's levels, ignore yours" ) ),
                          ( "best", _("Use least critical of your and device's levels") ),
                          ( "worst", _("Use most critical of your and device's levels") ),
                          ( "devdefault", _("Use device's levels if present, otherwise yours") ),
                          ( "usrdefault", _("Use your own levels if present, otherwise the device's") ),
                      ],
                      default_value = "usrdefault",
                )),
                ( "trend_compute",
                  Dictionary(
                      title = _("Trend computation"),
                      label = _("Enable trend computation"),
                      elements = [
                          ( "period",
                              Integer(
                                  title = _("Observation period for temperature trend computation"),
                                  default_value = 30,
                                  minvalue = 5,
                                  unit= _("minutes")
                              )
                              ),
                          ( "trend_levels",
                              Tuple(
                                  title = _("Levels on temperature increase per period"),
                                  elements = [
                                      Integer(title = _("Warning at"), unit = u"°C / " + _("period"), default_value = 5),
                                      Integer(title = _("Critical at"), unit = u"°C / " + _("period"), default_value = 10)
                                  ]
                              )
                              ),
                          ( "trend_levels_lower",
                              Tuple(
                                  title = _("Levels on temperature decrease per period"),
                                  elements = [
                                      Integer(title = _("Warning at"), unit = u"°C / " + _("period"), default_value = 5),
                                      Integer(title = _("Critical at"), unit = u"°C / " + _("period"), default_value = 10)
                                  ]
                              )
                              ),
                          ( "trend_timeleft",
                              Tuple(
                                  title = _("Levels on the time left until a critical temperature (upper or lower) is reached"),
                                  elements = [
                                      Integer(title = _("Warning if below"), unit = _("minutes"), default_value = 240,),
                                      Integer(title = _("Critical if below"), unit = _("minutes"), default_value = 120, ),
                                  ]
                              )
                              )
                      ],
                      optional_keys = ["trend_levels", "trend_levels_lower", "trend_timeleft"],
                  ),
                ),
            ]
        ),
        forth = lambda v: type(v) == tuple and { "levels" : v } or v,
    ),
    TextAscii(
        title = _("Sensor ID"),
        help = _("The identifier of the thermal sensor.")),
    "dict",
)

register_check_parameters(
    subgroup_environment,
    "room_temperature",
    _("Room temperature (external thermal sensors)"),
    Tuple(
        help = _("Temperature levels for external thermometers that are used "
                 "for monitoring the temperature of a datacenter. An example "
                 "is the webthem from W&T."),
        elements = [
            Integer(title = _("warning at"), unit = u"°C", default_value = 26),
            Integer(title = _("critical at"), unit = u"°C", default_value = 30),
        ]),
    TextAscii(
        title = _("Sensor ID"),
        help = _("The identifier of the thermal sensor.")),
    "first",
    deprecated=True,
)

register_check_parameters(
    subgroup_environment,
    "hw_single_temperature",
    _("Host/Device temperature"),
    Tuple(
        help = _("Temperature levels for hardware devices with "
                 "a single temperature sensor."),
        elements = [
            Integer(title = _("warning at"), unit = u"°C", default_value = 35),
            Integer(title = _("critical at"), unit = u"°C", default_value = 40),
        ]),
    None,
    "first",
    deprecated=True,
)

register_check_parameters(
    subgroup_environment,
    "evolt",
    _("Voltage levels (UPS / PDU / Other Devices)"),
    Tuple(
        help = _("Voltage Levels for devices like UPS or PDUs. "
                 "Several phases may be addressed independently."),
        elements = [
            Integer(title = _("warning if below"), unit = "V", default_value = 210),
            Integer(title = _("critical if below"), unit = "V", default_value = 180),
        ]),
    TextAscii(
        title = _("Phase"),
        help = _("The identifier of the phase the power is related to.")),
    "first"
)

register_check_parameters(
    subgroup_environment,
    "efreq",
    _("Nominal Frequencies"),
    Tuple(
        help = _("Levels for the nominal frequencies of AC devices "
                 "like UPSs or PDUs. Several phases may be addressed independently."),
        elements = [
            Integer(title = _("warning if below"), unit = "Hz", default_value = 40),
            Integer(title = _("critical if below"), unit = "Hz", default_value = 45),
        ]),
    TextAscii(
        title = _("Phase"),
        help = _("The identifier of the phase the power is related to.")),
    "first"
)

register_check_parameters(
    subgroup_environment,
    "epower",
    _("Electrical Power"),
    Tuple(
        help = _("Levels for the electrical power consumption of a device "
                 "like a UPS or a PDU. Several phases may be addressed independently."),
        elements = [
            Integer(title = _("warning if below"), unit = "Watt", default_value = 20),
            Integer(title = _("critical if below"), unit = "Watt", default_value = 1),
        ]),
    TextAscii(
        title = _("Phase"),
        help = _("The identifier of the phase the power is related to.")),
    "first"
)

register_check_parameters(
    subgroup_environment,
    "epower_single",
    _("Electrical Power for Devices with only one phase"),
    Tuple(
        help = _("Levels for the electrical power consumption of a device "),
        elements = [
            Integer(title = _("warning if at"), unit = "Watt", default_value = 300),
            Integer(title = _("critical if at"), unit = "Watt", default_value = 400),
        ]),
    None,
    "first"
)

register_check_parameters(
    subgroup_environment,
    "hw_temperature",
    _("Hardware temperature, multiple sensors"),
    Tuple(
        help = _("Temperature levels for hardware devices like "
                 "Brocade switches with (potentially) several "
                 "temperature sensors. Sensor IDs can be selected "
                 "in the rule."),
        elements = [
            Integer(title = _("warning at"), unit = u"°C", default_value = 35),
            Integer(title = _("critical at"), unit = u"°C", default_value = 40),
        ]),
    TextAscii(
        title = _("Sensor ID"),
        help = _("The identifier of the thermal sensor.")),
    "first",
    deprecated=True,
)

register_check_parameters(
    subgroup_environment,
    "hw_temperature_single",
    _("Hardware temperature, single sensor"),
    Tuple(
        help = _("Temperature levels for hardware devices like "
                 "DELL Powerconnect that have just one temperature sensor. "),
        elements = [
            Integer(title = _("warning at"), unit = u"°C", default_value = 35),
            Integer(title = _("critical at"), unit = u"°C", default_value = 40),
        ]),
    None,
    "first",
    deprecated=True,
)

register_check_parameters(
    subgroup_environment,
    "disk_temperature",
    _("Harddisk temperature (e.g. via SMART)"),
    Tuple(
        help = _("Temperature levels for hard disks, that is determined e.g. via SMART"),
        elements = [
            Integer(title = _("warning at"), unit = u"°C", default_value = 35),
            Integer(title = _("critical at"), unit = u"°C", default_value = 40),
        ]),
    TextAscii(
        title = _("Hard disk device"),
        help = _("The identificator of the hard disk device, e.g. <tt>/dev/sda</tt>.")),
    "first",
    deprecated=True,
)

register_check_parameters(
    subgroup_environment,
    "eaton_enviroment",
    _("Temperature and Humidity for Eaton UPS"),
    Dictionary(
        elements = [
            ( "temp",
              Tuple(
                  title = _("Temperature"),
                  elements = [
                      Integer(title = _("warning at"), unit = u"°C", default_value = 26),
                      Integer(title = _("critical at"), unit = u"°C", default_value = 30),
                  ])),
            ( "remote_temp",
              Tuple(
                  title = _("Remote Temperature"),
                  elements = [
                      Integer(title = _("warning at"), unit = u"°C", default_value = 26),
                      Integer(title = _("critical at"), unit = u"°C", default_value = 30),
                  ])),
            ( "humidity",
              Tuple(
                  title = _("Humidity"),
                  elements = [
                      Integer(title = _("warning at"), unit = u"%", default_value = 60),
                      Integer(title = _("critical at"), unit = u"%", default_value = 75),
                  ])),
            ]),
    None,
    "dict"
)

phase_elements = [
    ( "voltage",
      Tuple(
          title = _("Voltage"),
          elements = [
              Integer(title = _("warning if below"), unit = u"V", default_value = 210),
              Integer(title = _("critical if below"), unit = u"V", default_value = 200),
          ],
    )),
    ( "power",
      Tuple(
          title = _("Power"),
          elements = [
              Integer(title = _("warning at"), unit = u"W", default_value = 1000),
              Integer(title = _("critical at"), unit = u"W", default_value = 1200),
          ],
    )),
    ( "appower",
      Tuple(
          title = _("Apparent Power"),
          elements = [
              Integer(title = _("warning at"), unit = u"VA", default_value = 1100),
              Integer(title = _("critical at"), unit = u"VA", default_value = 1300),
          ],
    )),
    ( "current",
      Tuple(
          title = _("Current"),
          elements = [
              Integer(title = _("warning at"), unit = u"A", default_value = 5),
              Integer(title = _("critical at"), unit = u"A", default_value = 10),
          ],
    )),
    ( "frequency",
      Tuple(
          title = _("Frequency"),
          elements = [
              Integer(title = _("warning if below"), unit = u"Hz", default_value = 45),
              Integer(title = _("critical if below"), unit = u"Hz", default_value = 40),
              Integer(title = _("warning if above"), unit = u"Hz", default_value = 55),
              Integer(title = _("critical if above"), unit = u"Hz", default_value = 60),
          ],
    )),
    ( "differential_current_ac",
      Tuple(
          title = _("Differential current AC"),
          elements = [
              Float(title = _("warning at"), unit = u"mA", default_value = 3.5),
              Float(title = _("critical at"), unit = u"mA", default_value = 30),
          ],
    )),
    ( "differential_current_dc",
      Tuple(
          title = _("Differential current DC"),
          elements = [
              Float(title = _("warning at"), unit = u"mA", default_value = 70),
              Float(title = _("critical at"), unit = u"mA", default_value = 100),
          ],
    )),
]

register_check_parameters(
    subgroup_environment,
    "ups_outphase",
    _("Parameters for output phases of UPSs and PDUs"),
    Dictionary(
        help = _("This rule allows you to specify levels for the voltage, current, load, power "
                 "and apparent power of your device. The levels will only be applied if the device "
                 "actually supplies values for these parameters."),
        elements = phase_elements + [
            ( "load",
              Tuple(
                  title = _("Load"),
                  elements = [
                      Integer(title = _("warning at"), unit = u"%", default_value = 80),
                      Integer(title = _("critical at"), unit = u"%", default_value = 90),
                  ]
            )),
            ("map_device_states",
                ListOf(Tuple(
                    elements = [ TextAscii(size=10), MonitoringState() ]),
                    title    = _("Map device state"),
                    help     = _("Here you can enter either device state number (eg. from SNMP devices) "
                                 "or exact device state name and the related monitoring state."),
            )),
        ]),
    TextAscii(
        title = _("Output Name"),
        help = _("The name of the output, e.g. <tt>Phase 1</tt>/<tt>PDU 1</tt>")),
    "dict"
)

register_check_parameters(
    subgroup_environment,
    "el_inphase",
    _("Parameters for input phases of UPSs and PDUs"),
    Dictionary(
        help = _("This rule allows you to specify levels for the voltage, current, power "
                 "and apparent power of your device. The levels will only be applied if the device "
                 "actually supplies values for these parameters."),
        elements = phase_elements + [
            ("map_device_states",
                ListOf(Tuple(
                    elements = [ TextAscii(size=10), MonitoringState() ]),
                    title    = _("Map device state"),
                    help     = _("Here you can enter either device state number (eg. from SNMP devices) "
                                 "or exact device state name and the related monitoring state."),
            )),
        ],
    ),
    TextAscii(
        title = _("Input Name"),
        help = _("The name of the input, e.g. <tt>Phase 1</tt>")),
    "dict"
)

register_check_parameters(
    subgroup_environment,
    "hw_fans",
    _("FAN speed of Hardware devices"),
    Dictionary(
        elements = [
            ("lower",
            Tuple(
                help = _("Lower levels for the fan speed of a hardware device"),
                title = _("Lower levels"),
                elements = [
                    Integer(title = _("warning if below"), unit = u"rpm"),
                    Integer(title = _("critical if below"), unit = u"rpm"),
                ]),
            ),
            ( "upper",
            Tuple(
                help = _("Upper levels for the fan speed of a hardware device"),
                title = _("Upper levels"),
                elements = [
                    Integer(title = _("warning at"), unit = u"rpm", default_value = 8000),
                    Integer(title = _("critical at"), unit = u"rpm", default_value = 8400),
                ]),
            ),
            ( "output_metrics", Checkbox(title = _("Performance data"),
                                         label = _("Enable performance data"))),
        ],
        optional_keys = ["upper"],
    ),
    TextAscii(
        title = _("Fan Name"),
        help = _("The identificator of the fan.")),
    match_type = "dict",
)

register_check_parameters(
    subgroup_environment,
    "hw_fans_perc",
    _("Fan speed of hardware devices (in percent)"),
    Dictionary(
        elements = [
            ( "levels",
              Tuple(
                  title = _("Upper fan speed levels"),
                  elements = [
                      Percentage(title = _("warning if at")),
                      Percentage(title = _("critical if at")),
                  ]
            )),
            ( "levels_lower",
              Tuple(
                  title = _("Lower fan speed levels"),
                  elements = [
                      Percentage(title = _("warning if below")),
                      Percentage(title = _("critical if below")),
                  ]
            )),
        ]
    ),
    TextAscii(
        title = _("Fan Name"),
        help = _("The identifier of the fan.")),
    "dict",
)

register_check_parameters(
    subgroup_os,
    "pf_used_states",
    _("Number of used states of OpenBSD PF engine"),
    Dictionary(
        elements = [
            ("used",
            Tuple(
                title = _("Limits for the number of used states"),
                elements = [
                    Integer(title = _("warning at")),
                    Integer(title = _("critical at")),
                ]),
            ),
        ],
        optional_keys = [None],
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_environment,
    "pdu_gude",
    _("Levels for Gude PDU Devices"),
    Dictionary(
        elements = [
            ( "kWh",
              Tuple(
                  title = _("Total accumulated Active Energy of Power Channel"),
                  elements = [
                      Integer(title = _("warning at"), unit = _("kW") ),
                      Integer(title = _("critical at"), unit = _("kW")),
                  ])),
            ( "W",
              Tuple(
                  title = _("Active Power"),
                  elements = [
                      Integer(title = _("warning at"), unit = _("W") ),
                      Integer(title = _("critical at"), unit = _("W") ),
                  ])),
            ( "A",
              Tuple(
                  title = _("Current on Power Channel"),
                  elements = [
                      Integer(title = _("warning at"), unit = _("A") ),
                      Integer(title = _("critical at"), unit = _("A")),
                  ])),
            ( "V",
              Tuple(
                  title = _("Voltage on Power Channel"),
                  elements = [
                      Integer(title = _("warning if below"), unit = _("V") ),
                      Integer(title = _("critical if below"), unit = _("V") ),
                  ])),
            ( "VA",
              Tuple(
                  title = _("Line Mean Apparent Power"),
                  elements = [
                      Integer(title = _("warning at"), unit = _("VA") ),
                      Integer(title = _("critical at"), unit = _("VA")),
                  ])),
            ]),
    TextAscii(
        title = _("Phase Number"),
        help = _("The Number of the power Phase.")),
    match_type = "dict",
)


register_check_parameters(
    subgroup_environment,
    "hostsystem_sensors",
    _("Hostsystem sensor alerts"),
    ListOf(
        Dictionary(
        help     = _("This rule allows to override alert levels for the given sensor names."),
        elements = [("name", TextAscii(title = _("Sensor name")) ),
                    ("states", Dictionary(
                        title = _("Custom states"),
                        elements = [
                                (element,
                                  MonitoringState( title = "Sensor %s" %
                                                   description, label = _("Set state to"),
                                                   default_value = int(element) )
                                ) for (element, description) in [
                                         ("0", _("OK")),
                                         ("1", _("WARNING")),
                                         ("2", _("CRITICAL")),
                                         ("3", _("UNKNOWN"))
                                ]
                        ],
                    ))],
        optional_keys = False
        ),
        add_label = _("Add sensor name")
    ),
    None,
    "first"
)

register_check_parameters(
    subgroup_environment,
    "netapp_instance",
    _("Netapp Instance State"),
    ListOf(
        Dictionary(
        help     = _("This rule allows you to override netapp warnings"),
        elements = [
            ("name",  TextAscii(title = _("Warning starts with")) ),
            ("state", MonitoringState( title = "Set state to", default_value = 1 ))
                        ],
            optional_keys = False
        ),
        add_label = _("Add warning")
    ),
    None,
    "first"
)

register_check_parameters(
    subgroup_environment,
    "temperature_auto",
    _("Temperature sensors with builtin levels"),
    None,
    TextAscii(
        title = _("Sensor ID"),
        help = _("The identificator of the thermal sensor.")),
    "first",
    deprecated=True,
)

register_check_parameters(
    subgroup_environment,
    "temperature_trends",
    _("Temperature trends for devices with builtin levels"),
    Dictionary(
        title = _("Temperature Trend Analysis"),
        help = _("This rule enables and configures a trend analysis and corresponding limits for devices, "
                 "which have their own limits configured on the device. It will only work for supported "
                 "checks, right now the <tt>adva_fsp_temp</tt> check."),
        elements = [
            (  "trend_range",
               Optional(
                   Integer(
                       title = _("Time range for temperature trend computation"),
                       default_value = 30,
                       minvalue = 5,
                       unit= _("minutes")),
                   title = _("Trend computation"),
                   label = _("Enable trend computation")
                )
            ),
            (  "trend_c",
               Tuple(
                   title = _("Levels on trends in degrees Celsius per time range"),
                   elements = [
                       Integer(title = _("Warning at"), unit = u"°C / " + _("range"), default_value = 5),
                       Integer(title = _("Critical at"), unit = u"°C / " + _("range"), default_value = 10)
                   ]
                )
            ),
            (  "trend_timeleft",
               Tuple(
                   title = _("Levels on the time left until limit is reached"),
                   elements = [
                       Integer(title = _("Warning if below"), unit = _("minutes"), default_value = 240,),
                       Integer(title = _("Critical if below"), unit = _("minutes"), default_value = 120, ),
                    ]
                )
            ),
        ]
    ),
    TextAscii(
        title = _("Sensor ID"),
        help = _("The identifier of the thermal sensor.")),
    "dict",
    deprecated=True,
)
ntp_params = \
    Tuple(
        title = _("Thresholds for quality of time"),
        elements = [
            Integer(
                title = _("Critical at stratum"),
                default_value = 10,
                help = _("The stratum (\"distance\" to the reference clock) at which the check gets critical."),
            ),
            Float(
                title = _("Warning at"),
                unit = _("ms"),
                default_value = 200.0,
                help = _("The offset in ms at which a warning state is triggered."),
            ),
            Float(
                title = _("Critical at"),
                unit = _("ms"),
                default_value = 500.0,
                help = _("The offset in ms at which a critical state is triggered."),
            ),
        ]
    )

register_check_parameters(
   subgroup_os,
    "ntp_time",
    _("State of NTP time synchronisation"),
    Transform(
        Dictionary(
            elements = [
                ( "ntp_levels",
                  ntp_params, ),
                ( "alert_delay",
                  Tuple(
                     title = _("Phases without synchronization"),
                     elements = [
                         Age(title=_("Warning at"), display=["hours", "minutes"], default_value = 300, ),
                         Age(title=_("Critical at"), display=["hours", "minutes"], default_value = 3600,),
                     ]
               )),
            ]
       ),
       forth = lambda params: type(params) == tuple and { "ntp_levels" : params } or params
    ),
    None,
    "dict"
)

register_check_parameters(
   subgroup_os,
    "ntp_peer",
    _("State of NTP peer"),
    ntp_params,
    TextAscii(
        title = _("Name of the peer")),
    "first"
)

def transform_apc_symmetra(params):
    if type(params) in (list, tuple):
        params = { "levels": params }

    if "levels" in params and len(params["levels"]) > 2:
        cap = float(params["levels"][0])
        params["capacity"] = (cap, cap)
        del params["levels"]

    if "output_load" in params:
        del params["output_load"]

    return params

register_check_parameters(
   subgroup_environment,
    "apc_symentra",
    _("APC Symmetra Checks"),
    Transform(
        Dictionary(
            elements = [
                ("capacity",
                    Tuple(
                        title = _("Levels of battery capacity"),
                        elements = [
                            Percentage(
                                title = _("Warning below"),
                                default_value = 95.0,
                            ),
                            Percentage(
                                title = _("Critical below"),
                                default_value = 90.0,
                            ),
                        ]
                    ),
                ),
                ("post_calibration_levels",
                Dictionary(
                    title = _("Levels of battery parameters after calibration"),
                    help = _("After a battery calibration the battery capacity is reduced until the "
                             "battery is fully charged again. Here you can specify an alternative "
                             "lower level in this post-calibration phase. "
                             "Since apc devices remember the time of the last calibration only "
                             "as a date, the alternative lower level will be applied on the whole "
                             "day of the calibration until midnight. You can extend this time period "
                             "with an additional time span to make sure calibrations occuring just "
                             "before midnight do not trigger false alarms."
                    ),
                    elements = [
                        ("altcapacity",
                        Percentage(
                            title = _("Alternative critical battery capacity after calibration"),
                            default_value = 50,
                        )),
                        ("additional_time_span",
                        Integer(
                            title = ("Extend post-calibration phase by additional time span"),
                            unit = _("minutes"),
                            default_value = 0,
                        )),
                    ],
                    optional_keys = False,
                )),
            ("battime",
            Tuple(
                title = _("Time left on battery"),
                elements = [
                    Age(
                        title = _("Warning at"),
                        help = _("Time left on Battery at and below which a warning state is triggered"),
                        default_value = 0,
                        display = [ "hours", "minutes" ]
                    ),
                    Age(
                        title = _("Critical at"),
                        help = _("Time Left on Battery at and below which a critical state is triggered"),
                        default_value = 0,
                        display = [ "hours", "minutes" ]
                    ),
                ],
            ),
        )],
            optional_keys = ['post_calibration_levels', 'output_load', 'battime'],
        ),
        forth = transform_apc_symmetra,
    ),
    None,
    "first"
)

register_check_parameters(
    subgroup_environment,
    "smoke",
    _("Smoke Detection"),
    Tuple(
        help = _("For devices which measure smoke in percent"),
        elements = [
            Percentage(title = _("Warning at"),  allow_int = True, default_value= 1),
            Percentage(title = _("Critical at"), allow_int = True, default_value= 5),
        ]),
    TextAscii(
        title = _("Sensor ID"),
        help = _("The identifier of the sensor.")),
    "first",
)

register_check_parameters(
   subgroup_environment,
   "apc_ats_output",
   _("APC Automatic Transfer Switch Output"),
   Dictionary(
       title = _("Levels for ATS Output parameters"),
       optional_keys = True,
       elements = [
        ("output_voltage_max",
            Tuple(
             title = _("Maximum Levels for Voltage"),
             elements = [
               Integer(title = _("Warning at"), unit="Volt"),
               Integer(title = _("Critical at"), unit="Volt"),
            ])),
        ("output_voltage_min",
            Tuple(
             title = _("Minimum Levels for Voltage"),
             elements = [
               Integer(title = _("Warning if below"), unit="Volt"),
               Integer(title = _("Critical if below"), unit="Volt"),
            ])),
        ("load_perc_max",
            Tuple(
             title = _("Maximum Levels for load in percent"),
             elements = [
               Percentage(title = _("Warning at")),
               Percentage(title = _("Critical at")),
            ])),
        ("load_perc_min",
            Tuple(
             title = _("Minimum Levels for load in percent"),
             elements = [
               Percentage(title = _("Warning if below")),
               Percentage(title = _("Critical if below")),
            ])),

       ],
   ),
   TextAscii( title = _("ID of phase")),
   "dict",
)

register_check_parameters(
    subgroup_environment,
    "airflow",
    _("Airflow levels"),
    Dictionary(
       title = _("Levels for airflow"),
       elements = [
       ("level_low",
         Tuple(
           title = _("Lower levels"),
           elements = [
             Float(title = _("Warning if below"), unit=_("l/s"), default_value = 5.0, allow_int=True),
             Float(title = _("Critical if below"), unit=_("l/s"), default_value = 2.0, allow_int=True)
           ]
         )
       ),
       ("level_high",
         Tuple(
           title = _("Upper levels"),
           elements = [
             Float(title = _("Warning at"), unit=_("l/s"), default_value = 10.0, allow_int=True),
             Float(title = _("Critical at"), unit=_("l/s"), default_value = 11.0, allow_int=True)
           ]
         )
       ),
       ]
    ),
    None,
    match_type = "dict",
)


register_check_parameters(
   subgroup_environment,
    "ups_capacity",
    _("UPS Capacity"),
    Dictionary(
        title = _("Levels for battery parameters"),
        optional_keys = False,
        elements = [
        ("capacity",
            Tuple(
                title = _("Battery capacity"),
                elements = [
                    Integer(
                        title = _("Warning at"),
                        help = _("The battery capacity in percent at and below which a warning state is triggered"),
                        unit = "%",
                        default_value = 95,
                    ),
                    Integer(
                        title = _("Critical at"),
                        help = _("The battery capacity in percent at and below which a critical state is triggered"),
                        unit = "%",
                        default_value = 90,
                    ),
                ],
            ),
        ),
        ("battime",
            Tuple(
                title = _("Time left on battery"),
                elements = [
                    Integer(
                        title = _("Warning at"),
                        help = _("Time left on Battery at and below which a warning state is triggered"),
                        unit = _("min"),
                        default_value = 0,
                    ),
                    Integer(
                        title = _("Critical at"),
                        help = _("Time Left on Battery at and below which a critical state is triggered"),
                        unit = _("min"),
                        default_value = 0,
                    ),
                ],
            ),
        )],
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
   subgroup_applications,
    "mbg_lantime_state",
    _("Meinberg Lantime State"),
    Dictionary(
    title = _("Meinberg Lantime State"),
    elements = [
       ("stratum", Tuple(
            title = _("Warning levels for Stratum"),
            elements = [
                Integer(
                    title = _("Warning at"),
                    default_value = 2,
                ),
                Integer(
                    title = _("Critical at"),
                    default_value = 3,
            ),
            ])),
       ("offset", Tuple(
            title = _("Warning levels for Time Offset"),
            elements = [
                Integer(
                    title = _("Warning at"),
                    unit = _("microseconds"),
                    default_value = 10,
                ),
                Integer(
                    title = _("Critical at"),
                    unit = _("microseconds"),
                    default_value = 20,
            ),
            ])),
    ]),
    None,
    match_type = "dict",
)

register_check_parameters(
   subgroup_applications,
    "sansymphony_pool",
    _("Sansymphony: pool allocation"),
    Tuple(
        help = _("This rule sets the warn and crit levels for the percentage of allocated pools"),
        elements = [
            Integer(
                title = _("Warning at"),
                unit = _("percent"),
                default_value = 80,
            ),
            Integer(
                title = _("Critical at"),
                unit = _("percent"),
                default_value = 90,
            ),
        ]
    ),
    TextAscii(
        title = _("Name of the pool"),
    ),
    "first"
)

register_check_parameters(
   subgroup_applications,
    "sansymphony_alerts",
    _("Sansymphony: Number of unacknowlegded alerts"),
    Tuple(
        help = _("This rule sets the warn and crit levels for the number of unacknowlegded alerts"),
        elements = [
            Integer(
                title = _("Warning at"),
                unit = _("alerts"),
                default_value = 1,
            ),
            Integer(
                title = _("Critical at"),
                unit = _("alerts"),
                default_value = 2,
            ),
        ]
    ),
    None,
    "first"
)

register_check_parameters(
   subgroup_applications,
    "jvm_threads",
    _("JVM threads"),
    Tuple(
        help = _("This rule sets the warn and crit levels for the number of threads "
                 "running in a JVM."),
        elements = [
            Integer(
                title = _("Warning at"),
                unit = _("threads"),
                default_value = 80,
            ),
            Integer(
                title = _("Critical at"),
                unit = _("threads"),
                default_value = 100,
            ),
        ]
    ),
    TextAscii(
        title = _("Name of the virtual machine"),
        help = _("The name of the application server"),
        allow_empty = False,
    ),
    "first"
)

register_check_parameters(
    subgroup_applications,
    "sym_brightmail_queues",
    "Symantec Brightmail Queues",
    Dictionary(
        help = _("This check is used to monitor successful email delivery through "
                 "Symantec Brightmail Scanner appliances."),
        elements = [
            ("connections",
            Tuple(
                title = _("Number of connections"),
                elements = [
                    Integer(title = _("Warning at")),
                    Integer(title = _("Critical at")),
                ]
            )),
            ("messageRate",
            Tuple(
                title = _("Number of messages delivered"),
                elements = [
                    Integer(title = _("Warning at")),
                    Integer(title = _("Critical at")),
                ]
            )),
            ("dataRate",
            Tuple(
                title = _("Amount of data processed"),
                elements = [
                    Integer(title = _("Warning at")),
                    Integer(title = _("Cricital at")),
                ]
            )),
            ("queuedMessages",
            Tuple(
                title = _("Number of messages currently queued"),
                elements = [
                    Integer(title = _("Warning at")),
                    Integer(title = _("Critical at")),
                ]
            )),
            ("queueSize",
            Tuple(
                title = _("Size of the queue"),
                elements = [
                    Integer(title = _("Warning at")),
                    Integer(title = _("Critical at")),
                ]
            )),
            ("deferredMessages",
            Tuple(
                title = _("Number of messages in deferred state"),
                elements = [
                    Integer(title = _("Warning at")),
                    Integer(title = _("Critical at")),
                ]
            )),

        ],
    ),
    TextAscii(
        title = _("Instance name"),
        allow_empty = True),
    "dict",
)


register_check_parameters(
    subgroup_applications,
    "db2_logsize",
    _("DB2 logfile usage"),
    Dictionary(
        elements = [ ("levels",
            Transform(
                get_free_used_dynamic_valuespec("free", "logfile", default_value = (20.0, 10.0)),
                title = _("Logfile levels"),
                allow_empty = False,
                forth = transform_filesystem_free,
                back  = transform_filesystem_free
           ))
        ]
    ),
    TextAscii(
        title = _("Instance"),
        help = _("DB2 instance followed by database name, e.g db2taddm:CMDBS1")
    ),
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "db2_sortoverflow",
    _("DB2 Sort Overflow"),
    Dictionary(
         help = _("This rule allows you to set percentual limits for sort overflows."),
         elements = [
             ( "levels_perc",
               Tuple(
                   title = _("Overflows"),
                   elements = [
                       Percentage(title = _("Warning at"),  unit = _("%"), default_value = 2.0),
                       Percentage(title = _("Critical at"), unit = _("%"), default_value = 4.0),
                    ],
               ),
            ),
        ]
    ),
    TextAscii(
        title = _("Instance"),
        help = _("DB2 instance followed by database name, e.g db2taddm:CMDBS1")
    ),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "db2_tablespaces",
    _("DB2 Tablespaces"),
    Dictionary(
        help = _("A tablespace is a container for segments (tables, indexes, etc). A "
                 "database consists of one or more tablespaces, each made up of one or "
                 "more data files. Tables and indexes are created within a particular "
                 "tablespace. "
                 "This rule allows you to define checks on the size of tablespaces."),
        elements = db_levels_common,
    ),
    TextAscii(
        title = _("Instance"),
        help = _("The instance name, the database name and the tablespace name combined "
                 "like this db2wps8:WPSCOMT8.USERSPACE1")
    ),
    "dict"
)


register_check_parameters(
    subgroup_applications,
    "db2_connections",
    _("DB2 Connections"),
    Dictionary(
         help = _("This rule allows you to set limits for the maximum number of DB2 connections"),
         elements = [
             ( "levels_total",
               Tuple(
                   title = _("Number of current connections"),
                   elements = [
                       Integer(title = _("Warning at"),  unit = _("connections"), default_value = 150),
                       Integer(title = _("Critical at"), unit = _("connections"), default_value = 200),
                    ],
               ),
            ),
        ]
    ),
    TextAscii(
        title = _("Instance"),
        help = _("DB2 instance followed by database name, e.g db2taddm:CMDBS1")
    ),
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "db2_counters",
    _("DB2 Counters"),
    Dictionary(
         help = _("This rule allows you to configure limits for the deadlocks and lockwaits "
                  "counters of a DB2."),
         elements = [
             ( "deadlocks",
               Tuple(
                   title = _("Deadlocks"),
                   elements = [
                       Float(title = _("Warning at"),  unit = _("deadlocks/sec")),
                       Float(title = _("Critical at"), unit = _("deadlocks/sec")),
                    ],
               ),
            ),
             ( "lockwaits",
               Tuple(
                   title = _("Lockwaits"),
                   elements = [
                       Float(title = _("Warning at"),  unit = _("lockwaits/sec")),
                       Float(title = _("Critical at"), unit = _("lockwaits/sec")),
                    ],
               ),
            ),
        ]
    ),
    TextAscii(
        title = _("Instance"),
        help = _("DB2 instance followed by database name, e.g db2taddm:CMDBS1")
    ),
    "dict",
)

register_check_parameters(
    subgroup_applications,
    "db2_backup",
    _("DB2 Time since last database Backup"),
    Optional(
        Tuple(
            elements = [
              Age(title = _("Warning at"),  display = ["days", "hours", "minutes"], default_value = 86400 * 14),
              Age(title = _("Critical at"), display = ["days", "hours", "minutes"], default_value = 86400 * 28)
            ]
        ),
        title = _("Specify time since last successful backup"),
    ),
    TextAscii(
        title = _("Instance"),
        help = _("DB2 instance followed by database name, e.g db2taddm:CMDBS1")
    ),
    "first"
)


register_check_parameters(
    subgroup_applications,
    "db2_mem",
    _("Memory levels for DB2 memory usage"),
    Tuple(
        elements = [
                Percentage(title = _("Warning if less than"), unit = _("% memory left")),
                Percentage(title = _("Critical if less than"), unit = _("% memory left")),
              ],
    ),
    TextAscii(
        title = _("Instance name"),
        allow_empty = True),
    "first"
)

register_check_parameters(
    subgroup_applications,
    "windows_updates",
    _("WSUS (Windows Updates)"),
    Tuple(
        title = _("Parameters for the Windows Update Check with WSUS"),
        help = _("Set the according numbers to 0 if you want to disable alerting."),
        elements = [
                Integer(title = _("Warning if at least this number of important updates are pending")),
                Integer(title = _("Critical if at least this number of important updates are pending")),
                Integer(title = _("Warning if at least this number of optional updates are pending")),
                Integer(title = _("Critical if at least this number of optional updates are pending")),
                Age(title = _("Warning if time until forced reboot is less then"), default_value = 604800),
                Age(title = _("Critical if time time until forced reboot is less then"), default_value = 172800),
                Checkbox(title = _("display all important updates verbosely"), default_value = True),
              ],
    ),
    None,
    "first"
)

synology_update_states = [
 (1, "Available"),
 (2, "Unavailable"),
 (4, "Disconnected"),
 (5, "Others"),
]

register_check_parameters(
    subgroup_applications,
    "synology_update",
    _("Synology Updates"),
    Dictionary(
        title = _("Update State"),
        elements = [
            ("ok_states", ListChoice(
              title = _("States which result in OK"),
              choices = synology_update_states,
              default_value = [ 2 ]
            )),
            ("warn_states", ListChoice(
              title = _("States which result in Warning"),
              choices = synology_update_states,
              default_value = [ 5 ]
            )),
            ("crit_states", ListChoice(
              title = _("States which result in Critical"),
              choices = synology_update_states,
              default_value = [ 1,4 ]
            )),
        ],
        optional_keys = None,
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "antivir_update_age",
    _("Age of last AntiVirus update"),
    Tuple(
        title = _("Age of last AntiVirus update"),
            elements = [
                Age(title = _("Warning level for time since last update")),
                Age(title = _("Critical level for time since last update")),
            ]
    ),
    None,
    "first"
)

register_check_parameters(subgroup_applications,
    "logwatch_ec",
    _('Logwatch Event Console Forwarding'),
    Alternative(
        title = _("Forwarding"),
        help = _("Instead of using the regular logwatch check all lines received by logwatch can "
                 "be forwarded to a Check_MK event console daemon to be processed. The target event "
                 "console can be configured for each host in a separate rule."),
        style = "dropdown",
        elements = [
            FixedValue(
                "",
                totext = _("Messages are handled by logwatch."),
                title = _("No forwarding"),
            ),
            Dictionary(
                title = _('Forward Messages to Event Console'),
                elements = [
                    ('method', Transform(
                        # TODO: Clean this up to some CascadingDropdown()
                        Alternative(
                            style = "dropdown",
                            title = _("Forwarding Method"),
                            elements = [
                                FixedValue(
                                    "",
                                    title = _("Local: Send events to local Event Console in same OMD site"),
                                    totext = _("Directly forward to Event Console"),
                                ),
                                TextAscii(
                                    title = _("Local: Send events to local Event Console into unix socket"),
                                    allow_empty = False,
                                ),

                                FixedValue(
                                    "spool:",
                                    title = _("Local: Spooling - Send events to local event console in same OMD site"),
                                    totext = _("Spool to Event Console"),
                                ),
                                Transform(
                                    TextAscii(),
                                    title = _("Local: Spooling - Send events to local Event Console into given spool directory"),
                                    allow_empty = False,
                                    forth = lambda x: x[6:],        # remove prefix
                                    back  = lambda x: "spool:" + x, # add prefix
                                ),
                                CascadingDropdown(
                                    title = _("Remote: Send events to remote syslog host"),
                                    choices = [
                                        ("tcp", _("Send via TCP"), Dictionary(
                                            elements = [
                                                ("address", TextAscii(
                                                    title = _("Address"),
                                                    allow_empty = False,
                                                )),
                                                ("port", Integer(
                                                    title = _("Port"),
                                                    allow_empty = False,
                                                    default_value = 514,
                                                    minvalue = 1,
                                                    maxvalue = 65535,
                                                    size = 6,
                                                )),
                                                ("spool", Dictionary(
                                                    title = _("Spool messages that could not be sent"),
                                                    help = _("Messages that can not be forwarded, e.g. when the target Event Console is "
                                                             "not running, can temporarily be stored locally. Forwarding is tried again "
                                                             "on next execution. When messages are spooled, the check will go into WARNING "
                                                             "state. In case messages are dropped by the rules below, the check will shortly "
                                                             "go into CRITICAL state for this execution."),
                                                    elements = [
                                                        ("max_age", Age(
                                                            title = _("Maximum spool duration"),
                                                            help = _("Messages that are spooled longer than this time will be thrown away."),
                                                            default_value = 60*60*24*7, # 1 week should be fine (if size is not exceeded)
                                                        )),
                                                        ("max_size", Filesize(
                                                            title = _("Maximum spool size"),
                                                            help = _("When the total size of spooled messages exceeds this number, the oldest "
                                                                     "messages of the currently spooled messages is thrown away until the left "
                                                                     "messages have the half of the maximum size."),
                                                            default_value = 500000, # do not save more than 500k of message
                                                        )),
                                                    ],
                                                    optional_keys = [],
                                                )),
                                            ],
                                            optional_keys = [ "spool" ],
                                        )),
                                        ("udp", _("Send via UDP"), Dictionary(
                                            elements = [
                                                ("address", TextAscii(
                                                    title = _("Address"),
                                                    allow_empty = False,
                                                )),
                                                ("port", Integer(
                                                    title = _("Port"),
                                                    allow_empty = False,
                                                    default_value = 514,
                                                    minvalue = 1,
                                                    maxvalue = 65535,
                                                    size = 6,
                                                )),
                                            ],
                                            optional_keys = [],
                                        )),
                                    ],
                                ),
                            ],
                            match = lambda x: 4 if type(x) == tuple else (0 if not x else (2 if x == 'spool:' else (3 if x.startswith('spool:') else 1)))
                        ),
                        # migrate old (tcp, address, port) tuple to new dict
                        forth = lambda v: (v[0], {"address": v[1], "port": v[2]}) if (type(v) == tuple and type(v[1]) != dict) else v,
                    )),
                    ('facility', DropdownChoice(
                        title = _("Syslog facility for forwarded messages"),
                        help = _("When forwarding messages and no facility can be extracted from the "
                                 "message this facility is used."),
                        choices = syslog_facilities,
                        default_value = 17, # local1
                    )),
                    ('restrict_logfiles',
                        ListOfStrings(
                            title = _('Restrict Logfiles (Prefix matching regular expressions)'),
                            help  = _("Put the item names of the logfiles here. For example \"System$\" "
                                      "to select the service \"LOG System\". You can use regular expressions "
                                      "which must match the beginning of the logfile name."),
                        ),
                    ),
                    ('monitor_logfilelist',
                        Checkbox(
                            title =  _("Monitoring of forwarded logfiles"),
                            label = _("Warn if list of forwarded logfiles changes"),
                            help = _("If this option is enabled, the check monitors the list of forwarded "
                                  "logfiles and will warn you if at any time a logfile is missing or exceeding "
                                  "when compared to the initial list that was snapshotted during service detection. "
                                  "Reinventorize this check in order to make it OK again."),
                     )
                    ),
                    ('expected_logfiles',
                        ListOfStrings(
                            title = _("List of expected logfiles"),
                            help = _("When the monitoring of forwarded logfiles is enabled, the check verifies that "
                                     "all of the logfiles listed here are reported by the monitored system."),
                        )
                    ),
                    ('logwatch_reclassify',
                        Checkbox(
                            title =  _("Reclassify messages before forwarding them to the EC"),
                            label = _("Apply logwatch patterns"),
                            help = _("If this option is enabled, the logwatch lines are first reclassified by the logwatch "
                                     "patterns before they are sent to the event console. If you reclassify specific lines to "
                                     "IGNORE they are not forwarded to the event console. This takes the burden from the "
                                     "event console to process the message itself through all of its rulesets. The reclassifcation "
                                     "of each line takes into account from which logfile the message originates. So you can create "
                                     "logwatch reclassification rules specifically designed for a logfile <i>access.log</i>, "
                                     "which do not apply to other logfiles."),
                     )
                    ),
                    ('separate_checks',
                        Checkbox(
                            title =  _("Create a separate check for each logfile"),
                            label = _("Separate check"),
                            help = _("If this option is enabled, there will be one separate check for each logfile found during "
                                     "the service discovery. This option also changes the behaviour for unknown logfiles. "
                                     "The default logwatch check forwards all logfiles to the event console, even logfiles "
                                     "which were not known during the service discovery. Creating one check per logfile changes "
                                     "this behaviour so that any data from unknown logfiles is discarded."),
                     )
                    )
                ],
                optional_keys = ['restrict_logfiles', 'expected_logfiles', 'logwatch_reclassify', 'separate_checks'],
                ignored_keys=['service_level'],
            ),
        ],
        default_value = '',
    ),
    None,
    'first',
)

register_rule(group + '/' + subgroup_applications,
    varname   = "logwatch_groups",
    title     = _('Logfile Grouping Patterns'),
    help      = _('The check <tt>logwatch</tt> normally creates one service for each logfile. '
                  'By defining grouping patterns you can switch to the check <tt>logwatch.groups</tt>. '
                  'If the pattern begins with a tilde then this pattern is interpreted as a regular '
                  'expression instead of as a filename globbing pattern and  <tt>*</tt> and <tt>?</tt> '
                  'are treated differently. '
                  'That check monitors a list of logfiles at once. This is useful if you have '
                  'e.g. a folder with rotated logfiles where the name of the current logfile'
                  'also changes with each rotation'),
    valuespec = ListOf(
        Tuple(
            help = _("This defines one logfile grouping pattern"),
            show_titles = True,
            orientation = "horizontal",
            elements = [
                TextAscii(
                     title = _("Name of group"),
                ),
                Tuple(
                    show_titles = True,
                    orientation = "vertical",
                    elements = [
                        TextAscii(title = _("Include Pattern")),
                        TextAscii(title = _("Exclude Pattern"))
                    ],
                ),
            ],
        ),
        add_label = _("Add pattern group"),
    ),
    match = 'all',
)

register_rule(
    group + "/" + subgroup_networking,
    "if_disable_if64_hosts",
    title = _("Hosts forced to use <tt>if</tt> instead of <tt>if64</tt>"),
    help = _("A couple of switches with broken firmware report that they "
             "support 64 bit counters but do not output any actual data "
             "in those counters. Listing those hosts in this rule forces "
             "them to use the interface check with 32 bit counters instead."))


# Create Rules for static checks
register_rulegroup("static", _("Manual Checks"),
    _("Statically configured Check_MK checks that do not rely on the inventory"))


# wmic_process does not support inventory at the moment
register_check_parameters(
    subgroup_applications,
    "wmic_process",
    _("Memory and CPU of processes on Windows"),
    Tuple(
        elements = [
            TextAscii(
                title = _("Name of the process"),
                allow_empty = False,
            ),
            Integer(title = _("Memory warning at"), unit = "MB"),
            Integer(title = _("Memory critical at"), unit = "MB"),
            Integer(title = _("Pagefile warning at"), unit = "MB"),
            Integer(title = _("Pagefile critical at"), unit = "MB"),
            Percentage(title = _("CPU usage warning at")),
            Percentage(title = _("CPU usage critical at")),
        ],
    ),
    TextAscii(
        title = _("Process name for usage in the Nagios service description"),
        allow_empty = False),
    "first", False
)

# Add checks that have parameters but are only configured as manual checks
def ps_convert_from_tuple(params):
    if type(params) in (list, tuple):
        if len(params) == 5:
            procname, warnmin, okmin, okmax, warnmax = params
            user = None
        elif len(params) == 6:
            procname, user, warnmin, okmin, okmax, warnmax = params
        params = {
            "process" : procname,
            "warnmin" : warnmin,
            "okmin"   : okmin,
            "okmax"   : okmax,
            "warnmax" : warnmax,
        }
        if user != None:
            params["user"] = user
    return params


register_check_parameters(
    subgroup_os,
    "zypper",
    _("Zypper Updates"),
    None,
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_os,
    "apt",
    _("APT Updates"),
    Dictionary(
        elements = [
            ( "normal",
               MonitoringState(
                  title = _("State when normal updates are pending"),
                  default_value = 1,
            )),
            ( "security",
               MonitoringState(
                  title = _("State when security updates are pending"),
                  default_value = 2,
            )),
        ]
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_environment,
    "airflow_deviation",
    _("Airflow Deviation in Percent"),
    Tuple(
        help = _("Levels for Airflow Deviation measured at airflow sensors "),
        elements = [
            Float(title = _("critical if below or equal"), unit = u"%", default_value = -20),
            Float(title = _("warning if below or equal"),  unit = u"%", default_value = -20),
            Float(title = _("warning if above or equal"),  unit = u"%", default_value = 20),
            Float(title = _("critical if above or equal"), unit = u"%", default_value = 20),
        ]),
    TextAscii(
        title = _("Detector ID"),
        help = _("The identifier of the detector.")),
    "first"
)


register_check_parameters(
    subgroup_applications,
    "citrix_load",
    _("Load of Citrix Server"),
    Transform(
        Tuple(
            title = _("Citrix Server load"),
            elements = [
                Percentage(title = _("Warning at"), default_value = 85.0, unit = "percent"),
                Percentage(title = _("Critical at"), default_value = 95.0, unit = "percent"),
            ]),
        forth = lambda x: (x[0]/100.0, x[1]/100.0),
        back = lambda x: (int(x[0]*100), int(x[1]*100))
    ),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_networking,
    "adva_ifs",
    _("Adva Optical Transport Laser Power"),
    Dictionary(
        elements = [
            ( "limits_output_power",
              Tuple(
                  title = _("Sending Power"),
                  elements = [
                      Float(title = _("lower limit"), unit = "dBm"),
                      Float(title = _("upper limit"), unit = "dBm"),
                  ])
            ),
            ( "limits_input_power",
              Tuple(
                  title = _("Received Power"),
                  elements = [
                      Float(title = _("lower limit"), unit = "dBm"),
                      Float(title = _("upper limit"), unit = "dBm"),
                  ])
            ),
        ]
    ),
    TextAscii(
       title = _("Interface"),
       allow_empty = False,
    ),
    "dict"
),

bluecat_operstates = [
        (1, "running normally"),
        (2, "not running"),
        (3, "currently starting"),
        (4, "currently stopping"),
        (5, "fault"),
]

register_check_parameters(
    subgroup_networking,
    "bluecat_ntp",
    _("Bluecat NTP Settings"),
    Dictionary(
        elements = [
            ( "oper_states",
                Dictionary(
                    title = _("Operations States"),
                    elements = [
                        ( "warning",
                            ListChoice(
                                title = _("States treated as warning"),
                                choices = bluecat_operstates,
                                default_value = [ 2, 3, 4 ],
                                )
                        ),
                        ( "critical",
                            ListChoice(
                                title = _("States treated as critical"),
                                choices = bluecat_operstates,
                                default_value = [ 5 ],
                                )
                        ),
                    ],
                    required_keys = [ 'warning', 'critical' ],
                )
            ),
            ( "stratum",
              Tuple(
                  title = _("Levels for Stratum "),
                  elements = [
                      Integer(title = _("Warning at")),
                      Integer(title = _("Critical at")),
                  ])
            ),
        ]
    ),
    None,
    match_type = "dict",
),

register_check_parameters(
    subgroup_networking,
    "bluecat_dhcp",
    _("Bluecat DHCP Settings"),
    Dictionary(
        elements = [
            ( "oper_states",
                Dictionary(
                    title = _("Operations States"),
                    elements = [
                        ( "warning",
                            ListChoice(
                                title = _("States treated as warning"),
                                choices = bluecat_operstates,
                                default_value = [ 2, 3, 4 ],
                                )
                        ),
                        ( "critical",
                            ListChoice(
                                title = _("States treated as critical"),
                                choices = bluecat_operstates,
                                default_value = [ 5 ],
                                )
                        ),
                    ],
                    required_keys = [ 'warning', 'critical' ],
                )
            ),
        ],
        required_keys = [ 'oper_states' ],  # There is only one value, so its required
    ),
    None,
    match_type = "dict",
)

register_check_parameters(
    subgroup_networking,
    "bluecat_command_server",
    _("Bluecat Command Server Settings"),
    Dictionary(
        elements = [
            ( "oper_states",
                Dictionary(
                    title = _("Operations States"),
                    elements = [
                        ( "warning",
                            ListChoice(
                                title = _("States treated as warning"),
                                choices = bluecat_operstates,
                                default_value = [ 2, 3, 4 ],
                                )
                        ),
                        ( "critical",
                            ListChoice(
                                title = _("States treated as critical"),
                                choices = bluecat_operstates,
                                default_value = [ 5 ],
                                )
                        ),
                    ],
                    required_keys = [ 'warning', 'critical' ],
                )
            ),
        ],
        required_keys = [ 'oper_states' ],  # There is only one value, so its required
    ),
    None,
    match_type = "dict",
),

register_check_parameters(
    subgroup_networking,
    "bluecat_dns",
    _("Bluecat DNS Settings"),
    Dictionary(
        elements = [
            ( "oper_states",
                Dictionary(
                    title = _("Operations States"),
                    elements = [
                        ( "warning",
                            ListChoice(
                                title = _("States treated as warning"),
                                choices = bluecat_operstates,
                                default_value = [ 2, 3, 4 ],
                                )
                        ),
                        ( "critical",
                            ListChoice(
                                title = _("States treated as critical"),
                                choices = bluecat_operstates,
                                default_value = [ 5 ],
                                )
                        ),
                    ],
                    required_keys = [ 'warning', 'critical' ],
                )
            ),
        ],
        required_keys = [ 'oper_states' ],  # There is only one value, so its required
    ),
    None,
    match_type = "dict",
),

bluecat_ha_operstates = [
   ( 1 , "standalone"),
   ( 2 , "active"),
   ( 3 , "passiv"),
   ( 4 , "stopped"),
   ( 5 , "stopping"),
   ( 6 , "becoming active"),
   ( 7 , "becomming passive"),
   ( 8 , "fault"),
]

register_check_parameters(
    subgroup_networking,
    "bluecat_ha",
    _("Bluecat HA Settings"),
    Dictionary(
        elements = [
            ( "oper_states",
                Dictionary(
                    title = _("Operations States"),
                    elements = [
                        ( "warning",
                            ListChoice(
                                title = _("States treated as warning"),
                                choices = bluecat_ha_operstates,
                                default_value = [ 5, 6, 7 ],
                                ),
                        ),
                        ( "critical",
                            ListChoice(
                                title = _("States treated as critical"),
                                choices = bluecat_ha_operstates ,
                                default_value = [ 8, 4 ],
                                ),
                        ),
                    ],
                    required_keys = [ 'warning', 'critical' ],
                )
            ),
        ],
        required_keys = [ 'oper_states' ],  # There is only one value, so its required
    ),
    None,
    match_type = "dict",
)


register_check_parameters(
    subgroup_networking,
    "steelhead_connections",
    _("Steelhead connections"),
    Dictionary(
        elements = [
            ("total", Tuple(
                title = _("Levels for total amount of connections"),
                elements = [
                    Integer(title = _("Warning at")),
                    Integer(title = _("Critical at")),
                ],
            )),
            ("optimized", Tuple(
                title = _("Levels for optimized connections"),
                elements = [
                    Integer(title = _("Warning at")),
                    Integer(title = _("Critical at")),
                ],
            )),
            ("passthrough", Tuple(
                title = _("Levels for passthrough connections"),
                elements = [
                    Integer(title = _("Warning at")),
                    Integer(title = _("Critical at")),
                ],
            )),
            ("halfOpened", Tuple(
                title = _("Levels for half opened connections"),
                elements = [
                    Integer(title = _("Warning at")),
                    Integer(title = _("Critical at")),
                ],
            )),
            ("halfClosed", Tuple(
                title = _("Levels for half closed connections"),
                elements = [
                    Integer(title = _("Warning at")),
                    Integer(title = _("Critical at")),
                ],
            )),
            ("established", Tuple(
                title = _("Levels for established connections"),
                elements = [
                    Integer(title = _("Warning at")),
                    Integer(title = _("Critical at")),
                ],
            )),
            ("active", Tuple(
                title = _("Levels for active connections"),
                elements = [
                    Integer(title = _("Warning at")),
                    Integer(title = _("Critical at")),
                ],
            )),
        ],
    ),
    None,
    "dict",
)


register_check_parameters(
    subgroup_storage,
    "fc_port",
    _("FibreChannel Ports (FCMGMT MIB)"),
    Dictionary(
        elements = [
            ("bw",
              Alternative(
                  title = _("Throughput levels"),
                  help = _("Please note: in a few cases the automatic detection of the link speed "
                           "does not work. In these cases you have to set the link speed manually "
                           "below if you want to monitor percentage values"),
                  elements = [
                      Tuple(
                        title = _("Used bandwidth of port relative to the link speed"),
                        elements = [
                            Percentage(title = _("Warning at"), unit = _("percent")),
                            Percentage(title = _("Critical at"), unit = _("percent")),
                        ]
                    ),
                    Tuple(
                        title = _("Used Bandwidth of port in megabyte/s"),
                        elements = [
                            Integer(title = _("Warning at"), unit = _("MByte/s")),
                            Integer(title = _("Critical at"), unit = _("MByte/s")),
                        ]
                    )
                  ])
            ),
            ("assumed_speed",
                Float(
                    title = _("Assumed link speed"),
                    help = _("If the automatic detection of the link speed does "
                             "not work you can set the link speed here."),
                    unit = _("Gbit/s")
                )
            ),
            ("rxcrcs",
                Tuple (
                    title = _("CRC errors rate"),
                    elements = [
                        Percentage( title = _("Warning at"), unit = _("percent")),
                        Percentage( title = _("Critical at"), unit = _("percent")),
                    ]
               )
            ),
            ("rxencoutframes",
                Tuple (
                    title = _("Enc-Out frames rate"),
                    elements = [
                        Percentage( title = _("Warning at"), unit = _("percent")),
                        Percentage( title = _("Critical at"), unit = _("percent")),
                    ]
                )
            ),
            ("notxcredits",
                Tuple (
                    title = _("No-TxCredits errors"),
                    elements = [
                        Percentage( title = _("Warning at"), unit = _("percent")),
                        Percentage( title = _("Critical at"), unit = _("percent")),
                    ]
                )
            ),
            ("c3discards",
                Tuple (
                    title = _("C3 discards"),
                    elements = [
                        Percentage( title = _("Warning at"), unit = _("percent")),
                        Percentage( title = _("Critical at"), unit = _("percent")),
                    ]
                )
            ),
            ("average",
                Integer (
                    title = _("Averaging"),
                    help = _("If this parameter is set, all throughputs will be averaged "
                           "over the specified time interval before levels are being applied. Per "
                           "default, averaging is turned off. "),
                   unit = _("minutes"),
                   minvalue = 1,
                   default_value = 5,
                )
            ),
#            ("phystate",
#                Optional(
#                    ListChoice(
#                        title = _("Allowed states (otherwise check will be critical)"),
#                        choices = [ (1, _("unknown") ),
#                                    (2, _("failed") ),
#                                    (3, _("bypassed") ),
#                                    (4, _("active") ),
#                                    (5, _("loopback") ),
#                                    (6, _("txfault") ),
#                                    (7, _("nomedia") ),
#                                    (8, _("linkdown") ),
#                                  ]
#                    ),
#                    title = _("Physical state of port") ,
#                    negate = True,
#                    label = _("ignore physical state"),
#                )
#            ),
#            ("opstate",
#                Optional(
#                    ListChoice(
#                        title = _("Allowed states (otherwise check will be critical)"),
#                        choices = [ (1, _("unknown") ),
#                                    (2, _("unused") ),
#                                    (3, _("ready") ),
#                                    (4, _("warning") ),
#                                    (5, _("failure") ),
#                                    (6, _("not participating") ),
#                                    (7, _("initializing") ),
#                                    (8, _("bypass") ),
#                                    (9, _("ols") ),
#                                  ]
#                    ),
#                    title = _("Operational state") ,
#                    negate = True,
#                    label = _("ignore operational state"),
#                )
#            ),
#            ("admstate",
#                Optional(
#                    ListChoice(
#                        title = _("Allowed states (otherwise check will be critical)"),
#                        choices = [ (1, _("unknown") ),
#                                    (2, _("online") ),
#                                    (3, _("offline") ),
#                                    (4, _("bypassed") ),
#                                    (5, _("diagnostics") ),
#                                  ]
#                    ),
#                    title = _("Administrative state") ,
#                    negate = True,
#                    label = _("ignore administrative state"),
#                )
#            )
        ]
    ),
    TextAscii(
        title = _("port name"),
        help = _("The name of the FC port"),
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_environment,
    "plug_count",
    _("Number of active Plugs"),
    Tuple(
        help = _("Levels for the number of active plugs in a device."),
        elements = [
            Integer(title = _("critical if below or equal"), default_value = 30),
            Integer(title = _("warning if below or equal"), default_value = 32),
            Integer(title = _("warning if above or equal"), default_value = 38),
            Integer(title = _("critical if above or equal"), default_value = 40),
        ]),
    None,
    "first"
)

# Rules for configuring parameters of checks (services)
register_check_parameters(
    subgroup_environment,
    "ucs_bladecenter_chassis_voltage",
    _("UCS Bladecenter Chassis Voltage Levels"),
    Dictionary(
        help = _("Here you can configure the 3.3V and 12V voltage levels for each chassis."),
        elements = [
            ( "levels_3v_lower",
            Tuple(
                title = _("3.3 Volt Output Lower Levels"),
                elements = [
                    Float(title = _("warning if below or equal"),  unit = "V", default_value = 3.25),
                    Float(title = _("critical if below or equal"), unit = "V", default_value = 3.20),
                ]
            )),
            ( "levels_3v_upper",
            Tuple(
                title = _("3.3 Volt Output Upper Levels"),
                elements = [
                    Float(title = _("warning if above or equal"),  unit = "V", default_value = 3.4),
                    Float(title = _("critical if above or equal"), unit = "V", default_value = 3.45),
                ]
            )),
            ( "levels_12v_lower",
            Tuple(
                title = _("12 Volt Output Lower Levels"),
                elements = [
                    Float(title = _("warning if below or equal"),  unit = "V", default_value = 11.9),
                    Float(title = _("critical if below or equal"), unit = "V", default_value = 11.8),
                ]
            )),
            ( "levels_12v_upper",
            Tuple(
                title = _("12 Volt Output Upper Levels"),
                elements = [
                    Float(title = _("warning if above or equal"),  unit = "V", default_value = 12.1),
                    Float(title = _("critical if above or equal"), unit = "V", default_value = 12.2),
                ]
            ))
        ]
    ),
    TextAscii(
        title = _("Chassis"),
        help = _("The identifier of the chassis.")),
    "dict"
)

register_check_parameters(
    subgroup_environment,
    "hp_msa_psu_voltage",
    _("HP MSA Power Supply Voltage Levels"),
    Dictionary(
        help = _("Here you can configure the 3.3V and 12V voltage levels for each power supply."),
        elements = [
            ( "levels_33v_lower",
            Tuple(
                title = _("3.3 Volt Output Lower Levels"),
                elements = [
                    Float(title = _("warning if below or equal"),  unit = "V", default_value = 3.25),
                    Float(title = _("critical if below or equal"), unit = "V", default_value = 3.20),
                ]
            )),
            ( "levels_33v_upper",
            Tuple(
                title = _("3.3 Volt Output Upper Levels"),
                elements = [
                    Float(title = _("warning if above or equal"),  unit = "V", default_value = 3.4),
                    Float(title = _("critical if above or equal"), unit = "V", default_value = 3.45),
                ]
            )),
            ( "levels_5v_lower",
            Tuple(
                title = _("5 Volt Output Lower Levels"),
                elements = [
                    Float(title = _("warning if below or equal"),  unit = "V", default_value = 3.25),
                    Float(title = _("critical if below or equal"), unit = "V", default_value = 3.20),
                ]
            )),
            ( "levels_5v_upper",
            Tuple(
                title = _("5 Volt Output Upper Levels"),
                elements = [
                    Float(title = _("warning if above or equal"),  unit = "V", default_value = 3.4),
                    Float(title = _("critical if above or equal"), unit = "V", default_value = 3.45),
                ]
            )),
            ( "levels_12v_lower",
            Tuple(
                title = _("12 Volt Output Lower Levels"),
                elements = [
                    Float(title = _("warning if below or equal"),  unit = "V", default_value = 11.9),
                    Float(title = _("critical if below or equal"), unit = "V", default_value = 11.8),
                ]
            )),
            ( "levels_12v_upper",
            Tuple(
                title = _("12 Volt Output Upper Levels"),
                elements = [
                    Float(title = _("warning if above or equal"),  unit = "V", default_value = 12.1),
                    Float(title = _("critical if above or equal"), unit = "V", default_value = 12.2),
                ]
            ))
        ]
    ),
    TextAscii(
        title = _("Power Supply name"),
        help = _("The identifier of the power supply.")),
    "dict"
)

register_check_parameters(
     subgroup_applications,
    "jvm_gc",
    _("JVM garbage collection levels"),
    Dictionary(
        help = _("This ruleset also covers Tomcat, Jolokia and JMX. "),
        elements = [
            ( "CollectionTime",
               Alternative(
                   title = _("Collection time levels"),
                   elements = [
                       Tuple(
                           title = _("Time of garbage collection in ms per minute"),
                           elements = [
                               Integer(title = _("Warning at"),
                                       unit = _("ms"),
                                       allow_empty = False),
                               Integer(title = _("Critical at"),
                                       unit = _("ms"),
                                       allow_empty = False),
                           ]
                       )
                   ])),
            ( "CollectionCount",
               Alternative(
                   title = _("Collection count levels"),
                   elements = [
                       Tuple(
                           title = _("Count of garbage collection per minute"),
                           elements = [
                               Integer(title = _("Warning at"), allow_empty = False),
                               Integer(title = _("Critical at"), allow_empty = False),
                           ]
                       )
                   ])),
        ]),
    TextAscii(
        title = _("Name of the virtual machine and/or<br>garbage collection type"),
        help = _("The name of the application server"),
        allow_empty = False,
    ),
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "jvm_tp",
    _("JVM tomcat threadpool levels"),
    Dictionary(
        help = _("This ruleset also covers Tomcat, Jolokia and JMX. "),
        elements = [
            ( "currentThreadCount",
               Alternative(
                   title = _("Current thread count levels"),
                   elements = [
                       Tuple(
                           title = _("Percentage levels of current thread count in threadpool"),
                           elements = [
                               Integer(title = _("Warning at"),
                                       unit = _(u"%"),
                                       allow_empty = False),
                               Integer(title = _("Critical at"),
                                       unit = _(u"%"),
                                       allow_empty = False),
                           ]
                       )
                   ])),
            ( "currentThreadsBusy",
               Alternative(
                   title = _("Current threads busy levels"),
                   elements = [
                       Tuple(
                           title = _("Percentage of current threads busy in threadpool"),
                           elements = [
                               Integer(title = _("Warning at"),
                                       unit = _(u"%"),
                                       allow_empty = False),
                               Integer(title = _("Critical at"),
                                       unit = _(u"%"),
                                       allow_empty = False),
                           ]
                       )
                   ])),
        ]),
    TextAscii(
        title = _("Name of the virtual machine and/or<br>threadpool"),
        help = _("The name of the application server"),
        allow_empty = False,
    ),
    "dict"
)


register_check_parameters(
    subgroup_applications,
    "docker_node_containers",
    _("Docker node container levels"),
    Dictionary(
        help = _("Allows to define absolute levels for all, running, paused, and stopped containers."),
        elements = [
            ("upper_levels",
            Tuple(
                title = _("Containers upper levels"),
                elements = [
                    Integer(title = _("Warning at"),
                            allow_empty = False),
                    Integer(title = _("Critical at"),
                            allow_empty = False),
                ]
            )),
            ("lower_levels",
            Tuple(
                title = _("Containers lower levels"),
                elements = [
                    Integer(title = _("Warning at"),
                            allow_empty = False),
                    Integer(title = _("Critical at"),
                            allow_empty = False),
                ]
            )),
            ("running_upper_levels",
            Tuple(
                title = _("Running containers upper levels"),
                elements = [
                    Integer(title = _("Warning at"),
                            allow_empty = False),
                    Integer(title = _("Critical at"),
                            allow_empty = False),
                ]
            )),
            ("running_lower_levels",
            Tuple(
                title = _("Running containers lower levels"),
                elements = [
                    Integer(title = _("Warning at"),
                            allow_empty = False),
                    Integer(title = _("Critical at"),
                            allow_empty = False),
                ]
            )),
            ("paused_upper_levels",
            Tuple(
                title = _("Paused containers upper levels"),
                elements = [
                    Integer(title = _("Warning at"),
                            allow_empty = False),
                    Integer(title = _("Critical at"),
                            allow_empty = False),
                ]
            )),
            ("paused_lower_levels",
            Tuple(
                title = _("Paused containers lower levels"),
                elements = [
                    Integer(title = _("Warning at"),
                            allow_empty = False),
                    Integer(title = _("Critical at"),
                            allow_empty = False),
                ]
            )),
            ("stopped_upper_levels",
            Tuple(
                title = _("Stopped containers upper levels"),
                elements = [
                    Integer(title = _("Warning at"),
                            allow_empty = False),
                    Integer(title = _("Critical at"),
                            allow_empty = False),
                ]
            )),
            ("stopped_lower_levels",
            Tuple(
                title = _("Stopped containers lower levels"),
                elements = [
                    Integer(title = _("Warning at"),
                            allow_empty = False),
                    Integer(title = _("Critical at"),
                            allow_empty = False),
                ]
            )),
        ]),
    None,
    "dict"
)


register_check_parameters(
    subgroup_applications,
    "docker_node_disk_usage",
    _("Docker node disk usage"),
    Dictionary(
        help = _("Allows to define levels for the counts and size of Docker Containers, Images, Local Volumes, and the Build Cache."),
        elements = [
            ("size",
             Tuple(
                 title = _("Size"),
                 elements = [
                     Filesize(title = _("Warning at"),
                             allow_empty = False),
                     Filesize(title = _("Critical at"),
                             allow_empty = False),
                 ]
            )),
            ("reclaimable",
             Tuple(
                 title = _("Reclaimable"),
                 elements = [
                     Filesize(title = _("Warning at"),
                             allow_empty = False),
                     Filesize(title = _("Critical at"),
                             allow_empty = False),
                 ]
            )),
            ("count",
             Tuple(
                 title = _("Total count"),
                 elements = [
                     Integer(title = _("Warning at"),
                             allow_empty = False),
                     Integer(title = _("Critical at"),
                             allow_empty = False),
                 ]
            )),
            ("active",
             Tuple(
                 title = _("Active"),
                 elements = [
                     Integer(title = _("Warning at"),
                             allow_empty = False),
                     Integer(title = _("Critical at"),
                             allow_empty = False),
                 ]
            )),
        ]),
    TextAscii(
        title = _("Type"),
        help = _("Either Containers, Images, Local Volumes or Build Cache"),
        allow_empty = True,
    ),
    "dict"
)


def _transform_heartbeat_crm(params):
    if isinstance(params, dict):
        return params
    par_dict = {'max_age': params[0]}
    if params[1]:
        par_dict['dc'] = params[1]
    if params[2] > -1:
        par_dict['num_nodes'] = params[2]
    if params[3] > -1:
        par_dict['num_resources'] = params[3]
    return par_dict


register_check_parameters(
    subgroup_storage,
    "heartbeat_crm",
    _("Heartbeat CRM general status"),
    Transform(Dictionary(
        elements = [
            ("max_age",
             Integer(
                 title = _("Maximum age"),
                 help = _("Maximum accepted age of the reported data in seconds"),
                 unit = _("seconds"),
                 default_value = 60,
            )),
            ("dc",
             TextAscii(
                 allow_empty = False,
                 title = _("Expected DC"),
                 help = _("The hostname of the expected distinguished controller of the cluster"),
            )),
            ("num_nodes",
             Integer(
                 min_value = 0,
                 default_value = 2,
                 title = _("Number of Nodes"),
                 help = _("The expected number of nodes in the cluster"),
            )),
            ("num_resources",
             Integer(
                 min_value = 0,
                 title = _("Number of Resources"),
                 help = _("The expected number of resources in the cluster"),
            )),
        ],
        optional_keys=["dc", "num_nodes", "num_resources"],
    ), forth=_transform_heartbeat_crm),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_storage,
    "heartbeat_crm_resources",
    _("Heartbeat CRM resource status"),
    Optional(
        TextAscii(
            allow_empty = False
        ),
        title = _("Expected node"),
        help = _("The hostname of the expected node to hold this resource."),
        none_label = _("Do not enforce the resource to be hold by a specific node."),
    ),
    TextAscii(
        title = _("Resource Name"),
        help = _("The name of the cluster resource as shown in the service description."),
        allow_empty = False,
    ),
    "first"
)

register_check_parameters(
    subgroup_applications,
    "domino_tasks",
    _("Lotus Domino Tasks"),
    Dictionary(
        elements = [
            ( "process", Alternative(
                title = _("Name of the task"),
                style = "dropdown",
                elements = [
                    TextAscii(
                        title = _("Exact name of the task"),
                        size = 50,
                    ),
                    Transform(
                        RegExp(
                            size = 50,
                            mode = RegExp.prefix,
                        ),
                        title = _("Regular expression matching tasks"),
                        help = _("This regex must match the <i>beginning</i> of the complete "
                                 "command line of the task including arguments"),
                        forth = lambda x: x[1:],   # remove ~
                        back  = lambda x: "~" + x, # prefix ~
                    ),
                    FixedValue(
                        None,
                        totext = "",
                        title = _("Match all tasks"),
                    )
                ],
                match = lambda x: (not x and 2) or (x[0] == '~' and 1 or 0)
            )),
            ( "warnmin", Integer(
                title = _("Minimum number of matched tasks for WARNING state"),
                default_value = 1,
            )),
            ( "okmin", Integer(
                title = _("Minimum number of matched tasks for OK state"),
                default_value = 1,
            )),
            ( "okmax", Integer(
                title = _("Maximum number of matched tasks for OK state"),
                default_value = 99999,
            )),
            ( "warnmax", Integer(
                title = _("Maximum number of matched tasks for WARNING state"),
                default_value = 99999,
            )),
        ],
        required_keys = [ 'warnmin', 'okmin', 'okmax', 'warnmax', 'process' ],
    ),
    TextAscii(
        title = _("Name of service"),
        help = _("This name will be used in the description of the service"),
        allow_empty = False,
        regex = "^[a-zA-Z_0-9 _.-]*$",
        regex_error = _("Please use only a-z, A-Z, 0-9, space, underscore, "
                        "dot and hyphen for your service description"),
    ),
    match_type = "dict",
    has_inventory = False
)

register_check_parameters(
    subgroup_applications,
    "domino_mailqueues",
    _("Lotus Domino Mail Queues"),
    Dictionary(
        elements = [
            ( "queue_length",
            Tuple(
                title = _("Number of Mails in Queue"),
                elements = [
                    Integer(title = _("warning at"), default_value = 300 ),
                    Integer(title = _("critical at"), default_value = 350 ),
                ]
            )),
        ],
        required_keys = [ 'queue_length' ],
    ),
    DropdownChoice(
        choices = [
            ('lnDeadMail', _('Mails in Dead Queue')),
            ('lnWaitingMail', _('Mails in Waiting Queue')),
            ('lnMailHold', _('Mails in Hold Queue')),
            ('lnMailTotalPending', _('Total Pending Mails')),
            ('InMailWaitingforDNS', _('Mails Waiting for DNS Queue')),
        ],
        title = _("Domino Mail Queue Names"),
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_applications,
    "domino_users",
    _("Lotus Domino Users"),
    Tuple(
        title = _("Number of Lotus Domino Users"),
        elements = [
            Integer(title = _("warning at"), default_value = 1000 ),
            Integer(title = _("critical at"), default_value = 1500 ),
        ]
    ),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_applications,
    "domino_transactions",
    _("Lotus Domino Transactions"),
    Tuple(
        title = _("Number of Transactions per Minute on a Lotus Domino Server"),
        elements = [
            Integer(title = _("warning at"), default_value = 30000 ),
            Integer(title = _("critical at"), default_value = 35000 ),
        ]
    ),
    None,
    match_type = "first",
)

register_check_parameters(
    subgroup_applications,
    "netscaler_dnsrates",
    _("Citrix Netscaler DNS counter rates"),
    Dictionary(
        help = _("Counter rates of DNS parameters for Citrix Netscaler Loadbalancer "
                 "Appliances"),
        elements =  [
            ("query",
            Tuple(
                title = _("Upper Levels for Total Number of DNS queries"),
                elements = [
                    Float(title = _("Warning at"), default_value=1500.0, unit="/sec"),
                    Float(title = _("Critical at"), default_value=2000.0, unit="/sec")],
                ),
            ),
            ("answer",
            Tuple(
                title = _("Upper Levels for Total Number of DNS replies"),
                elements = [
                    Float(title = _("Warning at"), default_value=1500.0, unit="/sec"),
                    Float(title = _("Critical at"), default_value=2000.0, unit="/sec")],
                ),
            ),
        ]
    ),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "netscaler_tcp_conns",
    _("Citrix Netscaler Loadbalancer TCP Connections"),
    Dictionary(
        elements = [
            ( "client_conns",
                Tuple(
                    title = _("Max. number of client connections"),
                    elements = [
                        Integer(
                            title = _("Warning at"),
                            default_value = 25000,
                        ),
                        Integer(
                            title = _("Critical at"),
                            default_value = 30000,
                        ),
                    ]
                ),
            ),
            ( "server_conns",
                Tuple(
                    title = _("Max. number of server connections"),
                    elements = [
                        Integer(
                            title = _("Warning at"),
                            default_value = 25000,
                        ),
                        Integer(
                            title = _("Critical at"),
                            default_value = 30000,
                        ),
                    ]
                ),
            ),
        ]),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "netscaler_sslcerts",
    _("Citrix Netscaler SSL certificates"),
    Dictionary(
        elements = [
            ('age_levels',
             Tuple(
                 title = _("Remaining days of validity"),
                 elements = [
                     Integer(title = _("Warning below"), default_value = 30, min_value = 0 ),
                     Integer(title = _("Critical below"), default_value = 10, min_value = 0 ),
                     ],
                 ),
            ),
        ],
    ),
    TextAscii(
        title = _("Name of Certificate"),
    ),
    match_type = "dict"
)


register_check_parameters(
    subgroup_applications,
    "k8s_resources",
    _("Kubernetes resources"),
    Dictionary(elements=[
        ('pods',
         Tuple(
             title=_('Pods'),
             default_value=(80.0, 90.0),
             elements=[
                 Percentage(title=_("Warning above")),
                 Percentage(title=_("Critical above")),
             ],
         )),
        ('cpu',
         Tuple(
             title=_('CPU'),
             default_value=(80.0, 90.0),
             elements=[
                 Percentage(title=_("Warning above")),
                 Percentage(title=_("Critical above")),
             ],
         )),
        ('memory',
         Tuple(
             title=_('Memory'),
             default_value=(80.0, 90.0),
             elements=[
                 Percentage(title=_("Warning above")),
                 Percentage(title=_("Critical above")),
             ],
         )),
    ]),
    None,
    match_type="dict",
)

register_check_parameters(
    subgroup_applications,
    "k8s_roles",
    _("Kubernetes roles"),
    Dictionary(elements=[
        ('total',
         Tuple(
             title=_('Total'),
             default_value=(80.0, 90.0),
             elements=[
                 Integer(title=_("Warning above")),
                 Integer(title=_("Critical above")),
             ],
         )),
        ('cluster_roles',
         Tuple(
             title=_('Cluster roles'),
             default_value=(80.0, 90.0),
             elements=[
                 Integer(title=_("Warning above")),
                 Integer(title=_("Critical above")),
             ],
         )),
        ('roles',
         Tuple(
             title=_('Roles'),
             default_value=(80.0, 90.0),
             elements=[
                 Integer(title=_("Warning above")),
                 Integer(title=_("Critical above")),
             ],
         )),
    ]),
    None,
    match_type="dict",
)

register_check_parameters(
    subgroup_applications,
    "k8s_nodes",
    _("Kubernetes nodes"),
    Dictionary(elements=[
        ('levels',
         Tuple(
             title=_('Upper levels'),
             elements=[
                 Integer(title=_("Warning above")),
                 Integer(title=_("Critical above")),
             ],
         )),
        ('levels_lower',
         Tuple(
             title=_('Lower levels'),
             elements=[
                 Integer(title=_("Warning below")),
                 Integer(title=_("Critical below")),
             ],
         )),
    ]),
    None,
    match_type="dict",
)

register_check_parameters(
    subgroup_applications,
    "azure_agent_info",
    ("Azure Agent Info"),
    Dictionary(elements=[
        ("warning_levels",
         Tuple(
             title=_("Upper levels for encountered warnings"),
             elements=[
                 Integer(title=_("Warning at"), default_value=1),
                 Integer(title=_("Critical at"), default_value=10),
             ],
         )),
        ("exception_levels",
         Tuple(
             title=_("Upper levels for encountered exceptions"),
             elements=[
                 Integer(title=_("Warning at"), default_value=1),
                 Integer(title=_("Critical at"), default_value=1),
             ],
         )),
        ("remaining_reads_levels_lower",
         Tuple(
             title=_("Lower levels for remaining API reads"),
             elements=[
                 Integer(title=_("Warning below"), default_value=6000),
                 Integer(title=_("Critical below"), default_value=3000),
             ],
         )),
        ("remaining_reads_unknown_state",
         MonitoringState(title=_("State if remaining API reads are unknown"), default_value=1)),
    ]),
    TextAscii(title=_("Azure Agent Info")),
    match_type="dict",
)

register_check_parameters(
    subgroup_applications,
    "webserver",
    _("Azure web servers (IIS)"),
    Dictionary(
        elements=[
            (
                "avg_response_time_levels",
                Tuple(
                    title=_("Upper levels for average response time"),
                    elements=[
                        Float(title=_("Warning at"), default_value=1.00, unit="s"),
                        Float(title=_("Critical at"), default_value=10.0, unit="s"),
                    ]),
            ),
            (
                "error_rate_levels",
                Tuple(
                    title=_("Upper levels for rate of server errors"),
                    elements=[
                        Float(title=_("Warning at"), default_value=0.01, unit="1/s"),
                        Float(title=_("Critical at"), default_value=0.04, unit="1/s"),
                    ]),
            ),
            (
                "cpu_time_percent_levels",
                Tuple(
                    title=_("Upper levels for CPU time"),
                    elements=[
                        Float(title=_("Warning at"), default_value=85., unit="%"),
                        Float(title=_("Critical at"), default_value=95., unit="%"),
                    ]),
            ),
        ],),
    TextAscii(title=_("Name of the service")),
    match_type="dict",
)

register_check_parameters(
    subgroup_applications,
    'azure_storageaccounts',
    _("Azure Storage"),
    Dictionary(elements=[
        ('ingress_levels',
         Tuple(
             title=_("Levels on ingress data in bytes"),
             elements=[
                 Float(title=_("Warning at"), unit="B"),
                 Float(title=_("Critical at"), unit="B"),
             ],
         )),
        ('egress_levels',
         Tuple(
             title=_("Levels on ingress data in bytes"),
             elements=[
                 Float(title=_("Warning at"), unit="B"),
                 Float(title=_("Critical at"), unit="B"),
             ],
         )),
        ('used_capacity_levels',
         Tuple(
             title=_("Levels on used capacity in bytes"),
             elements=[
                 Float(title=_("Warning at"), unit="B"),
                 Float(title=_("Critical at"), unit="B"),
             ],
         )),
        ('server_latency_levels',
         Tuple(
             title=_("Levels on server latency in seconds"),
             help=_("Average latency used by Azure Storage to process a successful request"),
             elements=[
                 Float(title=_("Warning at"), unit="s"),
                 Float(title=_("Critical at"), unit="s"),
             ],
         )),
        ('e2e_latency_levels',
         Tuple(
             title=_("Levels on end-to-end latency in seconds"),
             help=_("Average end-to-end latency of successful requests made to a storage service"),
             elements=[
                 Float(title=_("Warning at"), unit="s"),
                 Float(title=_("Critical at"), unit="s"),
             ],
         )),
        ('transactions_levels',
         Tuple(
             title=_("Levels on transaction count"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ],
         )),
        ('availability_levels',
         Tuple(
             title=_("Levels on availability in percent"),
             elements=[
                 Float(title=_("Warning at"), unit="%"),
                 Float(title=_("Critical at"), unit="%"),
             ],
         )),
    ]),
    TextAscii(
        title=_("Storage account name"),
        help=_("Specify storage account names that the rule should apply to"),
    ),
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'azure_databases',
    _("Azure Databases"),
    Dictionary(
        title=_("Set Levels"),
        elements=[
            ('storage_percent_levels',
             Tuple(
                 title=_("Used storage in percent"),
                 elements=[
                     Float(title=_("Warning at"), unit=_('%'), default_value=85.0),
                     Float(title=_("Critical at"), unit=_('%'), default_value=95.0)
                 ])),
            ('cpu_percent_levels',
             Tuple(
                 title=_("CPU in percent"),
                 elements=[
                     Float(title=_("Warning at"), unit=_('%'), default_value=85.0),
                     Float(title=_("Critical at"), unit=_('%'), default_value=95.0)
                 ])),
            ('dtu_percent_levels',
             Tuple(
                 title=_("Database throughput units in percent"),
                 elements=[
                     Float(title=_("Warning at"), unit=_('%'), default_value=40.0),
                     Float(title=_("Critical at"), unit=_('%'), default_value=50.0)
                 ])),
        ],
    ),
    TextAscii(
        title=_("Database Name"),
        help=_("Specify database names that the rule should apply to"),
    ),
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'azure_vms',
    _("Azure Virtual Machines"),
    Dictionary(
        help=_("To obtain the data required for this check, please configure"
               " the datasource program \"Microsoft Azure\"."),
        elements=[
            ('map_provisioning_states',
             Dictionary(
                 title=_("Map provisioning states"),
                 elements=[
                     ("succeeded", MonitoringState(title="succeeded")),
                     ("failed", MonitoringState(title="failed", default_value=2)),
                 ])),
            ('map_power_states',
             Dictionary(
                 title=_("Map power states"),
                 elements=[
                     ("starting", MonitoringState(title="starting")),
                     ("running", MonitoringState(title="running")),
                     ("stopping", MonitoringState(title="stopping", default_value=1)),
                     ("stopped", MonitoringState(title="stopped", default_value=1)),
                     ("deallocating", MonitoringState(title="deallocating")),
                     ("deallocated", MonitoringState(title="deallocated")),
                     ("unknown", MonitoringState(title=_("unknown"), default_value=3)),
                 ])),
        ],
    ),
    TextAscii(title=_("VM name")),
    match_type='dict',
)


def _azure_vms_summary_levels(title, lower=(None, None), upper=(None, None)):
    return Dictionary(
        title=_(title),
        elements=[
            ("levels_lower",
             Tuple(
                 title=_("Lower levels"),
                 elements=[
                     Integer(title=_("Warning below"), default_value=lower[0]),
                     Integer(title=_("Critical below"), default_value=lower[1]),
                 ])),
            ("levels",
             Tuple(
                 title=_("Upper levels"),
                 elements=[
                     Integer(title=_("Warning at"), default_value=upper[0]),
                     Integer(title=_("Critical at"), default_value=upper[1]),
                 ])),
        ])


register_check_parameters(
    subgroup_applications,
    'azure_vms_summary',
    _("Azure Virtual Machines Summary"),
    Dictionary(
        help=_("To obtain the data required for this check, please configure"
               " the datasource program \"Microsoft Azure\"."),
        elements=[
            ('levels_provisioning',
             Dictionary(
                 title=_("Levels for provisioning count"),
                 elements=[
                     ("succeeded", _azure_vms_summary_levels("Succeeded provionings", (0, -1))),
                     ("failed", _azure_vms_summary_levels("Failed provisionings", (-1, -1),
                                                          (1, 1))),
                 ])),
            ('levels_power',
             Dictionary(
                 title=_("Levels for power state count"),
                 elements=[
                     ("starting", _azure_vms_summary_levels("Starting VMs")),
                     ("running", _azure_vms_summary_levels("Running VMs")),
                     ("stopping", _azure_vms_summary_levels("Stopping VMs")),
                     ("stopped", _azure_vms_summary_levels("Stopped VMs")),
                     ("deallocating", _azure_vms_summary_levels("Deallocating VMs")),
                     ("deallocated", _azure_vms_summary_levels("Deallocated VMs")),
                     ("unknown", _azure_vms_summary_levels("VMs in unknown state", upper=(1, 1))),
                 ])),
        ],
    ),
    None,
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'azure_virtualnetworkgateways',
    _("Azure VNet Gateway"),
    Dictionary(elements=[
        (
            'connections_levels_upper',
            Tuple(
                title=_("Upper levels on number of Point-to-site connections"),
                elements=[Float(title=_("Warning at")),
                          Float(title=_("Critical at"))]),
        ),
        (
            'connections_levels_lower',
            Tuple(
                title=_("Lower levels on number of Point-to-site connections"),
                elements=[Float(title=_("Warning below")),
                          Float(title=_("Critical below"))]),
        ),
        (
            'p2s_bandwidth_levels_upper',
            Tuple(
                title=_("Upper levels on Point-to-site bandwidth in bytes per second"),
                elements=[
                    Float(title=_("Warning at"), unit="B/s"),
                    Float(title=_("Critical at"), unit="B/s")
                ]),
        ),
        (
            'p2s_bandwidth_levels_lower',
            Tuple(
                title=_("Lower levels on Point-to-site bandwidth in bytes per second"),
                elements=[
                    Float(title=_("Warning below"), unit="B/s"),
                    Float(title=_("Critical below"), unit="B/s")
                ]),
        ),
        (
            's2s_bandwidth_levels_upper',
            Tuple(
                title=_("Upper levels on Site-to-site bandwidth in bytes per second"),
                elements=[
                    Float(title=_("Warning at"), unit="B/s"),
                    Float(title=_("Critical at"), unit="B/s")
                ]),
        ),
        (
            's2s_bandwidth_levels_lower',
            Tuple(
                title=_("Lower levels on Site-to-site bandwidth in bytes per second"),
                elements=[
                    Float(title=_("Warning below"), unit="B/s"),
                    Float(title=_("Critical below"), unit="B/s")
                ]),
        ),
    ]),
    TextAscii(
        title=_("Virtual network gateway name"),
        help=_("Specify virtual network gateway names that the rule should apply to"),
    ),
    match_type='dict',
)

def _vs_s3_buckets():
    return ('bucket_size_levels',
            Alternative(
                title=_("Upper levels for the bucket size"),
                style="dropdown",
                elements=[
                    Tuple(
                        title=_("Set levels"),
                        elements=[
                            Filesize(title=_("Warning at")),
                            Filesize(title=_("Critical at")),
                        ]),
                    Tuple(
                        title=_("No levels"),
                        elements=[
                            FixedValue(None, totext=""),
                            FixedValue(None, totext=""),
                        ]),
                ]))

register_check_parameters(
    subgroup_applications,
    'aws_s3_buckets_objects',
    _("AWS/S3 Bucket Objects"),
    Dictionary(elements=[_vs_s3_buckets()]),
    TextAscii(title=_("The bucket name")),
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'aws_s3_buckets',
    _("AWS/S3 Buckets"),
    Dictionary(elements=[_vs_s3_buckets()]),
    None,
    match_type='dict',
)

def _vs_cpu_credits_balance():
    return ('balance_levels_lower',
            Alternative(
                title=_("Lower levels for CPU balance"),
                style="dropdown",
                elements=[
                    Tuple(
                        title=_("Set levels"),
                        elements=[
                            Integer(title=_("Warning at or below")),
                            Integer(title=_("Critical at or below")),
                        ]),
                    Tuple(
                        title=_("No levels"),
                        elements=[
                            FixedValue(None, totext=""),
                            FixedValue(None, totext=""),
                        ]),
                ]))

register_check_parameters(
    subgroup_applications,
    'aws_ec2_cpu_credits',
    _("AWS/EC2 CPU Credits"),
    Dictionary(elements=[_vs_cpu_credits_balance()]),
    None,
    match_type='dict',
)

def _vs_burst_balance():
    return ('burst_balance_levels_lower',
            Alternative(
                title=_("Lower levels for burst balance"),
                style="dropdown",
                elements=[
                    Tuple(
                        title=_("Set levels"),
                        elements=[
                            Percentage(title=_("Warning at or below")),
                            Percentage(title=_("Critical at or below")),
                        ]),
                    Tuple(
                        title=_("No levels"),
                        elements=[
                            FixedValue(None, totext=""),
                            FixedValue(None, totext=""),
                        ]),
                ]))

register_check_parameters(
    subgroup_applications,
    'aws_ebs_burst_balance',
    _("AWS/EBS Burst Balance"),
    Dictionary(elements=[_vs_burst_balance()]),
    TextAscii(title=_("Block storage name")),
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'aws_costs_and_usage',
    _("AWS/CE Costs and Usage"),
    Dictionary(elements=[('levels_unblended',
                          Tuple(
                              title=_("Upper levels for unblended costs"),
                              elements=[
                                  Integer(title=_("Warning at"), unit=_("USD per day")),
                                  Integer(title=_("Critical at"), unit=_("USD per day")),
                              ]))]),
    None,
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'aws_elb_statistics',
    _("AWS/ELB Statistics"),
    Dictionary(elements=[
        ('levels_surge_queue_length',
         Tuple(
             title=_("Upper levels for surge queue length"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ])),
        ('levels_spillover',
         Tuple(
             title=_("Upper levels for the number of requests that were rejected (spillover)"),
             elements=[
                 Integer(title=_("Warning at")),
                 Integer(title=_("Critical at")),
             ])),
    ]),
    None,
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'aws_elb_latency',
    _("AWS/ELB Latency"),
    Dictionary(elements=[
        ('levels_latency',
         Tuple(
             title=_("Upper levels for latency"),
             elements=[
                 Age(title=_("Warning at")),
                 Age(title=_("Critical at")),
             ])),
    ]),
    None,
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'aws_elb_http',
    _("AWS/ELB HTTP Errors"),
    Dictionary(elements=[
        ('levels_http_4xx_perc',
         Tuple(
             title=_("Upper percentual levels for HTTP 400 errors"),
             help=_("Specify levels for HTTP 400 errors in percentage "
                    "which refer to the total number of requests"),
             elements=[
                 Percentage(title=_("Warning at")),
                 Percentage(title=_("Critical at")),
             ])),
        ('levels_http_5xx_perc',
         Tuple(
             title=_("Upper percentual levels for HTTP 500 errors"),
             help=_("Specify levels for HTTP 500 errors in percentage "
                    "which refer to the total number of requests"),
             elements=[
                 Percentage(title=_("Warning at")),
                 Percentage(title=_("Critical at")),
             ])),
    ]),
    None,
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'aws_elb_healthy_hosts',
    _("AWS/ELB Healthy Hosts"),
    Dictionary(elements=[
        ('levels_overall_hosts_health_perc',
         Tuple(
             title=_("Upper percentual levels for healthy hosts"),
             help=_("These levels refer to the total number of instances or hosts "
                    "that are registered to the load balancer which is the sum of "
                    "healthy and unhealthy instances."),
             elements=[
                 Percentage(title=_("Warning at")),
                 Percentage(title=_("Critical at")),
             ])),
    ]),
    None,
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'aws_elb_backend_connection_errors',
    _("AWS/ELB Backend Connection Errors"),
    Dictionary(elements=[
        ('levels_backend_connections_errors_rate',
         Tuple(
             title=_("Upper levels for backend connection errors per second"),
             elements=[
                 Float(title=_("Warning at")),
                 Float(title=_("Critical at")),
             ])),
    ]),
    None,
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'aws_rds_cpu_credits',
    _("AWS/RDS CPU Credits"),
    Dictionary(elements=[_vs_cpu_credits_balance(), _vs_burst_balance()]),
    TextAscii(title=_("Database identifier")),
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'aws_rds_disk_usage',
    _("AWS/RDS Disk Usage"),
    Dictionary(elements=[
            ('levels',
             Alternative(
                 title=_("Upper levels for disk usage"),
                 style="dropdown",
                 elements=[
                     Tuple(
                         title=_("Set levels"),
                         elements=[
                             Percentage(title=_("Warning at")),
                             Percentage(title=_("Critical at")),
                         ]),
                     Tuple(
                         title=_("No levels"),
                         elements=[
                             FixedValue(None, totext=""),
                             FixedValue(None, totext=""),
                         ]),
                 ])),
    ]),
    TextAscii(title=_("Database identifier")),
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'aws_rds_connections',
    _("AWS/RDS Connections"),
    Dictionary(elements=[
            ('levels',
             Alternative(
                 title=_("Upper levels for connections in use"),
                 style="dropdown",
                 elements=[
                     Tuple(
                         title=_("Set levels"),
                         elements=[
                             Integer(title=_("Warning at")),
                             Integer(title=_("Critical at")),
                         ]),
                     Tuple(
                         title=_("No levels"),
                         elements=[
                             FixedValue(None, totext=""),
                             FixedValue(None, totext=""),
                         ]),
                 ])),
    ]),
    TextAscii(title=_("Database identifier")),
    match_type='dict',
)

register_check_parameters(
    subgroup_applications,
    'aws_rds_replica_lag',
    _("AWS/RDS Replica Lag"),
    Dictionary(elements=[
            ('lag_levels',
             Alternative(
                 title=_("Upper levels replica lag"),
                 style="dropdown",
                 elements=[
                     Tuple(
                         title=_("Set levels"),
                         elements=[
                             Age(title=_("Warning at")),
                             Age(title=_("Critical at")),
                         ]),
                     Tuple(
                         title=_("No levels"),
                         elements=[
                             FixedValue(None, totext=""),
                             FixedValue(None, totext=""),
                         ]),
                 ])),
            ('slot_levels',
             Alternative(
                 title=_("Upper levels the oldest replication slot lag"),
                 style="dropdown",
                 elements=[
                     Tuple(
                         title=_("Set levels"),
                         elements=[
                             Filesize(title=_("Warning at")),
                             Filesize(title=_("Critical at")),
                         ]),
                     Tuple(
                         title=_("No levels"),
                         elements=[
                             FixedValue(None, totext=""),
                             FixedValue(None, totext=""),
                         ]),
                 ])),
    ]),
    TextAscii(title=_("Database identifier")),
    match_type='dict',
)

register_check_parameters(
    subgroup_environment,
    "siemens_plc_flag",
    _("State of Siemens PLC Flags"),
    DropdownChoice(
        help = _("This rule sets the expected state, the one which should result in an OK state, "
                 "of the monitored flags of Siemens PLC devices."),
        title = _("Expected flag state"),
        choices = [
             (True,  _("Expect the flag to be: On")),
             (False, _("Expect the flag to be: Off")),
        ],
        default_value = True
    ),
    TextAscii(
        title = _("Device Name and Value Ident"),
        help = _("You need to concatenate the device name which is configured in the special agent "
                 "for the PLC device separated by a space with the ident of the value which is also "
                 "configured in the special agent."),
        allow_empty = True),
    match_type = "first",
)

register_check_parameters(
    subgroup_environment,
    "siemens_plc_duration",
    _("Siemens PLC Duration"),
    Dictionary(
        elements = [
            ('duration', Tuple(
                title = _("Duration"),
                elements = [
                    Age(
                        title = _("Warning at"),
                    ),
                    Age(
                        title = _("Critical at"),
                    ),
                ]
            )),
        ],
        help = _("This rule is used to configure thresholds for duration values read from "
                 "Siemens PLC devices."),
        title = _("Duration levels"),
    ),
    TextAscii(
        title = _("Device Name and Value Ident"),
        help = _("You need to concatenate the device name which is configured in the special agent "
                 "for the PLC device separated by a space with the ident of the value which is also "
                 "configured in the special agent."),
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_environment,
    "siemens_plc_counter",
    _("Siemens PLC Counter"),
    Dictionary(
        elements = [
            ('levels', Tuple(
                title = _("Counter level"),
                elements = [
                    Integer(
                        title = _("Warning at"),
                    ),
                    Integer(
                        title = _("Critical at"),
                    ),
                ]
            )),
        ],
        help = _("This rule is used to configure thresholds for counter values read from "
                 "Siemens PLC devices."),
        title = _("Counter levels"),
    ),
    TextAscii(
        title = _("Device Name and Value Ident"),
        help = _("You need to concatenate the device name which is configured in the special agent "
                 "for the PLC device separated by a space with the ident of the value which is also "
                 "configured in the special agent."),
    ),
    match_type = "dict",
)

register_check_parameters(
    subgroup_storage,
    "bossock_fibers",
    _("Number of Running Bossock Fibers"),
    Tuple(
        title = _("Number of fibers"),
              elements = [
              Integer(title = _("Warning at"),  unit=_("fibers")),
              Integer(title = _("Critical at"), unit=_("fibers")),
              ]
    ),
    TextAscii( title = _("Node ID")),
    "first"
)
register_check_parameters(
    subgroup_environment,
    "carbon_monoxide",
    ("Carbon monoxide"),
    Dictionary(
        elements = [
            (
                "levels_ppm",
                Tuple(
                    title = "Levels in parts per million",
                    elements = [
                        Integer(title = _("Warning at"),  unit=_("ppm"), default = 10),
                        Integer(title = _("Critical at"), unit=_("ppm"), default = 25),
                    ]
                )
            ),
        ]
    ),
    None,
    "dict"
)
