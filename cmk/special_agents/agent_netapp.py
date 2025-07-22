#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Checkmk NetApp Agent

Required user permissions
#########################

General:
 cf-status
 diagnosis-status-get
 perf-object-get-instances
 perf-object-instance-list-info-iter
 storage-shelf-environment-list-info
 system-get-info
 system-get-version

7-Mode specific:
 aggr-list-info
 disk-list-info
 license-v2-list-info
 net-ifconfig-get
 snapvault-secondary-relationship-status-list-iter-end
 snapvault-secondary-relationship-status-list-iter-next
 snapvault-secondary-relationship-status-list-iter-start
 vfiler-list-info
 volume-list-info
 quota-report

Cluster-Mode specific:
 aggr-get-iter
 fcp-adapter-get-iter
 fcp-interface-get-iter
 net-interface-get-iter
 net-port-get-iter
 snapmirror-get-iter
 storage-disk-get-iter
 storage-shelf-environment-list-info
 system-get-node-info-iter
 system-node-get-iter
 volume-get-iter
 vserver-get-iter
 quota-report-iter

Additionally you may need to make further adjustments for the Ontap 9.5:
 * Give access for HTTPs
 * Give access to ONtapi
 * Create a role for the command ''statistics' on the Ontap 9.5:
     sec log role create -role netapp-monitoring-role -cmddirname \"statistics\" -access readonly
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import warnings
from collections.abc import Iterable, Mapping, MutableMapping, Sequence
from typing import Any
from xml.dom import minidom

import requests
import urllib3

from cmk.utils.password_store import replace_passwords

from cmk.special_agents.v0_unstable.misc import vcrtrace

# pylint: disable=inconsistent-return-statements

try:
    import lxml.etree as ET
except ImportError:
    # 2.0 backwards compatibility
    import xml.etree.ElementTree as ET  # type: ignore[no-redef]

__version__ = "2.3.0p36"

USER_AGENT = f"checkmk-special-netapp-{__version__}"

COUNTERS_CLUSTERMODE_MAX_RECORDS = 500
QUERY_MAX_RECORDS = 500
COUNTERS_CLUSTERMODE_MAX_INSTANCES_PER_REQUEST = 500

Section = Iterable[str]
Query = tuple[str, Any]
Args = argparse.Namespace
LicenseInformation = MutableMapping[str, MutableMapping[str, Any]]

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# TODO: Couldn't we use create_urllib3_context() instead of this access violation?
urllib3.util.ssl_.DEFAULT_CIPHERS += ":" + ":".join(
    [
        "DH+3DES",
        "DH+HIGH",
        "ECDH+3DES",
        "ECDH+HIGH",
        "RSA+3DES",
        "RSA+HIGH",
    ]
)

# This suppress deprecated warning on older python versions
warnings.filterwarnings("ignore")


def parse_arguments(argv: Sequence[str]) -> Args:
    class Formatter(argparse.RawDescriptionHelpFormatter):
        def _get_help_string(self, action: argparse.Action) -> str | None:
            return action.help

    def positive_int(value: str) -> int:
        ivalue = int(value)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError(f"{value} is an invalid positive int value")
        return ivalue

    description, epilog = __doc__.split("\n\n", 1)  # See module's doc-string.
    parser = argparse.ArgumentParser(
        description=description.strip(),
        formatter_class=Formatter,
        epilog=epilog.lstrip(),
    )
    parser.add_argument(
        "host_address",
        help="Host name or IP address of NetApp Filer.",
    )
    parser.add_argument(
        "user",
        help="Username for NetApp login",
    )
    parser.add_argument(
        "secret",
        help="Secret/Password for NetApp login",
    )

    parser.add_argument("--vcrtrace", action=vcrtrace(filter_headers=[("authorization", "****")]))

    parser.add_argument(
        "-t",
        "--timeout",
        type=positive_int,
        default=120,
        help=(
            "Set the network timeout to the NetApp filer to TIMEOUT seconds. "
            "Note: the timeout is not only applied to the connection, but also "
            "to each individual subquery. (Default is %(default)s seconds)"
        ),
    )
    parser.add_argument(
        "--no_counters",
        nargs="*",
        type=str,
        default=[],
        choices=["volumes"],
        help=(
            "(clustermode only), skip counters for the given element. "
            'Right now only "volumes" is supported.'
        ),
    )

    parser.add_argument(
        "--xml",
        dest="dump_xml",
        action="store_true",
        help="Dump XML messages into agent output.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode: let Python exceptions come through.",
    )
    parser.add_argument(
        "--no-tls",
        action="store_true",
        help="Use http instead of https",
    )

    if not argv:
        # This is done to always print out the *full* help when no arguments are passed, not just
        # the abbreviated help which is generated by `argparse`.
        parser.print_help(sys.stderr)
        sys.exit(1)

    return parser.parse_args(argv)


def prettify(elem: ET._Element) -> str:
    rough_string = ET.tostring(elem)
    reparsed = minidom.parseString(rough_string)
    return str(reparsed.toprettyxml(indent="\t"))


class ErrorMessages:
    def __init__(self) -> None:
        self.messages: set[str] = set()

    def add_message(self, message: str) -> None:
        self.messages.add(message)

    def remove_messages(self, infix_text: str) -> None:
        new_messages = set()
        for message in self.messages:
            if infix_text in message:
                continue
            new_messages.add(message)
        self.messages = new_messages

    def format_messages(self) -> str:
        return "\n".join(self.messages)


class NetAppNode:
    def __init__(self, xml_element: ET._Element | str) -> None:
        if isinstance(xml_element, str):
            xml_element = ET.Element(xml_element)
        self.node: ET._Element = xml_element
        self.element = self

    def __getitem__(self, key: str) -> str:
        if key == "name":
            return str(self.node.tag.split("}")[-1])
        if key == "content":
            return self.node.text or ""
        raise KeyError(key)

    def __getattr__(self, what: str) -> Any:
        return object.__getattribute__(self, what)

    def child_get_string(self, what: str) -> str | None:
        for element in self.node:
            if element.tag.split("}")[-1] == what:
                return None if element.text is None else str(element.text)
        return None

    def child_get(self, what: str) -> NetAppNode | None:
        for element in self.node:
            if element.tag.split("}")[-1] == what:
                return NetAppNode(element)
        return None

    def children_get(self) -> Iterable[NetAppNode]:
        yield from map(NetAppNode, self.node)

    def append(self, element: ET._Element) -> None:
        self.node.append(element)

    def extend_attributes_list(self, new_attrs: NetAppNode) -> None:
        for child in self.node:
            if child.tag.endswith("attributes-list"):
                child.extend(new_attrs.get_node())

    def extend_instances_list(self, new_attrs: NetAppNode) -> None:
        for child in self.node:
            if child.tag.endswith("instances"):
                child.extend(new_attrs.get_node())

    def get_node(self) -> ET._Element:
        return self.node


class NetAppRootNode(NetAppNode):
    def __init__(self, vfiler: str | None) -> None:
        root_node = ET.Element(
            "netapp",
            version="1.8",
            xmlns="http://www.netapp.com/filer/admin",
            nmsdk_language="Python",
            nmsdk_version="5.2",
        )
        NetAppNode.__init__(self, root_node)
        if vfiler:
            self.node.attrib["vfiler"] = vfiler


# NetApp Response Oject, holds the actual content in the NetAppNode member variable
class NetAppResponse:
    # We have seen devices (NetApp Release 8.3.2P9) occasionally send
    # invalid XML characters, leading to an exception during parsing.
    # In that case replace them and try again.
    # According to https://www.w3.org/TR/xml/#charsets
    # these should never be in an XML output:
    INVALID_XML = re.compile(b"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]")

    def __init__(self, response: requests.Response, debug: bool) -> None:
        self.status = None
        self.content = None
        self.reason = None

        self.raw_response_text = response.text  # needed only for xml-dump

        # Check for invalid authorization
        if response.status_code == 401:
            self.status = "failed"
            self.reason = "Authorization failed"
            return

        # We except an XML answer (not HTML)
        try:
            try:
                tree = ET.fromstring(response.content)
            except ET.ParseError:
                # retry with some invalid characters replaced
                tree = ET.fromstring(NetAppResponse.INVALID_XML.sub(b"", response.content))
        except ET.ParseError as exc:
            if debug:
                raise
            self.status = "parse-exception"
            self.reason = str(exc)
            return

        self.content = NetAppNode(tree)

        results = self.content.child_get("results")
        assert results
        self.status = str(results.node.attrib["status"])
        if self.status != "passed":
            self.reason = str(results.node.attrib["reason"])

    def results_status(self) -> str | None:
        return self.status

    def results_reason(self) -> str | None:
        return self.reason

    def get_results(self) -> NetAppNode:
        if self.content is None:
            raise RuntimeError("Response has no content")
        if (results := self.content.child_get("results")) is None:
            raise RuntimeError("Response has no results")
        return results


class NetAppConnection:
    def __init__(
        self,
        hostname: str,
        user: str,
        password: str,
        no_tls: bool,
        timeout: int,
        *,
        debug: bool = False,
        dump_xml: bool = False,
    ) -> None:
        self.url = (
            f"{'http' if no_tls else 'https'}://{hostname}"
            "/servlets/netapp.servlets.admin.XMLrequest_filer"
        )
        self.user = user
        self.password = password
        self.timeout = timeout
        self.vfiler: str | None = None

        self.status = None
        self.error_messages = ErrorMessages()
        self.suppress_errors = False

        self.headers = {}
        self.headers["Content-type"] = 'text/xml; charset="UTF-8"'
        self.headers["User-Agent"] = USER_AGENT
        self.session = requests.Session()
        self.debug = debug
        self.dump_xml = dump_xml

    def get_xml_message_from_node(self, node: ET._Element) -> str:
        return ET.tostring(node, encoding="unicode")

    def add_error_message(self, message: str) -> None:
        if not self.suppress_errors:
            self.error_messages.add_message(message)

    # Converts: ['perf-object-get-instances', [['objectname', 'nfsv3'], ['instance-uuids', [['instance-uuid', '5']]]]]
    # into a xml etree:
    #    <perf-object-get-instances>
    #        <objectname>nfsv3</objectname>
    #        <instance-uuids>
    #            <instance-uuid>5</instance-uuid>
    #        </instance-uuids>
    #    </perf-object-get-instances>
    def create_node_from_list(
        self, the_list: Query, parent_node: ET._Element | None
    ) -> ET._Element:
        name, elements = (the_list[0], the_list[1] if len(the_list) > 1 else [])
        new_node = ET.Element(name)
        for entry in elements:
            if isinstance(entry[1], (list, tuple)):
                self.create_node_from_list(entry, new_node)
            else:  # simple (key, value) pair
                ET.SubElement(new_node, entry[0]).text = entry[1]

        if parent_node is None:
            parent_node = new_node
        else:
            parent_node.append(new_node)
        return parent_node

    def get_response(self, query_content: Query) -> NetAppResponse:
        node = self.create_node_from_list(query_content, None)

        # Nodes are always enveloped in the root_node
        root_node = NetAppRootNode(vfiler=self.vfiler)
        root_node.append(node)

        request_message = self.get_xml_message_from_node(root_node.get_node())
        if self.dump_xml:
            print("######## START QUERY ########")
            print(prettify(root_node.get_node()))

        req = requests.Request(
            "POST",
            self.url,
            data=request_message,
            headers=self.headers,
            auth=(self.user, self.password),
        )
        prepped = self.session.prepare_request(req)

        # No SSL certificate check..
        response = self.session.send(prepped, timeout=self.timeout, verify=False)

        netapp_response = NetAppResponse(response, self.debug)

        if self.dump_xml:
            print("######## GOT RESPONSE #######")
            if netapp_response.results_status() != "passed":
                print(
                    "Error: Unable to parse content of response:\n%s"
                    % netapp_response.results_reason()
                )
                if netapp_response.results_status() == "parse-exception":
                    print("Raw response text:\n%r" % netapp_response.raw_response_text)
            else:
                results = netapp_response.get_results()
                print(prettify(results.get_node()))

        if netapp_response.results_status() != "passed":
            reason = netapp_response.results_reason()
            assert reason
            if not reason.startswith("Unable to find API"):
                self.add_error_message(
                    f"Querying class {node.tag}: {netapp_response.results_reason()}"
                )

        return netapp_response

    def invoke(self, *args_: str) -> NetAppNode | None:
        invoke_list = (args_[0], list(zip(args_[1::2], args_[2::2])))
        response = self.get_response(invoke_list)
        if response:
            return response.get_results()
        return None

    def set_vfiler(self, name: str) -> None:
        self.vfiler = name


def create_dict(  # pylint: disable=too-many-branches
    instances: NetAppNode | None,
    custom_key: Sequence[str] | str | None = None,
    is_counter: bool = True,
) -> MutableMapping[str, Any]:
    if custom_key is None:
        custom_key = []

    if not instances:
        return {}

    result = {}
    for instance in instances.children_get():
        values = {}
        if is_counter:
            counters = instance.child_get("counters")
            assert counters
            for node in counters.children_get():
                values[node.child_get_string("name")] = node.child_get_string("value") or ""
        else:
            for node in instance.children_get():
                values[node.element["name"]] = node.element["content"] or ""

        if custom_key:
            if isinstance(custom_key, list):
                tokens = []
                for name in custom_key:
                    tokens.append(values[name])
                key = "|".join(tokens)
            elif isinstance(custom_key, str):
                key = values[custom_key]
            else:
                assert False
        else:
            # Used to identify counters
            child_name = instance.child_get_string("name")
            assert child_name
            key = child_name

        result[key] = values
    return result


def format_config(  # pylint: disable=too-many-branches
    instances: NetAppNode,
    prefix: str,
    config_key: Sequence[str] | str,
    config_report: Sequence[str] | str = "all",
    config_scale: Mapping[str, int] | None = None,
    config_rename: Mapping[str, str] | None = None,
    extra_info: Mapping[str, Mapping[str, str]] | None = None,
    extra_info_report: Sequence[str] | str = "all",
    delimeter: str = "\t",
    skip_missing_config_key: bool = False,
) -> str:
    # Format config as one liner. Might add extra info identified by config_key

    config_scale = {} if config_scale is None else config_scale
    config_rename = {} if config_rename is None else config_rename
    extra_info = {} if extra_info is None else extra_info

    result = []
    values = {}

    def collect_values(node: NetAppNode, namespace: str = "") -> None:
        for entry in node.children_get():
            collect_values(entry, namespace + node.element["name"] + ".")

        if node.element["content"]:
            values["{}{}".format(namespace, node.element["name"])] = node.element["content"]

    for instance in instances.children_get():
        values = {}
        for node in instance.children_get():
            collect_values(node)

        line = []
        if isinstance(config_key, str):
            if skip_missing_config_key and config_key not in values:
                # The config_key is not available in the xml node
                # Looks like the information is only available through the other node
                continue

            instance_key = values.get(config_key, config_key)
            if config_key in values:
                del values[config_key]
        else:
            instance_key_list = []
            for entry in config_key:
                instance_key_list.append(values.get(entry, ""))
            instance_key = ".".join(instance_key_list)

        line.append(f"{prefix} {instance_key}")
        for key, value in values.items():
            if config_report == "all" or key in config_report:
                if key in config_scale:
                    value = str(int(value) * config_scale[key])
                key = config_rename.get(key, key)
                line.append(f"{key} {value}")

        if instance_key in extra_info:
            for key, value in extra_info[instance_key].items():
                if value and (extra_info_report == "all" or key in extra_info_report):
                    line.append(f"{key} {value}")

        result.append(("%s" % delimeter).join(line))
    return "\n".join(result)


# Format instance without subnodes as key/value lines
def format_as_key_value(
    plain_instance: NetAppNode,
    prefix: str = "",
    report: Sequence[str] | str = "all",
    delimeter: str = "\t",
) -> str:
    result = []
    for node in plain_instance.children_get():
        if report == "all" or node.element["name"] in report:
            if node.element["content"]:
                result.append(
                    "{}{}{}{}".format(
                        prefix, node.element["name"], delimeter, node.element["content"]
                    )
                )
    return "\n".join(result)


# Output a single dictionary
def format_dict(
    the_dict: Mapping[str, Any],
    prefix: str = "",
    report: Sequence[str] | str = "all",
    delimeter: str = "\t",
    as_line: bool = False,
) -> str:
    result = []

    values = {}
    for key, value in the_dict.items():
        if report == "all" or key in report:
            values[key] = value

    if as_line:
        line = []
        if prefix:
            line.append(prefix)
        for key, value in values.items():
            line.append(f"{key} {value}")
        return ("%s" % delimeter).join(line)
    for key, value in values.items():
        result.append(f"{prefix}{key}{delimeter}{value}")
    return "\n".join(result)


def output_error_section(server: NetAppConnection) -> None:
    print("<<<netapp_api_connection>>>")
    # Remove some messages which may appear on a Netapp Simulator
    server.error_messages.remove_messages(
        "storage-shelf-environment-list-info: Enclosure services scan not done"
    )
    server.error_messages.remove_messages("environment-sensors-get-iter: invalid operation")
    print(server.error_messages.format_messages())


def query_nodes(
    server: NetAppConnection,
    nodes: Sequence[str],
    what: str,
    node_attribute: str = "node-name",
) -> Mapping[str, NetAppNode]:
    results: dict[str, NetAppNode] = {}
    for node in nodes:
        ET.SubElement(ET.Element(what), node_attribute).text = node
        response = server.get_response((what, [(node_attribute, node)]))

        if response.results_status() != "passed":
            # NOTE(frans) - is this intentional?
            return {}
        value = response.get_results()
        results[f"{what}.{node}"] = value

    return results


def query(
    server: NetAppConnection,
    what: str,
    return_toplevel_node: bool = False,
) -> NetAppNode | None:
    if what.endswith("iter"):
        response = server.get_response((what, [("max-records", str(QUERY_MAX_RECORDS))]))
    else:
        response = server.get_response((what, []))

    if response.results_status() != "passed":
        return None

    results = response.get_results()
    tag_string = results.child_get_string("next-tag")
    while tag_string:
        # We need to start additinal query until all data is fetched
        tag_response = server.get_response(
            (
                what,
                [
                    ("max-records", str(QUERY_MAX_RECORDS)),
                    ("tag", tag_string),
                ],
            )
        )
        if tag_response.results_status() != "passed":
            return None
        tag_results = tag_response.get_results()
        if tag_results.child_get_string("num-records") == "0":
            break

        # Get attributes-list and add this content to the initial response
        tag_string = tag_results.child_get_string("next-tag")
        attr_children = tag_results.child_get("attributes-list")
        assert attr_children
        results.extend_attributes_list(attr_children)

    if return_toplevel_node:
        return results

    data = list(results.children_get())
    if not data:
        return None
    return data[0]


def fetch_license_information(server: NetAppConnection) -> LicenseInformation:
    # Some sections are not queried when a license is missing
    try:
        server.suppress_errors = True
        license_info = query(server, "license-list-info")
        licenses: LicenseInformation = {
            "v1": {},
            "v1_disabled": {},
            "v2": {},
            "v2_disabled": {},
        }
        if license_info:
            licenses["v1"] = create_dict(license_info, custom_key=["service"], is_counter=False)
            for license_, values in licenses["v1"].items():
                if values.get("is-licensed", "") == "false":
                    licenses["v1_disabled"][license_] = values

        # The v2 license info is not used, yet
        licensev2_info = query(server, "license-v2-list-info")
        if licensev2_info:
            licenses["v2"] = create_dict(licensev2_info, custom_key=["package"], is_counter=False)
        return licenses
    finally:
        server.suppress_errors = False


def fetch_nodes(server: NetAppConnection) -> Sequence[str]:
    # This query may fail for unknown reasons. Some clustermode systems report 0 results
    response = server.get_response(("system-get-node-info-iter", []))
    if response.results_status() == "failed":
        return []

    nodename_field = "system-name"
    results = response.get_results()
    attr_list = results.child_get("attributes-list")

    # Fallback query to determine the available node names
    if not attr_list:
        response = server.get_response(("system-node-get-iter", []))
        if response.results_status() == "failed":
            return []
        results = response.get_results()
        attr_list = results.child_get("attributes-list")
        nodename_field = "node"

    assert attr_list
    return [
        name
        for instance in attr_list.children_get()
        for name in (instance.child_get_string(nodename_field),)
        if name
    ]


def process_vserver_status(server: NetAppConnection) -> None:
    vservers = query(server, "vserver-get-iter")
    if not vservers:
        return
    vserver_dict = create_dict(vservers, custom_key=["vserver-name"], is_counter=False)
    print("<<<netapp_api_vs_status:sep(9)>>>")
    for vserver, vserver_data in vserver_dict.items():
        words = [vserver]
        for key in ("state", "vserver-subtype"):
            if vserver_data.get(key):
                words += [key, str(vserver_data[key])]
        print("\t".join(words))


def process_interfaces(
    interfaces: NetAppNode | None,
    ports: NetAppNode | None,
    if_counters: NetAppNode | None,
) -> None:
    if not interfaces:
        return

    # Gather counters-info, which is the same as if_counters but with potentially stripped keys
    # and re-applying a misspelling ('send' rather than 'sent') in order to keep metric names
    if_counters_dict = create_dict(if_counters, custom_key="instance_name")
    extra_info = {
        if_key.split(":")[-1]: {
            {
                "sent_data": "send_data",
                "sent_packet": "send_packet",
                "sent_errors": "send_errors",
            }.get(k, k): v
            for k, v in values.items()
        }
        for if_key, values in if_counters_dict.items()
    }

    # update `extra_info` for every interfaces with associated port-values if available
    interface_dict = create_dict(interfaces, custom_key="interface-name", is_counter=False)
    port_dict = create_dict(ports, custom_key=["node", "port"], is_counter=False)
    #   I didn't dare to put this here but this mapping seems to be unambigeous
    # assert all(i.get("current-node") and i.get("current-port") for i in interface_dict.values())
    # assert all(i.get("node") and i.get("port") for i in port_dict.values())
    #   note: not all ports referenced by interfaces are defined in port_dict:
    #    print(interface_dict.keys() - extra_port_info.keys())
    for port_values in port_dict.values():
        for if_key, if_values in interface_dict.items():
            if (
                if_values["current-port"] == port_values["port"]
                and if_values["current-node"] == port_values["node"]
            ):
                # Assertion has been true in all tested situations
                # assert not port_values.keys() & extra_info.setdefault(if_key, {}).keys()
                extra_info.setdefault(if_key, {}).update(port_values)

    # Gather information about failover redundancy among broadcast-groups
    # Assertion has been true in all tested situations:
    # assert all(
    #    "broadcast-domain" in port or port["port-type"] in {"physical", "if_group"}
    #    for port in port_dict.values()
    # )
    broadcast_domains: dict[str, set[str]] = {}
    for port in port_dict.values():
        if "broadcast-domain" not in port:
            continue
        broadcast_domains.setdefault(port["broadcast-domain"], set()).add(
            f"{port['node']}|{port['port']}|{port['link-status']}"
        )

    # Apply failover information to extra_info
    for name, values in interface_dict.items():
        # Assertion has been true in all tested situations:
        #  assert "failover-group" in values or values["use-failover-group"] == "disabled"
        extra_info.setdefault(name, {})["failover_ports"] = (
            ";".join(broadcast_domains[failover_group])
            if "failover-group" in values
            and (failover_group := values["failover-group"]) in broadcast_domains
            else "none"
        )

    print("<<<netapp_api_if:sep(9)>>>")
    print(
        format_config(
            interfaces,
            "interface",
            "interface-name",
            extra_info=extra_info,
            extra_info_report=[
                "recv_data",
                "send_data",
                "recv_mcasts",
                "send_mcasts",
                "recv_errors",
                "send_errors",
                "instance_name",
                "link-status",
                "operational-speed",
                "recv_packet",
                "send_packet",
                "failover_ports",
            ],
        )
    )


def process_ports(server: NetAppConnection) -> None:
    ports = query(server, "net-port-get-iter")
    if ports:
        print("<<<netapp_api_ports:sep(9)>>>")
        print(format_config(ports, "port", ["node", "port"]))


def process_cpu(server: NetAppConnection) -> None:
    # CPU Util for both nodes
    node_info = query(server, "system-get-node-info-iter")
    system_info = query(server, "system-node-get-iter")
    if node_info and system_info:
        print("<<<netapp_api_cpu:sep(9)>>>")
        print(
            format_config(
                node_info,
                "cpu-info",
                "system-name",
                config_report=["number-of-processors"],
                config_rename={"number-of-processors": "num_processors"},
            )
        )
        print(
            format_config(
                system_info,
                "cpu-info",
                "node",
                config_scale={"cpu-busytime": 1000000},
                config_report=["cpu-busytime", "nvram-battery-status"],
                config_rename={"cpu-busytime": "cpu_busy"},
            )
        )


def process_clustermode(  # pylint: disable=too-many-branches
    args: Args, server: NetAppConnection, licenses: LicenseInformation
) -> None:
    netapp_mode = "clustermode"
    nodes = fetch_nodes(server)

    process_vserver_status(server)
    process_vserver_traffic(netapp_mode, server)
    process_interfaces(
        interfaces=query(server, "net-interface-get-iter"),
        ports=query(server, "net-port-get-iter"),
        if_counters=query_counters_clustermode(server, "lif"),
    )
    process_ports(server)
    process_fibrechannel_ports(netapp_mode, server)
    process_cpu(server)

    # Cluster info
    # TODO: check is missing
    ha_partners: dict[str, str] = {}  # Used later on by environmental sensors
    if "cf" not in licenses["v1_disabled"]:
        cluster_status = query_nodes(server, nodes, "cf-status", node_attribute="node")
        if cluster_status:
            print("<<<netapp_api_cm_cluster:sep(9)>>>")
            for node, entry in cluster_status.items():
                # Small trick to improve formatting
                container = NetAppNode("container")
                container.append(entry.get_node())

                partner_name = entry.child_get_string("partner-name")
                if partner_name:
                    ha_partners[node] = partner_name
                print(format_config(container, "cluster", node.split(".", 1)[1]))

            # Systemtime for each node
            current_time = int(time.time())
            print("<<<netapp_api_systemtime:sep(9)>>>")
            for node, entry in cluster_status.items():
                node_current_time = entry.child_get_string("current-time")
                print(f"{node[10:]}\t{current_time}\t{node_current_time}")

    # Disk
    disks = query(server, "storage-disk-get-iter")
    if disks:
        print("<<<netapp_api_disk:sep(9)>>>")
        print(
            format_config(
                disks,
                "disk",
                "disk-uid",
                config_report=[
                    "disk-inventory-info.shelf-bay",
                    "disk-inventory-info.serial-number",
                    "disk-inventory-info.vendor",
                    "disk-raid-info.container-type",
                    "disk-raid-info.position",
                    "disk-raid-info.used-blocks",
                    "disk-raid-info.physical-blocks",
                ],
                config_scale={
                    "disk-raid-info.physical-blocks": 4096,
                    "disk-raid-info.used-blocks": 4096,
                },
                config_rename={
                    "disk-inventory-info.shelf-bay": "bay",
                    "disk-inventory-info.serial-number": "serial-number",
                    "disk-inventory-info.vendor": "vendor-id",
                    "disk-raid-info.container-type": "raid-state",
                    "disk-raid-info.position": "raid-type",
                    "disk-raid-info.used-blocks": "used-space",
                    "disk-raid-info.physical-blocks": "physical-space",
                },
            )
        )

    # Volumes
    volumes = query(server, "volume-get-iter")
    if "volumes" in args.no_counters:
        volume_counters = None
    else:
        volume_counters = query_counters_clustermode(server, "volume")
    if volumes:
        print("<<<netapp_api_volumes:sep(9)>>>")
        print(
            format_config(
                volumes,
                "volume",
                "volume-id-attributes.instance-uuid",
                config_report=[
                    "volume-space-attributes.size-available",
                    "volume-space-attributes.size-total",
                    "volume-space-attributes.is-space-enforcement-logical",
                    "volume-space-attributes.logical-used",
                    "volume-state-attributes.state",
                    "volume-id-attributes.owning-vserver-name",
                    "volume-id-attributes.name",
                    "volume-id-attributes.node",
                    "volume-id-attributes.msid",
                    "volume-inode-attributes.files-total",
                    "volume-inode-attributes.files-used",
                ],
                config_rename={
                    "volume-space-attributes.size-available": "size-available",
                    "volume-space-attributes.size-total": "size-total",
                    "volume-space-attributes.is-space-enforcement-logical": "is-space-enforcement-logical",
                    "volume-space-attributes.logical-used": "logical-used",
                    "volume-state-attributes.state": "state",
                    "volume-id-attributes.owning-vserver-name": "vserver_name",
                    "volume-id-attributes.name": "name",
                    "volume-id-attributes.msid": "msid",
                    "volume-id-attributes.node": "node",
                    "volume-inode-attributes.files-total": "files-total",
                    "volume-inode-attributes.files-used": "files-used",
                },
                extra_info=create_dict(volume_counters, custom_key=["instance_uuid"]),
                extra_info_report=[
                    z + y + x  #
                    for x in ["data", "latency", "ops"]  #
                    for y in ["read_", "write_"]
                    for z in ["", "nfs_", "cifs_", "san_", "fcp_", "iscsi_"]
                ]
                + ["instance_name"],
                skip_missing_config_key=True,
            )
        )

    # Aggregations
    aggregations = query(server, "aggr-get-iter")
    if aggregations:
        print("<<<netapp_api_aggr:sep(9)>>>")
        print(
            format_config(
                aggregations,
                "aggregation",
                "aggregate-name",
                config_report=[
                    "aggr-space-attributes.size-available",
                    "aggr-space-attributes.size-total",
                ],
                config_rename={
                    "aggr-space-attributes.size-available": "size-available",
                    "aggr-space-attributes.size-total": "size-total",
                },
            )
        )

    # LUNs
    luns = query(server, "lun-get-iter")
    if luns:
        print("<<<netapp_api_luns:sep(9)>>>")
        print(
            format_config(
                luns,
                "lun",
                "path",
                config_report=[
                    "size",
                    "size-used",
                    "path",
                    "online",
                    "read-only",
                    "vserver",
                    "volume",
                ],
            )
        )

    # Diagnosis status
    diag_status = query(server, "diagnosis-status-get")
    if diag_status:
        print("<<<netapp_api_status>>>")
        print(format_config(diag_status, "status", "status"))

    # NetApp System Version/Info
    system_version = query(server, "system-get-version", return_toplevel_node=True)
    system_info = query(server, "system-get-node-info-iter")
    if system_version:
        print("<<<netapp_api_info:sep(9)>>>")
        print(format_as_key_value(system_version))
        if system_info:
            child_dict = create_dict(system_info, custom_key="system-name", is_counter=False)
            for key, values in child_dict.items():
                print(format_dict(values, prefix="node %s" % key, as_line=True))

    # Snapmirror / Snapvault lag-time
    snapmirror_info = query(server, "snapmirror-get-iter")
    if snapmirror_info:
        print("<<<netapp_api_snapvault:sep(9)>>>")
        # NOTE: destination-location is used as the item name for clustermode snapvault services, as the destination
        # volume may not be unique. For 7mode installations, this has not been implemented, as we do not have a test case
        # and we do not know whether the issue exists.
        print(
            format_config(
                snapmirror_info,
                "snapvault",
                "destination-volume",
                config_report=[
                    "destination-volume-node",
                    "policy",
                    "mirror-state",
                    "source-vserver",
                    "lag-time",
                    "relationship-status",
                    "destination-location",
                ],
                config_rename={
                    "destination-volume-node": "destination-system",
                    "mirror-state": "state",
                    "source-vserver": "source-system",
                    "relationship-status": "status",
                },
            )
        )

    # Environmental sensors
    environment_info = query_nodes(server, nodes, "storage-shelf-environment-list-info")
    processed_nodes = []
    if environment_info:
        for node, values in environment_info.items():
            if node in processed_nodes:
                continue

            # HA partners always report redundant environmental data.
            # (Node1/Node2) <--Cluster--> (Node3/Node4)
            # We skip data from Node2 and Node4.
            processed_nodes.append(node)
            if node in ha_partners:
                processed_nodes.append(ha_partners[node])

            channel_list = values.child_get("shelf-environ-channel-list")
            if not channel_list:
                continue

            for channel in channel_list.children_get():  # cycle channel list
                for shelf in channel.child_get(
                    "shelf-environ-shelf-list"
                ).children_get():  # cycle shelf list
                    shelf_id = shelf.child_get_string("shelf-id")
                    for what, section in [
                        ("power-supply-list", "netapp_api_psu"),
                        ("cooling-element-list", "netapp_api_fan"),
                        ("temp-sensor-list", "netapp_api_temp"),
                    ]:
                        print("<<<%s:sep(9)>>>" % section)
                        child_node = shelf.child_get(what)
                        assert isinstance(child_node, NetAppNode)
                        print(format_config(child_node, what, shelf_id))

    # Controller Status
    environment = query(server, "environment-sensors-get-iter")
    if environment:
        print("<<<netapp_api_environment:sep(9)>>>")
        print(format_config(environment, "sensor-name", "sensor-name"))

    # Qtree quota usage
    quota_info = query(server, "quota-report-iter")
    if quota_info:
        print("<<<netapp_api_qtree_quota:sep(9)>>>")
        print(
            format_config(
                quota_info,
                "quota",
                "tree",
                config_report=[
                    "volume",
                    "tree",
                    "disk-limit",
                    "disk-used",
                    "quota-type",
                    "quota-users.quota-user.quota-user-name",
                ],
                config_rename={"quota-users.quota-user.quota-user-name": "quota-users"},
            )
        )

    # LUNs
    luns = query(server, "lun-get-iter")
    if luns:
        print("<<<netapp_api_luns:sep(9)>>>")
        print(
            format_config(
                luns,
                "lun",
                "path",
                config_report=[
                    "size",
                    "size-used",
                    "path",
                    "online",
                    "read-only",
                    "vserver",
                    "volume",
                ],
            )
        )


def process_7mode(  # pylint: disable=too-many-branches
    args: Args, server: NetAppConnection, licenses: LicenseInformation
) -> None:
    interfaces = query(server, "net-ifconfig-get")
    if_counters = query_counters_7mode(server, "ifnet")
    if interfaces:
        print("<<<netapp_api_if:sep(9)>>>")
        print(
            format_config(
                interfaces,
                "interface",
                "interface-name",
                extra_info=create_dict(if_counters),
                extra_info_report=[
                    "recv_data",
                    "send_data",
                    "recv_mcasts",
                    "send_mcasts",
                    "recv_errors",
                    "send_errors",
                    "instance_name",
                    "mediatype",
                    "recv_packet",
                    "send_packet",
                ],
            )
        )

    # TODO: Fibrechannel interfaces

    # CPU
    system_counters = query_counters_7mode(server, "system")
    if system_counters:
        print("<<<netapp_api_cpu:sep(9)>>>")
        dict_counters = create_dict(system_counters)
        print(format_dict(dict_counters.get("system", {}), report=["cpu_busy", "num_processors"]))

    # Volumes
    volumes = query(server, "volume-list-info")
    if "volumes" in args.no_counters:
        volume_counters = None
    else:
        volume_counters = query_counters_7mode(server, "volume")
    if volumes:
        print("<<<netapp_api_volumes:sep(9)>>>")
        print(
            format_config(
                volumes,
                "volume",
                "name",
                config_report=[
                    "name",
                    "volume-info",
                    "size-total",
                    "size-available",
                    "volumes",
                    "files-total",
                    "files-used",
                    "state",
                ],
                extra_info=create_dict(volume_counters),
                extra_info_report=[
                    z + y + x  #
                    for x in ["data", "latency", "ops"]  #
                    for y in ["read_", "write_"]
                    for z in ["", "nfs_", "cifs_", "san_", "fcp_", "iscsi_"]
                ]
                + ["instance_name"],
            )
        )

    # Aggregation
    aggregations = query(server, "aggr-list-info")
    if aggregations:
        print("<<<netapp_api_aggr:sep(9)>>>")
        print(
            format_config(
                aggregations,
                "aggregation",
                "name",
                config_report=["name", "size-total", "size-available"],
            )
        )

    # Snapshot info
    assert volumes
    print("<<<netapp_api_snapshots:sep(9)>>>")
    for volume in volumes.children_get():
        # Small trick improve formatting
        container = NetAppNode("container")
        container.append(volume.get_node())
        print(
            format_config(
                container,
                "volume_snapshot",
                "name",
                config_report=[
                    "name",
                    "size-total",
                    "snapshot-percent-reserved",
                    "state",
                    "snapshot-blocks-reserved",
                    "reserve-used-actual",
                ],
            )
        )

    # Protocols
    print("<<<netapp_api_protocol:sep(9)>>>")
    for what, key in [
        ("nfsv3", "nfs"),
        ("nfsv4", "nfsv4"),
        ("iscsi", "iscsi"),
        ("cifs", "cifs"),
        ("fcp", "fcp"),
    ]:
        protocol_counters = query_counters_7mode(server, what)
        if protocol_counters:
            protocol_dict = create_dict(protocol_counters)
            print(
                format_dict(
                    protocol_dict[key],
                    report=[
                        "instance_name",
                        "%s_read_ops" % what,
                        "%s_write_ops" % what,
                    ],
                    prefix="protocol %s" % key,
                    as_line=True,
                )
            )

    # Diagnosis status
    diag_status = query(server, "diagnosis-status-get")
    if diag_status:
        print("<<<netapp_api_status>>>")
        print(format_config(diag_status, "status", "status"))

    # Disks
    disk_info = query(server, "disk-list-info")
    if disk_info:
        print("<<<netapp_api_disk:sep(9)>>>")
        print(
            format_config(
                disk_info,
                "disk",
                "disk-uid",
                config_report=[
                    "raid-state",
                    "raid-type",
                    "physical-space",
                    "bay",
                    "raid-type",
                    "used-space",
                    "serial-number",
                    "disk-uid",
                    "disk-model",
                    "vendor-id",
                ],
            )
        )

    # VFiler
    vfiler_info = query(server, "vfiler-list-info")
    vfiler_names = [""]  # default is no vfiler
    if vfiler_info:
        print("<<<netapp_api_vf_status:sep(9)>>>")
        for vfiler_node in vfiler_info.children_get():
            name = vfiler_node.child_get_string("name")
            assert name
            vfiler_names.append(name)
            response = server.invoke("vfiler-get-status", "vfiler", name)
            assert response
            print("{}\t{}".format(name, response.child_get_string("status")))

    # Snapvaults
    if "sv_ontap_sec" not in licenses["v1_disabled"]:
        print("<<<netapp_api_snapvault:sep(9)>>>")
        for vfiler in vfiler_names:
            server.set_vfiler(vfiler)
            response = server.invoke("snapvault-secondary-relationship-status-list-iter-start")
            assert response
            records = response.child_get_string("records")
            if not records or records == "0":
                continue
            tag = response.child_get_string("tag")
            assert tag
            response = server.invoke(
                "snapvault-secondary-relationship-status-list-iter-next",
                "maximum",
                records,
                "tag",
                tag,
            )
            assert response
            status_list = response.child_get("status-list")
            assert status_list
            print(
                format_config(
                    status_list,
                    "snapvault",
                    "source-path",
                    config_report=[
                        "lag-time",
                        "state",
                        "status",
                        "source-system",
                        "destination-system",
                    ],
                )
            )
            server.invoke("snapvault-secondary-relationship-status-list-iter-end", "tag", tag)
        server.set_vfiler("")  # revert back to default (no) vfiler

    # Snapmirror
    for vfiler in vfiler_names + [""]:
        server.set_vfiler(vfiler)
        response = server.invoke("snapmirror-get-status")
        assert response
        data = list(response.children_get())
        if not data or len(data) == 1:
            continue
        print(
            format_config(
                data[1],
                "snapvault",
                "source-location",
                config_report=[
                    "lag-time",
                    "state",
                    "status",
                    "source-location",
                    "destination-location",
                ],
                config_rename={
                    "source-location": "source-system",
                    "destination-location": "destination-system",
                },
            )
        )
    server.set_vfiler("")

    # VFiler Counters
    vfiler_counters = query_counters_7mode(server, "vfiler")
    if vfiler_counters:
        print("<<<netapp_api_vf_stats:sep(9)>>>")
        vfiler_dict = create_dict(vfiler_counters)
        for key, values in vfiler_dict.items():
            print(format_dict(values, prefix="vfiler %s" % key, as_line=True))

    # NetApp System Version/Info
    system_info = query(server, "system-get-info")
    system_version = query(server, "system-get-version", return_toplevel_node=True)
    if system_info or system_version:
        print("<<<netapp_api_info:sep(9)>>>")
        if system_info:
            print(format_as_key_value(system_info))
        if system_version:
            print(format_as_key_value(system_version))

    # 7Mode Cluster info
    if "cf" not in licenses["v1_disabled"]:
        cluster_status = query(server, "cf-status", return_toplevel_node=True)
        if cluster_status:
            print("<<<netapp_api_cluster:sep(9)>>>")
            print(format_as_key_value(cluster_status))

            if system_info:
                system_name = system_info.child_get_string("system-name")
                print("<<<netapp_api_systemtime:sep(9)>>>")
                node_current_time = cluster_status.child_get_string("current-time")
                current_time = int(time.time())
                print(f"{system_name}\t{current_time}\t{node_current_time}")

    # Sensors: Temp, Fan, PSU
    # Definition: all sensors are always monitored by one of the filers
    # We choose this filer by an alphanumerical compare
    assert system_info
    system_name = system_info.child_get_string("system-name")
    assert system_name
    partner_system_name = system_info.child_get_string("partner-system-name")
    if not partner_system_name or system_name < partner_system_name:
        environ_info = query(server, "storage-shelf-environment-list-info")
        if environ_info:
            for channel in environ_info.children_get():
                shelf_list = channel.child_get("shelf-environ-shelf-list")
                if shelf_list:
                    for shelf in shelf_list.children_get():
                        shelf_id = shelf.child_get_string("shelf-id")
                        assert shelf_id
                        for what, section in [
                            ("power-supply-list", "netapp_api_psu"),
                            ("cooling-element-list", "netapp_api_fan"),
                            ("temp-sensor-list", "netapp_api_temp"),
                        ]:
                            print("<<<%s:sep(9)>>>" % section)
                            node = shelf.child_get(what)
                            assert node
                            print(format_config(node, what, shelf_id))

    # License information
    print("<<<netapp_api_licenses:sep(9)>>>")
    licensev2_info = query(server, "license-v2-list-info")
    if licensev2_info:
        print(format_config(licensev2_info, "license", "package"))

    # Qtree quota usage
    quota_info = query(server, "quota-report")
    if quota_info:
        print("<<<netapp_api_qtree_quota:sep(9)>>>")
        print(
            format_config(
                quota_info,
                "quota",
                "tree",
                config_report=[
                    "volume",
                    "tree",
                    "disk-limit",
                    "disk-used",
                    "quota-type",
                    "quota-users.quota-user.quota-user-name",
                ],
                config_rename={"quota-users.quota-user.quota-user-name": "quota-users"},
            )
        )


def process_mode_specific(
    netapp_mode: str,
    args: Args,
    server: NetAppConnection,
    licenses: LicenseInformation,
) -> None:
    if netapp_mode == "clustermode":
        process_clustermode(args, server, licenses)
    else:
        process_7mode(args, server, licenses)


def process_vserver_traffic(netapp_mode: str, server: NetAppConnection) -> None:
    print("<<<netapp_api_vs_traffic:sep(9)>>>")
    for what in [
        "lif:vserver",
        "fcp_lif:vserver",
        "iscsi_lif:vserver",
        "cifs:vserver",
        "nfsv3",
        "nfsv4",
        "nfsv4_1",
    ]:
        result = query_counters(netapp_mode, server, what)
        if result:
            result_dict = create_dict(result)
            for value in result_dict.values():
                print(format_dict(value, prefix="protocol %s" % what, as_line=True))


def process_fibrechannel_ports(netapp_mode: str, server: NetAppConnection) -> None:
    fcp_counters = query_counters(netapp_mode, server, "fcp_lif")
    fcp_ports = query(server, "fcp-interface-get-iter")
    fcp_adapter = query(server, "fcp-adapter-get-iter")

    if fcp_counters:
        print("<<<netapp_api_fcp:sep(9)>>>")
        port_dict = create_dict(fcp_adapter, custom_key="port-name", is_counter=False)
        fcp_counter_dict = create_dict(fcp_counters, custom_key="instance_name")

        for values in fcp_counter_dict.values():
            if values["port_wwpn"] in port_dict:
                values.update(port_dict[values["port_wwpn"]])
        assert fcp_ports
        print(format_config(fcp_ports, "fcp", "interface-name", extra_info=fcp_counter_dict))


def fetch_netapp_mode(server: NetAppConnection) -> str:
    # Determine if this filer is running 7mode or Clustermode
    version_info = query(server, "system-get-version", return_toplevel_node=True)
    assert version_info

    clustered_info = version_info.child_get_string("is-clustered")
    if clustered_info:
        return "7mode" if clustered_info.lower() == "false" else "clustermode"

    # Looks like the is-clustered attribute is not set, e.g. NetApp 7-Mode Version 8.0
    version_string = (version_info.child_get_string("version") or "").lower()
    assert version_string
    # TODO: Needs improvement. Unfortunately the version info string does not provide
    # exact info whether its a 7mode or a clustermode system
    # Possible approach: Query a class which does not exist in 7-mode and evaluate response
    if "NetApp Release 7.3.5.1".lower() in version_string:
        return "7mode"
    return "7mode" if "7-mode" in version_string else "clustermode"

    # DEBUG
    # version_info = query(server, "system-api-list")


def query_counters_clustermode(server: NetAppConnection, what: str) -> NetAppNode | None:
    response = server.get_response(
        (
            "perf-object-instance-list-info-iter",
            [
                ("objectname", what),
                ("max-records", str(COUNTERS_CLUSTERMODE_MAX_RECORDS)),
            ],
        )
    )

    results = response.get_results()
    tag_string = results.child_get_string("next-tag")
    while tag_string:
        # We need to start additinal query until all data is fetched
        tag_response = server.get_response(
            (
                "perf-object-instance-list-info-iter",
                [
                    ("objectname", what),
                    ("max-records", str(COUNTERS_CLUSTERMODE_MAX_RECORDS)),
                    ("tag", tag_string),
                ],
            )
        )
        if tag_response.results_status() != "passed":
            return None
        tag_results = tag_response.get_results()
        if tag_results.child_get_string("num-records") == "0":
            break

        # Get attributes-list and add this content to the initial response
        tag_string = tag_results.child_get_string("next-tag")
        attr_children = tag_results.child_get("attributes-list")
        assert attr_children
        results.extend_attributes_list(attr_children)

    if response.results_status() != "passed":
        return None

    instance_list = results.child_get("attributes-list")
    if not instance_list:
        return None

    instance_uuids = [
        uuid
        for instance_data in instance_list.children_get()
        for uuid in (instance_data.child_get_string("uuid"),)
        if uuid
    ]

    if not instance_uuids:
        return None  # Nothing to query..

    # I was unable to find an iterator API to query clustermode perfcounters...
    # Maybe the perf-object-get-instances is already able to provide huge amounts
    # of counter info in a single call
    responses = []
    while instance_uuids:
        uuids = []
        for idx, uuid in enumerate(instance_uuids):
            if idx >= COUNTERS_CLUSTERMODE_MAX_INSTANCES_PER_REQUEST:
                break
            uuids.append(("instance-uuid", uuid))

        perfobject_node: Query = (
            "perf-object-get-instances",
            [("objectname", what), ("instance-uuids", uuids)],
        )
        response = server.get_response(perfobject_node)

        if response.results_status() != "passed":
            return None

        responses.append(response)
        instance_uuids = instance_uuids[COUNTERS_CLUSTERMODE_MAX_INSTANCES_PER_REQUEST:]

    initial_results = responses[0].get_results()
    for response in responses[1:]:
        results = response.get_results()
        the_instances = results.child_get("instances")
        assert the_instances
        initial_results.extend_instances_list(the_instances)
    return initial_results.child_get("instances")


def query_counters_7mode(server: NetAppConnection, what: str) -> NetAppNode | None:
    perfobject_node = ("perf-object-get-instances-iter-start", [("objectname", what)])
    response = server.get_response(perfobject_node)
    results = response.get_results()
    assert results
    records = results.child_get_string("records")
    tag = results.child_get_string("tag")
    assert tag

    if not records or records == "0":
        return None

    responses: list[NetAppResponse] = []
    while records != "0":
        perfobject_node = (
            "perf-object-get-instances-iter-next",
            [("tag", tag), ("maximum", "1000")],
        )
        response = server.get_response(perfobject_node)
        results = response.get_results()
        records = results.child_get_string("records")
        responses.append(response)
        if not records or records == "0":
            perfobject_node = ("perf-object-get-instances-iter-end", [("tag", tag)])
            server.get_response(perfobject_node)
            break

    initial_results = responses[0].get_results()
    for response in responses[1:]:
        results = response.get_results()
        the_instances = results.child_get("instances")
        if the_instances:
            initial_results.extend_instances_list(the_instances)
    return initial_results.child_get("instances")


def query_counters(
    netapp_mode: str,
    server: NetAppConnection,
    what: str,
) -> NetAppNode | None:
    if netapp_mode == "clustermode":
        return query_counters_clustermode(server, what)
    return query_counters_7mode(server, what)


def netapp_session(args: Args) -> NetAppConnection:
    try:
        return NetAppConnection(
            args.host_address,
            args.user,
            args.secret,
            args.no_tls,
            args.timeout,
            debug=args.debug,
            dump_xml=args.dump_xml,
        )

    except Exception:
        if args.debug:
            raise
        sys.stderr.write(
            "Cannot connect to NetApp Server. Maybe you provided wrong "
            "credentials. Please check your connection settings and try "
            "again."
        )
        sys.exit(1)


def main() -> int:
    replace_passwords()
    args = parse_arguments(sys.argv[1:])

    session = netapp_session(args)
    try:
        netapp_mode = fetch_netapp_mode(session)
        licenses = fetch_license_information(session)

        process_mode_specific(netapp_mode, args, session, licenses)

        return 0

    except Exception as exc:
        # Shouldn't happen at all...
        session.add_error_message("Agent Exception (contact developer): %s" % exc)
        if args.debug:
            raise
        return 1
    finally:
        output_error_section(session)


if __name__ == "__main__":
    sys.exit(main())
