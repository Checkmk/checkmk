#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from cmk.inventory_ui.v1_unstable import (
    AgeNotation,
    Alignment,
    BackgroundColor,
    BoolField,
    ChoiceField,
    DecimalNotation,
    Label,
    LabelColor,
    Node,
    NumberField,
    SINotation,
    StrictPrecision,
    Table,
    TextField,
    Title,
    Unit,
    View,
)

UNIT_AGE = Unit(AgeNotation())
UNIT_BITS_PER_SECOND = Unit(SINotation("bits/s"))
UNIT_COUNT = Unit(DecimalNotation(""), StrictPrecision(0))
UNIT_NUMBER = Unit(DecimalNotation(""))


def _render_ip_address_type(value: str) -> Label | str:
    match value:
        case "ipv4":
            return "IPv4"
        case "ipv6":
            return "IPv6"
        case _:
            return value


def _render_ipv4_network(value: str) -> Label | str:
    return Label("Default") if value == "0.0.0.0/0" else value


def _render_route_type(value: str) -> Label | str:
    return Label("Local route") if value == "local" else Label("Gateway route")


def _style_if_available(value: bool) -> Iterable[Alignment | BackgroundColor | LabelColor]:
    yield Alignment.CENTER
    if value:
        yield BackgroundColor.LIGHT_GREEN
    else:
        yield BackgroundColor.DARK_GRAY


def _style_if_state(value: int) -> Iterable[Alignment | BackgroundColor | LabelColor]:
    yield Alignment.CENTER
    match value:
        case 1:
            yield BackgroundColor.LIGHT_GREEN
        case 2:
            yield BackgroundColor.DARK_RED
        case _:
            yield BackgroundColor.PURPLE


node_networking = Node(
    name="networking",
    path=["networking"],
    title=Title("Networking"),
    attributes={
        "hostname": TextField(Title("Host name")),
        "total_interfaces": NumberField(Title("Total interfaces"), render=UNIT_COUNT),
        "total_ethernet_ports": NumberField(Title("Ports"), render=UNIT_COUNT),
        "available_ethernet_ports": NumberField(Title("Ports available"), render=UNIT_COUNT),
    },
)

node_networking_addresses = Node(
    name="networking_addresses",
    path=["networking", "addresses"],
    title=Title("IP addresses"),
    table=Table(
        view=View(name="invipaddresses", title=Title("IP addresses")),
        columns={
            "address": TextField(Title("Address")),
            "device": TextField(Title("Device")),
            "type": TextField(Title("Address type"), render=_render_ip_address_type),
            "network": TextField(Title("Network")),
            "netmask": TextField(Title("Netmask")),
            "prefixlength": TextField(Title("Prefix length")),
            "broadcast": TextField(Title("Broadcast")),
            "scope_id": TextField(Title("Scope ID")),
        },
    ),
)

node_networking_interfaces = Node(
    name="networking_interfaces",
    path=["networking", "interfaces"],
    title=Title("Network interfaces"),
    attributes={"is_show_more": BoolField(Title("Is show more"))},
    table=Table(
        view=View(name="invinterface", title=Title("Network interfaces")),
        columns={
            "index": NumberField(Title("Index"), render=UNIT_NUMBER),
            "name": TextField(Title("Name")),
            "description": TextField(Title("Description")),
            "alias": TextField(Title("Alias")),
            "oper_status": ChoiceField(
                Title("Operational status"),
                mapping={
                    1: "up (1)",
                    2: "down (2)",
                    3: "testing (3)",
                    4: "unknown (4)",
                    5: "dormant (5)",
                    6: "not present (6)",
                    7: "lower layer down (7)",
                },
                style=_style_if_state,
            ),
            "admin_status": ChoiceField(
                Title("Administrative status"),
                mapping={
                    1: "up (1)",
                    2: "down (2)",
                },
                style=_style_if_state,
            ),
            "available": BoolField(
                Title("Port usage"),
                render_true=Label("free"),
                render_false=Label("used"),
                style=_style_if_available,
            ),
            "speed": NumberField(Title("Speed"), render=UNIT_BITS_PER_SECOND),
            "last_change": NumberField(Title("Last change"), render=UNIT_AGE),
            "port_type": ChoiceField(
                Title("Type"),
                mapping={
                    1: "other (1)",
                    2: "regular1822 (2)",
                    3: "hdh1822 (3)",
                    4: "ddnX25 (4)",
                    5: "rfc877x25 (5)",
                    6: "ethernetCsmacd (6)",
                    7: "iso88023Csmacd (7)",
                    8: "iso88024TokenBus (8)",
                    9: "iso88025TokenRing (9)",
                    10: "iso88026Man (10)",
                    11: "starLan (11)",
                    12: "proteon10Mbit (12)",
                    13: "proteon80Mbit (13)",
                    14: "hyperchannel (14)",
                    15: "fddi (15)",
                    16: "lapb (16)",
                    17: "sdlc (17)",
                    18: "ds1 (18)",
                    19: "e1 (19)",
                    20: "basicISDN (20)",
                    21: "primaryISDN (21)",
                    22: "propPointToPointSerial (22)",
                    23: "ppp (23)",
                    24: "softwareLoopback (24)",
                    25: "eon (25)",
                    26: "ethernet3Mbit (26)",
                    27: "nsip (27)",
                    28: "slip (28)",
                    29: "ultra (29)",
                    30: "ds3 (30)",
                    31: "sip (31)",
                    32: "frameRelay (32)",
                    33: "rs232 (33)",
                    34: "para (34)",
                    35: "arcnet (35)",
                    36: "arcnetPlus (36)",
                    37: "atm (37)",
                    38: "miox25 (38)",
                    39: "sonet (39)",
                    40: "x25ple (40)",
                    41: "iso88022llc (41)",
                    42: "localTalk (42)",
                    43: "smdsDxi (43)",
                    44: "frameRelayService (44)",
                    45: "v35 (45)",
                    46: "hssi (46)",
                    47: "hippi (47)",
                    48: "modem (48)",
                    49: "aal5 (49)",
                    50: "sonetPath (50)",
                    51: "sonetVT (51)",
                    52: "smdsIcip (52)",
                    53: "propVirtual (53)",
                    54: "propMultiplexor (54)",
                    55: "ieee80212 (55)",
                    56: "fibreChannel (56)",
                    57: "hippiInterface (57)",
                    58: "frameRelayInterconnect (58)",
                    59: "aflane8023 (59)",
                    60: "aflane8025 (60)",
                    61: "cctEmul (61)",
                    62: "fastEther (62)",
                    63: "isdn (63)",
                    64: "v11 (64)",
                    65: "v36 (65)",
                    66: "g703at64k (66)",
                    67: "g703at2mb (67)",
                    68: "qllc (68)",
                    69: "fastEtherFX (69)",
                    70: "channel (70)",
                    71: "ieee80211 (71)",
                    72: "ibm370parChan (72)",
                    73: "escon (73)",
                    74: "dlsw (74)",
                    75: "isdns (75)",
                    76: "isdnu (76)",
                    77: "lapd (77)",
                    78: "ipSwitch (78)",
                    79: "rsrb (79)",
                    80: "atmLogical (80)",
                    81: "ds0 (81)",
                    82: "ds0Bundle (82)",
                    83: "bsc (83)",
                    84: "async (84)",
                    85: "cnr (85)",
                    86: "iso88025Dtr (86)",
                    87: "eplrs (87)",
                    88: "arap (88)",
                    89: "propCnls (89)",
                    90: "hostPad (90)",
                    91: "termPad (91)",
                    92: "frameRelayMPI (92)",
                    93: "x213 (93)",
                    94: "adsl (94)",
                    95: "radsl (95)",
                    96: "sdsl (96)",
                    97: "vdsl (97)",
                    98: "iso88025CRFPInt (98)",
                    99: "myrinet (99)",
                    100: "voiceEM (100)",
                    101: "voiceFXO (101)",
                    102: "voiceFXS (102)",
                    103: "voiceEncap (103)",
                    104: "voiceOverIp (104)",
                    105: "atmDxi (105)",
                    106: "atmFuni (106)",
                    107: "atmIma (107)",
                    108: "pppMultilinkBundle (108)",
                    109: "ipOverCdlc (109)",
                    110: "ipOverClaw (110)",
                    111: "stackToStack (111)",
                    112: "virtualIpAddress (112)",
                    113: "mpc (113)",
                    114: "ipOverAtm (114)",
                    115: "iso88025Fiber (115)",
                    116: "tdlc (116)",
                    117: "gigabitEthernet (117)",
                    118: "hdlc (118)",
                    119: "lapf (119)",
                    120: "v37 (120)",
                    121: "x25mlp (121)",
                    122: "x25huntGroup (122)",
                    123: "trasnpHdlc (123)",
                    124: "interleave (124)",
                    125: "fast (125)",
                    126: "ip (126)",
                    127: "docsCableMaclayer (127)",
                    128: "docsCableDownstream (128)",
                    129: "docsCableUpstream (129)",
                    130: "a12MppSwitch (130)",
                    131: "tunnel (131)",
                    132: "coffee (132)",
                    133: "ces (133)",
                    134: "atmSubInterface (134)",
                    135: "l2vlan (135)",
                    136: "l3ipvlan (136)",
                    137: "l3ipxvlan (137)",
                    138: "digitalPowerline (138)",
                    139: "mediaMailOverIp (139)",
                    140: "dtm (140)",
                    141: "dcn (141)",
                    142: "ipForward (142)",
                    143: "msdsl (143)",
                    144: "ieee1394 (144)",
                    145: "if-gsn (145)",
                    146: "dvbRccMacLayer (146)",
                    147: "dvbRccDownstream (147)",
                    148: "dvbRccUpstream (148)",
                    149: "atmVirtual (149)",
                    150: "mplsTunnel (150)",
                    151: "srp (151)",
                    152: "voiceOverAtm (152)",
                    153: "voiceOverFrameRelay (153)",
                    154: "idsl (154)",
                    155: "compositeLink (155)",
                    156: "ss7SigLink (156)",
                    157: "propWirelessP2P (157)",
                    158: "frForward (158)",
                    159: "rfc1483 (159)",
                    160: "usb (160)",
                    161: "ieee8023adLag (161)",
                    162: "bgppolicyaccounting (162)",
                    163: "frf16MfrBundle (163)",
                    164: "h323Gatekeeper (164)",
                    165: "h323Proxy (165)",
                    166: "mpls (166)",
                    167: "mfSigLink (167)",
                    168: "hdsl2 (168)",
                    169: "shdsl (169)",
                    170: "ds1FDL (170)",
                    171: "pos (171)",
                    172: "dvbAsiIn (172)",
                    173: "dvbAsiOut (173)",
                    174: "plc (174)",
                    175: "nfas (175)",
                    176: "tr008 (176)",
                    177: "gr303RDT (177)",
                    178: "gr303IDT (178)",
                    179: "isup (179)",
                    180: "propDocsWirelessMaclayer (180)",
                    181: "propDocsWirelessDownstream (181)",
                    182: "propDocsWirelessUpstream (182)",
                    183: "hiperlan2 (183)",
                    184: "propBWAp2Mp (184)",
                    185: "sonetOverheadChannel (185)",
                    186: "digitalWrapperOverheadChannel (186)",
                    187: "aal2 (187)",
                    188: "radioMAC (188)",
                    189: "atmRadio (189)",
                    190: "imt (190)",
                    191: "mvl (191)",
                    192: "reachDSL (192)",
                    193: "frDlciEndPt (193)",
                    194: "atmVciEndPt (194)",
                    195: "opticalChannel (195)",
                    196: "opticalTransport (196)",
                    197: "propAtm (197)",
                    198: "voiceOverCable (198)",
                    199: "infiniband (199)",
                    200: "teLink (200)",
                    201: "q2931 (201)",
                    202: "virtualTg (202)",
                    203: "sipTg (203)",
                    204: "sipSig (204)",
                    205: "docsCableUpstreamChannel (205)",
                    206: "econet (206)",
                    207: "pon155 (207)",
                    208: "pon622 (208)",
                    209: "bridge (209)",
                    210: "linegroup (210)",
                    211: "voiceEMFGD (211)",
                    212: "voiceFGDEANA (212)",
                    213: "voiceDID (213)",
                    214: "mpegTransport (214)",
                    215: "sixToFour (215)",
                    216: "gtp (216)",
                    217: "pdnEtherLoop1 (217)",
                    218: "pdnEtherLoop2 (218)",
                    219: "opticalChannelGroup (219)",
                    220: "homepna (220)",
                    221: "gfp (221)",
                    222: "ciscoISLvlan (222)",
                    223: "actelisMetaLOOP (223)",
                    224: "fcipLink (224)",
                    225: "rpr (225)",
                    226: "qam (226)",
                    227: "lmp (227)",
                    228: "cblVectaStar (228)",
                    229: "docsCableMCmtsDownstream (229)",
                    230: "adsl2 (230)",
                    231: "macSecControlledIF (231)",
                    232: "macSecUncontrolledIF (232)",
                    233: "aviciOpticalEther (233)",
                    234: "atmbond (234)",
                    235: "voiceFGDOS (235)",
                    236: "mocaVersion1 (236)",
                    237: "ieee80216WMAN (237)",
                    238: "adsl2plus (238)",
                    239: "dvbRcsMacLayer (239)",
                    240: "dvbTdm (240)",
                    241: "dvbRcsTdma (241)",
                    242: "x86Laps (242)",
                    243: "wwanPP (243)",
                    244: "wwanPP2 (244)",
                    245: "voiceEBS (245)",
                    246: "ifPwType (246)",
                    247: "ilan (247)",
                    248: "pip (248)",
                    249: "aluELP (249)",
                    250: "gpon (250)",
                    251: "vdsl2 (251)",
                    252: "capwapDot11Profile (252)",
                    253: "capwapDot11Bss (253)",
                    254: "capwapWtpVirtualRadio (254)",
                    255: "bits (255)",
                    256: "docsCableUpstreamRfPort (256)",
                    257: "cableDownstreamRfPort (257)",
                    258: "vmwareVirtualNic (258)",
                    259: "ieee802154 (259)",
                    260: "otnOdu (260)",
                    261: "otnOtu (261)",
                    262: "ifVfiType (262)",
                    263: "g9981 (263)",
                    264: "g9982 (264)",
                    265: "g9983 (265)",
                    266: "aluEpon (266)",
                    267: "aluEponOnu (267)",
                    268: "aluEponPhysicalUni (268)",
                    269: "aluEponLogicalLink (269)",
                    270: "aluGponOnu (270)",
                    271: "aluGponPhysicalUni (271)",
                    272: "vmwareNicTeam (272)",
                    277: "docsOfdmDownstream (277)",
                    278: "docsOfdmaUpstream (278)",
                    279: "gfast (279)",
                    280: "sdci (280)",
                    281: "xboxWireless (281)",
                    282: "fastdsl (282)",
                    283: "docsCableScte55d1FwdOob (283)",
                    284: "docsCableScte55d1RetOob (284)",
                    285: "docsCableScte55d2DsOob (285)",
                    286: "docsCableScte55d2UsOob (286)",
                    287: "docsCableNdf (287)",
                    288: "docsCableNdr (288)",
                    289: "ptm (289)",
                    290: "ghn (290)",
                },
            ),
            "phys_address": TextField(Title("Physical address (MAC)")),
            "vlantype": TextField(Title("VLAN type")),
            "vlans": TextField(Title("VLANs")),
        },
    ),
)

node_networking_kube = Node(
    name="networking_kube",
    path=["networking", "kube"],
    title=Title("Kubernetes"),
    table=Table(
        columns={
            "ip": TextField(Title("IP address")),
            "address_type": TextField(Title("Type")),
        },
    ),
)

node_networking_routes = Node(
    name="networking_routes",
    path=["networking", "routes"],
    title=Title("Routes"),
    table=Table(
        columns={
            "target": TextField(Title("Target"), render=_render_ipv4_network),
            "device": TextField(Title("Device")),
            "type": TextField(Title("Type of route"), render=_render_route_type),
            "gateway": TextField(Title("Gateway")),
        },
    ),
)

node_networking_sip_interfaces = Node(
    name="networking_sip_interfaces",
    path=["networking", "sip_interfaces"],
    title=Title("SIP Interfaces"),
    table=Table(
        columns={
            "index": TextField(Title("Index")),
            "name": TextField(Title("Name")),
            "application_type": TextField(Title("Application Type")),
            "sys_interface": TextField(Title("System Interface")),
            "device": TextField(Title("Device")),
            "tcp_port": TextField(Title("TCP Port")),
            "gateway": TextField(Title("Gateway")),
        },
    ),
)

node_networking_tunnels = Node(
    name="networking_tunnels",
    path=["networking", "tunnels"],
    title=Title("Networking tunnels"),
    table=Table(
        view=View(name="invtunnels", title=Title("Networking tunnels")),
        columns={
            "peername": TextField(Title("Peer name")),
            "index": TextField(Title("Index")),
            "peerip": TextField(Title("Peer IP address")),
            "sourceip": TextField(Title("Source IP address")),
            "tunnelinterface": TextField(Title("Tunnel interface")),
            "linkpriority": TextField(Title("Link priority")),
        },
    ),
)

node_networking_wlan = Node(
    name="networking_wlan",
    path=["networking", "wlan"],
    title=Title("WLAN"),
)

node_networking_wlan_controller = Node(
    name="networking_wlan_controller",
    path=["networking", "wlan", "controller"],
    title=Title("Controller"),
)

node_networking_wlan_controller_accesspoints = Node(
    name="networking_wlan_controller_accesspoints",
    path=["networking", "wlan", "controller", "accesspoints"],
    title=Title("Access points"),
    table=Table(
        columns={
            "name": TextField(Title("Name")),
            "group": TextField(Title("Group")),
            "ip_addr": TextField(Title("IP address")),
            "model": TextField(Title("Model")),
            "serial": TextField(Title("Serial number")),
            "sys_location": TextField(Title("System location")),
        },
    ),
)

node_networking_cdp_cache = Node(
    name="networking_cdp_cache",
    path=["networking", "cdp_cache"],
    title=Title("CDP cache"),
)

node_networking_cdp_cache_neighbors = Node(
    name="networking_cdp_cache_neighbors",
    path=["networking", "cdp_cache", "neighbors"],
    title=Title("CDP neighbors"),
    table=Table(
        view=View(name="invcdpcache", title=Title("CDP neighbors")),
        columns={
            "neighbor_name": TextField(Title("Neighbor name")),
            "neighbor_port": TextField(Title("Neighbor port")),
            "local_port": TextField(Title("Local port")),
            "neighbor_address": TextField(Title("Neighbor address")),
            "neighbor_id": TextField(Title("Neighbor ID")),
            "platform": TextField(Title("Neighbor platform")),
            "platform_details": TextField(Title("Neighbor platform details")),
            "capabilities": TextField(Title("Capabilities")),
            "duplex": TextField(Title("Duplex")),
            "native_vlan": TextField(Title("Native VLAN")),
            "vtp_mgmt_domain": TextField(Title("VTP domain")),
            "power_consumption": TextField(Title("Power level")),
        },
    ),
)


node_networking_lldp_cache = Node(
    name="networking_lldp_cache",
    path=["networking", "lldp_cache"],
    title=Title("LLDP cache"),
    table=Table(
        columns={
            "local_cap_supported": TextField(Title("Capabilities supported")),
            "local_cap_enabled": TextField(Title("Capabilities enabled")),
        },
    ),
)


node_networking_lldp_cache_neighbors = Node(
    name="networking_lldp_cache_neighbors",
    path=["networking", "lldp_cache", "neighbors"],
    title=Title("LLDP neighbors"),
    table=Table(
        view=View(name="invlldpcache", title=Title("LLDP neighbors")),
        columns={
            "capabilities": TextField(Title("Capabilities supported")),
            "capabilities_map_supported": TextField(Title("Capabilities supported")),
            "local_port": TextField(Title("Local port")),
            "neighbor_address": TextField(Title("Neighbor address")),
            "neighbor_id": TextField(Title("Neighbor ID")),
            "neighbor_name": TextField(Title("Neighbor name")),
            "neighbor_port": TextField(Title("Neighbor port")),
            "port_description": TextField(Title("Neighbor port description")),
            "system_description": TextField(Title("Neighbor description")),
        },
    ),
)

node_networking_interfaces_name = Node(
    name=".networking.interfaces:*.name",
    path=["networking", "interfaces", "name"],
    title=Title("Name"),
)

node_networking_device_uplinks = Node(
    name="networking_device_uplinks",
    path=["networking", "uplinks"],
    title=Title("Device uplinks"),
    table=Table(
        view=View(name="invdeviceuplinks", title=Title("Device uplinks")),
        columns={
            "interface": TextField(Title("Interface")),
            "protocol": TextField(Title("Protocol")),
            "address": TextField(Title("Address")),
            "gateway": TextField(Title("Gateway")),
            "public_address": TextField(Title("Public address")),
            "assignment_mode": TextField(Title("Assignment mode")),
        },
    ),
)
