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
        empty_text = _("Access Check_MK Agent via TCP"),
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
                       help = _("Port number for HTTPS connection to vSphere"),
                       default_value = 443,
                       minvalue = 1,
                       maxvalue = 65535,
                  )
                ),
                ( "timeout",
                  Integer(
                      title = _("Connect Timeout"),
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
                             ( "licenses",       _("License Usage") ),
                         ],
                         default_value = [ "hostsystem", "virtualmachine", "datastore", "counters" ],
                         allow_empty = False,
                       ),
                       forth = lambda v: [ x.replace("storage", "datastore") for x in v ],
                       title = _("Retrieve information about..."),
                    )
                 ),
                 ( "host_pwr_display",
                   DropdownChoice(
                       title = _("Display ESX Host power state on"),
                       choices = [
                           ( None,      _("The queried ESX system (vCenter / Host)") ),
                           ( "esxhost", _("The ESX Host") ),
                           ( "vm",      _("The Virtual Machine") ),
                       ],
                       default = None,
                   )
                 ),
                 ( "vm_pwr_display",
                   DropdownChoice(
                       title = _("Display VM power state on"),
                       choices = [
                           ( None,      _("The queried ESX system (vCenter / Host)") ),
                           ( "esxhost", _("The ESX Host") ),
                           ( "vm",      _("The Virtual Machine") ),
                       ],
                       default = None,
                   )
                 ),
                 ( "spaces",
                   DropdownChoice(
                       title = _("Spaces in hostnames"),
                       choices = [
                           ( "cut",        _("Cut everything after first space") ),
                           ( "underscore", _("Replace with underscores") ),
                       ],
                       default = "underscore",
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
            optional_keys = [ "tcp_port", "timeout", "vm_pwr_display", "host_pwr_display" ],
        ),
        title = _("Check state of VMWare ESX via vSphere"),
        help = _("This rule selects the vSphere agent instead of the normal Check_MK Agent "
                 "and allows monitoring of VMWare ESX via the vSphere API. You can configure "
                 "your connection settings here."),
        forth = lambda a: dict([("skip_placeholder_vms", True), ("use_pysphere" , False), ("spaces", "underscore")] + a.items())
    ),
    factory_default = FACTORY_DEFAULT_UNUSED, # No default, do not use setting if no rule matches
    match = 'first')

register_rule(group,
    "special_agents:netapp",
    Dictionary(
            title = _("Username and password for the NetApp Filer."),
            elements = [
                ( "username",
                  TextAscii(
                      title = _("Username"),
                      allow_empty = False,
                  )
                ),
                ( "password",
                  Password(
                      title = _("Password"),
                      allow_empty = False,
                  )
                ),
            ],
            optional_keys = False
    ),
    title = _("Check NetApp via WebAPI"),
    help  = _("This rule set selects the NetApp special agent instead of the normal Check_MK Agent "
              "and allows monitoring via the NetApp API. Right now only <i>7-Mode</i> is supported, "
              "<i>Cluster Mode</i> will follow soon. Important: To make this special agent NetApp work "
              "you will have to provide two additional python files (<tt>NaServer.py</tt>, <tt>NaElement.py</tt>) "
              "from the NetApp Manageability SDK. They need to be put into the site directory "
              "into <tt>~/local/lib/python</tt>. The user requires a number of permissions for specific API classes. "
              "They are displayed if you call the agent with <tt>agent_netapp --help</tt>. The agent itself "
              "is located in the site directory under <tt>~/share/check_mk/agents/special</tt>."),
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
                ("piggybag",  _("Run in piggyback mode")),
              ],
              allow_empty = True
           )
        ]
    ),
    factory_default = FACTORY_DEFAULT_UNUSED, # No default, do not use setting if no rule matches
    match = "first")

register_rule(group,
    "special_agents:emcvnx",
     Dictionary(
        title = _("Check state of EMC VNX storage systems"),
        help = _("This rule selects the EMC VNX agent instead of the normal Check_MK Agent "
                 "and allows monitoring of EMC VNX storage systems by calling naviseccli "
                 "commandline tool locally on the monitoring system. Make sure it is installed "
                 "and working. You can configure your connection settings here."
                 ),
        elements = [
            ( "user",
              TextAscii(
                  title = _("EMC VNX admin user name"),
                  allow_empty = True,
                  help = _("If you leave user name and password empty, the special agent tries to "
                           "authenticate against the EMC VNX device by Security Files. "
                           "These need to be created manually before using. Therefor run as "
                           "instance user (if using OMD) or Nagios user (if not using OMD) "
                           "a command like "
                           "<tt>naviseccli -AddUserSecurity -scope 0 -password PASSWORD -user USER</tt> "
                           "This creates <tt>SecuredCLISecurityFile.xml</tt> and "
                           "<tt>SecuredCLIXMLEncrypted.key</tt> in the home directory of the user "
                           "and these files are used then."
                           ),
              )
            ),
            ( "password",
              Password(
                  title = _("EMC VNX admin user password"),
                  allow_empty = True,
              )
            ),
            ( "infos",
              Transform(
                  ListChoice(
                     choices = [
                         ( "disks",          _("Disks") ),
                         ( "hba",            _("iSCSI HBAs") ),
                         ( "hwstatus",       _("Hardware Status") ),
                         ( "raidgroups",     _("RAID Groups") ),
                         ( "agent",          _("Model and Revsion") ),
                     ],
                     default_value = [ "disks", "hba", "hwstatus", ],
                     allow_empty = False,
                   ),
                   title = _("Retrieve information about..."),
                )
             ),
        ],
        optional_keys = [ ],
    ),
    factory_default = FACTORY_DEFAULT_UNUSED, # No default, do not use setting if no rule matches
    match = 'first')

register_rule(group,
    "special_agents:ibmsvc",
     Dictionary(
        title = _("Check state of IBM SVC / V7000 storage systems"),
        help = _("This rule set selects the <tt>ibmsvc</tt> agent instead of the normal Check_MK Agent "
                 "and allows monitoring of IBM SVC / V7000 storage systems by calling "
                 "ls* commands there over SSH. "
                 "Make sure you have SSH key authentication enabled for your monitoring user. "
                 "That means: The user your monitoring is running under on the monitoring "
                 "system must be able to ssh to the storage system as the user you gave below "
                 "without password."
                 ),
        elements = [
            ( "user",
              TextAscii(
                  title = _("IBM SVC / V7000 user name"),
                  allow_empty = True,
                  help = _("User name on the storage system. Read only permissions are sufficient."),
              )
            ),
            ( "accept-any-hostkey",
               Checkbox(
                   title = _("Accept any SSH Host Key"),
                   label = _("Accept any SSH Host Key"),
                   default_value = False,
                   help = _("Accepts any SSH Host Key presented by the storage device. "
                            "Please note: This might be a security issue because man-in-the-middle "
                            "attacks are not recognized! Better solution would be to add the "
                            "SSH Host Key of the monitored storage devices to the .ssh/known_hosts "
                            "file for the user your monitoring is running under (on OMD: the site user)"
                   ))
            ),
            ( "infos",
              Transform(
                  ListChoice(
                     choices = [
                         ( "lshost",          _("Hosts Connected") ),
                         ( "lslicense",       _("Licensing Status") ),
                         ( "lsmdisk",         _("MDisks") ),
                         ( "lsmdiskgrp",      _("MDisksGrps") ),
                         ( "lsnode",          _("IO Groups") ),
                         ( "lsnodestats",     _("Node Stats") ),
                         ( "lssystem",        _("System Info") ),
                         ( "lssystemstats",   _("System Stats") ),
                         ( "lseventlog",      _("Event Log") ),
                         ( "lsportfc",        _("FC Ports") ),
                         ( "lsportsas",       _("SAS Ports") ),
                         ( "lsenclosure",     _("Enclosures") ),
                         ( "lsenclosurestats", _("Enclosure Stats") ),
                         ( "lsarray",         _("RAID Arrays") ),
                     ],
                     default_value = [ "lshost", "lslicense", "lsmdisk", "lsmdiskgrp", "lsnode",
                                       "lsnodestats", "lssystem", "lssystemstats", "lsportfc",
                                       "lsenclosure", "lsenclosurestats", "lsarray" ],
                     allow_empty = False,
                   ),
                   title = _("Retrieve information about..."),
                )
             ),
        ],
        optional_keys = [ ],
    ),
    factory_default = FACTORY_DEFAULT_UNUSED, # No default, do not use setting if no rule matches
    match = 'first')


register_rule(group,
    "special_agents:random",
     FixedValue(
        {},
        title = _("Create random monitoring data"),
        help = _("By configuring this rule for a host - instead of the normal "
                 "Check_MK agent random monitoring data will be created."),
        totext = _("Create random monitoring data"),
    ),
    factory_default = FACTORY_DEFAULT_UNUSED, # No default, do not use setting if no rule matches
    match = 'first')

register_rule(group,
    "special_agents:fritzbox",
     Dictionary(
        title = _("Check state of Fritz!Box Devices"),
        help = _("This rule selects the Fritz!Box agent, which uses UPNP to gather information "
                 "about configuration and connection status information."),
        elements = [
            ( "timeout",
              Integer(
                  title = _("Connect Timeout"),
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
    factory_default = FACTORY_DEFAULT_UNUSED, # No default, do not use setting if no rule matches
    match = 'first')


register_rulegroup("datasource_programs",
    _("Datasource Programs"),
    _("Specialized agents, e.g. check via SSH, ESX vSphere, SAP R/3"))

group = "datasource_programs"


register_rule(group,
    "special_agents:innovaphone",
    Tuple(
        title = _("Innovaphone Gateways"),
        help = _( "Please specify the user and password needed to access the xml interface"),
        elements = [
           TextAscii(title = _("Username")),
           Password( title = _("Password")),
        ]
    ),
    factory_default = FACTORY_DEFAULT_UNUSED,
    match = "first")

register_rule(group,
    "special_agents:hivemanager",
    Tuple(
        title = _("Aerohive HiveManager"),
        help = _( "Activate monitoring of host via a HTTP connect to the HiveManager"),
        elements = [
           TextAscii(title = _("Username")),
           Password( title = _("Password")),
        ]
    ),
    factory_default = FACTORY_DEFAULT_UNUSED,
    match = "first")

register_rule(group,
    "special_agents:allnet_ip_sensoric",
     Dictionary(
        title = _("Check state of ALLNET IP Sensoric Devices"),
        help = _("This rule selects the ALLNET IP Sensoric agent, which fetches "
                 "/xml/sensordata.xml from the device by HTTP and extracts the "
                 "needed monitoring information from this file."),
        elements = [
            ( "timeout",
              Integer(
                  title = _("Connect Timeout"),
                  help = _("The network timeout in seconds when communicating via HTTP. "
                           "The default is 10 seconds."),
                  default_value = 10,
                  minvalue = 1,
                  unit = _("seconds"),
              )
            ),
        ],
        optional_keys = [ "timeout" ],
    ),
    factory_default = FACTORY_DEFAULT_UNUSED, # No default, do not use setting if no rule matches
    match = 'first')


register_rule(group,
    "special_agents:ucs_bladecenter",
    Dictionary(
        elements = [
            ( "username",
              TextAscii(
                  title = _("Username"),
                  allow_empty = False,
              )
            ),
            ( "password",
              Password(
                  title = _("Password"),
                  allow_empty = False,
              )
            ),
        ],
        optional_keys = False
    ),
    title = _("Check state of UCS Bladecenter"),
    help = _("This rule selects the UCS Bladecenter agent instead of the normal Check_MK Agent "
             "which collects the data through the UCS Bladecenter Web API"),
    match = 'first')


def validate_siemens_plc_values(value, varprefix):
    valuetypes = {}
    for index, (db_number, address, datatype, valuetype, ident) in enumerate(value):
        valuetypes.setdefault(valuetype, [])
        if ident in valuetypes[valuetype]:
            raise MKUserError("%s_%d_%d" % (varprefix, index+1, 4),
                              _("The ident of a value needs to be unique per valuetype."))
        valuetypes[valuetype].append(ident)

group = "datasource_programs"
register_rule(group,
    "special_agents:siemens_plc",
    Dictionary(
        elements = [
            ("rack", Integer(
                title = _("Number of the Rack"),
                minvalue = 0,
            )),
            ("slot", Integer(
                title = _("Number of the Slot"),
                minvalue = 0,
            )),
            ("tcp_port", Integer(
                title = _("TCP Port number"),
                help = _("Port number for communicating with the PLC"),
                default_value = 102,
                minvalue = 1,
                maxvalue = 65535,
            )),
            ("timeout", Integer(
                title = _("Connect Timeout"),
                help = _("The connect timeout in seconds when establishing a connection "
                         "with the PLC."),
                default_value = 60,
                minvalue = 1,
                unit = _("seconds"),
            )),
            ("values", ListOf(
                Tuple(
                    elements = [
                        Integer(
                            title = "<nobr>%s</nobr>" % _("DB Number"),
                            minvalue = 1,
                        ),
                        Integer(
                            title = _("Address"),
                        ),
                        DropdownChoice(
                            title = _("Datatype"),
                            choices = [
                                ("dint", _("Double Integer (DINT)")),
                                ("real", _("Real Number (REAL)")),
                            ],
                        ),
                        DropdownChoice(
                            title = _("Type of the value"),
                            choices = [
                                (None,    _("Unclassified")),
                                ("temp",  _("Temperature")),
                                ("hours", _("Hours")),
                            ],
                        ),
                        ID(
                            title = _("Ident of the value"),
                            help = _(" An identifier of your choice. This identifier "
                                     "is used by the Check_MK checks to access "
                                     "and identify the single values. The identifier "
                                     "needs to be unique within a group of VALUETYPES."),
                        ),
                    ],
                    orientation = "horizontal",
                ),
                title = _("Values to fetch"),
                validate = validate_siemens_plc_values,
            )),
        ],
        optional_keys = ["timeout"],
        title = _("Siemens PLC (SPS)"),
        help = _("This rule selects the Siemens PLC agent instead of the normal Check_MK Agent "
                 "and allows monitoring of Siemens PLC using the Snap7 API. You can configure "
                 "your connection settings and values to fetch here."),
    ),
    factory_default = FACTORY_DEFAULT_UNUSED, # No default, do not use setting if no rule matches
    match = 'first')
