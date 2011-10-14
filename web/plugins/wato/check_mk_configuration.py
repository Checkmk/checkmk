#!/usr/bin/python
# encoding: utf-8

#   +----------------------------------------------------------------------+
#   |           ____             __ _                                      |
#   |          / ___|___  _ __  / _(_) __ ___   ____ _ _ __ ___            |
#   |         | |   / _ \| '_ \| |_| |/ _` \ \ / / _` | '__/ __|           |
#   |         | |__| (_) | | | |  _| | (_| |\ V / (_| | |  \__ \           |
#   |          \____\___/|_| |_|_| |_|\__, | \_/ \__,_|_|  |___/           |
#   |                                 |___/                                |
#   +----------------------------------------------------------------------+
#   | Configuration variables for main.mk                                  |
#   +----------------------------------------------------------------------+

group = _("Configuration of Checks")

# ignored_checktypes --> Hier brauchen wir noch einen neuen Value-Typ

group = _("Multisite & WATO")

register_configvar(group,
    "debug",
    Checkbox(title = _("Debug mode"),
             label = _("enable debug mode"),
             help = _("When Multisite is running in debug mode, all Livestatus queries done in " 
                      "views are output. Also when errors occur a complete Python stack trace "
                      "is being output."),
            default_value = False),
    domain = "multisite")

register_configvar(group,
    "show_livestatus_errors",
    Checkbox(title = _("Show MK Livestatus error messages"),
             label = _("show errors"),
             help = _("This option controls whether error messages from unreachable sites are shown in the output of "
                      "views. Those error messages shall alert you that not all data from all sites has been shown. "
                      "Other people - however - find those messages distracting. "),
             default_value = True),
    domain = "multisite")

register_configvar(group, 
    "soft_query_limit",
    Integer(title = _("Soft query limit"),
            help = _("Whenever the number of returned datasets of a view would exceed this "
                     "limit, a warning is being displayed and no further data is being shown. "
                     "A normal user can override this limit with one mouse click."),
            minvalue = 1,
            default_value = 1000),
    domain = "multisite")

register_configvar(group, 
    "hard_query_limit",
    Integer(title = _("Hard query limit"),
            help = _("Whenever the number of returned datasets of a view would exceed this "
                     "limit, an error message is shown. The normal user cannot override "
                     "the hard limit. The purpose of the hard limit is to secure the server "
                     "against useless queries with huge result sets."),
            minvalue = 1,
            default_value = 5000),
    domain = "multisite")

register_configvar(group, 
    "quicksearch_dropdown_limit",
    Integer(title = _("Number of elements to show in Quicksearch"),
            help = _("When typing a texts in the Quicksearch snapin, a dropdown will "
                     "appear listing all matching host names containing that text. "  
                     "That list is limited in size so that the dropdown will not get "
                     "too large when you have a huge number of lists. "),
            minvalue = 1,
            default_value = 80),
    domain = "multisite")

register_configvar(group,
    "start_url",
    TextAscii(title = _("Start-URL to display in main frame"),
              help = _("When you point your browser to the Multisite GUI, usually the dashboard "
                       "is shown in the main (right) frame. You can replace this with any other "
                       "URL you like here."),
              default_value = "dashboard.py"),
    domain = "multisite")


register_configvar(group,
    "wato_hide_filenames",
    Checkbox(title = _("Hide internal folder names in WATO"),
             label = _("hide folder names"),
             help = _("When enabled, then the internal names of WATO folder in the filesystem "
                      "are not shown. They will automatically be derived from the name of the folder "
                      "when a new folder is being created. Disable this option if you want to see and "
                      "set the filenames manually."),
             default_value = True),
    domain = "multisite")
                       

group = _("Operation mode of Check_MK") 

register_configvar(group,
    "tcp_connect_timeout", 
    Float(title = _("Agent TCP connect timeout (sec)"),
          help = _("Timeout for TCP connect to agent in seconds. If the agent does "
                   "not respond within this time, it is considered to be unreachable. "
                   "Note: This does <b>not</b> limit the time the agent needs to "
                   "generate its output."),
          minvalue = 1.0))


register_configvar(group,
    "simulation_mode",
    Checkbox(title = _("Simulation mode"),
             label = _("Run in simulation mode"),
             help = _("This boolean variable allows you to bring check_mk into a dry run mode. "
                      "No hosts will be contacted, no DNS lookups will take place and data is read "
                      "from cache files that have been created during normal operation or have "
                      "been copied here from another monitoring site.")))


register_configvar(group,
    "delay_precompile",
    Checkbox(title = _("Delay precompiling of host checks"),
             label = _("delay precompiling"),
             help = _("If you enable this option, then Check_MK will not directly Python-bytecompile "
                      "all host checks when activating the configuration and restarting Nagios. "
                      "Instead it will delay this to the first "
                      "time the host is actually checked being by Nagios.<p>This reduces the time needed "
                      "for the operation, but on the other hand will lead to a slightly higher load "
                      "of Nagios for the first couple of minutes after the restart. ")))


register_configvar(group,
    "debug_log",
    Optional(Filename(label = _("Absolute path to log file")),
          title = _("Logfile for debugging errors in checks"),
          label = _("Activate logging errors into a logfile"),
          help = _("If this option is used and set to a filename, Check_MK will create a debug logfile " 
                   "containing details about failed checks (those which have state UNKNOWN " 
                   "and the output UNKNOWN - invalid output from plugin.... Per default no "
                   "logfile is written.")))

register_configvar(group,
    "cluster_max_cachefile_age",
    Integer(title = _("Maximum cache file age for clusters"),
            label = _("seconds"),
            help = _("The number of seconds a cache file may be old if check_mk should " 
                     "use it instead of getting information from the target hosts while " 
                     "checking a cluster. Per default this is enabled and set to 90 seconds. " 
                     "If your check cycle is not set to a larger value then one minute then "
                     "you should increase this accordingly.")))

register_configvar(group,
    "check_submission",
    DropdownChoice(title = _("Check submission method"),
         help = _("If you set this to <b>Nagios command pipe</b>, then Check_MK will write its "
                  "check results into the Nagios command pipe. This is the classical way. "
                  "Choosing <b>Create check files</b> "
                  "skips one phase in the Nagios core and directly create Nagios check files. "
                  "The reduces the overhead but might not be compatible with other monitoring "
                  "cores."),
         choices = [ ("pipe", _("Nagios command pipe")),
                     ("file", _("Create check files")) ]))

group = _("Inventory - automatic service detection")

register_configvar(group,
    "inventory_check_interval",
    Optional(
        Integer(title = _("Do inventory check every"),
                label = _("minutes"),
                min_value = 1),
        title = _("Enable regular inventory checks"),
        help = _("If enabled, Check_MK will create one additional check per host "
                 "that does a regular check, if the inventory would find new services "
                 "currently un-monitored.")))

register_configvar(group,
    "inventory_check_severity",
    DropdownChoice(
        title = _("Severity of failed inventory check"),
        help = _("Please select which alarm state the inventory check services "
                 "shall assume in case that un-monitored services are found."),
        choices = [
            (0, _("OK - do not alert, just display")),
            (1, _("Warning") ),
            (2, _("Critical") ),
            (3, _("Unknown") ),
            ]))
        



register_configvar(group,
    "always_cleanup_autochecks",
    Checkbox(title = _("Always cleanup autochecks"),
             help = _("When switched on, Check_MK will always cleanup the autochecks files "
                      "after each inventory, i.e. create one file per host. This is the same "
                      "as adding the option <tt>-u</tt> to each call of <tt>-I</tt> on the "
                      "command line.")))


group = _("Check configuration")

# if_inventory_porttypes = [ '6', '32', '117' ]
# if_inventory_portstates = [ '1' ]

_if_portstate_choices = [ 
                        ( '1', 'up(1)'),
                        ( '2', 'down(2)'),
                        ( '3', 'testing(3)'),
                        ( '4', 'unknown(4)'),
                        ( '5', 'dormant(5)') ,
                        ( '6', 'notPresent(6)'),
                        ( '7', 'lowerLayerDown(7)'),
                        ]

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

register_configvar(group,
    "if_inventory_monitor_state",
    Checkbox(title = _("Monitor port state of network interfaces"),
             label = _("monitor port state"),
             help = _("When this option is active then during inventory of networking interfaces "
                      "(and switch ports) the current operational state of the port will "
                      "automatically be coded as a check parameter into the check. That way the check "
                      "will get warning or critical when the state changes. This setting can later "
                      "by overridden on a per-host and per-port base by defining special check "
                      "parameters via a rule.")))

register_configvar(group,
    "if_inventory_monitor_speed",
    Checkbox(title = _("Monitor port speed of network interfaces"),
             label = _("monitor port speed"),
             help = _("When this option is active then during inventory of networking interfaces "
                      "(and switch ports) the current speed setting of the port will "
                      "automatically be coded as a check parameter into the check. That way the check "
                      "will get warning or critical when speed later changes (for example from "
                      "100 MBit/s to 10 MBit/s). This setting can later "
                      "by overridden on a per-host and per-port base by defining special check "
                      "parameters via a rule.")))

register_configvar(group,
    "if_inventory_uses_description",
    Checkbox(title = _("Use description as service name for network interface checks"),
             label = _("use description"),
             help = _("This option lets Check_MK use the interface description as item instead "
                      "of the port number. ")))

register_configvar(group,
    "if_inventory_uses_alias",
    Checkbox(title = _("Use alias as service name for network interface checks"),
             label = _("use alias"),
             help = _("This option lets Check_MK use the alias of the port (ifAlias) as item instead "
                      "of the port number. If no alias is available then the port number is used " 
                      "anyway.")))

register_configvar(group,
   "if_inventory_portstates",
   ListChoice(title = _("Network interface port states to inventorize"),
              help = _("When doing inventory on switches or other devices with network interfaces "
                       "then only ports found in one of the configured port states will be added to the monitoring."),
              choices = _if_portstate_choices))

register_configvar(group,
   "if_inventory_porttypes",
   ListChoice(title = _("Network interface port types to inventorize"),
              help = _("When doing inventory on switches or other devices with network interfaces "
                       "then only ports of the specified types will be created services for."),
              choices = _if_porttype_choices,
              columns = 3))



#   +----------------------------------------------------------------------+
#   |                         ____        _                                |
#   |                        |  _ \ _   _| | ___                           |
#   |                        | |_) | | | | |/ _ \                          |
#   |                        |  _ <| |_| | |  __/                          |
#   |                        |_| \_\\__,_|_|\___|                          |
#   |                                                                      |
#   |       ____            _                 _   _                        |
#   |      |  _ \  ___  ___| | __ _ _ __ __ _| |_(_) ___  _ __  ___        |
#   |      | | | |/ _ \/ __| |/ _` | '__/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |_| |  __/ (__| | (_| | | | (_| | |_| | (_) | | | \__ \       |
#   |      |____/ \___|\___|_|\__,_|_|  \__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Declaration of rules to be defined in main.mk or in folders          |
#   +----------------------------------------------------------------------+

group = _("Grouping")

register_rule(group, 
    "host_groups",
    GroupSelection(
        "host",
        title = _("Assignment of hosts to host groups")),
    match = "all")

register_rule(group, 
    "service_groups",
    GroupSelection(
        "service",
        title = _("Assignment of services to service groups")),
    match = "all",
    itemtype = "service")

register_rule(group, 
    "host_contactgroups",
    GroupSelection(
        "contact",
        title = _("Assignment of hosts to contact groups")),
    match = "all")

register_rule(group, 
    "service_contactgroups",
    GroupSelection(
        "contact",
        title = _("Assignment of services to contact groups")),
    match = "all",
    itemtype = "service")


group = _("Monitoring Configuration") 

register_rule(group, 
    "extra_host_conf:max_check_attempts",
    Integer(title = _("Maximum number of check attempts for host"), 
            help = _("The maximum number of failed host checks until the host will be considered "
                     "in a hard down state"),
            minvalue = 1))

register_rule(group, 
    "extra_service_conf:max_check_attempts",
    Integer(title = _("Maximum number of check attempts for service"), 
            help = _("The maximum number of failed checks until a service problem state will "
                     "be considered as <u>hard</u>. Only hard state trigger notifications. "),
            minvalue = 1),
    itemtype = "service")


register_rule(group,
    "extra_host_conf:notification_period",
    TimeperiodSelection(
        title = _("Notification period for hosts"),
        help = _("If you specify a notification period for a host then notifications "
                 "about problems of that host (not of its services!) will only be sent "
                 "if those problems occur within the notification period. Also you can "
                 "filter out problems in the problems views for objects not being in "
                 "their notification period (you can think of the notification period "
                 "as the 'service time'.")),
    )

register_rule(group,
    "extra_service_conf:notification_period",
    TimeperiodSelection(
        title = _("Notification period for services"),
        help = _("If you specify a notification period for a service then notifications "
                 "about that service will only be sent "
                 "if those problems occur within the notification period. Also you can "
                 "filter out problems in the problems views for objects not being in "
                 "their notification period (you can think of the notification period "
                 "as the 'service time'.")),
    itemtype = "service")

register_rule(group,
    "only_hosts",
    title = _("Hosts to be monitored"),
    help = _("By adding rules to this ruleset you can define a subset of your hosts "
             "to be actually monitored. As long as the rule set is empty "
             "all configured hosts will be monitored. As soon as you add at least one "
             "rule, only hosts with a matching rule will be monitored."),
    optional = True, # only_hosts is None per default
    )

register_rule(group,
    "ignored_services",
    title = _("Ignored services"),
    help = _("Services that are declared as <u>ignored</u> by this rule set will not be added "
             "to a host during inventory (automatic service detection). Services that already "
             "exist will continued to be monitored but be marked as obsolete in the service "
             "list of a host."),
    itemtype = "service")

group = _("SNMP")

_snmpv3_basic_elements = [
     DropdownChoice(
         choices = [ 
             ( "authPriv",     _("authPriv")),   
             ( "authNoPriv",   _("authNoPriv")), 
             ( "noAuthNoPriv", _("noAuthNoPriv")), 
             ],
         title = _("Security level")),
      DropdownChoice(
          choices = [
             ( "md5", _("MD5") ),
             ( "sha", _("SHA1") ),
          ],
          title = _("Authentication protocol")),
     TextAscii(title = _("Security name")),
     TextAscii(title = _("Authentication password"))]

register_rule(group,
    "snmp_communities",
    Alternative(
       elements = [
           TextAscii(
               title = _("SNMP community (SNMP Versions 1 and 2c)"),
               allow_empty = False),
           Tuple(
               title = _("Credentials for SNMPv3"),
               elements = _snmpv3_basic_elements),
           Tuple(
               title = _("Credentials for SNMPv3 including privacy options"),
               elements = _snmpv3_basic_elements + [
                  DropdownChoice(
                      choices = [
                         ( "DES", _("DES") ),
                         ( "AES", _("AES") ),
                      ],
                      title = _("Privacy protocol")),
                 TextAscii(title = _("Privacy pass phrase")),
                   ])],
        title = _("SNMP communities of monitored hosts")))


group = _("Operation mode of Check_MK") 

register_rule(group,
    "agent_ports",
    Integer(title = _("TCP port for connection to Check_MK agent"),
            help = _("This variable allows to specify the TCP port to " 
                     "be used to connect to the agent on a per-host-basis. "),
            minvalue = 1,
            maxvalue = 65535))


register_rule(group,
    "dyndns_hosts",
    title = _("Hosts with dynamic DNS lookup during monitoring"),
    help = _("This ruleset selects host for dynamic DNS lookup during monitoring. Normally "
             "the IP addresses of hosts are statically configured or looked up when you "
             "activate the changes. In some rare cases DNS lookups must be done each time "
             "a host is connected to, e.g. when the IP address of the host is dynamic "
             "and can change."))

#   +----------------------------------------------------------------------+
#   |                      ____ _               _                          |
#   |                     / ___| |__   ___  ___| | __                      |
#   |                    | |   | '_ \ / _ \/ __| |/ /                      |
#   |                    | |___| | | |  __/ (__|   <                       |
#   |                     \____|_| |_|\___|\___|_|\_\                      |
#   |                                                                      |
#   |        ____                                _                         |
#   |       |  _ \ __ _ _ __ __ _ _ __ ___   ___| |_ ___ _ __ ___          |
#   |       | |_) / _` | '__/ _` | '_ ` _ \ / _ \ __/ _ \ '__/ __|         |
#   |       |  __/ (_| | | | (_| | | | | | |  __/ ||  __/ |  \__ \         |
#   |       |_|   \__,_|_|  \__,_|_| |_| |_|\___|\__\___|_|  |___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Rules for configuring parameters of checks (services)                |
#   +----------------------------------------------------------------------+

group = _("Check Parameters")
register_rule(group, 
    "checkgroup_parameters:filesystem",
    Dictionary(title = _("Filesystems (used space and growth)"),
        elements = [
            ( "levels", 
              Tuple(
                  title = _("Levels for the used space"),
                  elements = [
                      Percentage(title = _("Warning at"),  label = _("% usage")),  
                      Percentage(title = _("Critical at"), label = _("% usage"))])),
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
            (  "trend_range",
               Integer(
                   title = _("Range for filesystem trend computation"),
                   minvalue = 1,
                   label= _("hours"))),
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
    itemtype = "item",
    itemname = _("mount point"),
    match = "dict",
    )

register_rule(group,
    "checkgroup_parameters:if",
    Dictionary(title = _("Network interfaces and switch ports"),
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
                               Integer(title = _("Critical at"), label = _("% of port speed")),
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
    match = "dict",
    itemtype = "item",
    itemname = _("port specification"),
    )

            
            



register_rule(group, 
    "checkgroup_parameters:cpu_load",
    Tuple(title = _("CPU load (not utilization!)"), 
          help = _("The CPU load of a system is the number of processes currently being "
                   "in the state <u>running</u>, i.e. either they occupy a CPU or wait "
                   "for one. The <u>load average</u> is the averaged CPU load over the last 1, "
                   "5 or 15 minutes. The following levels will be applied on the average "
                   "load. On Linux system the 15-minute average load is used when applying "
                   "those levels."),
          elements = [
              Integer(title = _("Warning at a load of")),
              Integer(title = _("Critical at a load of"))]),
    )


