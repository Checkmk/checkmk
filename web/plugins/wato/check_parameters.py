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

# Rules for configuring parameters of checks (services)

register_rulegroup("checkparams", _("Parameters for Inventorized Checks"),
    _("Levels and other parameters for checks found by the Check_MK inventory.\n"
      "Use these rules in order to define parameters like filesystem levels, "
      "levels for CPU load and other things for services that have been found "
      "by the automatic service detection (inventory) of Check_MK."))
group = "checkparams"

subgroup_networking =   _("Networking")
subgroup_storage =      _("Storage, Filesystems and Files")
subgroup_os =           _("Operating System Resources")
subgroup_printing =     _("Printers")
subgroup_environment =  _("Temperature, Humidity, Electrical Parameters, etc.")
subgroup_applications = _("Applications, Processes &amp; Services")
subgroup_virt =         _("Virtualization")
subgroup_hardware =     _("Hardware, BIOS")
subgroup_inventory =    _("Inventory - automatic service detection")

register_rule(group + "/" + subgroup_networking,
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
                     Float(title = _("Warning if above"), unit = "ms"),
                     Float(title = _("Critical if above"), unit = "ms"),
                 ])),
           ( "loss",
             Tuple(
                 title = _("Packet loss"),
                 help = _("When the percentual number of lost packets is equal or greater then "
                          "the level, then the according state is triggered. The default for critical "
                          "is 100%. That means that the check is only critical if <b>all</b> packets "
                          "are lost."),
                 elements = [
                     Percentage(title = _("Warning if above")),
                     Percentage(title = _("Critical if above")),
                 ])),

            ( "packets",
              Integer(
                  title = _("Number of packets"),
                  help = _("Number ICMP echo request packets to send to the target host on each "
                           "check execution. All packets are sent directly on check execution. Afterwards "
                           "the check waits for the incoming packets."),
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

register_rule(group + '/' + subgroup_applications,
    varname   = "logwatch_rules",
    title     = _('Logwatch Patterns'),
    valuespec = ListOf(
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
             RegExp(
                 title = _("Pattern (Regex)"),
                 size  = 40,
             ),
             TextAscii(
                 title = _("Comment"),
                 size  = 40,
             ),
          ]
      ),
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
    itemtype = 'item',
    itemname = 'Logfile',
    itemhelp = _("Put the item names of the logfiles here. For example \"System$\" "
                 "to select the service \"LOG System\". You can use regular "
                 "expressions which must match the beginning of the logfile name."),
    match = 'all',
)

register_rule(group + '/' + subgroup_inventory,
    varname   = "inventory_services_rules",
    title     = _("Windows Service Inventory"),
    valuespec = Dictionary(
        elements = [
            ('services', ListOfStrings(
                title = _("Services (Regular Expressions)"),
                help  = _('Matching the begining of the service names (regular expression). '
                          'If no service is given, this rule will match all services.'),
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

#dublicate: check_mk_configuration.py
_if_portstate_choices = [
                        ( '1', 'up(1)'),
                        ( '2', 'down(2)'),
                        ( '3', 'testing(3)'),
                        ( '4', 'unknown(4)'),
                        ( '5', 'dormant(5)') ,
                        ( '6', 'notPresent(6)'),
                        ( '7', 'lowerLayerDown(7)'),
                        ]

#dublicate: check_mk_configuration.py
_if_porttype_choices = [
  ("1", "other(1)" ), ("2", "regular1822(2)" ), ("3", "hdh1822(3)" ), ("4", "ddnX25(4)" ),
  ("5", "rfc877x25(5)" ), ("6", "ethernetCsmacd(6)" ), ("7", "iso88023Csmacd(7)" ), ("8",
  "iso88024TokenBus(8)" ), ("9", "iso88025TokenRing(9)" ), ("10", "iso88026Man(10)" ),
  ("11", "starLan(11)" ), ("12", "proteon10Mbit(12)" ), ("13", "proteon80Mbit(13)" ), ("14",
  "hyperchannel(14)" ), ("15", "fddi(15)" ), ("16", "lapb(16)" ), ("17", "sdlc(17)" ), ("18",
  "ds1(18)" ), ("19", "e1(19)" ), ("20", "basicISDN(20)" ), ("21", "primaryISDN(21)" ), ("22",
  "propPointToPointSerial(22)" ), ("23", "ppp(23)" ), ("24", "softwareLoopback(24)" ), ("25",
  "eon(25)" ), ("26", "ethernet3Mbit(26)" ), ("27", "nsip(27)" ), ("28", "slip(28)" ), ("29",
  "ultra(29)" ), ("30", "ds3(30)" ), ("31", "sip(31)" ), ("32", "frameRelay(32)" ), ("33",
  "rs232(33)" ), ("34", "para(34)" ), ("35", "arcnet(35)" ), ("36", "arcnetPlus(36)" ),
  ("37", "atm(37)" ), ("38", "miox25(38)" ), ("39", "sonet(39)" ), ("40", "x25ple(40)" ),
  ("41", "iso88022llc(41)" ), ("42", "localTalk(42)" ), ("43", "smdsDxi(43)" ), ("44",
  "frameRelayService(44)" ), ("45", "v35(45)" ), ("46", "hssi(46)" ), ("47", "hippi(47)" ),
  ("48", "modem(48)" ), ("49", "aal5(49)" ), ("50", "sonetPath(50)" ), ("51", "sonetVT(51)"
  ), ("52", "smdsIcip(52)" ), ("53", "propVirtual(53)" ), ("54", "propMultiplexor(54)" ),
  ("55", "ieee80212(55)" ), ("56", "fibreChannel(56)" ), ("57", "hippiInterface(57)" ), ("58",
  "frameRelayInterconnect(58)" ), ("59", "aflane8023(59)" ), ("60", "aflane8025(60)" ), ("61",
  "cctEmul(61)" ), ("62", "fastEther(62)" ), ("63", "isdn(63)" ), ("64", "v11(64)" ), ("65",
  "v36(65)" ), ("66", "g703at64k(66)" ), ("67", "g703at2mb(67)" ), ("68", "qllc(68)" ), ("69",
  "fastEtherFX(69)" ), ("70", "channel(70)" ), ("71", "ieee80211(71)" ), ("72", "ibm370parChan(72)"
  ), ("73", "escon(73)" ), ("74", "dlsw(74)" ), ("75", "isdns(75)" ), ("76", "isdnu(76)" ),
  ("77", "lapd(77)" ), ("78", "ipSwitch(78)" ), ("79", "rsrb(79)" ), ("80", "atmLogical(80)" ),
  ("81", "ds0(81)" ), ("82", "ds0Bundle(82)" ), ("83", "bsc(83)" ), ("84", "async(84)" ), ("85",
  "cnr(85)" ), ("86", "iso88025Dtr(86)" ), ("87", "eplrs(87)" ), ("88", "arap(88)" ), ("89",
  "propCnls(89)" ), ("90", "hostPad(90)" ), ("91", "termPad(91)" ), ("92", "frameRelayMPI(92)" ),
  ("93", "x213(93)" ), ("94", "adsl(94)" ), ("95", "radsl(95)" ), ("96", "sdsl(96)" ), ("97",
  "vdsl(97)" ), ("98", "iso88025CRFPInt(98)" ), ("99", "myrinet(99)" ), ("100", "voiceEM(100)"
  ), ("101", "voiceFXO(101)" ), ("102", "voiceFXS(102)" ), ("103", "voiceEncap(103)" ), ("104",
  "voiceOverIp(104)" ), ("105", "atmDxi(105)" ), ("106", "atmFuni(106)" ), ("107", "atmIma(107)"
  ), ("108", "pppMultilinkBundle(108)" ), ("109", "ipOverCdlc(109)" ), ("110", "ipOverClaw(110)"
  ), ("111", "stackToStack(111)" ), ("112", "virtualIpAddress(112)" ), ("113", "mpc(113)" ),
  ("114", "ipOverAtm(114)" ), ("115", "iso88025Fiber(115)" ), ("116", "tdlc(116)" ), ("117",
  "gigabitEthernet(117)" ), ("118", "hdlc(118)" ), ("119", "lapf(119)" ), ("120", "v37(120)" ),
  ("121", "x25mlp(121)" ), ("122", "x25huntGroup(122)" ), ("123", "trasnpHdlc(123)" ), ("124",
  "interleave(124)" ), ("125", "fast(125)" ), ("126", "ip(126)" ), ("127", "docsCableMaclayer(127)"
  ), ( "128", "docsCableDownstream(128)" ), ("129", "docsCableUpstream(129)" ), ("130",
  "a12MppSwitch(130)" ), ("131", "tunnel(131)" ), ("132", "coffee(132)" ), ("133", "ces(133)" ),
  ("134", "atmSubInterface(134)" ), ("135", "l2vlan(135)" ), ("136", "l3ipvlan(136)" ), ("137",
  "l3ipxvlan(137)" ), ("138", "digitalPowerline(138)" ), ("139", "mediaMailOverIp(139)" ),
  ("140", "dtm(140)" ), ("141", "dcn(141)" ), ("142", "ipForward(142)" ), ("143", "msdsl(143)" ),
  ("144", "ieee1394(144)" ), ( "145", "if-gsn(145)" ), ("146", "dvbRccMacLayer(146)" ), ("147",
  "dvbRccDownstream(147)" ), ("148", "dvbRccUpstream(148)" ), ("149", "atmVirtual(149)" ),
  ("150", "mplsTunnel(150)" ), ("151", "srp(151)" ), ("152", "voiceOverAtm(152)" ), ("153",
  "voiceOverFrameRelay(153)" ), ("154", "idsl(154)" ), ( "155", "compositeLink(155)" ),
  ("156", "ss7SigLink(156)" ), ("157", "propWirelessP2P(157)" ), ("158", "frForward(158)" ),
  ("159", "rfc1483(159)" ), ("160", "usb(160)" ), ("161", "ieee8023adLag(161)" ), ("162",
  "bgppolicyaccounting(162)" ), ("163", "frf16MfrBundle(163)" ), ("164", "h323Gatekeeper(164)"
  ), ("165", "h323Proxy(165)" ), ("166", "mpls(166)" ), ("167", "mfSigLink(167)" ), ("168",
  "hdsl2(168)" ), ("169", "shdsl(169)" ), ("170", "ds1FDL(170)" ), ("171", "pos(171)" ), ("172",
  "dvbAsiIn(172)" ), ("173", "dvbAsiOut(173)" ), ("174", "plc(174)" ), ("175", "nfas(175)" ), (
  "176", "tr008(176)" ), ("177", "gr303RDT(177)" ), ("178", "gr303IDT(178)" ), ("179", "isup(179)" ),
  ("180", "propDocsWirelessMaclayer(180)" ), ("181", "propDocsWirelessDownstream(181)" ), ("182",
  "propDocsWirelessUpstream(182)" ), ("183", "hiperlan2(183)" ), ("184", "propBWAp2Mp(184)" ),
  ("185", "sonetOverheadChannel(185)" ), ("186", "digitalWrapperOverheadChannel(186)" ), ("187",
  "aal2(187)" ), ("188", "radioMAC(188)" ), ("189", "atmRadio(189)" ), ("190", "imt(190)" ), ("191",
  "mvl(191)" ), ("192", "reachDSL(192)" ), ("193", "frDlciEndPt(193)" ), ("194", "atmVciEndPt(194)"
  ), ("195", "opticalChannel(195)" ), ("196", "opticalTransport(196)" ), ("197", "propAtm(197)" ),
  ("198", "voiceOverCable(198)" ), ("199", "infiniband(199)" ), ("200", "teLink(200)" ), ("201",
  "q2931(201)" ), ("202", "virtualTg(202)" ), ("203", "sipTg(203)" ), ("204", "sipSig(204)" ), (
  "205", "docsCableUpstreamChannel(205)" ), ("206", "econet(206)" ), ("207", "pon155(207)" ), ("208",
  "pon622(208)" ), ("209", "bridge(209)" ), ("210", "linegroup(210)" ), ("211", "voiceEMFGD(211)"
  ), ("212", "voiceFGDEANA(212)" ), ("213", "voiceDID(213)" ), ("214", "mpegTransport(214)" ),
  ("215", "sixToFour(215)" ), ("216", "gtp(216)" ), ("217", "pdnEtherLoop1(217)" ), ("218",
  "pdnEtherLoop2(218)" ), ("219", "opticalChannelGroup(219)" ), ("220", "homepna(220)" ),
  ("221", "gfp(221)" ), ("222", "ciscoISLvlan(222)" ), ("223", "actelisMetaLOOP(223)" ), ("224",
  "fcipLink(224)" ), ("225", "rpr(225)" ), ("226", "qam(226)" ), ("227", "lmp(227)" ), ("228",
  "cblVectaStar(228)" ), ("229", "docsCableMCmtsDownstream(229)" ), ("230", "adsl2(230)" ), ]

register_rule(group + '/' + subgroup_networking,
    varname   = "inventory_if_rules",
    title     = _("Network interface and switch port Inventory"),
    valuespec = Dictionary(
        elements = [
         ("use_desc", Checkbox(
                title = _("Use description as service name for network interface checks"),
                label = _("use description"),
                help = _("This option lets Check_MK use the interface description as item instead "
                         "of the port number. If no description is available then the port number is "
                         "used anyway."))),
        ("use_alias", Checkbox(
                 title = _("Use alias as service name for network interface checks"),
                     label = _("use alias"),
                     help = _("This option lets Check_MK use the alias of the port (ifAlias) as item instead "
                              "of the port number. If no alias is available then the port number is used "
                              "anyway."))),
        ("portstates", ListChoice(title = _("Network interface port states to inventorize"),
              help = _("When doing inventory on switches or other devices with network interfaces "
                       "then only ports found in one of the configured port states will be added to the monitoring."),
              choices = _if_portstate_choices)),
        ("porttypes", ListChoice(title = _("Network interface port types to inventorize"),
              help = _("When doing inventory on switches or other devices with network interfaces "
                       "then only ports of the specified types will be created services for."),
              choices = _if_porttype_choices,
              columns = 3)),

        ],
        help = _('This rule can be used to control the inventory for network ports. '
                 'You can configure the port types and port states for inventory'
                 'and the use of alias or description as service name.'),
    ),
    match = 'dict',
)
register_rule(group + '/' + subgroup_inventory,
    varname   = "inventory_processes_rules",
    title     = _('Process Inventory'),
    valuespec = Dictionary(
        elements = [
            ('descr', TextAscii(
                title = _('Service Description'),
                allow_empty = False,
                help  = _('<p>The service description may contain one or more occurances of <tt>%s</tt>. If you do this, then the pattern must be a regular '
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
                elements = [
                    TextAscii(
                        title = _("Exact name of the process without argments"),
                        size = 50,
                    ),
                    Transform(
                        RegExp(size = 50),
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
                match = lambda x: (not x and 2) or (x[0] == '~' and 1 or 0),
                default_value = '/usr/sbin/foo',
            )),
            ('user', Alternative(
                title = _('Name of the User'),
                elements = [
                    FixedValue(
                        None,
                        totext = "",
                        title = _("Match all users"),
                    ),
                    TextAscii(
                        title = _('Exact name of the user'),
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
                         'create duplicate services with the same description otherwise.</p>'),
            )),
            ('perfdata', Checkbox(
                title = _('Performance Data'),
                label = _('Collect count of processes, memory and cpu usage'),
            )),
            ('levels', Tuple(
                title = _('Levels'),
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
        optional_keys = [],
    ),
    match = 'all',
)

register_rule(group + '/' + subgroup_inventory,
    varname   = "inventory_sap_values",
    title     = _('SAP Single Value Inventory'),
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
                        RegExp(size = 100),
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
    match = 'list',
)

register_check_parameters(
    subgroup_applications,
    "ad_replication",
    _("Active Directory Replication"),
    Tuple(
        help = _("The number of replication failures"),
        elements = [
           Integer(title = _("Warning if above"), unit = _("failures")),
           Integer(title = _("Critical if above"), unit = _("failures")),
        ]
      ),
    TextAscii(
        title = _("Replication Partner"),
        help = _("The name of the replication partner (Destination DC Site/Destination DC)."),
    ),
    "first"
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
                       Age(title = _("Warning if above")),
                       Age(title = _("Critical if above")),
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
                       Filesize(title = _("Warning if above")),
                       Filesize(title = _("Critical if above")),
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
    None
)

register_check_parameters(
    subgroup_storage,
    "brocade_fcport",
    _("Brocade FC FibreChannel ports"),
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
                            Percentage(title = _("Warning if above"), unit = _("percent")),
                            Percentage(title = _("Critical if above"), unit = _("percent")),
                        ]
                    ),
                    Tuple(
                        title = _("Used Bandwidth of port in megabyte/s"),
                        elements = [
                            Integer(title = _("Warning if above"), unit = _("MByte/s")),
                            Integer(title = _("Critical if above"), unit = _("MByte/s")),
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
                        Percentage( title = _("Warning if above"), unit = _("percent")),
                        Percentage( title = _("Critical if above"), unit = _("percent")),
                    ]
               )
            ),
            ("rxencoutframes",
                Tuple (
                    title = _("Enc-Out frames rate"),
                    elements = [
                        Percentage( title = _("Warning if above"), unit = _("percent")),
                        Percentage( title = _("Critical if above"), unit = _("percent")),
                    ]
                )
            ),
            ("notxcredits",
                Tuple (
                    title = _("No-TxCredits errors"),
                    elements = [
                        Percentage( title = _("Warning if above"), unit = _("percent")),
                        Percentage( title = _("Critical if above"), unit = _("percent")),
                    ]
                )
            ),
            ("c3discards",
                Tuple (
                    title = _("C3 discards"),
                    elements = [
                        Percentage( title = _("Warning if above"), unit = _("percent")),
                        Percentage( title = _("Critical if above"), unit = _("percent")),
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
    "first"
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
         "ignored since it is modified by the power saving algorithms.")),
    TextAscii(
        title = _("Mount point"),
        allow_empty = False),
    "first"
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
                     Age(title = _("Warning if above")),
                     Age(title = _("Critical if above")),
                 ]
           )),
       ]
   ),
   None,
   "first",
)

register_check_parameters(
   subgroup_os,
    "systemtime",
    _("Windows system time offset"),
    Tuple(
        title = _("Time offset"),
        elements = [
           Integer(title = _("Warning if above"), unit = _("Seconds")),
           Integer(title = _("Critical if above"), unit = _("Seconds")),
        ]
    ),
    None,
    "first"
)

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
                      Filesize(title = _("Warning if above")),
                      Filesize(title = _("Critical if above")),
                    ]
                )
            )

        ]
    ),
    TextAscii(
        title = _("File name"),
        allow_empty = True),
    "first"
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
                  '<tt>/var/log/apache/*.log</tt>. For files contained in a group '
                  'the inventory will automatically create a group service instead '
                  'of single services for each file. This rule also applies when '
                  'you use manual configured checks instead of inventorized ones.'),
    valuespec = ListOf(
      Tuple(
          help = _("This defines one file grouping pattern"),
          show_titles = True,
          orientation = "horizontal",
          elements = [
             TextAscii(
                 title = _("Name of group"),
             ),
             TextAscii(
                 title = _("File pattern (using * and ?)"),
             ),
          ]
      ),
      add_label = _("Add pattern"),
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
        ]
    ),
    TextAscii(
        title = _("File Group Name"),
        help = _("This name must match the name of the group defined "
                 "in the <a href=\"wato.py?mode=edit_ruleset&varname=fileinfo_groups\">%s</a> ruleset.") % \
                    (_('File Grouping Patterns')),
        allow_empty = True),
    "first"
)

register_check_parameters(
    subgroup_storage,
    "netapp_fcprtio",
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
                      Filesize(title = _("Warning if above")),
                      Filesize(title = _("Critical if above")),
                    ]
                )
            )

        ]
    ),
    TextAscii(
        title = _("File name"),
        allow_empty = True),
    "first"
)


register_check_parameters(
    subgroup_os,
    "memory_pagefile_win",
    _("Memory and pagefile levels for Windows"),
    Dictionary(
        elements = [
            ( "memory",
               Alternative(
                   title = _("Memory Levels"),
                   elements = [
                       Tuple(
                           title = _("Usage Levels in Percent"),
                           elements = [
                               Percentage(title = _("Warning if above") ),
                               Percentage(title = _("Critical if above") ),
                           ]
                       ),
                       Tuple(
                           title = _("Absolute Usage Levels"),
                           elements = [
                                Filesize(title = _("Warning if above")),
                                Filesize(title = _("Critical if above")),
                           ]
                        )
                   ])),
            ( "pagefile",
               Alternative(
                   title = _("Pagefile Levels"),
                   elements = [
                       Tuple(
                           title = _("Usage Levels in Percent"),
                           elements = [
                               Percentage(title = _("Warning if above")),
                               Percentage(title = _("Critical if above")),
                           ]
                       ),
                       Tuple(
                           title = _("Absolute Usage Levels"),
                           elements = [
                                Filesize(title = _("Warning if above")),
                                Filesize(title = _("Critical if above")),
                           ]
                        )
                   ])),
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
                  help = _("Here you can set the number of remaining open slots"),
                  elements = [
                      Integer(title = _("Warning if above"),  label = _("slots")),
                      Integer(title = _("Critical if above"), label = _("slots"))
                  ]
              )
            )
        ]
    ),
    TextAscii(
        title = _("Apache Server"),
        help  = _("A string-combination of servername and port, e.g. 127.0.0.1:5000.")
    ),
    "first"
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
    None
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
                          title = _("IP-Address of Tunnel Endpoint"),
                          allow_empty = False,
                          ),
                      TextAscii(
                          title = _("Name of Tunnel"),
                          ),
                      MonitoringState(
                          default_value = 2,
                          title = _("State if this tunnel is not found"),
                          )]),
                  add_label = _("Add another Tunnel"),
                  movable = False,
                  title = _("VPN Tunnel"),
                  )),
            ( "state",
              MonitoringState(
                  title = _("Default state if inventorized, unregistered tunnel is not found"),
                  help = _("Default state if a tunnel, which was inventorized but is not listed in this rule, "
                      "is not longer present in the snmp data"),
                  ),
            ),
        ],
    ),
    TextAscii( title = _("IP-Address of Tunnel Endpoint")),
    "first"
)

register_check_parameters(
    subgroup_networking,
    "wlc_clients",
    _("WLC WiFi client connections"),
    Tuple(
        title = _("Number of connections"),
        help = _("Number of connections for a WiFi"),
              elements = [
              Integer(title = _("Critical if below"), unit=_("connections")),
              Integer(title = _("Warning if below"),  unit=_("connections")),
              Integer(title = _("Warning if above"),  unit=_("connections")),
              Integer(title = _("Critical if above"), unit=_("connections")),
              ]
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
           ),
           ( "ap_model",
            ListOf(
                Tuple(
                    elements = [
                        TextAscii(title = _("AP model")),
                        MonitoringState( title=_("State when missing"), default_value = 2)
                    ]
                ),
                title = _("Access point device id"),
            add_label = _("Add id"))
           )
        ]
    ),
   TextAscii(title = _("Access Point")),
   "first",
)
register_check_parameters(
    subgroup_networking,
    "tcp_conn_stats",
    ("TCP connection stats (LINUX / UNIX)"),
    Dictionary(
        elements = [
            ( "ESTABLISHED",
              Tuple(
                  title = _("ESTABLISHED"),
                  help = _("connection up and passing data"),
                  elements = [
                      Integer(title = _("Warning if above"),  label = _("connections")),
                      Integer(title = _("Critical if above"), label = _("connections"))
                  ]
              )
            ),
            ( "SYN_SENT",
              Tuple(
                  title = _("SYN_SENT"),
                  help = _("session has been requested by us; waiting for reply from remote endpoint"),
                  elements = [
                      Integer(title = _("Warning if above"),  label = _("connections")),
                      Integer(title = _("Critical if above"), label = _("connections"))
                  ]
              )
            ),
            ( "SYN_RECV",
              Tuple(
                  title = _("SYN_RECV"),
                  help = _("session has been requested by a remote endpoint "
                           "for a socket on which we were listening"),
                  elements = [
                      Integer(title = _("Warning if above"),  label = _("connections")),
                      Integer(title = _("Critical if above"), label = _("connections"))
                  ]
              )
            ),
            ( "LAST_ACK",
              Tuple(
                  title = _("LAST_ACK"),
                  help = _("our socket is closed; remote endpoint has also shut down; "
                           " we are waiting for a final acknowledgement"),
                  elements = [
                      Integer(title = _("Warning if above"),  label = _("connections")),
                      Integer(title = _("Critical if above"), label = _("connections"))
                  ]
              )
            ),
            ( "CLOSE_WAIT",
              Tuple(
                  title = _("CLOSE_WAIT"),
                  help = _("remote endpoint has shut down; the kernel is waiting "
                           "for the application to close the socket"),
                  elements = [
                      Integer(title = _("Warning if above"),  label = _("connections")),
                      Integer(title = _("Critical if above"), label = _("connections"))
                  ]
              )
            ),
            ( "TIME_WAIT",
              Tuple(
                  title = _("TIME_WAIT"),
                  help = _("socket is waiting after closing for any packets left on the network"),
                  elements = [
                      Integer(title = _("Warning if above"),  label = _("connections")),
                      Integer(title = _("Critical if above"), label = _("connections"))
                  ]
              )
            ),
            ( "CLOSED",
              Tuple(
                  title = _("CLOSED"),
                  help = _("socket is not being used"),
                  elements = [
                      Integer(title = _("Warning if above"),  label = _("connections")),
                      Integer(title = _("Critical if above"), label = _("connections"))
                  ]
              )
            ),
            ( "CLOSING",
              Tuple(
                  title = _("CLOSING"),
                  help = _("our socket is shut down; remote endpoint is shut down; "
                           "not all data has been sent"),
                  elements = [
                      Integer(title = _("Warning if above"),  label = _("connections")),
                      Integer(title = _("Critical if above"), label = _("connections"))
                  ]
              )
            ),
            ( "FIN_WAIT1",
              Tuple(
                  title = _("FIN_WAIT1"),
                  help = _("our socket has closed; we are in the process of "
                           "tearing down the connection"),
                  elements = [
                      Integer(title = _("Warning if above"),  label = _("connections")),
                      Integer(title = _("Critical if above"), label = _("connections"))
                  ]
              )
            ),
            ( "FIN_WAIT2",
              Tuple(
                  title = _("FIN_WAIT2"),
                  help = _("the connection has been closed; our socket is waiting "
                           "for the remote endpoint to shutdown"),
                  elements = [
                      Integer(title = _("Warning if above"),  label = _("connections")),
                      Integer(title = _("Critical if above"), label = _("connections"))
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
                      Integer(title = _("Warning if above"),  label = _("connections")),
                      Integer(title = _("Critical if above"), label = _("connections"))
                  ]
              )
            ),
        ]
    ),
    None,
    "first"
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
            ( "min_states",
               Tuple(
                   title = _("Minimum number of connections or listeners"),
                   elements = [
                       Integer(title = _("Warning if above")),
                       Integer(title = _("Critical if above")),
                    ],
               ),
            ),
            ( "max_states",
               Tuple(
                   title = _("Maximum number of connections or listeners"),
                   elements = [
                       Integer(title = _("Warning if above")),
                       Integer(title = _("Critical if above")),
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
    "msx_queues",
    _("MS Exchange Message Queues"),
    Tuple(
        help = _("This rule applies to the number of E-Mails in the various Exchange Message Queues"),
        elements = [
            Integer(title = _("Warning if above"), unit = _("E-Mails")),
            Integer(title = _("Critical if above"), unit = _("E-Mails"))
        ]),
        OptionalDropdownChoice(
            title = _("Explicit Queue Names"),
            help = _("Select queue names that the rule should apply"),
           choices = [
              ( "Active Remote Delivery",  _("Active Remote Delivery") ),
              ( "Retry Remote Delivery",   _("Retry Remote Delivery") ),
              ( "Active Mailbox Delivery", _("Active Mailbox Delivery") ),
              ( "Poison Queue Length",     _("Poison Queue Length") ),
              ],
           otherlabel = _("specify manually ->"),
           explicit = TextAscii(allow_empty = False)),
    "first"
)

def get_filesystem_valuespec(what):
    if what == "used":
        title  = _("used space")
        course = _("above")
    else:
        title  = _("free space")
        course = _("below")


    vs_subgroup =  [
                    Tuple( title = _("Percentage %s") % title,
                        elements = [
                            Percentage(title = _("Warning if %s") % course, unit = _("%"), minvalue = 0.0),
                            Percentage(title = _("Critical if %s") % course, unit = _("%"), minvalue = 0.0),
                        ]
                    ),
                    Tuple( title = _("Absolute %s") % title,
                        elements = [
                            Integer(title = _("Warning if %s") % course, unit = _("MB"), minvalue = 0),
                            Integer(title = _("Critical if %s") % course, unit = _("MB"), minvalue = 0),
                        ]
                    )
                   ]

    return Alternative(
            title = _("Levels for filesystem %s") % title,
            show_alternative_title = True,
            default_value = (80.0, 90.0),
                    elements = vs_subgroup + [
                                ListOf(
                                    Tuple(
                                        orientation = "horizontal",
                                        elements = [
                                            Filesize(title = _("Filesystem larger than")),
                                            Alternative(
                                                title = _("Levels for %s") % title,
                                                elements = vs_subgroup
                                            )
                                        ]
                                    ),
                                    title = _('Dynamic levels'),
                                )],
                    )

def match_filesystem_level_type(value):
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

def transform_filesystem_levels(value):
    tuple_convert = lambda val: tuple(map(lambda x: -x, val))

    if type(value) == tuple:
        return tuple_convert(value)
    else:
        result = []
        for item in value:
            result.append((item[0], tuple_convert(item[1])))
        return result


filesystem_elements = [
    ("levels",
        Alternative(
            title = _("Levels for filesystem"),
            show_alternative_title = True,
            default_value = (80.0, 90.0),
            match = match_filesystem_level_type,
            elements = [
                   get_filesystem_valuespec("used"),
                   Transform(
                            get_filesystem_valuespec("free"),
                            title = _("Levels for filesystem free space"),
                            allow_empty = False,
                            forth = transform_filesystem_levels,
                            back  = transform_filesystem_levels
                    )
                ]
                )
    ),
    ( "flex_levels",
      FixedValue(
          None,
          totext = "",
          title = _("Hidden identifier key for flexible level usage")
          )),
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
              Percentage(title = _("Warning if above"),  unit = _("% usage"), allow_int = True, default_value=50),
              Percentage(title = _("Critical if above"), unit = _("% usage"), allow_int = True, default_value=60)])),
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
               Integer(title = _("Warning if above"), unit = _("MB / range"), default_value = 100),
               Integer(title = _("Critical if above"), unit = _("MB / range"), default_value = 200)
           ])),
    (  "trend_perc",
       Tuple(
           title = _("Levels for the percentual growth per time range"),
           elements = [
               Percentage(title = _("Warning if above"), unit = _("% / range"), default_value = 5,),
               Percentage(title = _("Critical if above"), unit = _("% / range"), default_value = 10,),
           ])),
    (  "trend_timeleft",
       Tuple(
           title = _("Levels on the time left until the filesystem gets full"),
           elements = [
               Integer(title = _("Warning if below"), unit = _("hours"), default_value = 12,),
               Integer(title = _("Critical if below"), unit = _("hours"), default_value = 6, ),
           ])),
    ( "trend_perfdata",
      Checkbox(
          title = _("Trend performance data"),
          label = _("Enable generation of performance data from trends"))),
]

register_check_parameters(
    subgroup_storage,
    "filesystem",
    _("Filesystems (used space and growth)"),
    Dictionary(
        elements = filesystem_elements,
        hidden_keys = ["flex_levels"],
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
    "esx_vsphere_datastores",
    _("ESX Datastores (used space and growth)"),
    Dictionary(
        elements = filesystem_elements + [
            ("provisioning_levels", Tuple(
                title = _("Provisioning Levels"),
                help = _("Configure thresholds for overprovisioning of datastores."),
                elements = [
                  Percentage(title = _("Warning at overprovisioning of")),
                  Percentage(title = _("Critical at overprovisioning of")),
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

register_check_parameters(
    subgroup_networking,
    "if",
    _("Network interfaces and switch ports"),
    Dictionary(
        elements = [
            ( "errors",
              Tuple(
                  title = _("Levels for error rates"),
                  help = _("These levels make the check go warning or critical whenever the "
                           "<b>percentual error rate</b> of the monitored interface reaches "
                           "the given bounds. The error rate is computed by dividing number of "
                           "errors by the total number of packets (successful plus errors)."),
                  elements = [
                      Percentage(title = _("Warning if above"), label = _("errors"), default_value = 0.01),
                      Percentage(title = _("Critical if above"), label = _("errors"), default_value = 0.1)
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
                     ( None,       _("ignore speed") ),
                     ( 10000000,    "10 MBit/s" ),
                     ( 100000000,   "100 MBit/s" ),
                     ( 1000000000,  "1 GBit/s" ),
                     ( 10000000000, "10 GBit/s" ) ],
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
             ( "assumed_speed_in",
               OptionalDropdownChoice(
                        title = _("Assumed input speed"),
                        help = _("If the automatic detection of the link speed does not work "
                                 "or the switch's capabilities are throttled because of the network setup "
                                 "you can set the assumed speed here."),
                  choices = [
                     ( None,       _("ignore speed") ),
                     ( 10000000,    "10 MBit/s" ),
                     ( 100000000,   "100 MBit/s" ),
                     ( 1000000000,  "1 GBit/s" ),
                     ( 10000000000, "10 GBit/s" ) ],
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
                     ( 10000000,    "10 MBit/s" ),
                     ( 100000000,   "100 MBit/s" ),
                     ( 1000000000,  "1 GBit/s" ),
                     ( 10000000000, "10 GBit/s" ) ],
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
             ( "traffic",
               Alternative(
                   title = _("Used bandwidth (traffic)"),
                   help = _("Settings levels on the used bandwidth is optional. If you do set "
                            "levels you might also consider using an averaging."),
                   elements = [
                       Tuple(
                           title = _("Percentual levels (in relation to port speed)"),
                           elements = [
                               Percentage(title = _("Warning if above"), label = _("% of port speed")),
                               Percentage(title = _("Critical if above"), label = _("% of port speed")),
                           ]
                       ),
                       Tuple(
                           title = _("Absolute levels in bits or bytes per second"),
                           help = _("Depending on the measurement unit (defaults to byte) the absolute levels are set in bit or byte"),
                           elements = [
                               Integer(title = _("Warning if above"), label = _("bits / bytes per second")),
                               Integer(title = _("Critical if above"), label = _("bits / bytes per second")),
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
                     default_value = 15,
                 )
               ),


           ]),
    TextAscii(
        title = _("port specification"),
        allow_empty = False),
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
                            "levels you might also consider using an averaging."),
                   elements = [
                       Tuple(
                           title = _("Percentual levels (in relation to policy speed)"),
                           elements = [
                               Percentage(title = _("Warning if above"), maxvalue=1000, label = _("% of port speed")),
                               Percentage(title = _("Critical if above"), maxvalue=1000, label = _("% of port speed")),
                           ]
                       ),
                       Tuple(
                           title = _("Absolute levels in bits or bytes per second"),
                           help = _("Depending on the measurement unit (defaults to bit) the absolute levels are set in bit or byte"),
                           elements = [
                               Integer(title = _("Warning if above"), size = 10, label = _("bits / bytes per second")),
                               Integer(title = _("Critical if above"), size = 10, label = _("bits / bytes per second")),
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
               ( "drop",
                 Alternative(
                     title = _("Number of dropped bits or bytes per second"),
                     help = _("Depending on the measurement unit (defaults to bit) you can set the warn and crit "
                              "levels for the number of dropped bits or bytes"),
                     elements = [
                         Tuple(
                             title = _("Percentual levels (in relation to policy speed)"),
                             elements = [
                                 Percentage(title = _("Warning if above"), maxvalue=1000, label = _("% of port speed")),
                                 Percentage(title = _("Critical if above"), maxvalue=1000, label = _("% of port speed")),
                             ]
                         ),
                         Tuple(
                             elements = [
                                 Integer(title = _("Warning if above"), size = 8, label = _("bits / bytes per second")),
                                 Integer(title = _("Critical if above"), size = 8, label = _("bits / bytes per second")),
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
    "cisco_mem",
    _("Cisco Memory Usage"),
    Alternative(
        elements = [
            Tuple(
                title = _("Specify levels in percentage of total RAM"),
                elements = [
                  Percentage(title = _("Warning at a usage of"), label = _("% of RAM"), maxvalue = None),
                  Percentage(title = _("Critical at a usage of"), label = _("% of RAM"), maxvalue = None)
                ]
            ),
            Tuple(
                title = _("Specify levels in absolute usage values"),
                elements = [
                  Integer(title = _("Warning if above"), unit = _("MB")),
                  Integer(title = _("Critical if above"), unit = _("MB"))
                ]
            ),
        ]
    ),
    TextAscii(
        title = _("Memory Pool Name"),
        allow_empty = False
    ),
    None
)

register_check_parameters(
    subgroup_os,
    "memory",
    _("Main memory usage (Linux / UNIX / Other Devices)"),
    Alternative(
        help = _("The levels for memory usage on Linux and UNIX systems take into account the "
               "currently used memory (RAM or SWAP) by all processes and sets this in relation "
               "to the total RAM of the system. This means that the memory usage can exceed 100%. "
               "A usage of 200% means that the total size of all processes is twice as large as "
               "the main memory, so <b>at least</b> the half of it is currently swapped out. "
               "Besides Linux and UNIX systems, these parameters are also used for memory checks "
               "of other devices, like Fortigate devices."),
        elements = [
            Tuple(
                title = _("Specify levels in percentage of total RAM"),
                elements = [
                    # Disable limit of value to 101%, because levels > 100% make sense here
                    # (swap+ram is > ram)
                    Percentage(title = _("Warning at a memory usage of"), default_value = 80.0, maxvalue = None),
                    Percentage(title = _("Critical at a memory usage of"), default_value = 90.0, maxvalue = None)]),
            Tuple(
                title = _("Specify levels in absolute usage values"),
                elements = [
                  Integer(title = _("Warning if above"), unit = _("MB")),
                  Integer(title = _("Critical if above"), unit = _("MB"))]),
            ]),
    None, None
)

register_check_parameters(
    subgroup_os,
    "esx_host_memory",
    _("Main memory usage of ESX host system"),
    Tuple(
        title = _("Specify levels in percentage of total RAM"),
        elements = [
          Percentage(title = _("Warning at a RAM usage of"), default_value = 80.0),
          Percentage(title = _("Critical at a RAM usage of"), default_value = 90.0)]),
    None, None
)

register_check_parameters(
    subgroup_applications,
    "esx_vsphere_objects",
    _("State of ESX hosts and virtual machines"),
    Dictionary(
        help = _("Usually the check goes to WARN if a VM or host is powered off and OK otherwise. "
                 "You can change this behaviour on a per-state-base here."),
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

register_check_parameters(
    subgroup_printing,
    "printer_supply",
    _("Printer cardridge levels"),
    Tuple(
          help = _("Levels for printer cardridges."),
          elements = [
              Float(title = _("Warning remaining")),
              Float(title = _("Critical remaining"))]
    ),
    TextAscii(
        title = _("cardridge specification"),
        allow_empty = True
    ),
    None,
)
register_check_parameters(
    subgroup_printing,
    "windows_printer_queues",
    _("Number of open jobs of a printer on windows" ),
    Tuple(
          help = _("This rule is applied to the number of print jobs "
                   "currently waiting in windows printer queue."),
          elements = [
              Integer(title = _("Warning if above"), unit = _("jobs"), default_value = 40),
              Integer(title = _("Critical if above"), unit = _("jobs"), default_value = 60),
          ]
    ),
    TextAscii(
        title = _("Printer Name"),
        allow_empty = True
    ),
    None
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
    None, None
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
    None, None
)

register_check_parameters(
    subgroup_os,
    "cpu_utilization_os",
    _("CPU utilization for Windows and ESX Hosts"),
    Dictionary(
        help = _("This rule configures levels for the CPU utilization (not load) for "
                 "the operating systems Windows and VMWare ESX host systems. The utilization "
                 "ranges from 0 to 100 - regardless of the number of CPUs."),
        elements = [
            ( "levels",
                Levels(
                    title = _("Levels"),
                    unit = "%",
                    default_levels = (85, 90),
                    default_difference = (5, 8),
                    default_value = None,
                ),
            ),
            ( "average",
              Integer(
                  title = _("Averaging"),
                  help = _("When this option is activated then the CPU utilization is being "
                           "averaged <b>before</b> the levels are being applied."),
                  unit = "min",
                  default_value = 15,
                  label = _("Compute average over last "),
            )),
        ]
    ),
    None, None
)

register_check_parameters(
    subgroup_os,
    "cpu_iowait",
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
    None, None
)

register_check_parameters(
    subgroup_environment,
    "humidity",
    _("Humidity Levels"),
    Tuple(
          help = _("This Rulset sets the threshold limits for humidity sensors"),
          elements = [
              Integer(title = _("Critical if below"), unit="%" ),
              Integer(title = _("Warning if below"), unit="%" ),
              Integer(title = _("Warning if above"), unit="%" ),
              Integer(title = _("Critical if above"), unit="%" ),
              ]),
    TextAscii(
        title = _("Service descriptions"),
        allow_empty = False),
     None
)

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
        elements = [
            ("levels",
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
                  minvalue = 0.1,
                  maxvalue = 1.0)),
            (  "magic_normsize",
               Integer(
                   title = _("Reference size for magic factor"),
                   minvalue = 1,
                   default_value = 1000,
                   label = _("MB"))),
            ( "levels_low",
              Tuple(
                  title = _("Minimum levels if using magic factor"),
                  help = _("The tablespace levels will never fall below these values, when using "
                           "the magic factor and the tablespace is very small."),
                  elements = [
                      Percentage(title = _("Warning if above"),  unit = _("% usage"), allow_int = True),
                      Percentage(title = _("Critical if above"), unit = _("% usage"), allow_int = True)])),
            ( "autoextend",
                Checkbox(
                  title = _("Autoextend"),
                  label = _("Autoextension is expected"),
                  help = "")),
                   ]),
    TextAscii(
        title = _("Explicit tablespaces"),
        help = _("Here you can set explicit tablespaces by defining them via SID and the tablespace name, separated by a dot, for example <b>pengt.TEMP</b>"),
        regex = '.+\..+',
        allow_empty = False),
     None
)

register_check_parameters(
    subgroup_applications,
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
     None
)

register_check_parameters(
    subgroup_applications,
    "mssql_backup",
    _("MSSQL Time since last Backup"),
    Optional(
        Tuple(
            elements = [
              Integer(title = _("Warning if older than"), unit = _("seconds")),
              Integer(title = _("Critical if older than"), unit = _("seconds"))
            ]
        ),
        title = _("Specify time since last successful backup"),
    ),
    TextAscii(
        title = _("Service descriptions"),
        allow_empty = False),
     None
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
                       Float(title = _("Warning if above"),  unit = _("requests/sec")),
                       Float(title = _("Critical if above"), unit = _("requests/sec")),
                    ],
               ),
            ),
            ( "lock_timeouts/sec",
               Tuple(
                   title = _("Lock Timeouts / sec"),
                   help = _("Number of lock requests per second that timed out, including requests for NOWAIT locks."),
                   elements = [
                       Float(title = _("Warning if above"),  unit = _("timeouts/sec")),
                       Float(title = _("Critical if above"), unit = _("timeouts/sec")),
                    ],
               ),
            ),
            ( "number_of_deadlocks/sec",
               Tuple(
                   title = _("Number of Deadlocks / sec"),
                   help = _("Number of lock requests per second that resulted in a deadlock."),
                   elements = [
                       Float(title = _("Warning if above"),  unit = _("deadlocks/sec")),
                       Float(title = _("Critical if above"), unit = _("deadlocks/sec")),
                    ],
               ),
            ),
            ( "lock_waits/sec",
               Tuple(
                   title = _("Lock Waits / sec"),
                   help = _("Number of lock requests per second that required the caller to wait."),
                   elements = [
                       Float(title = _("Warning if above"),  unit = _("waits/sec")),
                       Float(title = _("Critical if above"), unit = _("waits/sec")),
                    ],
               ),
            ),
         ]
    ),
    TextAscii(
        title = _("Service descriptions"),
        allow_empty = False
    ),
    None
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
                       Integer(title = _("Warning if above"),  unit = _("sessions"), default_value = 100),
                       Integer(title = _("Critical if above"), unit = _("sessions"), default_value = 200),
                    ],
               ),
            ),
            ( "running",
               Tuple(
                   title = _("Number of currently running sessions"),
                   help = _("Levels for the number of sessions that are currently active"),
                   elements = [
                       Integer(title = _("Warning if above"),  unit = _("sessions"), default_value = 10),
                       Integer(title = _("Critical if above"), unit = _("sessions"), default_value = 20),
                    ],
               ),
            ),
            ( "connections",
               Tuple(
                   title = _("Number of new connections per second"),
                   elements = [
                       Integer(title = _("Warning if above"),  unit = _("connection/sec"), default_value = 20),
                       Integer(title = _("Critical if above"), unit = _("connection/sec"), default_value = 40),
                    ],
               ),
            ),
         ]
    ),
    None,
    None
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
                      Float(title = _("warning if above"), unit = _("MB/s")),
                      Float(title = _("critical if above"), unit = _("MB/s"))
                  ])),
            ( "write",
              Tuple(
                  title = _("Write throughput"),
                  elements = [
                      Float(title = _("warning if above"), unit = _("MB/s")),
                      Float(title = _("critical if above"), unit = _("MB/s"))
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
    None,
    "dict"
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
                       Percentage(title = _("Warning if above")),
                       Percentage(title = _("Critical if above")),
                    ]
                )
            ),
        ]),
    None,
    "dict"
)

register_check_parameters(
    subgroup_applications,
    "dbsize",
    _("Size of MySQL/PostgresQL databases"),
    Optional(
        Tuple(
            elements = [
                Integer(title = _("warning if above"), unit = _("MB")),
                Integer(title = _("critical if above"), unit = _("MB")),
            ]),
        help = _("The check will trigger a warning or critical state if the size of the "
                 "database exceeds these levels."),
        title = _("Impose limits on the size of the database"),
    ),
    TextAscii(
        title = _("Name of the database"),
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
                       Integer(title = _("Warning if above"),  unit = _("sessions"), default_value = 100),
                       Integer(title = _("Critical if above"), unit = _("sessions"), default_value = 200),
                    ],
               ),
            ),
            ( "running",
               Tuple(
                   title = _("Number of currently running sessions"),
                   help = _("Levels for the number of sessions that are currently active"),
                   elements = [
                       Integer(title = _("Warning if above"),  unit = _("sessions"), default_value = 10),
                       Integer(title = _("Critical if above"), unit = _("sessions"), default_value = 20),
                    ],
               ),
            ),
         ]
    ),
    None,
    None
)


register_check_parameters(
    subgroup_applications,
    "oracle_sessions",
    _("Oracle Sessions"),
    Tuple(
         title = _("Number of active sessions"),
         help = _("This check monitors the current number of active sessions on Oracle"),
         elements = [
             Integer(title = _("Warning if above"),  unit = _("sessions"), default_value = 100),
             Integer(title = _("Critical if above"), unit = _("sessions"), default_value = 200),
          ],
     ),
    TextAscii(
        title = _("Database name"),
        allow_empty = False),
     None
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
                      Float(title = _("Warning if above"), unit = _("blocks/s")),
                      Float(title = _("Critical if above"), unit = _("blocks/s")),
                   ],
                ),
            ),
            ( "xact_commit",
                Tuple(
                   title = _("Commits"),
                   elements = [
                      Float(title = _("Warning if above"), unit = _("/s")),
                      Float(title = _("Critical if above"), unit = _("/s")),
                   ],
                ),
            ),
            ( "tup_fetched",
                Tuple(
                   title = _("Fetches"),
                   elements = [
                      Float(title = _("Warning if above"), unit = _("/s")),
                      Float(title = _("Critical if above"), unit = _("/s")),
                   ],
                ),
            ),
            ( "tup_deleted",
                Tuple(
                   title = _("Deletes"),
                   elements = [
                      Float(title = _("Warning if above"), unit = _("/s")),
                      Float(title = _("Critical if above"), unit = _("/s")),
                   ],
                ),
            ),
            ( "tup_updated",
                Tuple(
                   title = _("Updates"),
                   elements = [
                      Float(title = _("Warning if above"), unit = _("/s")),
                      Float(title = _("Critical if above"), unit = _("/s")),
                   ],
                ),
            ),
            ( "tup_inserted",
                Tuple(
                   title = _("Inserts"),
                   elements = [
                      Float(title = _("Warning if above"), unit = _("/s")),
                      Float(title = _("Critical if above"), unit = _("/s")),
                   ],
                ),
            ),
        ],
    ),
    TextAscii(
        title = _("Database name"),
        allow_empty = False),
    None
)

register_check_parameters(
    subgroup_applications,
    "win_dhcp_pools",
    _("Windows DHCP Pool"),
    Tuple(
          help = _("The count of remaining entries in the DHCP pool represents "
                   "the number of IP addresses left which can be assigned in the network"),
          elements = [
              Percentage(title = _("Warning if more than"), unit = _("pool entries")),
              Percentage(title = _("Critical if more than"), unit = _("pool entries")),
              ]),
    TextAscii(
        title = _("Service descriptions"),
        allow_empty = False),
     None
)

register_check_parameters(
    subgroup_os,
    "threads",
    _("Number of threads"),
    Tuple(
          help = _("These levels check the number of currently existing threads on the system. Each process has at "
                   "least one thread."),
          elements = [
              Integer(title = _("Warning if above"), unit = _("threads"), default_value = 1000),
              Integer(title = _("Critical if above"), unit = _("threads"), default_value = 2000)]),
    None, None
)

register_check_parameters(
    subgroup_applications,
    "vms_procs",
    _("Number of processes on OpenVMS"),
    Optional(
        Tuple(
              elements = [
                  Integer(title = _("Warning if above"), unit = _("processes"), default_value = 100),
                  Integer(title = _("Critical if above"), unit = _("processes"), default_value = 200)]),
        title = _("Impose levels on number of processes"),
    ),
    None, None
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
    "disk_io",
    _("Levels on disk IO (throughput)"),
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
                  help = _("When averaging is set, then an floating average value "
                           "of the disk throughput is computed and the levels for read "
                           "and write will be applied to the average instead of the current "
                           "value."),
                 unit = "min")),
            ( "latency",
              Tuple(
                  title = _("IO Latency"),
                  elements = [
                      Float(title = _("warning if above"),  unit = _("ms"), default_value = 80.0),
                      Float(title = _("critical if above"), unit = _("ms"), default_value = 160.0),
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
                      Float(title = _("warning if above"),  default_value = 80.0),
                      Float(title = _("critical if above"), default_value = 90.0),
             ])),
            ( "write_ql",
              Tuple(
                  title = _("Write Queue-Length"),
                  elements = [
                      Float(title = _("warning if above"),  default_value = 80.0),
                      Float(title = _("critical if above"), default_value = 90.0),
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
    OptionalDropdownChoice(
        choices = [ ( "SUMMARY",  _("Summary of all disks") ),
                    ( "read",     _("Summary of disk input (read)") ),
                    ( "write",    _("Summary of disk output (write)") ),
                  ],
        otherlabel = _("On explicit devices ->"),
        explicit = TextAscii(allow_empty = False),
        title = _("Device"),
        help = _("For a summarized throughput of all disks, specify <tt>SUMMARY</tt>, for a "
                 "sum of read or write throughput write <tt>read</tt> or <tt>write</tt> resp. "
                 "A per-disk IO is specified by the drive letter, a colon and a slash on Windows "
                 "(e.g. <tt>C:/</tt>) or by the device name on Linux/UNIX (e.g. <tt>/dev/sda</tt>).")),
    "first"
)


register_rule(
    group + '/' + subgroup_storage,
    "diskstat_inventory",
    ListChoice(
        title = _("Inventory mode for Disk IO check"),
        help = _("This rule controls which and how many checks will be created "
                 "for monitoring individual physical and logical disks."),
        choices = [
           ( "summary",  _("Create a summary over all physical disks") ),
           ( "legacy",   _("Create a summary for all read, one for write") ),
           ( "physical", _("Create a separate check for each physical disk") ),
           ( "lvm",      _("Create a separate check for each LVM volume (Linux)") ),
           ( "vxvm",     _("Creata a separate check for each VxVM volume (Linux)") ),
        ],
        default_value = [ 'summary' ],
    ),
    match="first")


register_rule(group + '/' + subgroup_networking,
    varname   = "if_groups",
    title     = _('Network interface groups'),
    help      = _('Normally the if checks create a single service for interface. '
                  'By defining if-group patterns multiple interfaces can be combined together. '
                  'A single service is created for this interface group showing the total traffic amount '
                  'of its members. You can configure if interfaces which are identified as group interfaces '
                  'should not show up as single service'),
    valuespec = ListOf(
                    Dictionary(
                        elements = [
                            ("name",
                                   TextAscii(
                                       title = _("Name of group"),
                                       help  = _("Name of group in service description"),
                                       allow_empty = False,
                                   )),
                            ("iftype", Integer(
                                title = _("Interface port type"),
                                help = _("The number of the port type. For example 53 (propVirtual)"),
                                default_value = 0,
                                minvalue = 1,
                                maxvalue = 255,
                            )),
                            ("single", Checkbox(
                                title = _("Do not list grouped interfaces separately"),
                            )),
                        ],
                        required_keys = ["name", "iftype", "single"]),
                    add_label = _("Add pattern")),
    match = 'all',
)

register_check_parameters(
    subgroup_applications,
    "mailqueue_length",
    _("Number of mails in outgoing mail queue"),
    Tuple(
          help = _("This rule is applied to the number of E-Mails that are "
                   "currently in the outgoing mail queue."),
          elements = [
              Integer(title = _("Warning if above"), unit = _("mails"), default_value = 10),
              Integer(title = _("Critical if above"), unit = _("mails"), default_value = 20),
          ]
    ),
    None,
    None
)

register_check_parameters(
    subgroup_os,
    "uptime",
    _("Display the system's uptime as a check"),
    None,
    None, None
)

register_check_parameters(
    subgroup_storage,
    "zpool_status",
    _("ZFS storage pool status"),
    None,
    None, None
)

register_check_parameters(
    subgroup_virt,
    "vm_state",
    _("Overall state of a virtual machine"),
    None,
    None, None
)

# register_check_parameters(
#     subgroup_virt,
#     "esx_hostsystems",
#     _("Available HostSystems in ESX cluster"),
#     None,
#     "first",
#     False,
# )


register_check_parameters(
    subgroup_hardware,
    "hw_errors",
    _("Simple checks for BIOS/Hardware errors"),
    None,
    None, None
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
    None,
    TextAscii(
        title = _("Name of the mount point"),
        help = _("For NFS enter the name of the mount point.")),
    "first"
)

register_check_parameters(
     subgroup_storage,
    "multipath",
    _("Multipathing - health of a multipath LUN"),
    Integer(
        title = _("Expected number of active paths")),
    TextAscii(
        title = _("Name of the MP LUN"),
        help = _("For Linux multipathing this is either the UUID (e.g. "
                 "60a9800043346937686f456f59386741), or the configured "
                 "alias.")),
    "first"
)

register_check_parameters(
     subgroup_storage,
    "hpux_multipath",
    _("Multipathing on HPUX - state of paths of a LUN"),
    Tuple(
        title = _("Expected path situation"),
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
    subgroup_applications,
    "services",
    _("Windows Services"),
    Dictionary(
        elements = [
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
                    default_value = ( "running", "auto", 0)),
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
        ),]
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
    "first",
    False,
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
    "raid_disk",
    _("RAID: state of a single disk"),
    TextAscii(
        title = _("Target state"),
        help = _("State the disk is expected to be in. Typical good states "
            "are online, host spare, OK and the like. The exact way of how "
            "to specify a state depends on the check and hard type being used. "
            "Please take examples from inventorized checks for reference.")),
    TextAscii(
        title = _("Number or ID of the disk"),
        help = _("How the disks are named depends on the type of hardware being "
                 "used. Please look at already inventorized checks for examples.")),
    "first"
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
     None
)

register_check_parameters(
    subgroup_environment,
    "room_temperature",
    _("Room temperature (external thermal sensors)"),
    Tuple(
        help = _("Temperature levels for external thermometers that are used "
                 "for monitoring the temperature of a datacenter. An example "
                 "is the webthem from W&amp;T."),
        elements = [
            Integer(title = _("warning if above"), unit = u"°C", default_value = 26),
            Integer(title = _("critical if above"), unit = u"°C", default_value = 30),
        ]),
    TextAscii(
        title = _("Sensor ID"),
        help = _("The identifier of the themal sensor.")),
    "first"
)

register_check_parameters(
    subgroup_environment,
    "hw_single_temperature",
    _("Host/Device temperature"),
    Tuple(
        help = _("Temperature levels for hardware devices with "
                 "a single temperature sensor."),
        elements = [
            Integer(title = _("warning if above"), unit = u"°C", default_value = 35),
            Integer(title = _("critical if above"), unit = u"°C", default_value = 40),
        ]),
    None,
    "first"
)

register_check_parameters(
    subgroup_environment,
    "evolt",
    _("Nominal Voltages"),
    Tuple(
        help = _("Voltage Levels for devices like UPS oder PDUs. "
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
    "hw_temperature",
    _("Hardware temperature (e.g. switches)"),
    Tuple(
        help = _("Temperature levels for hardware devices like "
                 "Brocade switches with (potentially) several "
                 "temperature sensors. Sensor IDs can be selected "
                 "in the rule."),
        elements = [
            Integer(title = _("warning if above"), unit = u"°C", default_value = 35),
            Integer(title = _("critical if above"), unit = u"°C", default_value = 40),
        ]),
    TextAscii(
        title = _("Sensor ID"),
        help = _("The identifier of the thermal sensor.")),
    "first"
)

register_check_parameters(
    subgroup_environment,
    "disk_temperature",
    _("Harddisk temperature (e.g. via SMART)"),
    Tuple(
        help = _("Temperature levels for hard disks, that is determined e.g. via SMART"),
        elements = [
            Integer(title = _("warning if above"), unit = u"°C", default_value = 35),
            Integer(title = _("critical if above"), unit = u"°C", default_value = 40),
        ]),
    TextAscii(
        title = _("Hard disk device"),
        help = _("The identificator of the hard disk device, e.g. <tt>/dev/sda</tt>.")),
    "first"
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
                      Integer(title = _("warning if above"), unit = u"°C", default_value = 26),
                      Integer(title = _("critical if above"), unit = u"°C", default_value = 30),
                  ])),
            ( "remote_temp",
              Tuple(
                  title = _("Remote Temperature"),
                  elements = [
                      Integer(title = _("warning if above"), unit = u"°C", default_value = 26),
                      Integer(title = _("critical if above"), unit = u"°C", default_value = 30),
                  ])),
            ( "humidity",
              Tuple(
                  title = _("Humidity"),
                  elements = [
                      Integer(title = _("warning if above"), unit = u"%", default_value = 60),
                      Integer(title = _("critical if above"), unit = u"%", default_value = 75),
                  ])),
            ]),
            None,
    "first"
)

register_check_parameters(
    subgroup_environment,
    "hw_fans",
    _("FAN speed of Hardware devices"),
    Tuple(
        help = _("Levels for the FAN speed of a hardware device like a switch"),
        elements = [
            Integer(title = _("warning if below"), unit = u"rpm", default_value = 3000),
            Integer(title = _("critical if below"), unit = u"rpm", default_value = 2500),
        ]),
    TextAscii(
        title = _("Fan Name"),
        help = _("The identificator of the fan.")),
    "first"
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
                      Integer(title = _("warning if above"), unit = _("kW") ),
                      Integer(title = _("critical if above"), unit = _("kW")),
                  ])),
            ( "W",
              Tuple(
                  title = _("Active Power"),
                  elements = [
                      Integer(title = _("warning if above"), unit = _("W") ),
                      Integer(title = _("critical if above"), unit = _("W") ),
                  ])),
            ( "A",
              Tuple(
                  title = _("Current on Power Channel"),
                  elements = [
                      Integer(title = _("warning if above"), unit = _("A") ),
                      Integer(title = _("critical if above"), unit = _("A")),
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
                      Integer(title = _("warning if above"), unit = _("VA") ),
                      Integer(title = _("critical if above"), unit = _("VA")),
                  ])),
            ]),
    TextAscii(
        title = _("Phase Number"),
        help = _("The Number of the power Phase.")),
    "first"
)


register_check_parameters(
    subgroup_environment,
    "temperature_auto",
    _("Temperature sensors with builtin levels"),
    None,
    TextAscii(
        title = _("Sensor ID"),
        help = _("The identificator of the themal sensor.")),
    "first"
)

register_check_parameters(
   subgroup_os,
    "ntp_time",
    _("State of NTP time synchronisation"),
    Tuple(
        elements = [
            Integer(
                title = _("Max. allowed stratum"),
                default_value = 10,
                help = _("The stratum (\"distance\" to the reference clock) at which the check gets critical."),
            ),
            Float(
                title = _("Warning if above"),
                unit = _("Milliseconds"),
                default_value = 200.0,
                help = _("The offset in ms at which a warning state is triggered."),
            ),
            Float(
                title = _("Critical if above"),
                unit = _("Milliseconds"),
                default_value = 500.0,
                help = _("The offset in ms at which a critical state is triggered."),
            ),
        ]
    ),
    None,
    "first"
)

register_check_parameters(
   subgroup_environment,
    "apc_symentra",
    _("APC Symmetra Checks"),
    Dictionary(
        elements = [
            ("levels",
            Tuple(
                title = _("Levels of battery parameters during normal operation"),
                elements = [
                    Integer(
                        title = _("Critical Battery Capacity"),
                        help = _("The battery capacity in percent at and below which a critical state is be triggered"),
                        unit = _("%"),
                        default_value = 95,
                    ),
                    Integer(
                        title = _("Critical Battery Temperature"),
                        help = _("The critical temperature of the battery"),
                        unit = _("C"),
                        default_value = 40,
                    ),
                    Integer(
                        title = _("Critical Battery Current"),
                        help = _("The critical battery current in Ampere"),
                        unit = _("A"),
                        default_value = 1,
                    ),
                    Integer(
                        title = _("Critical Battery Voltage"),
                        help = _("The output voltage at and below which a critical state is triggered."),
                        unit = _("V"),
                        default_value = 220,
                    ),
                ]
            )),
            ("post_calibration_levels",
            Dictionary(
                title = _("Levels of battery parameters after calibration"),
                help = _("After a battery calibration the battery capacity is reduced until the "
                         "battery is fully charged again. Here you can specify an alternative lower "
                         "level in this post-calibration phase. "
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
        ],
        optional_keys = ['post_calibration_levels'],
    ),
    None,
    "first"
)

syslog_facilities = [
    (0, "kern"),
    (1, "user"),
    (2, "mail"),
    (3, "daemon"),
    (4, "auth"),
    (5, "syslog"),
    (6, "lpr"),
    (7, "news"),
    (8, "uucp"),
    (9, "cron"),
    (10, "authpriv"),
    (11, "ftp"),
    (16, "local0"),
    (17, "local1"),
    (18, "local2"),
    (19, "local3"),
    (20, "local4"),
    (21, "local5"),
    (22, "local6"),
    (23, "local7"),
]

register_check_parameters(
   subgroup_applications,
    "jvm_threads",
    _("JVM threads"),
    Tuple(
        help = _("This rule sets the warn and crit levels for the number of threads "
                 "running in a JVM."),
        elements = [
            Integer(
                title = _("Warning if above"),
                unit = _("threads"),
                default_value = 80,
            ),
            Integer(
                title = _("Critical if above"),
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
        "jvm_uptime",
        _("JVM uptime (since last reboot)"),
        Dictionary(
            help = _("This rule sets the warn and crit levels for the uptime of a JVM. "),
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
                  Age(title = _("Warning if above")),
                  Age(title = _("Critical if above")),
                  ]
                  )),
            ]
            ),
        TextAscii(
                title = _("Name of the virtual machine"),
                help = _("The name of the application server"),
                allow_empty = False,
                ),
        "first",
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
                title = _("Warning if above"),
                unit = _("sessions"),
                default_value = 800,
            ),
            Integer(
                title = _("Critical if above"),
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
                 "of incoming requests to a JVM application server"),
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
                title = _("Warning if above"),
                unit = _("requests/sec"),
                default_value = 800,
            ),
            Integer(
                title = _("Critical if above"),
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
                title = _("Warning if above"),
                unit = _("requests"),
                default_value = 20,
            ),
            Integer(
                title = _("Critical if above"),
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
                 "non-heap and total memory area usage on web application servers."),
        elements = [
            ( "totalheap",
               Alternative(
                   title = _("Total Memory Levels"),
                   elements = [
                       Tuple(
                           title = _("Percentage levels of used space"),
                           elements = [
                               Percentage(title = _("Warning if above"), label = _("% usage")),
                               Percentage(title = _("Critical if above"), label = _("% usage")),
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
                               Percentage(title = _("Warning if above"), label = _("% usage")),
                               Percentage(title = _("Critical if above"), label = _("% usage")),
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
                               Percentage(title = _("Warning if above"), label = _("% usage")),
                               Percentage(title = _("Critical if above"), label = _("% usage")),
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
                    Integer(title = _("Warning if above")),
                    Integer(title = _("Critical if above")),
                ]
            )),
            ("messageRate",
            Tuple(
                title = _("Number of messages delivered"),
                elements = [
                    Integer(title = _("Warning if above")),
                    Integer(title = _("Critical if above")),
                ]
            )),
            ("dataRate",
            Tuple(
                title = _("Amount of data processed"),
                elements = [
                    Integer(title = _("Warning if above")),
                    Integer(title = _("Cricital if above")),
                ]
            )),
            ("queuedMessages",
            Tuple(
                title = _("Number of messages currently queued"),
                elements = [
                    Integer(title = _("Warning if above")),
                    Integer(title = _("Critical if above")),
                ]
            )),
            ("queueSize",
            Tuple(
                title = _("Size of the queue"),
                elements = [
                    Integer(title = _("Warning if above")),
                    Integer(title = _("Critical if above")),
                ]
            )),
            ("deferredMessages",
            Tuple(
                title = _("Number of messages in deferred state"),
                elements = [
                    Integer(title = _("Warning if above")),
                    Integer(title = _("Critical if above")),
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

register_check_parameters(subgroup_applications,
    "logwatch_ec",
    _('Logwatch Event Console Forwarding'),
    Alternative(
        title = _("Forwarding"),
        help = _("Instead of using the regular logwatch check all lines received by logwatch can "
                 "be forwarded to a Check_MK event console daemon to be processed. The target event "
                 "console can be configured for each host in a separate rule."),
        elements = [
            FixedValue(
                "",
                totext = _("Messages are handled by logwatch."),
                title = _("No forwarding"),
            ),
            Dictionary(
                title = _('Forward Messages to Event Console'),
                elements = [
                    ('restrict_logfiles',
                        ListOfStrings(
                            title = _('Restrict Logfiles (Prefix matching regular expressions)'),
                            help  = _("Put the item names of the logfiles here. For example \"System$\" "
                                      "to select the service \"LOG System\". You can use regular expressions "
                                      "which must match the beginning of the logfile name."),
                        ),
                    ),
                    ('method', Alternative(
                        title = _("Forwarding Method"),
                        elements = [
                            Alternative(
                                title = _("Send events to local event console"),
                                elements = [
                                    FixedValue(
                                        "",
                                        totext = _("Directly forward to event console"),
                                        title = _("Send events to local event console in same OMD site"),
                                    ),
                                    TextAscii(
                                        title = _("Send events to local event console into unix socket"),
                                        allow_empty = False,
                                    ),

                                    FixedValue(
                                        "spool:",
                                        totext = _("Spool to event console"),
                                        title = _("Spooling: Send events to local event console in same OMD site"),
                                    ),
                                    Transform(
                                        TextAscii(),
                                        title = _("Spooling: Send events to local event console into given spool directory"),
                                        allow_empty = False,
                                        forth = lambda x: x[6:],        # remove prefix
                                        back  = lambda x: "spool:" + x, # add prefix
                                    ),
                                ],
                                match = lambda x: x and (x == 'spool:' and 2 or x.startswith('spool:') and 3 or 1) or 0
                            ),
                            Tuple(
                                title = _("Send events to remote syslog host"),
                                elements = [
                                    DropdownChoice(
                                        choices = [
                                            ('udp', _('UDP')),
                                            ('tcp', _('TCP')),
                                        ],
                                        title = _("Protocol"),
                                    ),
                                    TextAscii(
                                        title = _("Address"),
                                        allow_empty = False,
                                    ),
                                    Integer(
                                        title = _("Port"),
                                        allow_empty = False,
                                        default_value = 514,
                                        minvalue = 1,
                                        maxvalue = 65535,
                                        size = 6,
                                    ),
                                ]
                            ),
                        ],
                    )),
                    ('facility', DropdownChoice(
                        title = _("Syslog facility for forwarded messages"),
                        help = _("When forwarding messages and no facility can be extracted from the "
                                 "message this facility is used."),
                        choices = syslog_facilities,
                        default_value = 17, # local1
                    )),
                ],
                optional_keys = ['restrict_logfiles'],
            ),
        ],
        default_value = '',
    ),
    None,
    'first',
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
    subgroup_applications,
    "ps",
    _("State and count of processes"),
    Transform(
        Dictionary(
            elements = [
                ( "process", Alternative(
                    title = _("Name of the process"),
                    style = "dropdown",
                    elements = [
                        TextAscii(
                            title = _("Exact name of the process without argments"),
                            size = 50,
                        ),
                        Transform(
                            RegExp(size = 50),
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
                ( "warnmin", Integer(
                    title = _("Minimum number of matched process for WARNING state"),
                    default_value = 1,
                )),
                ( "okmin", Integer(
                    title = _("Minimum number of matched process for OK state"),
                    default_value = 1,
                )),
                ( "okmax", Integer(
                    title = _("Maximum number of matched process for OK state"),
                    default_value = 1,
                )),
                ( "warnmax", Integer(
                    title = _("Maximum number of matched process for WARNING state"),
                    default_value = 1,
                )),
                ( "user", TextAscii(
                    title = _("Name of operating system user"),
                    help = _("Leave this empty, if the user does not matter"),
                    none_is_empty = True,
                )),
                ( "cpulevels",
                  Tuple(
                    title = _("Levels on CPU utilization"),
                    elements = [
                       Percentage(title = _("Warning if above"), default_value = 90),
                       Percentage(title = _("Critical if above"), default_value = 98),
                    ],
                )),
                ( "cpu_average",
                 Integer(
                     title = _("CPU Averaging"),
                     help = _("By activating averaging, Check_MK will compute the average of "
                              "the CPU utilization over a given interval. If you have defined "
                              "alerting levels then these will automatically be applied on the "
                              "averaged value. This helps to mask out short peaks. "),
                     unit = _("minutes"),
                     minvalue = 1,
                     default_value = 15,
                 )
               ),

            ],
            optional_keys = [ "user", "cpulevels", "cpu_average" ]),
        forth = ps_convert_from_tuple,
    ),
    TextAscii(
        title = _("Name of service"),
        help = _("This name will be used in the description of the service"),
        allow_empty = False,
        regex = "^[a-zA-Z_0-9 _.-]*$",
        regex_error = _("Please use only a-z, A-Z, 0-9, space, underscore, "
                        "dot and hyphon for your service description"),
    ),
    "first", True
)
