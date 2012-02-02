#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

#!/usr/bin/python
# encoding: utf-8

# Rules for configuring parameters of checks (services)                |

group = _("Parameters and rules for inventorized checks")

register_rule(group,
    "ping_levels",
    Dictionary(
        title = _("PING and host check parameters"),
        help = _("This rule sets the parameters for the host checks (via <tt>check_icmp</tt>) "
                 "and also for PING checks on ping-only-hosts. For the host checks only the "
                 "critical state is relevant, the warning levels are ignored."),
        elements = [
           ( "rta",
             Tuple(
                 title = _("Round trip average"),
                 elements = [
                     Float(title = _("Warning at"), unit = "ms"),
                     Float(title = _("Critical at"), unit = "ms"),
                 ])),
           ( "loss",
             Tuple(
                 title = _("Packet loss"),
                 help = _("When the percentual number of lost packets is equal or greater then "
                          "the level, then the according state is triggered. The default for critical "
                          "is 100%. That means that the check is only critical if <b>all</b> packets "
                          "are lost."),
                 elements = [
                     Percentage(title = _("Warning at")),
                     Percentage(title = _("Critical at")),
                 ])),

            ( "packets",
              Integer(
                  title = _("Number of packets"),
                  help = _("Number ICMP echo request packets to send to the target host"),
                  minvalue = 1,
                  maxvalue = 20,
               )),

             ( "timeout",
               Integer(
                   title = _("Total timeout of check"),
                   help = _("After this time (in seconds) the check is aborted, regardless "
                            "of how many packets have been received yet."),
                   minvalue = 1,
               )),
        ]),
        match="dict")

checkgroups = []

checkgroups.append((
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
    "first"
))


checkgroups.append((
    "brocade_fcport",
    _("Brocade FC FibreChannel ports"),
    Dictionary(
        elements = [
            ("bw",
              Alternative(
                  title = _("Throughput levels"),
                  help = _("In few cases you have to set the link speed manually it you want "
                           "to use relative levels"),
                  elements = [
                      Tuple(
                        title = _("Maximum bandwidth in relation to the total traffic"),
                        elements = [
                            Percentage(title = _("Warning at"), unit = _("percent")),
                            Percentage(title = _("Critical at"), unit = _("percent")),
                        ]
                    ),
                    Tuple(
                        title = _("Megabyte bandwidth of the port"),
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
                    help = _("If the automatic detection of the link "
                             "speed does not work and you want monitors the relative levels of the "
                             "throughtput you have to set the link speed here."),
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
            ("notcredits",
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
                    title = _("Average"),
                    help = _("A number in minutes. If this parameter is set, then "
                           "averaging is turned on and all levels will be applied "
                           "to the averaged values, not the the current ones. Per "
                           "default, averaging is turned off. "),
                   unit = _("minutes"),
                   minvalue = 1,
                )
            ),
            ("phystate",
                Optional(
                    ListChoice(
                        title = _("Allowed states (otherwise check will be critical)"),
                        choices = [ ("1", _("noCard") ),
                                    ("2", _("noTransceiver") ),
                                    ("3", _("laserFault") ),
                                    ("4", _("noLight") ),
                                    ("5", _("noSync") ),
                                    ("6", _("inSync") ),
                                    ("7", _("portFault") ),
                                    ("8", _("diagFault") ),
                                    ("9", _("lockRef") ),
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
                        choices = [ ("0", _("unknown") ),
                                    ("1", _("online") ),
                                    ("2", _("offline") ),
                                    ("3", _("testing") ),
                                    ("4", _("faulty") ),
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
                        choices = [ ("1", _("online") ),
                                    ("2", _("offline") ),
                                    ("3", _("testing") ),
                                    ("4", _("faulty") ),
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
        title = _("Portname"),
        help = _("The name of the switch port"),
    ),
    "first"
))

checkgroups.append((
    "systemtime",
    _("System time offset"),
    Tuple(
        title = _("Time offset"),
        elements = [
           Integer(title = _("Warning at"), unit = _("Seconds")),
           Integer(title = _("Critical at"), unit = _("Seconds")),
        ]
    ),
    None,
    "first"
))

checkgroups.append((
    "fileinfo",
    _("Fileinfo"),
    Dictionary(
        elements = [
            ( "minage",
                Tuple(
                    title = _("Minimal age"),
                    elements = [
                      Age(title = _("Warning younger then")),
                      Age(title = _("Critical younger then")),
                    ]
                )
            ),
            ( "maxage",
                Tuple(
                    title = _("Maximal age"),
                    elements = [
                      Age(title = _("Warning older then")),
                      Age(title = _("Critical older then")),
                    ]
                )
            ),
            ("minsize",
                Tuple( 
                    title = _("Minimal size"),
                    elements = [ 
                      Filesize(title = _("Warning lower as")), 
                      Filesize(title = _("Critical lower as")), 
                    ]
                )
            ),
            ("maxsize",
                Tuple( 
                    title = _("Maximal size"),
                    elements = [ 
                      Filesize(title = _("Warning higher as")), 
                      Filesize(title = _("Critical higher as")), 
                    ]
                )
            )

        ]
    ),
    None,
    "first"
))

checkgroups.append((
    "tcp_conn_stats",
    ("TCP connection stats"),
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
        ]
    ),
    None,
    "first"
))

checkgroups.append((
    "msx_queues",
    _("MS Exchange message queues"),
    Tuple(
        help = _("The length of the queues"),
        elements = [
            Integer(title = _("Warning at queue length")),
            Integer(title = _("Critical at queue length"))
        ]),
        OptionalDropdownChoice(
            title = _("Explicit Queue Names"),
            help = _("You can enter a number of explicit queues names that "
                     "rule should or should not apply here. Builtin queues:<br>"
                     "Active Remote Delivery<br>Active Mailbox Delivery<br>"
                     "Retry Remote Delivery<br>Poison Queue Length<br>"),
           choices = [
              ( "Active Remote Delivery",  "Active Remote Delivery" ),
              ( "Retry Remote Delivery",   "Retry Remote Delivery" ),
              ( "Active Mailbox Delivery", "Active Mailbox Delivery" ),
              ( "Poison Queue Length",     "Poison Queue Length" ),
              ],
           otherlabel = _("specify manually ->"),
           explicit = TextAscii(allow_empty = False)),
    "first")
)

checkgroups.append((
    "filesystem",
    _("Filesystems (used space and growth)"),
    Dictionary(
        elements = [
            ( "levels",
              Tuple(
                  title = _("Levels for the used space"),
                  elements = [
                      Percentage(title = _("Warning at"),  label = _("% usage"), allow_int = True),
                      Percentage(title = _("Critical at"), label = _("% usage"), allow_int = True)])),
            (  "magic",
               Float(
                  title = _("Magic factor (automatic level adaptation for large filesystems)"),
                  minvalue = 0.1,
                  maxvalue = 1.0)),
            (  "magic_normsize",
               Integer(
                   title = _("Reference size for magic factor"),
                   minvalue = 1,
                   label = _("GB"))),
            ( "levels_low",
              Tuple(
                  title = _("Minimum levels if using magic factor"),
                  help = _("The filesystem levels will never fall below these values, when using "
                           "the magic factor and the filesystem is very small."),
                  elements = [
                      Percentage(title = _("Warning at"),  label = _("% usage"), allow_int = True),
                      Percentage(title = _("Critical at"), label = _("% usage"), allow_int = True)])),
            (  "trend_range",
               Optional(
                   Integer(
                       title = _("Range for filesystem trend computation"),
                       minvalue = 1,
                       label= _("hours")),
                   title = _("Trend computation"),
                   label = _("Enable trend computation"))),
            (  "trend_mb",
               Tuple(
                   title = _("Levels on trends in MB per range"),
                   elements = [
                       Integer(title = _("Warning at"), label = _("MB / range")),
                       Integer(title = _("Critical at"), label = _("MB / range"))
                   ])),
            (  "trend_perc",
               Tuple(
                   title = _("Levels for the percentual growth"),
                   elements = [
                       Percentage(title = _("Warning at"), label = _("% / range")),
                       Percentage(title = _("Critical at"), label = _("% / range"))
                   ])),
            (  "trend_timeleft",
               Tuple(
                   title = _("Levels on the time left until the filesystem gets full"),
                   elements = [
                       Integer(title = _("Warning at"), label = _("days left")),
                       Integer(title = _("Critical at"), label = _("days left"))
                   ])),
            ( "trend_perfdata",
              Checkbox(
                  title = _("Trend performance data"),
                  label = _("Enable performance data from trends"))),


        ]),
    TextAscii(
        title = _("Mount point"),
        help = _("For Linux/UNIX systems, specify the mount point, for Windows systems "
                 "the drive letter uppercase followed by a colon, e.g. <tt>C:</tt>"),
        allow_empty = False),
    "dict")
)

checkgroups.append((
    "if",
    _("Network interfaces and switch ports"),
    Dictionary(
        elements = [
            ( "errors",
              Tuple(
                  title = _("Levels for error rates"),
                  help = _("This levels make the check go warning or critical whenever the "
                           "<b>percentual error rate</b> of the monitored interface exceeds "
                           "the given bounds. The error rate is computed by dividing number of "
                           "errors by the total number of packets (successful plus errors)."),
                  elements = [
                      Percentage(title = _("Warning at"), label = _("% errors")),
                      Percentage(title = _("Critical at"), label = _("% errors"))
                  ])),

             ( "speed",
               OptionalDropdownChoice(
                   title = _("Operating speed"),
                   help = _("If you use this parameter then the check goes warning if the "
                            "interface is not operating at the expected speed (e.g. it "
                            "is working with 100MBit/s instead of 1GBit/s.<b>Note:</b> "
                            "some interfaces do not provide speed information. In such cases "
                            "this setting is used as the assumed speed when it comes to "
                            "traffic monitoring (see below)."),
                  choices = [
                     ( None,       "ignore speed" ),
                     ( 10000000,   "10 MBit/s" ),
                     ( 100000000,  "100 MBit/s" ),
                     ( 1000000000, "1 GBit/s" ) ],
                  otherlabel = _("specify manually ->"),
                  explicit = \
                      Integer(title = _("Other speed in bits per second"),
                              label = _("Bits per second")))
             ),
             ( "state",
                Optional(
                    ListChoice(
                        title = _("Allowed states:"),
                        choices = _if_portstate_choices),
                    title = _("Operational State"),
                    help = _("Activating the monitoring of the operational state (opstate), "
                             "the check will get warning or critical of the current state "
                             "of the interface does not match the expected state or states."),
                    label = _("Ignore the operational state"),
                    none_label = _("ignore"),
                    negate = True)
             ),
             ( "traffic",
               Alternative(
                   title = _("Used bandwidth (traffic)"),
                   help = _("Settings levels on the used bandwidth is optional. If you do set "
                            "levels you might also consider using an averaging."),
                   elements = [
                       Tuple(
                           title = _("Percentual levels (in relation to port speed)"),
                           elements = [
                               Percentage(title = _("Warning at"), label = _("% of port speed")),
                               Percentage(title = _("Critical at"), label = _("% of port speed")),
                           ]
                       ),
                       Tuple(
                           title = _("Absolute levels in <b>bytes</b> per second"),
                           elements = [
                               Integer(title = _("Warning at"), label = _("bytes per second")),
                               Integer(title = _("Critical at"), label = _("bytes per second")),
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
                     label = _("minutes"),
                     minvalue = 1,
                 )
               ),


           ]),
    TextAscii(
        title = _("port specification"),
        allow_empty = False),
    "dict",
    ))


checkgroups.append((
    "memory",
    _("Main memory usage (Linux / UNIX)"),
    Alternative(
        help = _("The levels for memory usage on Linux and UNIX systems take into account the "
               "currently used memory (RAM or SWAP) by all processes and sets this in relation "
               "to the total RAM of the system. This means that the memory usage can exceed 100%. "
               "A usage of 200% means that the total size of all processes is twice as large as "
               "the main memory, so <b>at least</b> the half of it is currently swapped out."),
        elements = [
            Tuple(
                title = _("Specify levels in percentage of total RAM"),
                elements = [
                  Percentage(title = _("Warning at a usage of"), label = _("% of RAM"), max_value = None),
                  Percentage(title = _("Critical at a usage of"), label = _("% of RAM"), max_value = None)]),
            Tuple(
                title = _("Specify levels in absolute usage values"),
                elements = [
                  Integer(title = _("Warning at"), unit = _("MB")),
                  Integer(title = _("Critical at"), unit = _("MB"))]),
            ]),
    None, None))


checkgroups.append((
    "cpu_load",
    _("CPU load (not utilization!)"),
    Tuple(
          help = _("The CPU load of a system is the number of processes currently being "
                   "in the state <u>running</u>, i.e. either they occupy a CPU or wait "
                   "for one. The <u>load average</u> is the averaged CPU load over the last 1, "
                   "5 or 15 minutes. The following levels will be applied on the average "
                   "load. On Linux system the 15-minute average load is used when applying "
                   "those levels."),
          elements = [
              Integer(title = _("Warning at a load of")),
              Integer(title = _("Critical at a load of"))]),
    None, None))

checkgroups.append((
    "cpu_utilization",
    _("CPU utilization (disk wait)"),
    Optional(
        Tuple(
              elements = [
                  Percentage(title = _("Warning at a disk wait of"), label = "%"),
                  Percentage(title = _("Critical at a disk wait of"), label = "%")]),
        label = _("Alert on too high disk wait (IO wait)"),
        help = _("The CPU utilization sums up the percentages of CPU time that is used "
                 "for user processes, kernel routines (system), disk wait (sometimes also "
                 "called IO wait) or nothing (idle). "
                 "Currently you can only set warning/critical levels to the disk wait. This "
                 "is the total percentage of time all CPUs have nothing else to do then waiting "
                 "for data coming from or going to disk. If you have a significant disk wait "
                 "the the bottleneck of your server is IO. Please note that depending on the "
                 "applications being run this might or might not be totally normal.")),
    None, None))

checkgroups.append((
    "akcp_humidity",
    _("AKCP Humidity Levels"),
    Tuple(
          help = _("This Rulset sets the threshold limits for humidity sensors attached to " 
                   "AKCP Sensor Probe "),
          elements = [
              Integer(title = _("Critical if moisture lower than")),
              Integer(title = _("Warning if moisture lower than")),
              Integer(title = _("Warning if moisture higher than")),
              Integer(title = _("Critical if moisture higher than")),
              ]),
    TextAscii(
        title = _("Service descriptions"),
        allow_empty = False),
     None))

checkgroups.append((
    "oracle_logswitches",
    _("Oracle Logswitches"),
    Tuple(
          help = _("This check monitors the number of log switches of an ORACLE " 
                   "database instance in the last 60 minutes. You can set levels for upper and lower bounds."),
          elements = [
              Integer(title = _("Critical if fewer than"), unit=_("log switches")),
              Integer(title = _("Warning if fewer than"), unit=_("log switches")),
              Integer(title = _("Warning if more than"), unit=_("log switches")),
              Integer(title = _("Critical if more than"), unit=_("log switches")),
              ]),
    TextAscii(
        title = _("Service descriptions"),
        allow_empty = False),
     None))


checkgroups.append((
    "win_dhcp_pools",
    _("Windows DHCP Pool"),
    Tuple(
          help = _("The count of remaining entries in the DHCP pool represents "
                   "the number of IP addresses left which can be assigned in the network"),
          elements = [
              Percentage(title = _("Warning if pool usage higher than")),
              Percentage(title = _("Critical if pool usage higher than")),
              ]),
    TextAscii(
        title = _("Service descriptions"),
        allow_empty = False),
     None))

checkgroups.append((
    "threads",
    _("Number of threads"),
    Tuple(
          help = _("This levels check the number of currently existing threads on the system. Each process has at "
                   "least one thread."),
          elements = [
              Integer(title = _("Warning at"), label = _("threads")),
              Integer(title = _("Critical at"), label = _("threads"))]),
    None, None))

checkgroups.append((
    "vm_counter",
    _("Number of kernel events per second"),
    Tuple(
          help = _("This ruleset applies to several similar checks measing various kernel "
                   "events like context switches, process creations and major page faults. "
                   "Please create separate rules for each type of kernel counter you "
                   "want to set levels for."),
          show_titles = False,
          elements = [
              Optional(
                 Float(label = _("events per second")),
                 title = _("Set warning level:"),
                 sameline = True),
              Optional(
                 Float(label = _("events per second")),
                 title = _("Set critical level:"),
                 sameline = True)]),

    DropdownChoice(
        title = _("kernel counter"),
        choices = [ (x,x) for x in [
           "Context Switches",
           "Process Creations",
           "Major Page Faults" ]]),
    "first"))

checkgroups.append((
    "disk_io",
    _("Levels on disk IO (throughput)"),
    Dictionary(
        elements = [
            ( "read",
              Tuple(
                  title = _("Read throughput"),
                  elements = [
                      Integer(title = "warning at", unit = _("MB/s")),
                      Integer(title = "critical at", unit = _("MB/s"))
                  ])),
            ( "write",
              Tuple(
                  title = _("Write throughput"),
                  elements = [
                      Integer(title = "warning at", unit = _("MB/s")),
                      Integer(title = "critical at", unit = _("MB/s"))
                  ])),
            ( "average",
              Integer(
                  title = _("Average"),
                  help = _("When averaging is set, then an floating average value "
                           "of the disk throughput is computed and the levels for read "
                           "and write will be applied to the average instead of the current "
                           "value."),
                 unit = "min"))
        ]),
    OptionalDropdownChoice(
        choices = [ ( "SUMMARY", _("Summary of all disks") ),
                    ( "read",    _("Summary of disk input (read)") ),
                    ( "write",   _("Summary of disk output (write)") ),
                  ],
        otherlabel = _("One explicit devices ->"),
        explicit = TextAscii(allow_empty = False),
        title = _("Device"),
        help = _("For a summarized throughput of all disks, specify <tt>SUMMARY</tt>, for a "
                 "sum of read or write throughput write <tt>read</tt> or <tt>write</tt> resp. "
                 "A per-disk IO is specified by the drive letter and a colon on Windows "
                 "(e.g. <tt>C:</tt>) or by the device name on Linux/UNIX (e.g. <tt>/dev/sda</tt>).")),
    "first"))


checkgroups.append((
    "mailqueue_length",
    _("Number of mails in outgoing mail queue"),
    Tuple(
          help = _("This levels is applied to the number of Email that are currently in the outgoing mail queue."),
          elements = [
              Integer(title = _("Warning at"), label = _("mails")),
              Integer(title = _("Critical at"), label = _("mails"))]),
    None, None))

checkgroups.append((
    "uptime",
    _("Display the system's uptime as a check"),
    None,
    None, None))

# Create rules for check parameters of inventorized checks
for checkgroup, title, valuespec, itemspec, matchtype in checkgroups:
    if not valuespec:
        continue # would be useles rule if check has no parameters
    itemenum = None
    if itemspec:
        itemtype = "item"
        itemname = itemspec.title()
        itemhelp = itemspec.help()
        if isinstance(itemspec, DropdownChoice):
            itemenum = itemspec._choices
    else:
        itemtype = None
        itemname = None
        itemhelp = None

    register_rule(
        group,
        varname = "checkgroup_parameters:%s" % checkgroup,
        title = title,
        valuespec = valuespec,
        itemtype = itemtype, itemname = itemname,
        itemhelp = itemhelp,
        itemenum = itemenum,
        match = matchtype)


register_rule(
    group,
    "if_disable_if64_hosts",
    title = _("Hosts forced to use <tt>if</tt> instead of <tt>if64</tt>"),
    help = _("A couple of switches with broken firmware report that they "
             "support 64 bit counters but do not output any actual data "
             "in those counters. Listing those hosts in this rule forces "
             "them to use the interface check with 32 bit counters instead."))


# Create Rules for static checks
group = _("Statically configured checks")

for checkgroup, title, valuespec, itemspec, matchtype in checkgroups:
    elements = [
        CheckTypeGroupSelection(
            checkgroup,
            title = _("Checktype"),
            help = _("Please choose the check plugin")) ]
    if itemspec:
        elements.append(itemspec)
    if not valuespec:
        valuespec =\
            FixedValue(None,
                help = _("This check has no parameters."),
                totext = "")
    valuespec._title = _("Parameters")
    elements.append(valuespec)

    register_rule(
        group, "static_checks:%s" % checkgroup,
        title = title,
        valuespec = Tuple(
            title = valuespec.title(),
            elements = elements,
        ),
        match = "all")

