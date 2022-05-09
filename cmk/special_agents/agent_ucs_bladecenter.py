#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import logging
import sys
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import requests
import urllib3

from cmk.utils.exceptions import MKException

from cmk.special_agents.utils import vcrtrace

ElementAttributes = Dict[str, str]

# TODO Add functionality in the future
# import cmk.utils.password_store

# Be aware of
# root = ET.fromstring(content)
# => root is false if root has no sub elements, see
#    __main__:1: FutureWarning: The behavior of this method will change in
#    future versions.  Use specific 'len(elem)' or 'elem is not None' test
#    instead.

#   .--entities------------------------------------------------------------.
#   |                             _   _ _   _                              |
#   |                   ___ _ __ | |_(_) |_(_) ___  ___                    |
#   |                  / _ \ '_ \| __| | __| |/ _ \/ __|                   |
#   |                 |  __/ | | | |_| | |_| |  __/\__ \                   |
#   |                  \___|_| |_|\__|_|\__|_|\___||___/                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'
Entry = Tuple[str, Sequence[str]]
Entities = List[Tuple[str, str, Sequence[Entry]]]

# Cisco UCS B-Series Blade Servers
B_SERIES_ENTITIES: Entities = [
    # FANS
    (
        "ucs_bladecenter_fans",
        "UCSB",
        [
            ("equipmentFan", ["Dn", "Model", "OperState"]),
            ("equipmentFanModuleStats", ["Dn", "AmbientTemp"]),
            ("equipmentNetworkElementFanStats", ["Dn", "SpeedAvg"]),
            ("equipmentRackUnitFanStats", ["Dn", "SpeedAvg"]),
            ("equipmentFanStats", ["Dn", "SpeedAvg"]),
        ],
    ),
    # PSU
    (
        "ucs_bladecenter_psu",
        "UCSB",
        [
            ("equipmentPsuInputStats", ["Dn", "Current", "PowerAvg", "Voltage"]),
            ("equipmentPsuStats", ["Dn", "AmbientTemp", "Output12vAvg", "Output3v3Avg"]),
        ],
    ),
    # NETWORK
    (
        "ucs_bladecenter_if",
        "UCSB",
        [
            # Fibrechannel
            ("fcStats", ["Dn", "BytesRx", "BytesTx", "PacketsRx", "PacketsTx", "Suspect"]),
            ("fcErrStats", ["Dn", "Rx", "Tx", "CrcRx", "DiscardRx", "DiscardTx"]),
            (
                "fabricFcSanEp",
                ["Dn", "EpDn", "AdminState", "OperState", "PortId", "SwitchId", "SlotId"],
            ),
            ("fabricFcSanPc", ["Dn", "AdminState", "OperState", "OperSpeed"]),
            (
                "fabricFcSanPcEp",
                ["Dn", "EpDn", "AdminState", "OperState", "PortId", "SwitchId", "SlotId"],
            ),
            # Errors stats. These are also used by interconnects
            (
                "etherTxStats",
                ["Dn", "TotalBytes", "UnicastPackets", "MulticastPackets", "BroadcastPackets"],
            ),
            (
                "etherRxStats",
                ["Dn", "TotalBytes", "UnicastPackets", "MulticastPackets", "BroadcastPackets"],
            ),
            ("etherErrStats", ["Dn", "OutDiscard", "Rcv"]),
            # Ethernet
            (
                "fabricEthLanEp",
                [
                    "Dn",
                    "EpDn",
                    "AdminState",
                    "OperState",
                    "AdminSpeed",
                    "PortId",
                    "SwitchId",
                    "SlotId",
                ],
            ),
            (
                "fabricEthLanPc",
                ["Dn", "AdminState", "OperState", "AdminSpeed", "OperSpeed", "Name", "PortId"],
            ),
            (
                "fabricEthLanPcEp",
                ["Dn", "EpDn", "AdminState", "OperState", "PortId", "SwitchId", "SlotId"],
            ),
            # Interconnects
            (
                "fabricDceSwSrvEp",
                ["Dn", "EpDn", "AdminState", "OperState", "PortId", "SwitchId", "SlotId"],
            ),
            ("fabricDceSwSrvPc", ["Dn", "AdminState", "OperState", "OperSpeed", "Name", "PortId"]),
            (
                "fabricDceSwSrvPcEp",
                ["Dn", "EpDn", "AdminState", "OperState", "PortId", "SwitchId", "SlotId"],
            ),
        ],
    ),
    # Fault Instances
    (
        "ucs_bladecenter_faultinst",
        "UCSB",
        [
            ("faultInst", ["Dn", "Descr", "Severity"]),
        ],
    ),
    # TopSystem Info
    (
        "ucs_bladecenter_topsystem",
        "UCSB",
        [
            ("topSystem", ["Address", "CurrentTime", "Ipv6Addr", "Mode", "Name", "SystemUpTime"]),
        ],
    ),
]

# Cisco UCS C-Series Rack Servers
C_SERIES_ENTITIES: Entities = [
    (
        "ucs_c_rack_server_fans",
        "UCSC",
        [
            (
                "equipmentFan",
                [
                    "dn",
                    "id",
                    "model",
                    "operability",
                ],
            ),
        ],
    ),
    (
        "ucs_c_rack_server_psu",
        "UCSC",
        [
            (
                "equipmentPsu",
                [
                    "dn",
                    "id",
                    "model",
                    "operability",
                    "voltage",
                ],
            ),
        ],
    ),
    (
        "ucs_c_rack_server_power",
        "UCSC",
        [
            (
                "computeMbPowerStats",
                [
                    "dn",
                    "consumedPower",
                    "inputCurrent",
                    "inputVoltage",
                ],
            ),
        ],
    ),
    (
        "ucs_c_rack_server_temp",
        "UCSC",
        [
            (
                "computeRackUnitMbTempStats",
                [
                    "dn",
                    "ambientTemp",
                    "frontTemp",
                    "ioh1Temp",
                    "ioh2Temp",
                    "rearTemp",
                ],
            ),
        ],
    ),
    (
        "ucs_c_rack_server_environment",
        "UCSC",
        [
            (
                "processorEnvStats",
                [
                    "dn",
                    "id",
                    "description",
                    "temperature",
                ],
            ),
        ],
    ),
    (
        "ucs_c_rack_server_environment",
        "UCSC",
        [
            (
                "memoryUnitEnvStats",
                [
                    "dn",
                    "id",
                    "description",
                    "temperature",
                ],
            ),
        ],
    ),
    (
        "ucs_c_rack_server_health",
        "UCSC",
        [
            (
                "storageControllerHealth",
                [
                    "dn",
                    "id",
                    "health",
                ],
            ),
        ],
    ),
    (
        "ucs_c_rack_server_topsystem",
        "UCSC",
        [
            (
                "topSystem",
                [
                    "dn",
                    "address",
                    "currentTime",
                    "mode",
                    "name",
                ],
            ),
        ],
    ),
    (
        "ucs_c_rack_server_util",
        "UCSC",
        [
            (
                "serverUtilization",
                [
                    "dn",
                    "overallUtilization",
                    "cpuUtilization",
                    "memoryUtilization",
                    "ioUtilization",
                ],
            ),
        ],
    ),
    (
        "ucs_c_rack_server_led",
        "UCSC",
        [
            (
                "equipmentIndicatorLed",
                [
                    "dn",
                    "name",
                    "color",
                    "operState",
                ],
            ),
        ],
    ),
    (
        "ucs_c_rack_server_faultinst",
        "UCSC",
        [
            (
                "faultInst",
                [
                    "severity",
                    "cause",
                    "code",
                    "descr",
                    "affectedDN",
                ],
            ),
        ],
    ),
]
SERIES_NECESSARY_SECTIONS = ["ucs_bladecenter_faultinst", "ucs_c_rack_server_faultinst"]

# .
#   .--connection----------------------------------------------------------.
#   |                                          _   _                       |
#   |           ___ ___  _ __  _ __   ___  ___| |_(_) ___  _ __            |
#   |          / __/ _ \| '_ \| '_ \ / _ \/ __| __| |/ _ \| '_ \           |
#   |         | (_| (_) | | | | | | |  __/ (__| |_| | (_) | | | |          |
#   |          \___\___/|_| |_|_| |_|\___|\___|\__|_|\___/|_| |_|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class CommunicationException(MKException):
    pass


class Server:
    def __init__(self, hostname, username, password, verify_ssl):
        self._url = "https://%s/nuova" % hostname
        self._username = username
        self._password = password
        self._session = requests.Session()
        self._verify_ssl = verify_ssl
        self._cookie = None

    def login(self):
        logging.debug("Server.login: Login")
        attributes: ElementAttributes = {
            "inName": self._username,
            "inPassword": self._password,
        }

        root = self._communicate(ET.Element("aaaLogin", attrib=attributes))
        cookie = root.attrib.get("outCookie")
        if cookie:
            logging.debug("Server.login: Found cookie")
            self._cookie = cookie

    @staticmethod
    def filter_credentials(request):
        if b"inPassword=" in request.body:
            request.body = b"login request filtered out"
        return request

    def logout(self):
        logging.debug("Server.logout: Logout")
        attributes: ElementAttributes = {}
        if self._cookie:
            attributes.update({"inCookie": self._cookie})
        self._communicate(ET.Element("aaaLogout", attrib=attributes))

    def _get_bios_unit_name_from_dn(self, xml_object) -> str:
        dn = self._get_attribute_data(xml_object, "dn")
        return "/".join(dn.split("/")[0:2])

    def get_model_info(self) -> Mapping[str, str]:
        logging.debug("Server.get_model_info: Get model info")
        return {
            self._get_bios_unit_name_from_dn(bios_unit): self._get_attribute_data(
                bios_unit, "model"
            ).split("-")[0]
            for bios_unit in self._get_class_data("biosUnit")
        }

    def get_data_from_entities(
        self, entities: Entities, model_info: Mapping[str, str]
    ) -> Dict[str, List[Tuple[Any, Any]]]:
        """
        Returns dict[k: header, v: List[Tuple[class_id, List[Tuple[attribute, attribute data]]]]]
        from entities (B_SERIES_ENTITIES, C_SERIES_ENTITIES).
        """
        logging.debug("Server.get_data_from_entities: Try to get entities")
        data: Dict[str, List[Tuple[Any, Any]]] = {}
        for header, model, entries in entities:
            for class_id, attributes in entries:
                logging.debug(
                    "Server.get_data_from_entities: header: '%s', class_id: '%s' - attributes: '%s'",
                    header,
                    class_id,
                    ",".join(attributes),
                )

                try:
                    xml_objects = self._get_class_data(class_id)
                except CommunicationException as e:
                    logging.debug("Server.get_data_from_entities: Failed to get data")
                    if debug():
                        raise CommunicationException(e)
                    continue  # skip entity

                for xml_object in xml_objects:
                    # the call _get_class_data returns Model B and C xml_objects
                    # if a class_id exists for all model types (e.g. faultInst).
                    # Only xml_object of the correct Model type may be processed.
                    bios_unit_name = self._get_bios_unit_name_from_dn(xml_object)
                    if model != model_info.get(bios_unit_name, model):
                        continue

                    xml_data = []
                    for attribute in attributes:
                        attribute_data = self._get_attribute_data(xml_object, attribute)
                        # for some versions the attribute "affectedDN" was renamed to "dn"
                        if attribute_data is None and attribute == "affectedDN":
                            attribute_data = self._get_attribute_data(xml_object, "dn")
                        if attribute_data is None:
                            logging.debug("No such attribute '%s'", attribute)
                            # ensure order of entries in related check plugins is consistent
                            attribute_data = ""
                        xml_data.append((attribute, attribute_data))
                    data.setdefault(header, []).append((class_id, xml_data))
        return data

    def _get_attribute_data(self, xml_object, attribute):
        logging.debug("Server._get_attribute_data: Try getting attribute '%s'", attribute)
        attribute_data = xml_object.attrib.get(attribute)
        if attribute_data:
            return attribute_data

        # UCS-B-Series API change, eg.:
        # 'OperState'   -> 'operState'
        # 'AmbientTemp' -> 'ambientTemp'
        attribute_lower = attribute[0].lower() + attribute[1:]
        logging.debug(
            "Server._get_attribute_data: Try getting attribute '%s' (lower)", attribute_lower
        )
        attribute_data = xml_object.attrib.get(attribute_lower)
        if attribute_data:
            return attribute_data
        return None

    def _get_class_data(self, class_id):
        """
        Returns list of XML trees for class_id or empty list in case no entries are found.
        """
        attributes: ElementAttributes = {
            "classId": class_id,
            "inHierarchical": "false",
        }
        if self._cookie:
            attributes.update({"cookie": self._cookie})
        root = self._communicate(ET.Element("configResolveClass", attrib=attributes))

        # find all entries recursivelly
        xml_objects = root.findall(".//%s" % class_id)
        logging.debug("Server._get_class_data: Entries found: '%s'", xml_objects)
        return xml_objects

    def _communicate(self, xml_obj):
        """
        Sends a XML object and returns the response as XML tree. Raises CommunicationException
        in case of any error.
        """
        # From docs:
        # https://www.cisco.com/c/en/us/td/docs/unified_computing/ucs/sw/api/b_ucs_api_book/b_ucs_api_book_chapter_01.html#r_unsuccessfulresponses
        # Do not include XML version or DOCTYPE lines in the XML API document.
        # The inName and inPassword attributes are parameters.
        # xml_string = ET.tostring(xml_obj, encoding="utf8", method="xml")
        xml_string = ET.tostring(xml_obj)
        headers = {
            "Content-Length": str(len(xml_string)),
            "Content-Type": 'text/xml; charset="utf-8"',
        }
        logging.debug("Server._communicate: Sending XML string: '%s'", xml_string)

        try:
            if self._verify_ssl is False:
                urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)
            response = self._session.post(
                self._url, headers=headers, data=xml_string, verify=self._verify_ssl
            )
        except requests.ConnectionError as e:
            logging.debug("Server._communicate: PostError: '%s'", e)
            raise CommunicationException(e)
        except Exception as e:
            logging.debug("Server._communicate: PostError (other exception): '%s'", e)
            raise CommunicationException(e)

        content = response.content
        logging.debug(
            "Server._communicate: Got response content: '%s' (%s)", content, response.status_code
        )

        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            logging.debug("Server._communicate: ParseError: '%s'", e)
            raise CommunicationException(e)

        errors = root.attrib.get("errorDescr")
        if errors:
            logging.debug("Server._communicate: Errors found: '%s'", errors)
            if debug():
                raise CommunicationException(errors)
        return root


# .
#   .--main----------------------------------------------------------------.
#   |                                       _                              |
#   |                       _ __ ___   __ _(_)_ __                         |
#   |                      | '_ ` _ \ / _` | | '_ \                        |
#   |                      | | | | | | (_| | | | | |                       |
#   |                      |_| |_| |_|\__,_|_|_| |_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def debug():
    """Do not depend on argument parsing here."""
    return "-d" in sys.argv[1:] or "--debug" in sys.argv[1:]


def parse_arguments(argv):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--vcrtrace",
        action=vcrtrace(before_record_request=Server.filter_credentials),
    )
    parser.add_argument(
        "--no-cert-check",
        action="store_true",
        help="Disables the checking of the servers ssl certificate.",
    )
    parser.add_argument("--debug", action="store_true", help="Raise Python exceptions.")
    parser.add_argument("-u", "--username", required=True, help="The username.")
    parser.add_argument("-p", "--password", required=True, help="The password.")
    parser.add_argument("hostname")
    return parser.parse_args(argv)


def setup_logging(opt_debug):
    fmt = "%(levelname)s: %(name)s: %(filename)s: %(lineno)s: %(message)s"
    if opt_debug:
        lvl = logging.DEBUG
    else:
        lvl = logging.INFO
    logging.basicConfig(level=lvl, format=fmt)


def main(args=None):
    if args is None:
        # TODO Add functionality in the future
        # cmk.utils.password_store.replace_passwords()
        args = sys.argv[1:]

    args = parse_arguments(args)
    setup_logging(args.debug)
    handle = Server(args.hostname, args.username, args.password, not args.no_cert_check)
    try:
        handle.login()
    except CommunicationException as e:
        logging.debug("Login failed: '%s'", e)
        return 1
    except Exception as e:
        logging.debug("Login failed (other exception): '%s'", e)
        return 1

    model_info: Mapping[str, str] = {}
    try:
        model_info = handle.get_model_info()
    except (CommunicationException, IndexError) as e:
        logging.debug("Failed to get model info: '%s'", e)
        handle.logout()
        return 1
    except Exception as e:
        logging.debug("Failed to get model info (other exception): '%s'", e)
        handle.logout()
        return 1

    entities: Entities = B_SERIES_ENTITIES + C_SERIES_ENTITIES

    try:
        data = handle.get_data_from_entities(entities, model_info)
    except CommunicationException as e:
        logging.debug("Failed getting entity data: '%s'", e)
        handle.logout()
        return 1
    except Exception as e:
        logging.debug("Failed getting entity data (other exception): '%s'", e)
        handle.logout()
        return 1

    # some sections should always be in agent output, even if there is no data from the server
    for section in SERIES_NECESSARY_SECTIONS:
        if section not in data:
            sys.stdout.write("<<<%s:sep(9)>>>\n" % section)

    for header, class_data in data.items():
        sys.stdout.write("<<<%s:sep(9)>>>\n" % header)
        for class_id, values in class_data:
            values_str = "\t".join(["%s %s" % v for v in values])
            sys.stdout.write("%s\t%s\n" % (class_id, values_str))

    handle.logout()
    return 0


if __name__ == "__main__":
    sys.exit(main())
