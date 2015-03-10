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
        elements = check_icmp_params,
        ),
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
             RegExpUnicode(
                 title = _("Pattern (Regex)"),
                 size  = 40,
             ),
             TextUnicode(
                 title = _("Comment"),
                 size  = 40,
             ),
          ]
      ),
      title = _("Logfile pattern rules"),
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

#duplicate: check_mk_configuration.py
_if_portstate_choices = [
                        ( '1', 'up(1)'),
                        ( '2', 'down(2)'),
                        ( '3', 'testing(3)'),
                        ( '4', 'unknown(4)'),
                        ( '5', 'dormant(5)') ,
                        ( '6', 'notPresent(6)'),
                        ( '7', 'lowerLayerDown(7)'),
                        ]

#duplicate: check_mk_configuration.py
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

register_rule(group + '/' + subgroup_inventory,
    varname   = "inventory_if_rules",
    title     = _("Network Interface and Switch Port Discovery"),
    valuespec = Dictionary(
        elements = [
         ( "use_desc",
           Checkbox(
                title = _("Use description as service name for network interface checks"),
                label = _("use description"),
                help = _("This option lets Check_MK use the interface description as item instead "
                         "of the port number. If no description is available then the port number is "
                         "used anyway."))),
        ( "use_alias",
          Checkbox(
                 title = _("Use alias as service name for network interface checks"),
                     label = _("use alias"),
                     help = _("This option lets Check_MK use the alias of the port (ifAlias) as item instead "
                              "of the port number. If no alias is available then the port number is used "
                              "anyway."))),
        ( "match_alias",
          ListOfStrings(
              title = _("Match interface alias (regex)"),
              help = _("Only discover interfaces whose alias matches one of the configured "
                       "regular expressions. The match is done on the beginning of the alias. "
                       "This allows you to select interfaces based on the alias without having "
                       "the alias be part of the service description."),
              orientation = "horizontal",
              valuespec = RegExp(size = 32),
        )),
        ( "match_desc",
          ListOfStrings(
              title = _("Match interface description (regex)"),
              help = _("Only discover interfaces whose the description matches one of the configured "
                       "regular expressions. The match is done on the beginning of the description. "
                       "This allows you to select interfaces based on the description without having "
                       "the alias be part of the service description."),
              orientation = "horizontal",
              valuespec = RegExp(size = 32),
        )),
        ( "portstates",
          ListChoice(title = _("Network interface port states to discover"),
              help = _("When doing discovery on switches or other devices with network interfaces "
                       "then only ports found in one of the configured port states will be added to the monitoring."),
              choices = _if_portstate_choices,
              toggle_all = True,
              default_value = ['1'],
        )),
        ( "porttypes",
          ListChoice(title = _("Network interface port types to discover"),
              help = _("When doing discovery on switches or other devices with network interfaces "
                       "then only ports of the specified types will be created services for."),
              choices = _if_porttype_choices,
              columns = 3,
              toggle_all = True,
              default_value = [ '6', '32', '62', '117', '127', '128', '129', '180', '181', '182', '205','229' ],
        )),
        ( "rmon",
          Checkbox(
              title = _("Collect RMON statistics data"),
              help = _("If you enable this option, for every RMON capable switch port an additional service will "
                       "be created which is always OK and collects RMON data. This will give you detailed information "
                       "about the distribution of packet sizes transferred over the port. Note: currently "
                       "this extra RMON check does not honor the inventory settings for switch ports. In a future "
                       "version of Check_MK RMON data may be added to the normal interface service and not add "
                       "an additional service."),
              label = _("Create extra service with RMON statistics data (if available for the device)"),
        )),
        ],
        help = _('This rule can be used to control the inventory for network ports. '
                 'You can configure the port types and port states for inventory'
                 'and the use of alias or description as service name.'),
    ),
    match = 'dict',
)

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
        title = _("Levels on CPU utilization"),
        elements = [
           Percentage(title = _("Warning at"),  default_value = 90, maxvalue = 10000),
           Percentage(title = _("Critical at"), default_value = 98, maxvalue = 10000),
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
   ( "max_age",
     Tuple(
       title = _("Maximum allowed age"),
       help = _("Alarms you if the age of the process (not the consumed CPU time, but the real time) exceed the configured levels."),
       elements = [
           Age(title=_("Warning at:"), default_value = 3600,),
           Age(title=_("Critical at:"), default_value = 7200),
       ]
   )),
   ( "virtual_levels",
      Tuple(
        title = _("Virtual memory usage"),
        elements = [
            Filesize(title = _("Warning at")),
            Filesize(title = _("Critical at")),
        ],
   )),
   ( "resident_levels",
      Tuple(
        title = _("Physical memory usage"),
        elements = [
            Filesize(title = _("Warning at")),
            Filesize(title = _("Critical at")),
        ],
   )),
    ('handle_count', Tuple(
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
                            RegExp(size = 50),
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
    title     = _('Lotus Domino Task Inventory'),
    help      = _("Keep in mind that all configuration parameters in this rule are only applied during the "
                  "hosts inventory. Any changes later on require a host re-inventory"),
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
                        RegExp(size = 50),
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
                        RegExpUnicode(title = _("Include Pattern")),
                        RegExpUnicode(title = _("Exclude Pattern"))
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
    "first"
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
    "first",
)

register_check_parameters(
    subgroup_applications,
    "websphere_mq",
    _("Maximum number of messages in Websphere Message Queues"),
    Tuple(
      title = _('Maximum number of messages'),
          elements = [
             Integer(title = _("Warning at"), default_value = 1000 ),
             Integer(title = _("Critical at"), default_value = 1200 ),
          ]
    ),
    TextAscii(title = _("Name of Channel or Queue")),
    None,
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
    None
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
                     Age(title = _("Warning at")),
                     Age(title = _("Critical at")),
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
           Integer(title = _("Warning at"), unit = _("Seconds")),
           Integer(title = _("Critical at"), unit = _("Seconds")),
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
                  'you use manually configured checks instead of inventorized ones.'),
    valuespec = ListOf(
        Tuple(
            help = _("This defines one file grouping pattern"),
            show_titles = True,
            orientation = "horizontal",
            elements = [
                TextAscii(
                     title = _("Name of group"),
                     size = 10,
                ),
                Transform(
                    Tuple(
                        show_titles = True,
                        orientation = "vertical",
                        elements = [
                            TextAscii(title = _("Include Pattern"), size=40),
                            TextAscii(title = _("Exclude Pattern"), size=40),
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
                   title = _("Pagefile Levels"),
                   style = "dropdown",
                   elements = [
                       Tuple(
                           title = _("Pagefile usage in percent"),
                           elements = [
                               Percentage(title = _("Warning at")),
                               Percentage(title = _("Critical at")),
                           ]
                       ),
                       Transform(
                            Tuple(
                                title = _("Absolute free pagefile"),
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
                           title = _("Predictive levels"),
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
                  help = _("Here you can set the number of remaining open slots"),
                  elements = [
                      Integer(title = _("Warning at"),  label = _("slots")),
                      Integer(title = _("Critical at"), label = _("slots"))
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
    "first"
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
                ( "war_states",
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
                       Integer(title = _("Warning if below")),
                       Integer(title = _("Critical if below")),
                    ],
               ),
            ),
            ( "max_states",
               Tuple(
                   title = _("Maximum number of connections or listeners"),
                   elements = [
                       Integer(title = _("Warning at")),
                       Integer(title = _("Critical at")),
                    ],
               ),
            ),
        ]
    ),
    TextAscii(title = _("Connection name"), help = _("Specify an arbitrary name of this connection here"), allow_empty = False),
    "dict",
    has_inventory = False,
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

    return Alternative(
        title = _("Levels for %s %s") % (name, title),
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


filesystem_elements = [
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
    # Beware: this is a nasty hack that helps us to detect new-style paramters.
    # Something hat has todo with float/int conversion and has not been documented
    # by the one who implemented this.
    ( "flex_levels",
      FixedValue(
          None,
          totext = "",
          title = "",
          )),
    ( "show_levels",
      DropdownChoice(
          title = _("Display warn/crit levels in check output..."),
          choices = [
            ( "onproblem", _("Only if the status is non-OK")),
            ( "onmagic",   _("If the status is non-OK or a magic factor is set")),
            ( "always",    _("Always") ),
          ],
          default_value = "onmagic",
    )),
    ( "show_reserved",
      DropdownChoice(
          title = _("Show space reserved for the <tt>root</tt> user"),
          help = _("Check_MK accounts space that is reserved for the <tt>root</tt> user on Linux, Unix as "
                   "used space. Usually 5% are being reserved for root when a new filesystem is being created. "
                   "With this option you can have Check_MK display the current amount of reserved but yet unused "
                   "space."),
          choices = [
            ( True, _("Show reserved space") ),
            ( False, _("Do now show reserved space") ),
         ]
    )),
    ( "inodes_levels",
        Alternative(
                    title = _("Levels for Inodes"),
                    help  = _("The number of remaining inodes on the filesystem. "
                              "Please note that this setting has no effect on some filesystem checks."),
                    elements = [
                            Tuple( title = _("Percentage free"),
                                   elements = [
                                       Percentage(title = _("Warning if less than") , unit = "%", minvalue = 0.0),
                                       Percentage(title = _("Critical if less than"), unit = "%", minvalue = 0.0),
                                   ]
                            ),
                            Tuple( title = _("Absolute free"),
                                   elements = [
                                       Integer(title = _("Warning if less than"),  size = 10, unit = _("inodes"), minvalue = 0),
                                       Integer(title = _("Critical if less than"), size = 10, unit = _("inodes"), minvalue = 0),
                                ]
                            )
                    ]
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
              Percentage(title = _("Critical at"), unit = _("% usage"), allow_int = True, default_value=60)])),
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
    "ibm_svc_mdiskgrp",
    _("IBM SVC Pool Capacity"),
    Dictionary(
        elements = filesystem_elements + [
            ( "provisioning_levels", Tuple(
                title = _("Provisioning Levels"),
                help = _("A provisioning of over 100% means over provisioning."),
                elements = [
                    Percentage(title = _("Warning at provisioning of"), default_value = 110.0, maxvalue = None),
                    Percentage(title = _("Critical at provisioning of"), default_value = 120.0, maxvalue = None),
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
    subgroup_storage,
    "esx_vsphere_datastores",
    _("ESX Datastores (used space and growth)"),
    Dictionary(
        elements = filesystem_elements + [
            ("provisioning_levels", Tuple(
                title = _("Provisioning Levels"),
                help = _("Configure thresholds for overprovisioning of datastores."),
                elements = [
                  Percentage(title = _("Warning at overprovisioning of"), maxvalue = None),
                  Percentage(title = _("Critical at overprovisioning of"), maxvalue = None),
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
                      Percentage(title = _("Warning at"), label = _("errors"), default_value = 0.01, display_format = '%.3f' ),
                      Percentage(title = _("Critical at"), label = _("errors"), default_value = 0.1, display_format = '%.3f' )
                  ])),
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
             ( "traffic",
               Alternative(
                   title = _("Used bandwidth (maximum traffic)"),
                   help = _("Setting levels on the used bandwidth is optional. If you do set "
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
                           title = _("Absolute levels in bits or bytes per second"),
                           help = _("Depending on the measurement unit (defaults to byte) the absolute levels are set in bit or byte"),
                           elements = [
                               Integer(title = _("Warning at"), label = _("bits / bytes per second")),
                               Integer(title = _("Critical at"), label = _("bits / bytes per second")),
                           ]
                        )
                   ])
             ),
             ( "traffic_minimum",
               Alternative(
                   title = _("Used bandwidth (minimum traffic)"),
                   help = _("Setting levels on the used bandwidth is optional. If you do set "
                            "levels you might also consider using an averaging."),
                   elements = [
                       Tuple(
                           title = _("Percentual levels (in relation to port speed)"),
                           elements = [
                               Percentage(title = _("Warning if below"), label = _("% of port speed")),
                               Percentage(title = _("Critical if below"), label = _("% of port speed")),
                           ]
                       ),
                       Tuple(
                           title = _("Absolute levels in bits or bytes per second"),
                           help = _("Depending on the measurement unit (defaults to byte) the absolute levels are set in bit or byte"),
                           elements = [
                               Integer(title = _("Warning if below"), label = _("bits / bytes per second")),
                               Integer(title = _("Critical if below"), label = _("bits / bytes per second")),
                           ]
                        )
                   ])
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
    "first"
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
    TextAscii(
        title = _("Memory Pool Name"),
        allow_empty = False
    ),
    None
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
    None
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
    None
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

def LowerMemoryLevels(what, default_percents=None, of_what=None):
    return CascadingDropdown(
        title = _("Lower levels for %s") % what,
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
            ( "levels_shm",         UpperMemoryLevels(_("Shared Memory"),       ( 20.0,  30.0), _("RAM"))),
            ( "levels_pagetables",  UpperMemoryLevels(_("Page tables"),         (  8.0,  16.0), _("RAM"))),
            ( "levels_writeback",   UpperMemoryLevels(_("Disk Writeback"))),
            ( "levels_committed",   UpperMemoryLevels(_("Committed memory"),    (100.0, 150.0), _("RAM + Swap"))),
            ( "levels_commitlimit", LowerMemoryLevels(_("Commit Limit"),        ( 20.0,  10.0), _("RAM + Swap"))),
            ( "levels_vmalloc",     LowerMemoryLevels(_("Largest Free VMalloc Chunk"))),
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
    None, None
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
    None, None
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

def transform_printer_supply(l):
    if len(l) == 2:
        return l[0], l[1], False
    return l

register_check_parameters(
    subgroup_printing,
    "printer_supply",
    _("Printer cartridge levels"),
    Transform(
        Tuple(
              help = _("Levels for printer cartridges."),
              elements = [
                  Percentage(title = _("Warning remaining"), allow_int = True, default_value = 20.0),
                  Percentage(title = _("Critical remaining"), allow_int = True, default_value = 10.0),
                  Checkbox(
                        title = _("Upturn toner levels"),
                        label = _("Printer sends <i>used</i> material instead of <i>remaining</i>"),
                        help =  _("Some Printers (eg. Konica for Drum Cartdiges) returning the available"
                                  " fuel instead of what is left. In this case it's possible"
                                  " to upturn the levels to handle this behavior"
                                 )
                        ),]
             ),
             forth = transform_printer_supply,
    ),
    TextAscii(
        title = _("cartridge specification"),
        allow_empty = True
    ),
    None,
)
register_check_parameters(
    subgroup_printing,
    "windows_printer_queues",
    _("Number of open jobs of a printer on windows" ),
    Transform(
        Optional(
            Tuple(
                help = _("This rule is applied to the number of print jobs "
                         "currently waiting in windows printer queue."),
                elements = [
                    Integer(title = _("Warning at"), unit = _("jobs"), default_value = 40),
                    Integer(title = _("Critical at"), unit = _("jobs"), default_value = 60),
                ]
            ),
            label=_('Enable thresholds on the number of jobs'),
        ),
        forth = lambda old: old != (None, None) and old or None,
    ),
    TextAscii(
        title = _("Printer Name"),
        allow_empty = True
    ),
    None
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
    None,
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
    None,
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
    None
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
    None
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
    _("CPU utilization on Linux/UNIX"),
    Transform(
        Dictionary(
            elements = [
                ( "util",
                   Tuple(
                       title = _("Alert on too high CPU utilization"),
                       elements = [
                             Percentage(title = _("Warning at a utilization of"), default_value = 90.0),
                             Percentage(title = _("Critical at a utilization of"), default_value = 95.0)],

                       help = _("Here you can set levels on the total CPU utilization, i.e. the sum of "
                                "<i>system</i>, <i>user</i> and <i>iowait</i>. The levels are always applied "
                                "on the average utiliazation since the last check - which is usually one minute."),
                    )
                ),
                ( "iowait",
                   Tuple(
                       title = _("Alert on too high disk wait (IO wait)"),
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
            ]
        ),
        forth = lambda old: type(old) != dict and { "iowait" : old } or old,
    ),
    None,
    "dict",
)

register_check_parameters(
    subgroup_environment,
    "humidity",
    _("Humidity Levels"),
    Tuple(
          help = _("This Ruleset sets the threshold limits for humidity sensors"),
          elements = [
              Integer(title = _("Critical at or below"), unit="%" ),
              Integer(title = _("Warning at or below"), unit="%" ),
              Integer(title = _("Warning at or above"), unit="%" ),
              Integer(title = _("Critical at or above"), unit="%" ),
              ]),
    TextAscii(
        title = _("Sensor names"),
        allow_empty = False),
    None
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
                      Percentage(title = _("Maximum critical level"), unit = _("% free"), allow_int = True, default_value = 50.0)])),
            ( "autoextend",
                Checkbox(
                  title = _("Autoextend"),
                  label = _("Autoextension is expected"),
                  help = "")),
            ( "defaultincrement",
                Checkbox(
                  title = _("Default Increment"),
                  label = _("State is WARNING in case the next extent has the default size."),
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
    _("ORACLE Scheduler Job"),
    Dictionary(
        help = _("A scheduler job is an object in an ORACLE database which could be "
                 "compared to a cron job on Unix. "),
        elements = [
            ( "run_duration",
              Tuple(
                  title = _("Maximum run duration for last execution"),
                  help = _("Here you can define an upper limit for the run duration of "
                           "last execution of the job."),
                     elements = [
                          Age(title = _("warning at")),
                          Age(title = _("critical at")),
                     ])),
            ( "disabled", DropdownChoice(
             title = _("Job State"),
             totext = "",
             choices = [
                 ( True, _("Ignore the state of the Job")),
                 ( False, _("Consider the state of the job")),],
             help = _("The state of the job is ignored per default.")
            )),]),
    TextAscii(
        title = _("Scheduler Job Name"),
        help = _("Here you can set explicit Scheduler-Jobs by defining them via SID, Job-Owner "
                 "and Job-Name, separated by a dot, for example <tt>TUX12C.SYS.PURGE_LOG</tt>"),
        regex = '.+\..+',
        allow_empty = False),
    None
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
           )),
        ],
    ),
    TextAscii(
        title = _("Database SID"),
        size = 12,
        allow_empty = False),
    'first',
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
                  Filesize(title = _("Warning at")),
                  Filesize(title = _("Critical at"))
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
     None
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
        )]
    ),
    None,
    None
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
    "first"
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
    None
)

register_check_parameters(
    subgroup_applications,
    "job",
    _("Age of jobs controlled by mk-job"),
    Dictionary(
        elements = [
        ("age",
          Tuple(
            title = _("Maximum time since last start of job execution"),
            elements = [
                Age(title = _("Warning at"), default_value = 0),
                Age(title = _("Critical at"), default_value = 0)
            ]
          )
        )]
    ),
    TextAscii(
        title = _("Job name"),
    ),
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
                       Percentage(title = _("Warning at")),
                       Percentage(title = _("Critical at")),
                    ]
                )
            ),
        ]),
    None,
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
        ]),
    None,
    "dict"
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
    None
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
    "dbsize",
    _("Size of MySQL/PostgresQL databases"),
    Optional(
        Tuple(
            elements = [
                Integer(title = _("warning at"), unit = _("MB")),
                Integer(title = _("critical at"), unit = _("MB")),
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
             Integer(title = _("Warning at"),  unit = _("sessions"), default_value = 100),
             Integer(title = _("Critical at"), unit = _("sessions"), default_value = 200),
          ],
     ),
    TextAscii(
        title = _("Database name"),
        allow_empty = False),
     None
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
              Percentage(title = _("Warning if less than"), unit = _("% free pool entries")),
              Percentage(title = _("Critical if less than"), unit = _("% free pool entries")),
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
              Integer(title = _("Warning at"), unit = _("threads"), default_value = 1000),
              Integer(title = _("Critical at"), unit = _("threads"), default_value = 2000)]),
    None, None
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
    None, None
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
    "first"
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
    help      = _('Normally the Interface checks create a single service for interface. '
                  'By defining if-group patterns multiple interfaces can be combined together. '
                  'A single service is created for this interface group showing the total traffic amount '
                  'of its members. You can configure if interfaces which are identified as group interfaces '
                  'should not show up as single service. You can restrict grouped interfaces by iftype and the '
                  'item name of the single interface.'),
    valuespec = ListOf(
                    Dictionary(
                        elements = [
                            ("name",
                                   TextAscii(
                                       title = _("Name of group"),
                                       help  = _("Name of group in service description"),
                                       allow_empty = False,
                                   )),
                            ("iftype", Transform(
                                        DropdownChoice(
                                            title = _("Select interface port type"),
                                            choices = _if_porttype_choices,
                                            help = _("Only interfaces with the given port type are put into this group. "
                                                     "For example 53 (propVirtual)."),
                                        ),
                                    forth = lambda x: str(x),
                                    back  = lambda x: int(x),
                            )),
                            ("include_items", ListOfStrings(
                                title = _("Restrict interface items"),
                                help = _("Only interface with these item names are put into this group."),
                            )),
                            ("single", Checkbox(
                                title = _("Group separately"),
                                label = _("Do not list grouped interfaces separately"),
                            )),
                        ],
                        required_keys = ["name", "single"]),
                    add_label = _("Add pattern")),
    match = 'all',
)

register_rule(group + '/' + subgroup_inventory,
    varname   = "winperf_msx_queues_inventory",
    title     = _('MS Exchange Message Queues Inventory'),
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

register_check_parameters(
    subgroup_applications,
    "mailqueue_length",
    _("Number of mails in outgoing mail queue"),
    Tuple(
          help = _("This rule is applied to the number of E-Mails that are "
                   "currently in the outgoing mail queue."),
          elements = [
              Integer(title = _("Warning at"), unit = _("mails"), default_value = 10),
              Integer(title = _("Critical at"), unit = _("mails"), default_value = 20),
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
    _("Overall state of a virtual machine (for example ESX VMs)"),
    None,
    None, None
)


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
    _("Linux and Solaris Multipath Count"),
    Integer(
        help = _("This rules sets the expected number of active paths for a multipath LUN "
                 "on Linux and Solaris hosts"),
        title = _("Expected number of active paths")),
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
                                  "description. The UUID will be displayed in the pluging output."))
            ),
        ],
        help = _("This rule controls wether the UUID or the alias is used in the service description during "
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
    _("HPUX Multipath Count"),
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
    "first",
    True,
)

register_check_parameters(
    subgroup_storage,
    "netapp_disks",
    _("NetApp Broken/Spare Disk Ratio"),
    Dictionary(
        help = _("You can set a limit to the broken to spare disk ratio. "
                 "The ratio is calculated with <i>broken / (broken + spare)</i>."),
        elements = [
            ( "broken_spare_ratio",
            Tuple(
                title = _("Broken to spare ratio"),
                elements = [
                    Percentage(title = _("Warning at or above")),
                    Percentage(title = _("Critical at or above")),
                ]
            )),
        ],
        optional_keys = False
    ),
    None,
    "match"
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
    "match"
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
    None
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
            "Please take examples from discovered checks for reference.")),
    TextAscii(
        title = _("Number or ID of the disk"),
        help = _("How the disks are named depends on the type of hardware being "
                 "used. Please look at already discovered checks for examples.")),
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
        title = _("Plug Item number or name"),
        help = _("If you need the number or the name depends on the check. Just take a look to the service description. "),
        allow_empty = True),
     None
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
                          Integer(title = _("warning at"), unit = u"°C", default_value = 26),
                          Integer(title = _("critical at"), unit = u"°C", default_value = 30),
                      ]
                )),
                ( "levels_lower",
                  Tuple(
                      title = _("Lower Temperature Levels"),
                      elements = [
                          Integer(title = _("warning at"), unit = u"°C", default_value = 0),
                          Integer(title = _("critical at"), unit = u"°C", default_value = -10),
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
                 "is the webthem from W&amp;T."),
        elements = [
            Integer(title = _("warning at"), unit = u"°C", default_value = 26),
            Integer(title = _("critical at"), unit = u"°C", default_value = 30),
        ]),
    TextAscii(
        title = _("Sensor ID"),
        help = _("The identifier of the thermal sensor.")),
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
            Integer(title = _("warning at"), unit = u"°C", default_value = 35),
            Integer(title = _("critical at"), unit = u"°C", default_value = 40),
        ]),
    None,
    "first"
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
    "first"
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
    "first"
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

register_check_parameters(
    subgroup_environment,
    "ups_outphase",
    _("Parameters for output phases of UPSs"),
    Dictionary(
        elements = [
            ( "voltage",
              Tuple(
                  title = _("Voltage"),
                  elements = [
                      Integer(title = _("warning if below"), unit = u"V", default_value = 210),
                      Integer(title = _("critical if below"), unit = u"V", default_value = 200),
                  ])),
            ( "load",
              Tuple(
                  title = _("Load"),
                  elements = [
                      Integer(title = _("warning at"), unit = u"%", default_value = 80),
                      Integer(title = _("critical at"), unit = u"%", default_value = 90),
                  ])),
            ]),
    TextAscii(
        title = _("Output Name"),
        help = _("The name of the output, e.g. <tt>Phase 1</tt>")),
    "dict"
)

register_check_parameters(
    subgroup_environment,
    "el_inphase",
    _("Parameters for input phases of UPSs and PDUs"),
    Dictionary(
        elements = [
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
        ]
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
                help = _("Upper levels for the Fan speed of a hardware device"),
                title = _("Upper levels"),
                elements = [
                    Integer(title = _("warning at"), unit = u"rpm", default_value = 8000),
                    Integer(title = _("critical at"), unit = u"rpm", default_value = 8400),
                ]),
            ),
        ],
        optional_keys = ["upper"],
    ),
    TextAscii(
        title = _("Fan Name"),
        help = _("The identificator of the fan.")),
    "first"
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
    "first"
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
    "temperature_auto",
    _("Temperature sensors with builtin levels"),
    None,
    TextAscii(
        title = _("Sensor ID"),
        help = _("The identificator of the thermal sensor.")),
    "first"
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
                       Integer(title = _("Warning at"), unit = _(u"°C / range"), default_value = 5),
                       Integer(title = _("Critical at"), unit = _(u"°C / range"), default_value = 10)
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
    "dict"
)
ntp_params = \
    Tuple(
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
    ntp_params,
    None,
    "first"
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

def apc_convert_from_tuple(params):
    if type(params) in (list, tuple):
        params = { "levels": params}
    return params

register_check_parameters(
   subgroup_environment,
    "apc_symentra",
    _("APC Symmetra Checks"),
    Transform(
        Dictionary(
            elements = [
                ("levels",
                Tuple(
                    title = _("Levels of battery parameters during normal operation"),
                    elements = [
                        Integer(
                            title = _("Critical Battery Capacity"),
                            help = _("The battery capacity in percent at and below which a critical state is triggered"),
                            unit = "%", default_value = 95,
                        ),
                        Integer(
                            title = _("Critical System Temperature"),
                            help = _("The critical temperature of the System"),
                            unit = _("C"),
                            default_value = 55,
                        ),
                        Integer(
                            title = _("Critical Battery Current"),
                            help = _("The critical battery current in Ampere"),
                            unit = _("A"),
                            default_value = 1,
                        ),
                        Integer(
                            title = _("Critical Battery Voltage"),
                            help = _("The output voltage at and below which a critical state "
                                     "is triggered."),
                            unit = _("V"),
                            default_value = 220,
                        ),
                    ]
                )),
                ("output_load",
                Tuple(
                  title = _("Current Output Load"),
                  help = _("Here you can set levels on the current percentual output load of the UPS. "
                           "This load affects the running time of all components being supplied "
                           "with battery power."),
                  elements = [
                     Percentage(
                         title = _("Warning level"),
                     ),
                     Percentage(
                         title = _("Critical level"),
                     ),
                  ]
                )),
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
        forth = apc_convert_from_tuple
    ),
    None,
    "first"
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
            Integer(title = _( "Warning if below"), unit=_("l/s")),
            Integer(title = _( "Critical if below"), unit=_("l/s"))
          ]
        )
      ),
      ("level_high",
        Tuple(
          title = _("Upper levels"),
          elements = [
            Integer(title = _( "Warning at"), unit=_("l/s")),
            Integer(title = _( "Critical at"), unit=_("l/s"))
          ]
        )
      ),
      ]
   ),
   None,
   None,
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
    "first"
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
                    default_value = 1,
                ),
                Integer(
                    title = _("Critical at"),
                    default_value = 1,
            ),
            ])),
       ("offset", Tuple(
            title = _("Warning levels for Time Offset"),
            elements = [
                Integer(
                    title = _("Warning at"),
                    unit = _("microseconds"),
                    default_value = 1,
                ),
                Integer(
                    title = _("Critical at"),
                    unit = _("microseconds"),
                    default_value = 1,
            ),
            ])),
    ]),
    None,
    "first"
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
    "db2_logsizes",
    _("Size of DB2 logfiles"),
    get_free_used_dynamic_valuespec("free", "logfile", default_value = (20.0, 10.0)),
    TextAscii(
        title = _("Logfile name"),
        allow_empty = True),
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
 (3, "Connection"),
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
              default_value = [2, 3]
            )),
            ("warn_states", ListChoice(
              title = _("States which result in Warning"),
              choices = synology_update_states,
              default_value = [5]
            )),
            ("crit_states", ListChoice(
              title = _("States which result in Critical"),
              choices = synology_update_states,
              default_value = [1,4]
            )),
        ],
        optional_keys = None,
    ),
    None,
    "first"
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
                    )
                ],
                optional_keys = ['restrict_logfiles', 'expected_logfiles', 'logwatch_reclassify'],
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


# Rule for disovered process checks
register_check_parameters(
    subgroup_applications,
    "ps",
    _("State and count of processes"),
    Transform(
        Dictionary(
            elements = process_level_elements,
        ),
        forth = ps_convert_from_singlekeys,
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
                ( "user", Alternative(
                    title = _("Name of operating system user"),
                    style = "dropdown",
                    elements = [
                        TextAscii(
                            title = _("Exact name of the operating system user")
                        ),
                        Transform(
                            RegExp(size = 50),
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
            ] + process_level_elements,
            # required_keys = [ "process" ],
        ),
        forth = ps_convert_from_singlekeys,
    ),
    TextAscii(
        title = _("Process Name"),
        help = _("This name will be used in the description of the service"),
        allow_empty = False,
        regex = "^[a-zA-Z_0-9 _.-]*$",
        regex_error = _("Please use only a-z, A-Z, 0-9, space, underscore, "
                        "dot and hyphon for your service description"),
    ),
    "dict",
    has_inventory = False,
)

register_check_parameters(
    subgroup_os,
    "zypper",
    _("Zypper Updates"),
    None,
    None, None,
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
    "citrix_load",
    _("Load of Citrix Server"),
    Tuple(
        title = _("Citrix Server load"),
        elements = [
            Integer(title = _("warning at"), default_value = 8500),
            Integer(title = _("critical at"), default_value = 9500),
        ]),
    None, None
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
),

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
    "first"
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
    "first"
),

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
    "first"
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
    "first"
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
    "first"
),
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
    "first"
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
    subgroup_storage,
    "heartbeat_crm",
    _("Heartbeat CRM general status"),
    Tuple(
        elements = [
            Integer(
                title = _("Maximum age"),
                help = _("Maximum accepted age of the reported data in seconds"),
                unit = _("seconds"),
                default_value = 60,
            ),
            Optional(
                TextAscii(
                    allow_empty = False
                ),
                title = _("Expected DC"),
                help = _("The hostname of the expected distinguished controller of the cluster"),
            ),
            Optional(
                Integer(
                    min_value = 2,
                    default_value = 2
                ),
                title = _("Number of Nodes"),
                help = _("The expected number of nodes in the cluster"),
            ),
            Optional(
                Integer(
                    min_value = 0,
                ),
                title = _("Number of Resources"),
                help = _("The expected number of resources in the cluster"),
            ),
        ]
    ),
    None, None
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
                        RegExp(size = 50),
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
                        "dot and hyphon for your service description"),
    ),
    "first", False
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
    "first"
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
    None, None
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
    None, None
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
