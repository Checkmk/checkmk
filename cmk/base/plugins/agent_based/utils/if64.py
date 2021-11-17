#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, List, Mapping, Optional, Union

from ..agent_based_api.v1 import exists, OIDBytes, type_defs
from . import interfaces

BASE_OID = ".1.3.6.1.2.1"

END_OIDS: List[Union[str, OIDBytes]] = [
    "2.2.1.1",  # ifIndex                      0
    "2.2.1.2",  # ifDescr                      1
    "2.2.1.3",  # ifType                       2
    "2.2.1.5",  # ifSpeed                      3
    "2.2.1.8",  # ifOperStatus                 4
    "31.1.1.1.6",  # ifHCInOctets              5
    "31.1.1.1.7",  # ifHCInUcastPkts           6
    "31.1.1.1.8",  # ifHCInMulticastPkts       7
    "31.1.1.1.9",  # ifHCInBroadcastPkts       8
    "2.2.1.13",  # ifInDiscards                9
    "2.2.1.14",  # ifInErrors                  10
    "31.1.1.1.10",  # ifHCOutOctets            11
    "31.1.1.1.11",  # ifHCOutUcastPkts         12
    "31.1.1.1.12",  # ifHCOutMulticastPkts     13
    "31.1.1.1.13",  # ifHCOutBroadcastPkts     14
    "2.2.1.19",  # ifOutDiscards               15
    "2.2.1.20",  # ifOutErrors                 16
    "2.2.1.21",  # ifOutQLen                   17
    "31.1.1.1.18",  # ifAlias                  18
    OIDBytes("2.2.1.6"),  # ifPhysAddress      19
    "31.1.1.1.15",  # ifHighSpeed              20
]

HAS_ifHCInOctets = exists(".1.3.6.1.2.1.31.1.1.1.6.*")

_PORT_TYPES = {
    "other": "1",
    "regular1822": "2",
    "hdh1822": "3",
    "ddnX25": "4",
    "rfc877x25": "5",
    "ethernetCsmacd": "6",
    "iso88023Csmacd": "7",
    "iso88024TokenBus": "8",
    "iso88025TokenRing": "9",
    "iso88026Man": "10",
    "starLan": "11",
    "proteon10Mbit": "12",
    "proteon80Mbit": "13",
    "hyperchannel": "14",
    "fddi": "15",
    "lapb": "16",
    "sdlc": "17",
    "ds1": "18",
    "e1": "19",
    "basicISDN": "20",
    "primaryISDN": "21",
    "propPointToPointSerial": "22",
    "ppp": "23",
    "softwareLoopback": "24",
    "eon": "25",
    "ethernet3Mbit": "26",
    "nsip": "27",
    "slip": "28",
    "ultra": "29",
    "ds3": "30",
    "sip": "31",
    "frameRelay": "32",
    "rs232": "33",
    "para": "34",
    "arcnet": "35",
    "arcnetPlus": "36",
    "atm": "37",
    "miox25": "38",
    "sonet": "39",
    "x25ple": "40",
    "iso88022llc": "41",
    "localTalk": "42",
    "smdsDxi": "43",
    "frameRelayService": "44",
    "v35": "45",
    "hssi": "46",
    "hippi": "47",
    "modem": "48",
    "aal5": "49",
    "sonetPath": "50",
    "sonetVT": "51",
    "smdsIcip": "52",
    "propVirtual": "53",
    "propMultiplexor": "54",
    "ieee80212": "55",
    "fibreChannel": "56",
    "hippiInterface": "57",
    "frameRelayInterconnect": "58",
    "aflane8023": "59",
    "aflane8025": "60",
    "cctEmul": "61",
    "fastEther": "62",
    "isdn": "63",
    "v11": "64",
    "v36": "65",
    "g703at64k": "66",
    "g703at2mb": "67",
    "qllc": "68",
    "fastEtherFX": "69",
    "channel": "70",
    "ieee80211": "71",
    "ibm370parChan": "72",
    "escon": "73",
    "dlsw": "74",
    "isdns": "75",
    "isdnu": "76",
    "lapd": "77",
    "ipSwitch": "78",
    "rsrb": "79",
    "atmLogical": "80",
    "ds0": "81",
    "ds0Bundle": "82",
    "bsc": "83",
    "async": "84",
    "cnr": "85",
    "iso88025Dtr": "86",
    "eplrs": "87",
    "arap": "88",
    "propCnls": "89",
    "hostPad": "90",
    "termPad": "91",
    "frameRelayMPI": "92",
    "x213": "93",
    "adsl": "94",
    "radsl": "95",
    "sdsl": "96",
    "vdsl": "97",
    "iso88025CRFPInt": "98",
    "myrinet": "99",
    "voiceEM": "100",
    "voiceFXO": "101",
    "voiceFXS": "102",
    "voiceEncap": "103",
    "voiceOverIp": "104",
    "atmDxi": "105",
    "atmFuni": "106",
    "atmIma": "107",
    "pppMultilinkBundle": "108",
    "ipOverCdlc": "109",
    "ipOverClaw": "110",
    "stackToStack": "111",
    "virtualIpAddress": "112",
    "mpc": "113",
    "ipOverAtm": "114",
    "iso88025Fiber": "115",
    "tdlc": "116",
    "gigabitEthernet": "117",
    "hdlc": "118",
    "lapf": "119",
    "v37": "120",
    "x25mlp": "121",
    "x25huntGroup": "122",
    "trasnpHdlc": "123",
    "interleave": "124",
    "fast": "125",
    "ip": "126",
    "docsCableMaclayer": "127",
    "docsCableDownstream": "128",
    "docsCableUpstream": "129",
    "a12MppSwitch": "130",
    "tunnel": "131",
    "coffee": "132",
    "ces": "133",
    "atmSubInterface": "134",
    "l2vlan": "135",
    "l3ipvlan": "136",
    "l3ipxvlan": "137",
    "digitalPowerline": "138",
    "mediaMailOverIp": "139",
    "dtm": "140",
    "dcn": "141",
    "ipForward": "142",
    "msdsl": "143",
    "ieee1394": "144",
    "if-gsn": "145",
    "dvbRccMacLayer": "146",
    "dvbRccDownstream": "147",
    "dvbRccUpstream": "148",
    "atmVirtual": "149",
    "mplsTunnel": "150",
    "srp": "151",
    "voiceOverAtm": "152",
    "voiceOverFrameRelay": "153",
    "idsl": "154",
    "compositeLink": "155",
    "ss7SigLink": "156",
    "propWirelessP2P": "157",
    "frForward": "158",
    "rfc1483": "159",
    "usb": "160",
    "ieee8023adLag": "161",
    "bgppolicyaccounting": "162",
    "frf16MfrBundle": "163",
    "h323Gatekeeper": "164",
    "h323Proxy": "165",
    "mpls": "166",
    "mfSigLink": "167",
    "hdsl2": "168",
    "shdsl": "169",
    "ds1FDL": "170",
    "pos": "171",
    "dvbAsiIn": "172",
    "dvbAsiOut": "173",
    "plc": "174",
    "nfas": "175",
    "tr008": "176",
    "gr303RDT": "177",
    "gr303IDT": "178",
    "isup": "179",
    "propDocsWirelessMaclayer": "180",
    "propDocsWirelessDownstream": "181",
    "propDocsWirelessUpstream": "182",
    "hiperlan2": "183",
    "propBWAp2Mp": "184",
    "sonetOverheadChannel": "185",
    "digitalWrapperOverheadChannel": "186",
    "aal2": "187",
    "radioMAC": "188",
    "atmRadio": "189",
    "imt": "190",
    "mvl": "191",
    "reachDSL": "192",
    "frDlciEndPt": "193",
    "atmVciEndPt": "194",
    "opticalChannel": "195",
    "opticalTransport": "196",
    "propAtm": "197",
    "voiceOverCable": "198",
    "infiniband": "199",
    "teLink": "200",
    "q2931": "201",
    "virtualTg": "202",
    "sipTg": "203",
    "sipSig": "204",
    "docsCableUpstreamChannel": "205",
    "econet": "206",
    "pon155": "207",
    "pon622": "208",
    "bridge": "209",
    "linegroup": "210",
    "voiceEMFGD": "211",
    "voiceFGDEANA": "212",
    "voiceDID": "213",
    "mpegTransport": "214",
    "sixToFour": "215",
    "gtp": "216",
    "pdnEtherLoop1": "217",
    "pdnEtherLoop2": "218",
    "opticalChannelGroup": "219",
    "homepna": "220",
    "gfp": "221",
    "ciscoISLvlan": "222",
    "actelisMetaLOOP": "223",
    "fcipLink": "224",
    "rpr": "225",
    "qam": "226",
    "lmp": "227",
    "cblVectaStar": "228",
    "docsCableMCmtsDownstream": "229",
    "adsl2": "230",
}

_STATUS_NAMES = {
    "up": "1",
    "down": "2",
    "testing": "3",
    "unknown": "4",
    "dormant": "5",
    "not present": "6",
    "lower layer down": "7",
    "degraded": "8",
}


def _convert_type(if_type: str) -> str:
    try:
        int(if_type)
    except ValueError:
        return str(_PORT_TYPES.get(if_type, "1"))
    else:
        return if_type


def _convert_status(if_status: str) -> str:
    try:
        int(if_status)
    except ValueError:
        return str(_STATUS_NAMES.get(if_status, "4"))
    else:
        return if_status


def fix_if_64_highspeed(highspeed: str) -> str:
    return str(interfaces.saveint(highspeed) * 1000000)


def port_mapping(name, port_map: Mapping[str, str]) -> Optional[str]:
    return (
        f"maps to {port_map.get(name, '')}"
        if name in port_map
        else f"belongs to {' and '.join(k for k, v in port_map.items() if v == name)}"
        if name in port_map.values()
        else None
    )


def generic_parse_if64(
    string_table: type_defs.StringByteTable,
    port_map: Optional[Mapping[str, str]] = None,
) -> interfaces.Section:
    return [
        interfaces.Interface(
            index=str(line[0]),
            descr=str(line[1]),
            type=str(line[2]),
            speed=interfaces.saveint(line[3]),
            oper_status=str(line[4]),
            in_octets=interfaces.saveint(line[5]),
            in_ucast=interfaces.saveint(line[6]),
            in_mcast=interfaces.saveint(line[7]),
            in_bcast=interfaces.saveint(line[8]),
            in_discards=interfaces.saveint(line[9]),
            in_errors=interfaces.saveint(line[10]),
            out_octets=interfaces.saveint(line[11]),
            out_ucast=interfaces.saveint(line[12]),
            out_mcast=interfaces.saveint(line[13]),
            out_bcast=interfaces.saveint(line[14]),
            out_discards=interfaces.saveint(line[15]),
            out_errors=interfaces.saveint(line[16]),
            out_qlen=interfaces.saveint(line[17]),
            alias=str(line[18]),
            phys_address=line[19],
            extra_info=port_mapping(line[1], port_map) if port_map else None,
        )
        for line in string_table
    ]


def parse_if64(string_table: type_defs.StringByteTable) -> interfaces.Section:
    preprocessed_lines: type_defs.StringByteTable = []
    for line in string_table:
        # some DLINK switches apparently report a broken interface with index 0, filter that out
        if interfaces.saveint(line[0]) > 0:

            # ifHighSpeed can't represent interfaces with less than 10^6 bit bandwidth, ifSpeed is
            # capped at 4GBit.
            # combine the two to get the actual interface speed
            if line[20] in ["0", ""]:
                line[3] = str(interfaces.saveint(line[3]))
            else:
                line[3] = fix_if_64_highspeed(str(line[20]))

            # Fujitsu SC2 Servers do not use numeric values for port state and type
            line[2] = _convert_type(str(line[2]))
            line[4] = _convert_status(str(line[4]))

            # remove ifHighSpeed
            preprocessed_lines.append(line[:20])

    return generic_parse_if64(preprocessed_lines)


def generic_check_if64(
    item: str,
    params: Mapping[str, Any],
    section: interfaces.Section,
) -> type_defs.CheckResult:
    yield from interfaces.check_multiple_interfaces(
        item,
        params,
        section,
    )
