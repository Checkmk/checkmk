#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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
"""This module serves constants which are needed in several components
of Check_MK."""

from typing import Dict, List, Text, Tuple  # pylint: disable=unused-import

from cmk.utils.i18n import _

# TODO: Investigate Check_MK code for more defines and other places
#       where similar strucures are defined and use the things from
#       here or move new stuff to this module.


# TODO: Rename to service_state_names()
def core_state_names():
    # type: () -> Dict[int, Text]
    return {
        -1: _("NODATA"),
        0: _("OK"),
        1: _("WARNING"),
        2: _("CRITICAL"),
        3: _("UNKNOWN"),
    }


def service_state_name(state_num, deflt=u""):
    # type: (int, Text) -> Text
    return core_state_names().get(state_num, deflt)


def short_service_state_names():
    # type: () -> Dict[int, Text]
    return {
        -1: _("PEND"),
        0: _("OK"),
        1: _("WARN"),
        2: _("CRIT"),
        3: _("UNKN"),
    }


def short_service_state_name(state_num, deflt=u""):
    # type: (int, Text) -> Text
    return short_service_state_names().get(state_num, deflt)


def host_state_name(state_num, deflt=u""):
    # type: (int, Text) -> Text
    states = {
        0: _("UP"),
        1: _("DOWN"),
        2: _("UNREACHABLE"),
    }
    return states.get(state_num, deflt)


def short_host_state_name(state_num, deflt=u""):
    # type: (int, Text) -> Text
    states = {0: _("UP"), 1: _("DOWN"), 2: _("UNREACH")}
    return states.get(state_num, deflt)


def weekday_name(day_num):
    # type: (int) -> Text
    """Returns the human readable day name of a given weekday number (starting with 0 at Monday)"""
    return weekdays()[day_num]


def weekday_ids():
    # type: () -> List[str]
    """Returns a list of the internal week day names"""
    return [d[0] for d in weekdays_by_name()]


def weekdays():
    # type: () -> Dict[int, Text]
    """Returns a map of weekday number (starting with 0 at Monday) to the human readable day name"""
    return {
        0: _("Monday"),
        1: _("Tuesday"),
        2: _("Wednesday"),
        3: _("Thursday"),
        4: _("Friday"),
        5: _("Saturday"),
        6: _("Sunday"),
    }


def weekdays_by_name():
    # type: () -> List[Tuple[str, Text]]
    """Returns a list of two element tuples containing the weekday ID and the human readable day name"""
    return [
        ("monday", _("Monday")),
        ("tuesday", _("Tuesday")),
        ("wednesday", _("Wednesday")),
        ("thursday", _("Thursday")),
        ("friday", _("Friday")),
        ("saturday", _("Saturday")),
        ("sunday", _("Sunday")),
    ]


def month_name(month_num):
    # type: (int) -> Text
    """Returns the human readable month name of a given month number
    (starting with 0 = January)"""
    return [
        _("January"),
        _("February"),
        _("March"),
        _("April"),
        _("May"),
        _("June"),
        _("July"),
        _("August"),
        _("September"),
        _("October"),
        _("November"),
        _("December"),
    ][month_num]


def interface_oper_state_name(state_num, deflt=u""):
    # type: (int, Text) -> Text
    return interface_oper_states().get(state_num, deflt)


def interface_oper_states():
    # type: () -> Dict[int, Text]
    return {
        1: _("up"),
        2: _("down"),
        3: _("testing"),
        4: _("unknown"),
        5: _("dormant"),
        6: _("not present"),
        7: _("lower layer down"),
        8: _("degraded"),  # artificial, not official
        9: _("admin down"),  # artificial, not official
    }


def interface_port_types():
    # type: () -> Dict[int, str]
    return {
        1: "other",
        2: "regular1822",
        3: "hdh1822",
        4: "ddnX25",
        5: "rfc877x25",
        6: "ethernetCsmacd",
        7: "iso88023Csmacd",
        8: "iso88024TokenBus",
        9: "iso88025TokenRing",
        10: "iso88026Man",
        11: "starLan",
        12: "proteon10Mbit",
        13: "proteon80Mbit",
        14: "hyperchannel",
        15: "fddi",
        16: "lapb",
        17: "sdlc",
        18: "ds1",
        19: "e1",
        20: "basicISDN",
        21: "primaryISDN",
        22: "propPointToPointSerial",
        23: "ppp",
        24: "softwareLoopback",
        25: "eon",
        26: "ethernet3Mbit",
        27: "nsip",
        28: "slip",
        29: "ultra",
        30: "ds3",
        31: "sip",
        32: "frameRelay",
        33: "rs232",
        34: "para",
        35: "arcnet",
        36: "arcnetPlus",
        37: "atm",
        38: "miox25",
        39: "sonet",
        40: "x25ple",
        41: "iso88022llc",
        42: "localTalk",
        43: "smdsDxi",
        44: "frameRelayService",
        45: "v35",
        46: "hssi",
        47: "hippi",
        48: "modem",
        49: "aal5",
        50: "sonetPath",
        51: "sonetVT",
        52: "smdsIcip",
        53: "propVirtual",
        54: "propMultiplexor",
        55: "ieee80212",
        56: "fibreChannel",
        57: "hippiInterface",
        58: "frameRelayInterconnect",
        59: "aflane8023",
        60: "aflane8025",
        61: "cctEmul",
        62: "fastEther",
        63: "isdn",
        64: "v11",
        65: "v36",
        66: "g703at64k",
        67: "g703at2mb",
        68: "qllc",
        69: "fastEtherFX",
        70: "channel",
        71: "ieee80211",
        72: "ibm370parChan",
        73: "escon",
        74: "dlsw",
        75: "isdns",
        76: "isdnu",
        77: "lapd",
        78: "ipSwitch",
        79: "rsrb",
        80: "atmLogical",
        81: "ds0",
        82: "ds0Bundle",
        83: "bsc",
        84: "async",
        85: "cnr",
        86: "iso88025Dtr",
        87: "eplrs",
        88: "arap",
        89: "propCnls",
        90: "hostPad",
        91: "termPad",
        92: "frameRelayMPI",
        93: "x213",
        94: "adsl",
        95: "radsl",
        96: "sdsl",
        97: "vdsl",
        98: "iso88025CRFPInt",
        99: "myrinet",
        100: "voiceEM",
        101: "voiceFXO",
        102: "voiceFXS",
        103: "voiceEncap",
        104: "voiceOverIp",
        105: "atmDxi",
        106: "atmFuni",
        107: "atmIma",
        108: "pppMultilinkBundle",
        109: "ipOverCdlc",
        110: "ipOverClaw",
        111: "stackToStack",
        112: "virtualIpAddress",
        113: "mpc",
        114: "ipOverAtm",
        115: "iso88025Fiber",
        116: "tdlc",
        117: "gigabitEthernet",
        118: "hdlc",
        119: "lapf",
        120: "v37",
        121: "x25mlp",
        122: "x25huntGroup",
        123: "trasnpHdlc",
        124: "interleave",
        125: "fast",
        126: "ip",
        127: "docsCableMaclayer",
        128: "docsCableDownstream",
        129: "docsCableUpstream",
        130: "a12MppSwitch",
        131: "tunnel",
        132: "coffee",
        133: "ces",
        134: "atmSubInterface",
        135: "l2vlan",
        136: "l3ipvlan",
        137: "l3ipxvlan",
        138: "digitalPowerline",
        139: "mediaMailOverIp",
        140: "dtm",
        141: "dcn",
        142: "ipForward",
        143: "msdsl",
        144: "ieee1394",
        145: "if-gsn",
        146: "dvbRccMacLayer",
        147: "dvbRccDownstream",
        148: "dvbRccUpstream",
        149: "atmVirtual",
        150: "mplsTunnel",
        151: "srp",
        152: "voiceOverAtm",
        153: "voiceOverFrameRelay",
        154: "idsl",
        155: "compositeLink",
        156: "ss7SigLink",
        157: "propWirelessP2P",
        158: "frForward",
        159: "rfc1483",
        160: "usb",
        161: "ieee8023adLag",
        162: "bgppolicyaccounting",
        163: "frf16MfrBundle",
        164: "h323Gatekeeper",
        165: "h323Proxy",
        166: "mpls",
        167: "mfSigLink",
        168: "hdsl2",
        169: "shdsl",
        170: "ds1FDL",
        171: "pos",
        172: "dvbAsiIn",
        173: "dvbAsiOut",
        174: "plc",
        175: "nfas",
        176: "tr008",
        177: "gr303RDT",
        178: "gr303IDT",
        179: "isup",
        180: "propDocsWirelessMaclayer",
        181: "propDocsWirelessDownstream",
        182: "propDocsWirelessUpstream",
        183: "hiperlan2",
        184: "propBWAp2Mp",
        185: "sonetOverheadChannel",
        186: "digitalWrapperOverheadChannel",
        187: "aal2",
        188: "radioMAC",
        189: "atmRadio",
        190: "imt",
        191: "mvl",
        192: "reachDSL",
        193: "frDlciEndPt",
        194: "atmVciEndPt",
        195: "opticalChannel",
        196: "opticalTransport",
        197: "propAtm",
        198: "voiceOverCable",
        199: "infiniband",
        200: "teLink",
        201: "q2931",
        202: "virtualTg",
        203: "sipTg",
        204: "sipSig",
        205: "docsCableUpstreamChannel",
        206: "econet",
        207: "pon155",
        208: "pon622",
        209: "bridge",
        210: "linegroup",
        211: "voiceEMFGD",
        212: "voiceFGDEANA",
        213: "voiceDID",
        214: "mpegTransport",
        215: "sixToFour",
        216: "gtp",
        217: "pdnEtherLoop1",
        218: "pdnEtherLoop2",
        219: "opticalChannelGroup",
        220: "homepna",
        221: "gfp",
        222: "ciscoISLvlan",
        223: "actelisMetaLOOP",
        224: "fcipLink",
        225: "rpr",
        226: "qam",
        227: "lmp",
        228: "cblVectaStar",
        229: "docsCableMCmtsDownstream",
        230: "adsl2",
        231: "macSecControlledIF",
        232: "macSecUncontrolledIF",
        233: "aviciOpticalEther",
        234: "atmbond",
        235: "voiceFGDOS",
        236: "mocaVersion1",
        237: "ieee80216WMAN",
        238: "adsl2plus",
        239: "dvbRcsMacLayer",
        240: "dvbTdm",
        241: "dvbRcsTdma",
        242: "x86Laps",
        243: "wwanPP",
        244: "wwanPP2",
        245: "voiceEBS",
        246: "ifPwType",
        247: "ilan",
        248: "pip",
        249: "aluELP",
        250: "gpon",
        251: "vdsl2",
        252: "capwapDot11Profile",
        253: "capwapDot11Bss",
        254: "capwapWtpVirtualRadio",
        255: "bits",
        256: "docsCableUpstreamRfPort",
        257: "cableDownstreamRfPort",
        258: "vmwareVirtualNic",
        259: "ieee802154",
        260: "otnOdu",
        261: "otnOtu",
        262: "ifVfiType",
        263: "g9981",
        264: "g9982",
        265: "g9983",
        266: "aluEpon",
        267: "aluEponOnu",
        268: "aluEponPhysicalUni",
        269: "aluEponLogicalLink",
        270: "aluGponOnu",
        271: "aluGponPhysicalUni",
        272: "vmwareNicTeam",
        277: "docsOfdmDownstream",
        278: "docsOfdmaUpstream",
        279: "gfast",
        280: "sdci",
        281: "xboxWireless",
        282: "fastdsl",
        283: "docsCableScte55d1FwdOob",
        284: "docsCableScte55d1RetOob",
        285: "docsCableScte55d2DsOob",
        286: "docsCableScte55d2UsOob",
        287: "docsCableNdf",
        288: "docsCableNdr",
        289: "ptm",
        290: "ghn",
    }
