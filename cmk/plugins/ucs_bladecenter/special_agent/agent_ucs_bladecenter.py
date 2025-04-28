#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
>>> C_SERIES_REGEX.match("HXAF240C") is not None
True
>>> C_SERIES_REGEX.match("UCSC") is not None
True
>>> C_SERIES_REGEX.match("APIC") is not None
True
>>> B_SERIES_REGEX.match("UCSB") is not None
True
"""

import argparse
import logging
import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from typing import Any, Final

import requests
import urllib3

from cmk.ccc.exceptions import MKException

from cmk.utils.password_store import replace_passwords

from cmk.special_agents.v0_unstable.misc import vcrtrace
from cmk.special_agents.v0_unstable.request_helper import HostnameValidationAdapter

ElementAttributes = dict[str, str]

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
Entry = tuple[str, Sequence[str]]
Entities = list[tuple[str, re.Pattern[str], Sequence[Entry]]]

B_SERIES_REGEX = re.compile(r"^UCSB$")
# As of SUP-11234 hyperflex systems share the same hardware with UCSC systems.
# Those two models should be basically the same: UCSC-C240-M5SX and HXAF240C-M5SX
# 13th Nov 2023 Michael Frank (michael.frank@forvia.com)
# Added support for Cisco APIC Rackmount
C_SERIES_REGEX = re.compile(
    r"""
    ^
    (
        APIC      # apic-server-l3
        |
        UCSC      # normal, direct form
        |
        HX        # hyperflex
        (AF)?     # optional "all flash"
        [0-9]{3}  # model number
        C         # C for UCSC
    )
    $
""",
    re.VERBOSE,
)

# Cisco UCS B-Series Blade Servers
B_SERIES_ENTITIES: Entities = [
    # FANS
    (
        "ucs_bladecenter_fans",
        B_SERIES_REGEX,
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
        B_SERIES_REGEX,
        [
            ("equipmentPsuInputStats", ["Dn", "Current", "PowerAvg", "Voltage"]),
            ("equipmentPsuStats", ["Dn", "AmbientTemp", "Output12vAvg", "Output3v3Avg"]),
        ],
    ),
    # NETWORK
    (
        "ucs_bladecenter_if",
        B_SERIES_REGEX,
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
        B_SERIES_REGEX,
        [
            ("faultInst", ["Dn", "Descr", "Severity"]),
        ],
    ),
    # TopSystem Info
    (
        "ucs_bladecenter_topsystem",
        B_SERIES_REGEX,
        [
            ("topSystem", ["Address", "CurrentTime", "Ipv6Addr", "Mode", "Name", "SystemUpTime"]),
        ],
    ),
]

# Cisco UCS C-Series Rack Servers
C_SERIES_ENTITIES: Entities = [
    (
        "ucs_c_rack_server_fans",
        C_SERIES_REGEX,
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
        C_SERIES_REGEX,
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
        C_SERIES_REGEX,
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
        C_SERIES_REGEX,
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
        C_SERIES_REGEX,
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
        C_SERIES_REGEX,
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
        C_SERIES_REGEX,
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
        C_SERIES_REGEX,
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
        C_SERIES_REGEX,
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
        C_SERIES_REGEX,
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
        C_SERIES_REGEX,
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
    def __init__(
        self,
        hostname: str,
        username: str,
        password: str,
        cert_check: bool | str,
        debug: bool,
    ) -> None:
        self._url = "https://%s/nuova" % hostname
        self._username = username
        self._password = password
        self._session = requests.Session()
        self._verify_ssl = bool(cert_check)
        self._cookie: str | None = None
        self.debug: Final = debug

        if isinstance(cert_check, str):
            self._session.mount(self._url, HostnameValidationAdapter(cert_check))

    def login(self) -> None:
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

    def logout(self) -> None:
        logging.debug("Server.logout: Logout")
        attributes: ElementAttributes = {}
        if self._cookie:
            attributes.update({"inCookie": self._cookie})
        self._communicate(ET.Element("aaaLogout", attrib=attributes))

    def _get_bios_unit_name_from_dn(self, xml_object: ET.Element) -> str:
        if (dn := self._get_attribute_data(xml_object, "dn")) is None:
            raise ValueError("'dn' not found in XML object")
        return "/".join(dn.split("/")[0:2])

    def get_model_info(self) -> Mapping[str, str]:
        logging.debug("Server.get_model_info: Get model info")
        return {
            self._get_bios_unit_name_from_dn(bios_unit): value.split("-")[0]
            for bios_unit in self._get_class_data("biosUnit")
            if (value := self._get_attribute_data(bios_unit, "model")) is not None
        }

    def get_data_from_entities(
        self, entities: Entities, model_info: Mapping[str, str]
    ) -> dict[str, list[tuple[Any, Any]]]:
        """
        Returns dict[k: header, v: list[tuple[class_id, list[tuple[attribute, attribute data]]]]]
        from entities (B_SERIES_ENTITIES, C_SERIES_ENTITIES).
        """
        logging.debug("Server.get_data_from_entities: Try to get entities")
        data: dict[str, list[tuple[Any, Any]]] = {}
        for header, model_pattern, entries in entities:
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
                    if self.debug:
                        raise CommunicationException(e)
                    continue  # skip entity

                for xml_object in xml_objects:
                    # the call _get_class_data returns Model B and C xml_objects
                    # if a class_id exists for all model types (e.g. faultInst).
                    # Only xml_object of the correct Model type may be processed.
                    bios_unit_name = self._get_bios_unit_name_from_dn(xml_object)
                    if (model_prefix := model_info.get(bios_unit_name)) is not None:
                        if not model_pattern.match(model_prefix):
                            continue

                    xml_data = []
                    for attribute in attributes:
                        attribute_data = self._get_attribute_data(xml_object, attribute)
                        # for some versions the attribute "affectedDN" was renamed to "dn"
                        if attribute_data is None and attribute == "affectedDN":
                            attribute_data = self._get_attribute_data(xml_object, "dn")
                        if attribute_data is None:
                            logging.debug("No such attribute '%s'", attribute)
                            # ensure order of entries in related check plug-ins is consistent
                            attribute_data = ""
                        xml_data.append((attribute, attribute_data))
                    data.setdefault(header, []).append((class_id, xml_data))
        return data

    def _get_attribute_data(self, xml_object: ET.Element, attribute: str) -> str | None:
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
        logging.debug("Server._get_attribute_data: Try getting attribute '%s'", attribute)
        attribute_data = xml_object.attrib.get(attribute_lower)
        if attribute_data:
            return attribute_data
        logging.debug("Server._get_attribute_data: nothing found")
        return None

    def _get_class_data(self, class_id: str) -> list[ET.Element]:
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

    def _communicate(self, xml_obj: ET.Element) -> ET.Element:
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
        except Exception as e:
            logging.debug("Server._communicate: PostError: '%r'", e)
            raise

        content = response.content
        logging.debug(
            "Server._communicate: Got response content: '%s' (%s)", content, response.status_code
        )

        root = ET.fromstring(content)

        errors = root.attrib.get("errorDescr")
        if errors:
            logging.debug("Server._communicate: Errors found: '%s'", errors)
            if self.debug:
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


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--vcrtrace",
        action=vcrtrace(before_record_request=Server.filter_credentials),
    )
    cert_args = parser.add_mutually_exclusive_group()
    cert_args.add_argument(
        "--no-cert-check", action="store_true", help="Do not verify TLS certificate"
    )
    cert_args.add_argument(
        "--cert-server-name",
        help="Use this server name for TLS certificate validation.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Be more verbose in logging.")
    parser.add_argument("-d", "--debug", action="store_true", help="Raise python exceptions.")
    parser.add_argument("-u", "--username", required=True, help="The username.")
    parser.add_argument("-p", "--password", required=True, help="The password.")
    parser.add_argument("hostname")
    return parser.parse_args(argv)


def setup_logging(verbose: bool) -> None:
    fmt = "%(levelname)s: %(name)s: %(filename)s: %(lineno)s: %(message)s"
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format=fmt)


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        replace_passwords()
        argv = sys.argv[1:]

    args = parse_arguments(argv)
    setup_logging(args.verbose)
    handle = Server(args.hostname, args.username, args.password, not args.no_cert_check, args.debug)
    try:
        handle.login()
    except Exception as e:
        sys.stderr.write(f"Login failed: {e!r}\n")
        if args.debug:
            raise
        return 1

    model_info: Mapping[str, str] = {}
    try:
        model_info = handle.get_model_info()
    except Exception as e:
        sys.stderr.write(f"Failed to get model info: {e!r}\n")
        handle.logout()
        if args.debug:
            raise
        return 1

    entities: Entities = B_SERIES_ENTITIES + C_SERIES_ENTITIES

    try:
        data = handle.get_data_from_entities(entities, model_info)
    except Exception as e:
        sys.stderr.write(f"Failed getting entity data: {e!r}\n")
        handle.logout()
        if args.debug:
            raise
        return 1

    # some sections should always be in agent output, even if there is no data from the server
    for section in SERIES_NECESSARY_SECTIONS:
        if section not in data:
            sys.stdout.write("<<<%s:sep(9)>>>\n" % section)

    for header, class_data in data.items():
        sys.stdout.write("<<<%s:sep(9)>>>\n" % header)
        for class_id, values in class_data:
            values_str = "\t".join(["%s %s" % v for v in values])
            sys.stdout.write(f"{class_id}\t{values_str}\n")

    handle.logout()
    return 0


if __name__ == "__main__":
    sys.exit(main())
