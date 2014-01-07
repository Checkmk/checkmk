#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

register_rulegroup("datasource_programs",
    _("Datasource Programs"),
    _("Specialized agents, e.g. check via SSH, ESX vSphere, SAP R/3"))
group = "datasource_programs"

register_rule(group,
    "datasource_programs",
    TextAscii(
        title = _("Individual program call instead of agent access"),
        help = _("For agent based checks Check_MK allows you to specify an alternative "
                 "program that should be called by Check_MK instead of connecting the agent "
                 "via TCP. That program must output the agent's data on standard output in "
                 "the same format the agent would do. This is for example useful for monitoring "
                 "via SSH. The command line may contain the placeholders <tt>&lt;IP&gt;</tt> and "
                 "<tt>&lt;HOST&gt;</tt>."),
        label = _("Command line to execute"),
        size = 80,
        attrencode = True))

register_rule(group,
    "special_agents:vsphere",
     Transform(
         valuespec = Dictionary(
            elements = [
                ( "user",
                  TextAscii(
                      title = _("vSphere User name"),
                      allow_empty = False,
                  )
                ),
                ( "secret",
                  Password(
                      title = _("vSphere secret"),
                      allow_empty = False,
                  )
                ),
                ( "tcp_port",
                  Integer(
                       title = _("TCP Port number"),
                       help = _("Port number for connecting to vSphere"),
                       default_value = 4711,
                       minvalue = 1,
                       maxvalue = 65535,
                  )
                ),
                ( "timeout",
                  Integer(
                      title = _("Connection timeout"),
                      help = _("The network timeout in seconds when communicating with vSphere or "
                               "to the Check_MK Agent. The default is 60 seconds. Please note that this "
                               "is not a total timeout but is applied to each individual network transation."),
                      default_value = 60,
                      minvalue = 1,
                      unit = _("seconds"),
                  )
                ),
                ( "infos",
                  Transform(
                      ListChoice(
                         choices = [
                             ( "hostsystem",     _("Host Systems") ),
                             ( "virtualmachine", _("Virtual Machines") ),
                             ( "datastore",      _("Datastores") ),
                             ( "counters",       _("Performance Counters") ),
                         ],
                         default_value = [ "hostsystem", "virtualmachine", "datastore", "counters" ],
                         allow_empty = False,
                       ),
                       forth = lambda v: [ x.replace("storage", "datastore") for x in v ],
                       title = _("Retrieve information about..."),
                    )
                 ),
                 ( "direct",
                   DropdownChoice(
                       title = _("Type of query"),
                       choices = [
                           ( True,    _("Queried host is a host system" ) ),
                           ( False,   _("Queried host is the vCenter") ),
                           ( "agent", _("Queried host is the vCenter with Check_MK Agent installed") ),
                       ],
                       default = True,
                   )
                ),
                ( "skip_placeholder_vms",
                   Checkbox(
                       title = _("Placeholder VMs"),
                       label = _("Do no monitor placeholder VMs"),
                       default_value = True,
                       true_label = _("ignore"),
                       false_label = _("monitor"),
                       help = _("Placeholder VMs are created by the Site Recovery Manager(SRM) and act as backup "
                                "virtual machines in case the default vm is unable to start. This option tells the "
                                "vsphere agent to exclude placeholder vms in its output."
                       ))
                ),
                ( "use_pysphere",
                  Checkbox(
                    title = _("Compatibility mode"),
                    label = _("Support ESX 4.1 (using slower PySphere implementation)"),
                    true_label = _("Support 4.1"),
                    false_label = _("fast"),
                    help = _("The current very performant implementation of the ESX special agent "
                             "does not support older ESX versions than 5.0. Please use the slow "
                             "compatibility mode for those old hosts."),
                  )
                ),
            ],
            optional_keys = [ "tcp_port", "timeout", ],
        ),
        title = _("Check state of VMWare ESX via vSphere"),
        help = _("This rule selects the vSphere agent instead of the normal Check_MK Agent "
                 "and allows monitoring of VMWare ESX via the vSphere API. You can configure "
                 "your connection settings here."),
        forth = lambda a: dict([("skip_placeholder_vms", True), ("use_pysphere" , False)] + a.items())
    ),
    match = 'first')


register_rule(group,
    "special_agents:activemq",
    Tuple(
        title = _("Apache ActiveMQ queues"),
        help = _( "Configure the Server Address and the Portnumber of the target server"),
        elements = [
           TextAscii(title = _("Server Name")),
           Integer( title = _("Port Number"), default_value=8161 ),
           ListChoice(
              choices = [
                ("piggybag",  _("Run in piggybag mode")),
              ],
              allow_empty = True
           )
        ]
    ),
    match = "first")

register_rule(group,
    "special_agents:random",
     FixedValue(
        {},
        title = _("Create random monitoring data"),
        help = _("By configuring this rule for a host - instead of the normal "
                 "Check_MK agent random monitoring data will be created."),
        totext = _("No configuration neccessary."),
    ),
    match = 'first')

register_rule(group,
    "special_agents:fritzbox",
     Dictionary(
        title = _("Check state of Fritz!Box Devices"),
        help = _("This rule selects the Fritz!Box agent, which uses UPNP to gather information "
                 "about configuration and connection status information "),
        elements = [
            ( "timeout",
              Integer(
                  title = _("Connection timeout"),
                  help = _("The network timeout in seconds when communicating via UPNP. "
                           "The default is 10 seconds. Please note that this "
                           "is not a total timeout, instead it is applied to each API call."),
                  default_value = 10,
                  minvalue = 1,
                  unit = _("seconds"),
              )
            ),
        ],
        optional_keys = [ "timeout" ],
    ),
    match = 'first')
