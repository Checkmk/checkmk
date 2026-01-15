#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Special Agent to fetch Redfish data from management interfaces"""

import json
import logging
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import urllib3
from redfish import redfish_logger  # type: ignore[import-untyped]
from redfish.rest.v1 import (  # type: ignore[import-untyped]
    HttpClient,
    InvalidCredentialsError,
    JsonDecodingError,
    redfish_client,
    RetriesExhaustedError,
    ServerDownOrUnreachableError,
)

from cmk.utils import password_store

from cmk.special_agents.v0_unstable.agent_common import (
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import (
    Args,
    create_default_argument_parser,
)

SectionName = Literal["RackPDUs", "Mains", "Outlets", "Sensors"]


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
        help="""Number of connection retries before failing""",
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
    data_list: list = []
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


def fetch_sections(
    redfishobj: HttpClient, fetching_sections: Iterable[SectionName], data: Mapping
) -> Mapping[SectionName, Any]:
    """fetch a single section of Redfish data"""
    result_set = {}
    for section in fetching_sections:
        if section not in data.keys():
            continue
        section_data = fetch_data(redfishobj, data[section].get("@odata.id"), section)
        if section_data.get("Members@odata.count") == 0:
            continue
        if "Collection" in section_data.get("@odata.type"):
            if section_data.get("Members@odata.count", 0) != 0:
                result = fetch_collection(redfishobj, section_data, section)
                result_set[section] = result
        else:
            result_set[section] = section_data
    return result_set


def process_result(
    result: Mapping[SectionName, Any],
) -> None:
    """process and output a fetched result set"""
    for key, value in result.items():
        with SectionWriter(f"redfish_{key.lower()}") as w:
            if isinstance(value, list):
                for entry in value:
                    w.append_json(entry)
            else:
                w.append_json(value)


@dataclass(frozen=True, kw_only=True)
class Vendor:
    name: str
    version: str | None
    firmware_version: str | None


def detect_vendor(root_data: Any) -> Vendor:
    """Extract Vendor information from base data"""
    vendor_string = ""
    if root_data.get("Oem"):
        if len(root_data.get("Oem")) > 0:
            vendor_string = list(root_data.get("Oem"))[0]
    if vendor_string == "" and root_data.get("Vendor") is not None:
        vendor_string = root_data.get("Vendor")

    match vendor_string:
        case "Hpe" | "Hp":
            manager_data = root_data.get("Oem", {}).get(vendor_string, {}).get("Manager", {})[0]
            if not manager_data:
                return Vendor(name="HPE", version=None, firmware_version=None)

            return Vendor(
                name="HPE",
                version=(
                    manager_data.get("ManagerType")
                    or (
                        root_data.get("Oem", {})
                        .get(vendor_string, {})
                        .get("Moniker", {})
                        .get("PRODGEN")
                    )
                ),
                firmware_version=(
                    manager_data.get("ManagerFirmwareVersion")
                    or manager_data.get("Languages", {})[0].get("Version")
                ),
            )

        case "Lenovo" | "Huawei" | "Ami" | "Supermicro" as name:
            return Vendor(name=name, version=None, firmware_version=None)

        case "Dell":
            return Vendor(name="Dell", version="iDRAC", firmware_version=None)

        case "ts_fujitsu":
            return Vendor(name="Fujitsu", version="iRMC", firmware_version=None)

        case "Cisco" | "Cisco Systems Inc.":
            return Vendor(name="Cisco", version="CIMC", firmware_version=None)

        case "Raritan":
            return Vendor(name="Raritan", version="BMC", firmware_version=None)

    # TODO: Why not use the vendor_string anyway?
    return Vendor(name="Generic", version=None, firmware_version=None)


def get_information(redfishobj):
    """get a the information from the Redfish management interface"""
    base_data = fetch_data(redfishobj, "/redfish/v1", "Base")

    vendor_data = detect_vendor(base_data)

    manager_url = base_data.get("Managers", {}).get("@odata.id")
    systems_url = base_data.get("PowerEquipment", {}).get("@odata.id")

    manager_data = []
    fw_version = vendor_data.firmware_version

    # fetch managers
    if manager_url:
        manager_col = fetch_data(redfishobj, manager_url, "Manager")
        manager_data = fetch_collection(redfishobj, manager_col, "Manager")

        for element in manager_data:
            fw_version = fw_version or element.get("FirmwareVersion")

    labels: Mapping[str, str] = {
        "cmk/os_family": "redfish",
        **({"cmk/os_name": v} if (v := vendor_data.version) else {}),
        "cmk/os_platform": vendor_data.name,
        "cmk/os_type": "redfish",
        **({"cmk/os_version": fw_version} if fw_version else {}),
    }
    sys.stdout.write("<<<labels:sep(0)>>>\n" f"{json.dumps(labels)}\n")

    # fetch systems
    systems_data = list([fetch_data(redfishobj, systems_url, "PowerEquipment")])

    if manager_data:
        with SectionWriter("redfish_manager") as w:
            w.append_json(manager_data)

    with SectionWriter("redfish_system") as w:
        w.append_json(systems_data)

    resulting_sections: tuple[SectionName, ...] = ("RackPDUs",)
    for system in systems_data:
        result = fetch_sections(redfishobj, resulting_sections, system)
        process_result(result)
        sub_sections: tuple[SectionName, ...] = ("Mains", "Outlets", "Sensors")
        pdu_data = result["RackPDUs"]
        if isinstance(pdu_data, list):
            for entry in pdu_data:
                process_result(fetch_sections(redfishobj, sub_sections, entry))
        else:
            process_result(fetch_sections(redfishobj, sub_sections, pdu_data))

    return 0


def get_session(args: Args) -> HttpClient:
    """create a Redfish session with given arguments"""
    redfish_host = f"{args.proto}://{args.host}:{args.port}"
    if args.password_id:
        pw_id, pw_path = args.password_id.split(":")
    # Create a Redfish client object
    redfishobj = redfish_client(
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
    return redfishobj


def agent_redfish_main(args: Args) -> int:
    """main function for the special agent"""

    if not args.verify_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if args.debug:
        # Config logger used by Restful library
        logger_file = "RedfishApi.log"
        logger_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logger = redfish_logger(logger_file, logger_format, logging.INFO)
        logger.info("Redfish API")

    # Start Redfish Session Object
    try:
        redfishobj = get_session(args)
    except (
        ()
        if args.debug
        else (ServerDownOrUnreachableError, RetriesExhaustedError, InvalidCredentialsError)
    ) as exc:
        sys.stderr.write(f"{_render_login_error(exc)}\n")
        return 1

    get_information(redfishobj)
    redfishobj.logout()

    return 0


def _render_login_error(
    exc: ServerDownOrUnreachableError | RetriesExhaustedError | InvalidCredentialsError,
) -> str:
    match exc:
        case ServerDownOrUnreachableError():
            return f"Server not reachable or does not support RedFish. Error Message: {exc}"
        case RetriesExhaustedError():
            return f"Too many retries for connection attempt: {exc}"

    return str(exc)


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_redfish_main)


if __name__ == "__main__":
    sys.exit(main())
