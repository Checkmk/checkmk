#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Special Agent to fetch Redfish data from management interfaces"""

import logging
import sys
from collections.abc import Sequence
from pathlib import Path

import redfish
import urllib3
from redfish.rest.v1 import JsonDecodingError, RetriesExhaustedError, ServerDownOrUnreachableError

from cmk.utils import password_store

from cmk.special_agents.v0_unstable.agent_common import (
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import (
    Args,
    create_default_argument_parser,
)


def parse_arguments(argv: Sequence[str] | None) -> Args:
    """Parse arguments needed to construct an URL and for connection conditions"""

    parser = create_default_argument_parser(description=__doc__)
    # required
    parser.add_argument(
        "-u", "--user", default=None, help="Username for Redfish Login", required=True
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-s",
        "--password",
        default=None,
        help="""Password for Redfish Login. Preferred over --password-id""",
    )
    group.add_argument(
        "--password-id",
        default=None,
        help="""Password store reference to the password for Redfish login""",
    )
    # optional
    parser.add_argument(
        "-P",
        "--proto",
        default="https",
        help="""Use 'http' or 'https' (default=https)""",
    )
    parser.add_argument(
        "-p",
        "--port",
        default=443,
        type=int,
        help="Use alternative port (default: 443)",
    )
    parser.add_argument(
        "--verify_ssl",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--timeout",
        default=3,
        type=int,
        help="""Timeout in seconds for a connection attempt""",
    )
    parser.add_argument(
        "--retries",
        default=2,
        type=int,
        help="""Number auf connection retries before failing""",
    )
    # required
    parser.add_argument(
        "host",
        metavar="HOSTNAME",
        help="""IP address or hostname of your Redfish compatible BMC""",
    )

    return parser.parse_args(argv)


def dropnonascii(input_str):
    """Drop all non ASCII characters from string"""
    output_str = ""
    for i in input_str:
        num = ord(i)
        if num >= 0:
            if num <= 127:
                output_str = output_str + i

    return output_str


def fetch_data(redfishobj, url, component):
    """fetch a single data object from Redfish"""
    response_url = redfishobj.get(url, None)
    if response_url.status == 200:
        try:
            response_dict = response_url.dict
            return response_dict
        except JsonDecodingError:
            return {"error": f"{component} data had a JSON decoding problem\n"}

    return {"error": f"{component} data could not be fetched\n"}


def fetch_collection(redfishobj, data, component):
    """fetch a whole collection from Redfish data"""
    member_list = data.get("Members")
    data_list = []
    if not member_list:
        return data_list
    for element in member_list:
        if element.get("@odata.id"):
            element_data = fetch_data(redfishobj, element.get("@odata.id"), component)
            data_list.append(element_data)
    return data_list


def fetch_list_of_elements(redfishobj, fetch_elements, sections, data):
    """fetch a list of single elements from Redfish"""
    result_set = {}
    for element in fetch_elements:
        result_list = []
        element_list = []
        if element not in sections:
            continue
        if element not in data.keys():
            continue

        fetch_result = data.get(element)
        if isinstance(fetch_result, dict):
            element_list.append(fetch_result)
        else:
            element_list = fetch_result
        for entry in element_list:
            result = fetch_data(redfishobj, entry.get("@odata.id"), element)
            # debug output of fetching element
            # sys.stdout.write(f'Fetching {entry.get("@odata.id")}')
            if "error" in result.keys():
                continue
            if "Collection" in result.get("@odata.type", "No Data"):
                result_list.extend(fetch_collection(redfishobj, result, element))
            else:
                result_list.append(result)
        result_set[element] = result_list
    return result_set


def fetch_sections(redfishobj, fetching_sections, sections, data):
    """fetch a single section of Redfish data"""
    result_set = {}
    for section in fetching_sections:
        if section not in sections:
            continue
        if section not in data.keys():
            continue
        section_data = fetch_data(redfishobj, data.get(section).get("@odata.id"), section)
        if section_data.get("Members@odata.count") == 0:
            continue
        if "Collection" in section_data.get("@odata.type"):
            if section_data.get("Members@odata.count", 0) != 0:
                result = fetch_collection(redfishobj, section_data, section)
                result_set[section] = result
        else:
            result_set[section] = section_data
    return result_set


def process_result(result):
    """process and output a fetched result set"""
    for element in list(result.keys()):
        with SectionWriter(f"redfish_{element.lower()}") as w:
            if isinstance(result.get(element), list):
                for entry in result.get(element):
                    w.append_json(entry)
            else:
                w.append_json(result.get(element))


class VendorGeneric:
    """Generic Vendor Definition"""

    name = "Generic"
    version = None
    firmware_version = None
    view_supported = False
    view_select = None
    expand_string = ""


class VendorHPEData(VendorGeneric):
    """HPE specific settings"""

    name = "HPE"
    version = None
    firmware_version = None
    expand_string = "?$expand=."

    """
        Select and store view (supported from ILO 5)
        ATTENTION: This will only work as long as we are querying servers
        with "1" System, "1" Chassi and "1" Manager
        OK for now but will be changed once we have to query blade centers
    """
    view_supported = False
    view_select = {
        "Select": [
            {
                "From": f"/Systems/1/Memory/{expand_string}",
                "Properties": ["Members AS Memory"],
            },
            {
                "From": f"/Systems/1/Processors/{expand_string}",
                "Properties": ["Members AS Processors"],
            },
            {
                "From": f"/Systems/1/EthernetInterfaces/{expand_string}",
                "Properties": ["Members AS EthernetInterfaces"],
            },
            {
                "From": f"/Systems/1/BaseNetworkAdapters/{expand_string}",
                "Properties": ["Members AS NetworkAdapters"],
            },
            {
                "From": f"/Chassis/1/Power/{expand_string}",
                "Properties": ["PowerSupplies", "Redundancy AS PowerRedundancy"],
            },
            {"From": "/Chassis/1/Thermal/", "Properties": ["Temperatures", "Fans"]},
            {"From": f"/Managers/{expand_string}", "Properties": ["Members as ILO"]},
            {
                "From": f"/Managers/1/EthernetInterfaces/{expand_string}",
                "Properties": ["Members as ILOInterfaces"],
            },
        ]
    }
    view_response = None


class VendorLenovoData(VendorGeneric):
    """Lenovo specific settings"""

    name = "Lenovo"
    version = None
    firmware_version = None
    expand_string = "?$expand=*"


class VendorDellData(VendorGeneric):
    """Dell specific settings"""

    name = "Dell"
    version = None
    firmware_version = None
    expand_string = "?$expand=*($levels=1)"


class VendorHuaweiData(VendorGeneric):
    """Huawei specific settings"""

    name = "Huawei"
    version = None
    firmware_version = None
    expand_string = "?$expand=.%28$levels=1%29"


class VendorFujitsuData(VendorGeneric):
    """Fujitsu specific settings"""

    name = "Fujitsu"
    version = None
    firmware_version = None
    expand_string = "?$expand=Members"


class VendorCiscoData(VendorGeneric):
    """Cisco specific settings"""

    name = "Cisco"
    version = None
    firmware_version = None
    expand_string = ""


class VendorAmiData(VendorGeneric):
    """Ami specific settings"""

    name = "Ami"
    version = None
    firmware_version = None
    expand_string = ""


class VendorSupermicroData(VendorGeneric):
    """Supermicro specific settings"""

    name = "Supermicro"
    version = None
    firmware_version = None
    expand_string = ""


class VendorRaritanData(VendorGeneric):
    """Raritan specific settings"""

    name = "Raritan"
    version = None
    firmware_version = None
    expand_string = ""


def detect_vendor(root_data):  # pylint: disable=too-many-branches
    """Extract Vendor information from base data"""
    vendor_string = ""
    if root_data.get("Oem"):
        if len(root_data.get("Oem")) > 0:
            vendor_string = list(root_data.get("Oem"))[0]
    if vendor_string == "" and root_data.get("Vendor") is not None:
        vendor_string = root_data.get("Vendor")

    if vendor_string in ["Hpe", "Hp"]:
        vendor_data = VendorHPEData()
        manager_data = root_data.get("Oem", {}).get(vendor_string, {}).get("Manager", {})[0]
        if manager_data:
            vendor_data.version = manager_data.get("ManagerType")
            if vendor_data.version is None:
                vendor_data.version = (
                    root_data.get("Oem", {})
                    .get(vendor_string, {})
                    .get("Moniker", {})
                    .get("PRODGEN")
                )
            vendor_data.firmware_version = manager_data.get("ManagerFirmwareVersion")
            if vendor_data.firmware_version is None:
                vendor_data.firmware_version = manager_data.get("Languages", {})[0].get("Version")
            if vendor_data.version.lower() == "ilo 5":
                vendor_data.view_supported = True
    elif vendor_string in ["Lenovo"]:
        vendor_data = VendorLenovoData()
    elif vendor_string in ["Dell"]:
        vendor_data = VendorDellData()
        vendor_data.version = "iDRAC"
    elif vendor_string in ["Huawei"]:
        vendor_data = VendorHuaweiData()
    elif vendor_string in ["ts_fujitsu"]:
        vendor_data = VendorFujitsuData()
        vendor_data.version = "iRMC"
    elif vendor_string in ["Ami"]:
        vendor_data = VendorAmiData()
    elif vendor_string in ["Supermicro"]:
        vendor_data = VendorSupermicroData()
    elif vendor_string in ["Cisco", "Cisco Systems Inc."]:
        vendor_data = VendorCiscoData()
        vendor_data.version = "CIMC"
    elif vendor_string in ["Raritan"]:
        vendor_data = VendorRaritanData()
        vendor_data.version = "BMC"
    else:
        vendor_data = VendorGeneric()

    return vendor_data


def get_information(redfishobj):
    """get a the information from the Redfish management interface"""
    sections = ["PowerEquipment", "RackPDUs"]
    base_data = fetch_data(redfishobj, "/redfish/v1", "Base")

    vendor_data = detect_vendor(base_data)

    manager_url = base_data.get("Managers", {}).get("@odata.id")
    systems_url = base_data.get("PowerEquipment", {}).get("@odata.id")

    manager_data = False

    # fetch managers
    if manager_url:
        manager_col = fetch_data(redfishobj, manager_url, "Manager")
        manager_data = fetch_collection(redfishobj, manager_col, "Manager")

        for element in manager_data:
            if not vendor_data.firmware_version:
                vendor_data.firmware_version = element.get("FirmwareVersion", "")

    with SectionWriter("check_mk", " ") as w:
        w.append("Version: 2.0")
        w.append(f"AgentOS: {vendor_data.version} - {vendor_data.firmware_version}")

    # fetch systems
    systems_data = list([fetch_data(redfishobj, systems_url, "PowerEquipment")])

    if manager_data:
        with SectionWriter("redfish_manager") as w:
            w.append_json(manager_data)

    with SectionWriter("redfish_system") as w:
        w.append_json(systems_data)

    systems_sections = ["RackPDUs"]

    resulting_sections = list(set(systems_sections).intersection(sections))
    for system in systems_data:
        result = fetch_sections(redfishobj, resulting_sections, sections, system)
        process_result(result)
        sub_sections = ["Mains", "Outlets", "Sensors"]
        pdu_data = result.get("RackPDUs")
        if isinstance(pdu_data, list):
            for entry in pdu_data:
                result = fetch_sections(redfishobj, sub_sections, sub_sections, entry)
                process_result(result)
        else:
            result = fetch_sections(redfishobj, sub_sections, sub_sections, pdu_data)
            process_result(result)

    return 0


def get_session(args: Args):
    """create a Redfish session with given arguments"""
    try:
        redfish_host = f"{args.proto}://{args.host}:{args.port}"
        if args.password_id:
            pw_id, pw_path = args.password_id.split(":")
        # Create a Redfish client object
        redfishobj = redfish.redfish_client(
            base_url=redfish_host,
            username=args.user,
            password=(
                args.password
                if args.password is not None
                else password_store.lookup(Path(pw_path), pw_id)
            ),
            cafile="",
            default_prefix="/redfish/v1",
            timeout=args.timeout,
            max_retry=args.retries,
        )
        redfishobj.login(auth="basic")
    except ServerDownOrUnreachableError as excp:
        sys.stderr.write(
            f"ERROR: server not reachable or does not support RedFish. Error Message: {excp}\n"
        )
        sys.exit(1)
    except RetriesExhaustedError as excp:
        sys.stderr.write(f"ERROR: too many retries for connection attempt: {excp}\n")
        sys.exit(1)
    return redfishobj


def agent_redfish_main(args: Args) -> int:
    """main function for the special agent"""

    if not args.verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if args.debug:
        # Config logger used by Restful library
        logger_file = "RedfishApi.log"
        logger_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logger = redfish.redfish_logger(logger_file, logger_format, logging.INFO)
        logger.info("Redfish API")

    # Start Redfish Session Object
    redfishobj = get_session(args)
    get_information(redfishobj)
    redfishobj.logout()

    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_redfish_main)


if __name__ == "__main__":
    sys.exit(main())
