#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module serves constants which are needed in several components
of Check_MK."""

from typing import Dict, List, Tuple, Union

from cmk.utils.i18n import _

# TODO: Investigate Checkmk code for more defines and other places
#       where similar strucures are defined and use the things from
#       here or move new stuff to this module.


# TODO: Rename to service_state_names()
def core_state_names() -> Dict[int, str]:
    return {
        -1: _("NODATA"),
        0: _("OK"),
        1: _("WARNING"),
        2: _("CRITICAL"),
        3: _("UNKNOWN"),
    }


def service_state_name(state_num: int, deflt: str = u"") -> str:
    return core_state_names().get(state_num, deflt)


def short_service_state_names() -> Dict[int, str]:
    return {
        -1: _("PEND"),
        0: _("OK"),
        1: _("WARN"),
        2: _("CRIT"),
        3: _("UNKN"),
    }


def short_service_state_name(state_num: int, deflt: str = u"") -> str:
    return short_service_state_names().get(state_num, deflt)


def host_state_name(state_num: int, deflt: str = u"") -> str:
    states = {
        0: _("UP"),
        1: _("DOWN"),
        2: _("UNREACHABLE"),
    }
    return states.get(state_num, deflt)


def short_host_state_name(state_num: int, deflt: str = u"") -> str:
    states = {0: _("UP"), 1: _("DOWN"), 2: _("UNREACH")}
    return states.get(state_num, deflt)


def weekday_name(day_num: int) -> str:
    """Returns the human readable day name of a given weekday number (starting with 0 at Monday)"""
    return weekdays()[day_num]


def weekday_ids() -> List[str]:
    """Returns a list of the internal week day names"""
    return [d[0] for d in weekdays_by_name()]


def weekdays() -> Dict[int, str]:
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


def weekdays_by_name() -> List[Tuple[str, str]]:
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


def month_name(month_num: int) -> str:
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


def interface_oper_state_name(state_num: int, deflt: str = u"") -> str:
    return interface_oper_states().get(state_num, deflt)


# TODO: Slightly funny return type to match ListChoiceChoices. We should
# perhaps move the function to cmk.gui, so we can use the real type.
def interface_oper_states() -> Dict[Union[str, int], str]:
    return {
        1: _("up"),
        2: _("down"),
        3: _("testing"),
        4: _("unknown"),
        5: _("dormant"),
        6: _("not present"),
        7: _("lower layer down"),
        8: _("degraded"),  # artificial, not official
    }


# TODO: Slightly funny return type to match ListChoiceChoices. We should
# perhaps move the function to cmk.gui, so we can use the real type.
def interface_port_types() -> Dict[Union[str, int], str]:
    return {
        1: u"other",
        2: u"regular1822",
        3: u"hdh1822",
        4: u"ddnX25",
        5: u"rfc877x25",
        6: u"ethernetCsmacd",
        7: u"iso88023Csmacd",
        8: u"iso88024TokenBus",
        9: u"iso88025TokenRing",
        10: u"iso88026Man",
        11: u"starLan",
        12: u"proteon10Mbit",
        13: u"proteon80Mbit",
        14: u"hyperchannel",
        15: u"fddi",
        16: u"lapb",
        17: u"sdlc",
        18: u"ds1",
        19: u"e1",
        20: u"basicISDN",
        21: u"primaryISDN",
        22: u"propPointToPointSerial",
        23: u"ppp",
        24: u"softwareLoopback",
        25: u"eon",
        26: u"ethernet3Mbit",
        27: u"nsip",
        28: u"slip",
        29: u"ultra",
        30: u"ds3",
        31: u"sip",
        32: u"frameRelay",
        33: u"rs232",
        34: u"para",
        35: u"arcnet",
        36: u"arcnetPlus",
        37: u"atm",
        38: u"miox25",
        39: u"sonet",
        40: u"x25ple",
        41: u"iso88022llc",
        42: u"localTalk",
        43: u"smdsDxi",
        44: u"frameRelayService",
        45: u"v35",
        46: u"hssi",
        47: u"hippi",
        48: u"modem",
        49: u"aal5",
        50: u"sonetPath",
        51: u"sonetVT",
        52: u"smdsIcip",
        53: u"propVirtual",
        54: u"propMultiplexor",
        55: u"ieee80212",
        56: u"fibreChannel",
        57: u"hippiInterface",
        58: u"frameRelayInterconnect",
        59: u"aflane8023",
        60: u"aflane8025",
        61: u"cctEmul",
        62: u"fastEther",
        63: u"isdn",
        64: u"v11",
        65: u"v36",
        66: u"g703at64k",
        67: u"g703at2mb",
        68: u"qllc",
        69: u"fastEtherFX",
        70: u"channel",
        71: u"ieee80211",
        72: u"ibm370parChan",
        73: u"escon",
        74: u"dlsw",
        75: u"isdns",
        76: u"isdnu",
        77: u"lapd",
        78: u"ipSwitch",
        79: u"rsrb",
        80: u"atmLogical",
        81: u"ds0",
        82: u"ds0Bundle",
        83: u"bsc",
        84: u"async",
        85: u"cnr",
        86: u"iso88025Dtr",
        87: u"eplrs",
        88: u"arap",
        89: u"propCnls",
        90: u"hostPad",
        91: u"termPad",
        92: u"frameRelayMPI",
        93: u"x213",
        94: u"adsl",
        95: u"radsl",
        96: u"sdsl",
        97: u"vdsl",
        98: u"iso88025CRFPInt",
        99: u"myrinet",
        100: u"voiceEM",
        101: u"voiceFXO",
        102: u"voiceFXS",
        103: u"voiceEncap",
        104: u"voiceOverIp",
        105: u"atmDxi",
        106: u"atmFuni",
        107: u"atmIma",
        108: u"pppMultilinkBundle",
        109: u"ipOverCdlc",
        110: u"ipOverClaw",
        111: u"stackToStack",
        112: u"virtualIpAddress",
        113: u"mpc",
        114: u"ipOverAtm",
        115: u"iso88025Fiber",
        116: u"tdlc",
        117: u"gigabitEthernet",
        118: u"hdlc",
        119: u"lapf",
        120: u"v37",
        121: u"x25mlp",
        122: u"x25huntGroup",
        123: u"trasnpHdlc",
        124: u"interleave",
        125: u"fast",
        126: u"ip",
        127: u"docsCableMaclayer",
        128: u"docsCableDownstream",
        129: u"docsCableUpstream",
        130: u"a12MppSwitch",
        131: u"tunnel",
        132: u"coffee",
        133: u"ces",
        134: u"atmSubInterface",
        135: u"l2vlan",
        136: u"l3ipvlan",
        137: u"l3ipxvlan",
        138: u"digitalPowerline",
        139: u"mediaMailOverIp",
        140: u"dtm",
        141: u"dcn",
        142: u"ipForward",
        143: u"msdsl",
        144: u"ieee1394",
        145: u"if-gsn",
        146: u"dvbRccMacLayer",
        147: u"dvbRccDownstream",
        148: u"dvbRccUpstream",
        149: u"atmVirtual",
        150: u"mplsTunnel",
        151: u"srp",
        152: u"voiceOverAtm",
        153: u"voiceOverFrameRelay",
        154: u"idsl",
        155: u"compositeLink",
        156: u"ss7SigLink",
        157: u"propWirelessP2P",
        158: u"frForward",
        159: u"rfc1483",
        160: u"usb",
        161: u"ieee8023adLag",
        162: u"bgppolicyaccounting",
        163: u"frf16MfrBundle",
        164: u"h323Gatekeeper",
        165: u"h323Proxy",
        166: u"mpls",
        167: u"mfSigLink",
        168: u"hdsl2",
        169: u"shdsl",
        170: u"ds1FDL",
        171: u"pos",
        172: u"dvbAsiIn",
        173: u"dvbAsiOut",
        174: u"plc",
        175: u"nfas",
        176: u"tr008",
        177: u"gr303RDT",
        178: u"gr303IDT",
        179: u"isup",
        180: u"propDocsWirelessMaclayer",
        181: u"propDocsWirelessDownstream",
        182: u"propDocsWirelessUpstream",
        183: u"hiperlan2",
        184: u"propBWAp2Mp",
        185: u"sonetOverheadChannel",
        186: u"digitalWrapperOverheadChannel",
        187: u"aal2",
        188: u"radioMAC",
        189: u"atmRadio",
        190: u"imt",
        191: u"mvl",
        192: u"reachDSL",
        193: u"frDlciEndPt",
        194: u"atmVciEndPt",
        195: u"opticalChannel",
        196: u"opticalTransport",
        197: u"propAtm",
        198: u"voiceOverCable",
        199: u"infiniband",
        200: u"teLink",
        201: u"q2931",
        202: u"virtualTg",
        203: u"sipTg",
        204: u"sipSig",
        205: u"docsCableUpstreamChannel",
        206: u"econet",
        207: u"pon155",
        208: u"pon622",
        209: u"bridge",
        210: u"linegroup",
        211: u"voiceEMFGD",
        212: u"voiceFGDEANA",
        213: u"voiceDID",
        214: u"mpegTransport",
        215: u"sixToFour",
        216: u"gtp",
        217: u"pdnEtherLoop1",
        218: u"pdnEtherLoop2",
        219: u"opticalChannelGroup",
        220: u"homepna",
        221: u"gfp",
        222: u"ciscoISLvlan",
        223: u"actelisMetaLOOP",
        224: u"fcipLink",
        225: u"rpr",
        226: u"qam",
        227: u"lmp",
        228: u"cblVectaStar",
        229: u"docsCableMCmtsDownstream",
        230: u"adsl2",
        231: u"macSecControlledIF",
        232: u"macSecUncontrolledIF",
        233: u"aviciOpticalEther",
        234: u"atmbond",
        235: u"voiceFGDOS",
        236: u"mocaVersion1",
        237: u"ieee80216WMAN",
        238: u"adsl2plus",
        239: u"dvbRcsMacLayer",
        240: u"dvbTdm",
        241: u"dvbRcsTdma",
        242: u"x86Laps",
        243: u"wwanPP",
        244: u"wwanPP2",
        245: u"voiceEBS",
        246: u"ifPwType",
        247: u"ilan",
        248: u"pip",
        249: u"aluELP",
        250: u"gpon",
        251: u"vdsl2",
        252: u"capwapDot11Profile",
        253: u"capwapDot11Bss",
        254: u"capwapWtpVirtualRadio",
        255: u"bits",
        256: u"docsCableUpstreamRfPort",
        257: u"cableDownstreamRfPort",
        258: u"vmwareVirtualNic",
        259: u"ieee802154",
        260: u"otnOdu",
        261: u"otnOtu",
        262: u"ifVfiType",
        263: u"g9981",
        264: u"g9982",
        265: u"g9983",
        266: u"aluEpon",
        267: u"aluEponOnu",
        268: u"aluEponPhysicalUni",
        269: u"aluEponLogicalLink",
        270: u"aluGponOnu",
        271: u"aluGponPhysicalUni",
        272: u"vmwareNicTeam",
        277: u"docsOfdmDownstream",
        278: u"docsOfdmaUpstream",
        279: u"gfast",
        280: u"sdci",
        281: u"xboxWireless",
        282: u"fastdsl",
        283: u"docsCableScte55d1FwdOob",
        284: u"docsCableScte55d1RetOob",
        285: u"docsCableScte55d2DsOob",
        286: u"docsCableScte55d2UsOob",
        287: u"docsCableNdf",
        288: u"docsCableNdr",
        289: u"ptm",
        290: u"ghn",
    }
