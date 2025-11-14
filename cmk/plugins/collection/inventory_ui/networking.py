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
    IECNotation,
    Label,
    LabelColor,
    Node,
    NumberField,
    StrictPrecision,
    Table,
    TextField,
    Title,
    Unit,
    View,
)

UNIT_AGE = Unit(AgeNotation())
UNIT_BITS_PER_SECOND = Unit(IECNotation("bits/s"))
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
        yield LabelColor.BLACK
        yield BackgroundColor.LIGHT_GREEN
    else:
        yield LabelColor.WHITE
        yield BackgroundColor.DARK_GRAY


def _style_if_state(value: int) -> Iterable[Alignment | BackgroundColor | LabelColor]:
    yield Alignment.CENTER
    match value:
        case 1:
            yield LabelColor.BLACK
            yield BackgroundColor.LIGHT_GREEN
        case 2:
            yield LabelColor.WHITE
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
        columns={
            "address": TextField(Title("Address")),
            "device": TextField(Title("Device")),
            "type": TextField(Title("Address type"), render=_render_ip_address_type),
        },
    ),
)

node_networking_interfaces = Node(
    name="networking_interfaces",
    path=["networking", "interfaces"],
    title=Title("Network interfaces"),
    table=Table(
        view=View(name="invinterface", title=Title("Network interfaces")),
        columns={
            "index": NumberField(Title("Index"), render=UNIT_NUMBER),
            "description": TextField(Title("Description")),
            "alias": TextField(Title("Alias")),
            "oper_status": ChoiceField(
                Title("Operational status"),
                mapping={
                    1: "1 - up",
                    2: "2 - down",
                    3: "3 - testing",
                    4: "4 - unknown",
                    5: "5 - dormant",
                    6: "6 - not present",
                    7: "7 - lower layer down",
                },
                style=_style_if_state,
            ),
            "admin_status": ChoiceField(
                Title("Administrative status"),
                mapping={
                    1: "1 - up",
                    2: "2 - down",
                },
                style=_style_if_state,
            ),
            "available": BoolField(
                Title("Port usage"),
                render_true=Label("Free"),
                render_false=Label("Used"),
                style=_style_if_available,
            ),
            "speed": NumberField(Title("Speed"), render=UNIT_BITS_PER_SECOND),
            "last_change": NumberField(Title("Last change"), render=UNIT_AGE),
            "port_type": ChoiceField(
                Title("Type"),
                mapping={
                    1: "1 - other",
                    2: "2 - regular1822",
                    3: "3 - hdh1822",
                    4: "4 - ddnX25",
                    5: "5 - rfc877x25",
                    6: "6 - ethernetCsmacd",
                    7: "7 - iso88023Csmacd",
                    8: "8 - iso88024TokenBus",
                    9: "9 - iso88025TokenRing",
                    10: "10 - iso88026Man",
                    11: "11 - starLan",
                    12: "12 - proteon10Mbit",
                    13: "13 - proteon80Mbit",
                    14: "14 - hyperchannel",
                    15: "15 - fddi",
                    16: "16 - lapb",
                    17: "17 - sdlc",
                    18: "18 - ds1",
                    19: "19 - e1",
                    20: "20 - basicISDN",
                    21: "21 - primaryISDN",
                    22: "22 - propPointToPointSerial",
                    23: "23 - ppp",
                    24: "24 - softwareLoopback",
                    25: "25 - eon",
                    26: "26 - ethernet3Mbit",
                    27: "27 - nsip",
                    28: "28 - slip",
                    29: "29 - ultra",
                    30: "30 - ds3",
                    31: "31 - sip",
                    32: "32 - frameRelay",
                    33: "33 - rs232",
                    34: "34 - para",
                    35: "35 - arcnet",
                    36: "36 - arcnetPlus",
                    37: "37 - atm",
                    38: "38 - miox25",
                    39: "39 - sonet",
                    40: "40 - x25ple",
                    41: "41 - iso88022llc",
                    42: "42 - localTalk",
                    43: "43 - smdsDxi",
                    44: "44 - frameRelayService",
                    45: "45 - v35",
                    46: "46 - hssi",
                    47: "47 - hippi",
                    48: "48 - modem",
                    49: "49 - aal5",
                    50: "50 - sonetPath",
                    51: "51 - sonetVT",
                    52: "52 - smdsIcip",
                    53: "53 - propVirtual",
                    54: "54 - propMultiplexor",
                    55: "55 - ieee80212",
                    56: "56 - fibreChannel",
                    57: "57 - hippiInterface",
                    58: "58 - frameRelayInterconnect",
                    59: "59 - aflane8023",
                    60: "60 - aflane8025",
                    61: "61 - cctEmul",
                    62: "62 - fastEther",
                    63: "63 - isdn",
                    64: "64 - v11",
                    65: "65 - v36",
                    66: "66 - g703at64k",
                    67: "67 - g703at2mb",
                    68: "68 - qllc",
                    69: "69 - fastEtherFX",
                    70: "70 - channel",
                    71: "71 - ieee80211",
                    72: "72 - ibm370parChan",
                    73: "73 - escon",
                    74: "74 - dlsw",
                    75: "75 - isdns",
                    76: "76 - isdnu",
                    77: "77 - lapd",
                    78: "78 - ipSwitch",
                    79: "79 - rsrb",
                    80: "80 - atmLogical",
                    81: "81 - ds0",
                    82: "82 - ds0Bundle",
                    83: "83 - bsc",
                    84: "84 - async",
                    85: "85 - cnr",
                    86: "86 - iso88025Dtr",
                    87: "87 - eplrs",
                    88: "88 - arap",
                    89: "89 - propCnls",
                    90: "90 - hostPad",
                    91: "91 - termPad",
                    92: "92 - frameRelayMPI",
                    93: "93 - x213",
                    94: "94 - adsl",
                    95: "95 - radsl",
                    96: "96 - sdsl",
                    97: "97 - vdsl",
                    98: "98 - iso88025CRFPInt",
                    99: "99 - myrinet",
                    100: "100 - voiceEM",
                    101: "101 - voiceFXO",
                    102: "102 - voiceFXS",
                    103: "103 - voiceEncap",
                    104: "104 - voiceOverIp",
                    105: "105 - atmDxi",
                    106: "106 - atmFuni",
                    107: "107 - atmIma",
                    108: "108 - pppMultilinkBundle",
                    109: "109 - ipOverCdlc",
                    110: "110 - ipOverClaw",
                    111: "111 - stackToStack",
                    112: "112 - virtualIpAddress",
                    113: "113 - mpc",
                    114: "114 - ipOverAtm",
                    115: "115 - iso88025Fiber",
                    116: "116 - tdlc",
                    117: "117 - gigabitEthernet",
                    118: "118 - hdlc",
                    119: "119 - lapf",
                    120: "120 - v37",
                    121: "121 - x25mlp",
                    122: "122 - x25huntGroup",
                    123: "123 - trasnpHdlc",
                    124: "124 - interleave",
                    125: "125 - fast",
                    126: "126 - ip",
                    127: "127 - docsCableMaclayer",
                    128: "128 - docsCableDownstream",
                    129: "129 - docsCableUpstream",
                    130: "130 - a12MppSwitch",
                    131: "131 - tunnel",
                    132: "132 - coffee",
                    133: "133 - ces",
                    134: "134 - atmSubInterface",
                    135: "135 - l2vlan",
                    136: "136 - l3ipvlan",
                    137: "137 - l3ipxvlan",
                    138: "138 - digitalPowerline",
                    139: "139 - mediaMailOverIp",
                    140: "140 - dtm",
                    141: "141 - dcn",
                    142: "142 - ipForward",
                    143: "143 - msdsl",
                    144: "144 - ieee1394",
                    145: "145 - if-gsn",
                    146: "146 - dvbRccMacLayer",
                    147: "147 - dvbRccDownstream",
                    148: "148 - dvbRccUpstream",
                    149: "149 - atmVirtual",
                    150: "150 - mplsTunnel",
                    151: "151 - srp",
                    152: "152 - voiceOverAtm",
                    153: "153 - voiceOverFrameRelay",
                    154: "154 - idsl",
                    155: "155 - compositeLink",
                    156: "156 - ss7SigLink",
                    157: "157 - propWirelessP2P",
                    158: "158 - frForward",
                    159: "159 - rfc1483",
                    160: "160 - usb",
                    161: "161 - ieee8023adLag",
                    162: "162 - bgppolicyaccounting",
                    163: "163 - frf16MfrBundle",
                    164: "164 - h323Gatekeeper",
                    165: "165 - h323Proxy",
                    166: "166 - mpls",
                    167: "167 - mfSigLink",
                    168: "168 - hdsl2",
                    169: "169 - shdsl",
                    170: "170 - ds1FDL",
                    171: "171 - pos",
                    172: "172 - dvbAsiIn",
                    173: "173 - dvbAsiOut",
                    174: "174 - plc",
                    175: "175 - nfas",
                    176: "176 - tr008",
                    177: "177 - gr303RDT",
                    178: "178 - gr303IDT",
                    179: "179 - isup",
                    180: "180 - propDocsWirelessMaclayer",
                    181: "181 - propDocsWirelessDownstream",
                    182: "182 - propDocsWirelessUpstream",
                    183: "183 - hiperlan2",
                    184: "184 - propBWAp2Mp",
                    185: "185 - sonetOverheadChannel",
                    186: "186 - digitalWrapperOverheadChannel",
                    187: "187 - aal2",
                    188: "188 - radioMAC",
                    189: "189 - atmRadio",
                    190: "190 - imt",
                    191: "191 - mvl",
                    192: "192 - reachDSL",
                    193: "193 - frDlciEndPt",
                    194: "194 - atmVciEndPt",
                    195: "195 - opticalChannel",
                    196: "196 - opticalTransport",
                    197: "197 - propAtm",
                    198: "198 - voiceOverCable",
                    199: "199 - infiniband",
                    200: "200 - teLink",
                    201: "201 - q2931",
                    202: "202 - virtualTg",
                    203: "203 - sipTg",
                    204: "204 - sipSig",
                    205: "205 - docsCableUpstreamChannel",
                    206: "206 - econet",
                    207: "207 - pon155",
                    208: "208 - pon622",
                    209: "209 - bridge",
                    210: "210 - linegroup",
                    211: "211 - voiceEMFGD",
                    212: "212 - voiceFGDEANA",
                    213: "213 - voiceDID",
                    214: "214 - mpegTransport",
                    215: "215 - sixToFour",
                    216: "216 - gtp",
                    217: "217 - pdnEtherLoop1",
                    218: "218 - pdnEtherLoop2",
                    219: "219 - opticalChannelGroup",
                    220: "220 - homepna",
                    221: "221 - gfp",
                    222: "222 - ciscoISLvlan",
                    223: "223 - actelisMetaLOOP",
                    224: "224 - fcipLink",
                    225: "225 - rpr",
                    226: "226 - qam",
                    227: "227 - lmp",
                    228: "228 - cblVectaStar",
                    229: "229 - docsCableMCmtsDownstream",
                    230: "230 - adsl2",
                    231: "231 - macSecControlledIF",
                    232: "232 - macSecUncontrolledIF",
                    233: "233 - aviciOpticalEther",
                    234: "234 - atmbond",
                    235: "235 - voiceFGDOS",
                    236: "236 - mocaVersion1",
                    237: "237 - ieee80216WMAN",
                    238: "238 - adsl2plus",
                    239: "239 - dvbRcsMacLayer",
                    240: "240 - dvbTdm",
                    241: "241 - dvbRcsTdma",
                    242: "242 - x86Laps",
                    243: "243 - wwanPP",
                    244: "244 - wwanPP2",
                    245: "245 - voiceEBS",
                    246: "246 - ifPwType",
                    247: "247 - ilan",
                    248: "248 - pip",
                    249: "249 - aluELP",
                    250: "250 - gpon",
                    251: "251 - vdsl2",
                    252: "252 - capwapDot11Profile",
                    253: "253 - capwapDot11Bss",
                    254: "254 - capwapWtpVirtualRadio",
                    255: "255 - bits",
                    256: "256 - docsCableUpstreamRfPort",
                    257: "257 - cableDownstreamRfPort",
                    258: "258 - vmwareVirtualNic",
                    259: "259 - ieee802154",
                    260: "260 - otnOdu",
                    261: "261 - otnOtu",
                    262: "262 - ifVfiType",
                    263: "263 - g9981",
                    264: "264 - g9982",
                    265: "265 - g9983",
                    266: "266 - aluEpon",
                    267: "267 - aluEponOnu",
                    268: "268 - aluEponPhysicalUni",
                    269: "269 - aluEponLogicalLink",
                    270: "270 - aluGponOnu",
                    271: "271 - aluGponPhysicalUni",
                    272: "272 - vmwareNicTeam",
                    277: "277 - docsOfdmDownstream",
                    278: "278 - docsOfdmaUpstream",
                    279: "279 - gfast",
                    280: "280 - sdci",
                    281: "281 - xboxWireless",
                    282: "282 - fastdsl",
                    283: "283 - docsCableScte55d1FwdOob",
                    284: "284 - docsCableScte55d1RetOob",
                    285: "285 - docsCableScte55d2DsOob",
                    286: "286 - docsCableScte55d2UsOob",
                    287: "287 - docsCableNdf",
                    288: "288 - docsCableNdr",
                    289: "289 - ptm",
                    290: "290 - ghn",
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

node_networking_cdp_cache_neighbours = Node(
    name="networking_cdp_cache_neighbours",
    path=["networking", "cdp_cache", "neighbours"],
    title=Title("CDP neighbours"),
    table=Table(
        view=View(name="invcdpcache", title=Title("CDP neighbours")),
        columns={
            "neighbour_name": TextField(Title("Neighbour name")),
            "neighbour_port": TextField(Title("Neighbour port")),
            "local_port": TextField(Title("Local port")),
            "neighbour_address": TextField(Title("Neighbour address")),
            "neighbour_id": TextField(Title("Neighbour ID")),
            "platform": TextField(Title("Neighbour platform")),
            "platform_details": TextField(Title("Neighbour platform details")),
            "capabilities": TextField(Title("Capabilities")),
            "duplex": TextField(Title("Duplex")),
            "native_vlan": TextField(Title("Native VLAN")),
            "vtp_mgmt_domain": TextField(Title("VTP domain")),
            "power_consumption": TextField(Title("Power level")),
        },
    ),
)
