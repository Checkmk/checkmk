#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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

import argparse
import re
import sys
import time
import warnings
from typing import Any, Dict, List
from xml.dom import minidom  # type: ignore[import]

import requests
import urllib3

from cmk.special_agents.utils import vcrtrace

# Hackish early conditional import for legacy mode
# TODO: Check whether or not we can drop this

if "--legacy" in sys.argv:
    try:
        from NaElement import NaElement  # type: ignore[import] # pylint: disable=import-error
        from NaServer import NaServer  # type: ignore[import] # pylint: disable=import-error
    except Exception as e:
        sys.stderr.write(
            "Unable to import the files NaServer.py/NaElement.py.\nThese files are "
            "provided by the NetApp Managability SDK and must be put into "
            "the sites folder ~/local/lib/python.\nDetailed error: %s\n" % e
        )
        sys.exit(1)

try:
    import lxml.etree as ET
except ImportError:
    # 2.0 backwards compatibility
    import xml.etree.ElementTree as ET  # type: ignore[no-redef]

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# TODO: Couldn't we use create_urllib3_context() instead of this access violation?
urllib3.util.ssl_.DEFAULT_CIPHERS += ":" + ":".join(  # type: ignore[attr-defined]
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

# Use this block if you want to use TLS instead of SSL authentification
# import ssl
# from functools import wraps
# def sslwrap(func):
#    @wraps(func)
#    def bar(*args, **kw):
#        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
#        return func(*args, **kw)
#    return bar
#
# ssl.wrap_socket = sslwrap(ssl.wrap_socket)


def parse_arguments(argv):
    class Formatter(argparse.RawDescriptionHelpFormatter):
        def _get_help_string(self, action):
            return action.help

    def positive_int(num):
        val = int(num)
        if val < 0:
            raise ValueError

    description, epilog = __doc__.split("\n\n", 1)  # See module's doc-string.
    parser = argparse.ArgumentParser(
        description=description.strip(), formatter_class=Formatter, epilog=epilog.lstrip()
    )
    parser.add_argument(
        "host_address",
        help="Hostname or IP-address of NetApp Filer.",
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
        "--legacy",
        action="store_true",
        help="Legacy mode with NaServer.py/NaElements.py (not configurable in Setup)",
    )

    if not argv:
        # This is done to always print out the *full* help when no arguments are passed, not just
        # the abbreviated help which is generated by `argparse`.
        parser.print_help(sys.stderr)
        sys.exit(1)

    return parser.parse_args(argv)


# .
#   .--Direct XML----------------------------------------------------------.
#   |            ____  _               _    __  ____  __ _                 |
#   |           |  _ \(_)_ __ ___  ___| |_  \ \/ /  \/  | |                |
#   |           | | | | | '__/ _ \/ __| __|  \  /| |\/| | |                |
#   |           | |_| | | | |  __/ (__| |_   /  \| |  | | |___             |
#   |           |____/|_|_|  \___|\___|\__| /_/\_\_|  |_|_____|            |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Replaces the NaServer/NaElements based legacy mode                   |
#   '----------------------------------------------------------------------'


def prettify(elem):
    rough_string = ET.tostring(elem)
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="\t")


class ErrorMessages:
    def __init__(self):
        self.messages = set()

    def add_message(self, message):
        self.messages.add(message)

    def remove_messages(self, infix_text):
        new_messages = set()
        for message in self.messages:
            if infix_text in message:
                continue
            new_messages.add(message)
        self.messages = new_messages

    def format_messages(self):
        return "\n".join(self.messages)


class NetAppConnection:
    def __init__(self, hostname, user, password):
        self.hostname = hostname
        self.user = user
        self.password = password
        self.vfiler = None

        self.status = None
        self.error_messages = ErrorMessages()
        self.suppress_errors = False

        self.headers = {}
        self.headers["Content-type"] = 'text/xml; charset="UTF-8"'
        self.session = requests.Session()
        self.debug = False

    def get_xml_message_from_node(self, node):
        return ET.tostring(node, encoding="UTF-8")

    def add_error_message(self, message):
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
    def create_node_from_list(self, the_list, parent_node):
        new_node = ET.Element(the_list[0])
        if len(the_list) > 1:
            for entry in the_list[1]:
                if isinstance(entry[1], list):
                    self.create_node_from_list(entry, new_node)
                else:  # simple (key, value) pair
                    ET.SubElement(new_node, entry[0]).text = entry[1]

        if parent_node is None:
            parent_node = new_node
        else:
            parent_node.append(new_node)
        return parent_node

    def get_response(self, query_content):
        node = self.create_node_from_list(query_content, None)

        # Nodes are always enveloped in the root_node
        root_node = NetAppRootNode(vfiler=self.vfiler)
        root_node.append(node)

        request_message = self.get_xml_message_from_node(root_node.get_node())
        if self.debug:
            print("######## START QUERY ########")
            print(prettify(root_node.get_node()))

        req = requests.Request(
            "POST",
            "https://%s/servlets/netapp.servlets.admin.XMLrequest_filer" % self.hostname,
            data=request_message,
            headers=self.headers,
            auth=(self.user, self.password),
        )
        prepped = self.session.prepare_request(req)
        # No SSL certificate check..

        response = self.session.send(prepped, verify=False)

        netapp_response = NetAppResponse(response, self.debug)

        if self.debug:
            print("######## GOT RESPONSE #######")
            if netapp_response.results_status() != "passed":
                print(
                    "Error: Unable to parse content of response:\n%s"
                    % netapp_response.results_reason()
                )
                if netapp_response.results_status() == "parse-exception":
                    print("Raw response text:\n%r" % netapp_response.raw_response_text)
            else:
                print(prettify(netapp_response.get_results().get_node()))

        if netapp_response.results_status() != "passed":
            if not netapp_response.results_reason().startswith("Unable to find API"):
                self.add_error_message(
                    "Querying class %s: %s" % (node.tag, netapp_response.results_reason())
                )

        return netapp_response

    def invoke(self, *args_):
        invoke_list = [args_[0], [list(a) for a in zip(args_[1::2], args_[2::2])]]
        response = self.get_response(invoke_list)
        if response:
            return response.get_results()
        return None

    def set_vfiler(self, name):
        self.vfiler = name


class NetAppNode:
    def __init__(self, xml_element):
        if isinstance(xml_element, str):
            xml_element = ET.Element(xml_element)
        self.node = xml_element
        self.element = self

    def __getitem__(self, what):
        if what == "name":
            return self.node.tag.split("}")[-1]
        if what == "content":
            return self.node.text or ""
        return None

    def __getattr__(self, what):
        return object.__getattribute__(self, what)

    def child_get_string(self, what):
        for element in list(self.node):
            if element.tag.split("}")[-1] == what:
                return element.text
        return None

    def child_get(self, what):
        for element in list(self.node):
            if element.tag.split("}")[-1] == what:
                return NetAppNode(element)
        return None

    def children_get(self):
        return [NetAppNode(n) for n in self.node]

    def append(self, what):
        self.node.append(what)

    def extend_attributes_list(self, new_attrs):
        for child in self.node:
            if child.tag.endswith("attributes-list"):
                child.extend(new_attrs.get_node())

    def extend_instances_list(self, new_attrs):
        for child in self.node:
            if child.tag.endswith("instances"):
                child.extend(new_attrs.get_node())

    def get_node(self):
        return self.node


class NetAppRootNode(NetAppNode):
    def __init__(self, vfiler=False):
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
    INVALID_XML = re.compile("[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]")

    def __init__(self, response, debug):
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
                tree = ET.fromstring(NetAppResponse.INVALID_XML.sub("", response.text))
        except ET.ParseError as exc:
            if debug:
                raise
            self.status = "parse-exception"
            self.reason = str(exc)
            return

        self.content = NetAppNode(tree)

        self.status = self.content.child_get("results").node.attrib["status"]
        if self.status != "passed":
            self.reason = self.content.child_get("results").node.attrib["reason"]

    def results_status(self):
        return self.status

    def results_reason(self):
        return self.reason

    def get_results(self):
        if self.content is None:
            raise Exception("no content")
        return self.content.child_get("results")


# .
#   .--Format-Fctns--------------------------------------------------------.
#   |   _____                          _        _____    _                 |
#   |  |  ___|__  _ __ _ __ ___   __ _| |_     |  ___|__| |_ _ __  ___     |
#   |  | |_ / _ \| '__| '_ ` _ \ / _` | __|____| |_ / __| __| '_ \/ __|    |
#   |  |  _| (_) | |  | | | | | | (_| | ||_____|  _| (__| |_| | | \__ \    |
#   |  |_|  \___/|_|  |_| |_| |_|\__,_|\__|    |_|  \___|\__|_| |_|___/    |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def create_dict(instances, custom_key=None, is_counter=True):
    if custom_key is None:
        custom_key = []

    if not instances:
        return {}

    result = {}
    for instance in instances.children_get():
        values = {}
        if is_counter:
            for node in instance.child_get("counters").children_get():
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
            else:
                key = values[custom_key]
        else:
            # Used to identify counters
            key = instance.child_get_string("name")
        result[key] = values
    return result


# Format config as one liner. Might add extra info identified by config_key
def format_config(
    instances,
    prefix,
    config_key,
    config_report="all",
    config_scale=None,
    config_rename=None,
    extra_info=None,
    extra_info_report="all",
    delimeter="\t",
    skip_missing_config_key=False,
):

    config_scale = {} if config_scale is None else config_scale
    config_rename = {} if config_rename is None else config_rename
    extra_info = {} if extra_info is None else extra_info

    result = []
    values = {}

    def collect_values(node, namespace=""):
        for entry in node.children_get():
            collect_values(entry, namespace + node.element["name"] + ".")

        if node.element["content"]:
            values["%s%s" % (namespace, node.element["name"])] = node.element["content"]

    if instances is None:
        return ""

    for instance in instances.children_get():
        values = {}
        for node in instance.children_get():
            collect_values(node)

        line = []
        if isinstance(config_key, list):
            instance_key_list = []
            for entry in config_key:
                instance_key_list.append(values.get(entry, ""))
            instance_key = ".".join(instance_key_list)
        else:
            if skip_missing_config_key and config_key not in values:
                # The config_key is not available in the xml node
                # Looks like the information is only available through the other node
                continue

            instance_key = values.get(config_key, config_key)
            if config_key in values:
                del values[config_key]
        line.append("%s %s" % (prefix, instance_key))
        for key, value in values.items():
            if config_report == "all" or key in config_report:
                if key in config_scale:
                    value = int(value) * config_scale[key]
                key = config_rename.get(key, key)
                line.append("%s %s" % (key, value))

        if instance_key in extra_info:
            for key, value in extra_info[instance_key].items():
                if value and (extra_info_report == "all" or key in extra_info_report):
                    line.append("%s %s" % (key, value))

        result.append(("%s" % delimeter).join(line))
    return "\n".join(result)


# Format instance without subnodes as key/value lines
def format_as_key_value(plain_instance, prefix="", report="all", delimeter="\t"):
    result = []
    for node in plain_instance.children_get():
        if report == "all" or node.element["name"] in report:
            if node.element["content"]:
                result.append(
                    "%s%s%s%s" % (prefix, node.element["name"], delimeter, node.element["content"])
                )
    return "\n".join(result)


# Output a single dictionary
def format_dict(the_dict, prefix="", report="all", delimeter="\t", as_line=False):
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
            line.append("%s %s" % (key, value))
        return ("%s" % delimeter).join(line)
    for key, value in values.items():
        result.append("%s%s%s%s" % (prefix, key, delimeter, value))
    return "\n".join(result)


# .
#   .--Query-Helpers-------------------------------------------------------.
#   |  ___                              _   _      _                       |
#   | / _ \ _   _  ___ _ __ _   _      | | | | ___| |_ __   ___ _ __ ___   |
#   || | | | | | |/ _ \ '__| | | |_____| |_| |/ _ \ | '_ \ / _ \ '__/ __|  |
#   || |_| | |_| |  __/ |  | |_| |_____|  _  |  __/ | |_) |  __/ |  \__ \  |
#   | \__\_\\__,_|\___|_|   \__, |     |_| |_|\___|_| .__/ \___|_|  |___/  |
#   |                       |___/                   |_|                    |
#   +----------------------------------------------------------------------+


def debug_node(args, node):
    if args.legacy:
        print(node.sprintf())
    else:
        print(prettify(node.get_node()))


def output_error_section(args, server):
    if args.legacy:
        print("<<<netapp_api_connection>>>")
        sys.stdout.write("\n".join(section_errors))
    else:
        print("<<<netapp_api_connection>>>")
        # Remove some messages which may appear on a Netapp Simulator
        server.error_messages.remove_messages(
            "storage-shelf-environment-list-info: Enclosure services scan not done"
        )
        server.error_messages.remove_messages("environment-sensors-get-iter: invalid operation")
        print(server.error_messages.format_messages())


def query_nodes(args, server, nodes, what, node_attribute="node-name"):
    if args.legacy:
        results = {}
        for node in nodes:
            node_query = NaElement(what)  # pylint: disable=undefined-variable
            node_query.child_add_string(node_attribute, node)
            response = server.invoke_elem(node_query)
            if response.results_status() == "failed":
                section_errors.append("In class %s: %s" % (what, response.results_reason()))
                continue

            results["%s.%s" % (what, node)] = response
    else:
        results = {}
        for node in nodes:
            what_element = ET.Element(what)
            ET.SubElement(what_element, node_attribute).text = node
            response = server.get_response([what, [[node_attribute, node]]])

            if response.results_status() != "passed":
                return None

            results["%s.%s" % (what, node)] = response.get_results()

    return results


def query(args, server, what, return_toplevel_node=False):
    if args.legacy:
        # HACK: if "what" endswith "iter", add max_records = 5000
        # This approach is way easier than reading the tag, invoke another command and merge all answers together
        # This might lead to out of memory requests. The new mechanism handles this better
        if what.endswith("iter"):
            results = server.invoke(what, "max-records", 5000)
        else:
            results = server.invoke(what)

        if results.results_status() == "failed":
            section_errors.append("In class %s: %s" % (what, results.results_reason()))
            return None
    else:
        max_records = "2000"
        if isinstance(what, str):
            if what.endswith("iter"):
                response = server.get_response([what, [["max-records", max_records]]])
            else:
                response = server.get_response([what])
        else:
            response = server.get_response(what)

        if response.results_status() != "passed":
            return None

        results = response.get_results()
        tag_string = results.child_get_string("next-tag")
        while tag_string:
            # We need to start additinal query until all data is fetched
            tag_response = server.get_response(
                [what, [["max-records", max_records], ["tag", tag_string]]]
            )
            if tag_response.results_status() != "passed":
                return None
            if tag_response.get_results().child_get_string("num-records") == "0":
                break

            # Get attributes-list and add this content to the initial response
            tag_string = tag_response.get_results().child_get_string("next-tag")
            attr_children = tag_response.get_results().child_get("attributes-list")
            results.extend_attributes_list(attr_children)

    if return_toplevel_node:
        return results
    data = results.children_get()
    if data:
        return data[0]
    return None


def query_counters(args, server, netapp_mode, what):
    instance_uuids = []
    if args.legacy:
        counter_query = NaElement("perf-object-get-instances")  # pylint: disable=undefined-variable
        counter_query.child_add_string("objectname", what)

        # In clustermode there is no "get all" command for performance counters
        # We need to determine the instance names first and add them to the query
        if netapp_mode == "clustermode":
            instance_query = NaElement(
                "perf-object-instance-list-info-iter"
            )  # pylint: disable=undefined-variable
            instance_query.child_add_string("objectname", what)

            instance_query_response = server.invoke_elem(instance_query)
            instance_list = instance_query_response.child_get("attributes-list")
            if instance_list:
                for instance_data in instance_list.children_get():
                    instance_uuids.append(instance_data.child_get_string("uuid"))
                if not instance_uuids:
                    # Nothing to query..
                    return None

                instances_to_query = NaElement(
                    "instance-uuids"
                )  # pylint: disable=undefined-variable
                for uuid in instance_uuids:
                    instances_to_query.child_add_string("instance-uuid", uuid)
                counter_query.child_add(instances_to_query)
            else:
                return None

        # Query counters
        response = server.invoke_elem(counter_query)
        if response.results_status() == "failed":
            section_errors.append("In counter %s: %s" % (what, response.results_reason()))
        else:
            return response.child_get("instances")
    else:
        if netapp_mode == "clustermode":
            max_records = "3000"
            response = server.get_response(
                [
                    "perf-object-instance-list-info-iter",
                    [["objectname", what], ["max-records", max_records]],
                ]
            )

            results = response.get_results()
            tag_string = results.child_get_string("next-tag")
            while tag_string:
                # We need to start additinal query until all data is fetched
                tag_response = server.get_response(
                    [
                        "perf-object-instance-list-info-iter",
                        [["objectname", what], ["max-records", max_records], ["tag", tag_string]],
                    ]
                )
                if tag_response.results_status() != "passed":
                    return None
                if tag_response.get_results().child_get_string("num-records") == "0":
                    break

                # Get attributes-list and add this content to the initial response
                tag_string = tag_response.get_results().child_get_string("next-tag")
                attr_children = tag_response.get_results().child_get("attributes-list")
                results.extend_attributes_list(attr_children)

            if response.results_status() != "passed":
                return None

            instance_list = results.child_get("attributes-list")
            if not instance_list:
                return None

            for instance_data in instance_list.children_get():
                instance_uuids.append(instance_data.child_get_string("uuid"))

            if not instance_uuids:
                return None  # Nothing to query..

            # I was unable to find an iterator API to query clustermode perfcounters...
            # Maybe the perf-object-get-instances is already able to provide huge amounts
            # of counter info in a single call
            responses = []
            while instance_uuids:
                max_instances_per_request = 1000
                instances_to_query = ["instance-uuids", []]
                for idx, uuid in enumerate(instance_uuids):
                    if idx >= max_instances_per_request:
                        break
                    instances_to_query[1].append(["instance-uuid", uuid])
                    perfobject_node: List[Any] = [
                        "perf-object-get-instances",
                        [["objectname", what]],
                    ]
                    perfobject_node[1].append(instances_to_query)
                response = server.get_response(perfobject_node)

                if response.results_status() != "passed":
                    return None

                responses.append(response)
                instance_uuids = instance_uuids[max_instances_per_request:]

            initial_results = responses[0].get_results()
            for response in responses[1:]:
                the_instances = response.get_results().child_get("instances")
                initial_results.extend_instances_list(the_instances)
            return initial_results.child_get("instances")
        # 7 Mode
        perfobject_node = ["perf-object-get-instances-iter-start", [["objectname", what]]]
        response = server.get_response(perfobject_node)
        results = response.get_results()
        records = results.child_get_string("records")
        tag = results.child_get_string("tag")

        if not records or records == "0":
            return None

        responses = []
        while records != "0":
            perfobject_node = [
                "perf-object-get-instances-iter-next",
                [["tag", tag], ["maximum", "1000"]],
            ]
            response = server.get_response(perfobject_node)
            results = response.get_results()
            records = results.child_get_string("records")
            responses.append(response)
            if not records or records == "0":
                perfobject_node = ["perf-object-get-instances-iter-end", [["tag", tag]]]
                server.get_response(perfobject_node)
                break

        initial_results = responses[0].get_results()
        for response in responses[1:]:
            the_instances = response.get_results().child_get("instances")
            if the_instances:
                initial_results.extend_instances_list(the_instances)
        return initial_results.child_get("instances")
    return None


def fetch_netapp_mode(args, server):
    # Determine if this filer is running 7mode or Clustermode
    version_info = query(args, server, "system-get-version", return_toplevel_node=True)

    if not version_info:
        sys.stderr.write(",".join(section_errors))
        sys.exit(1)

    clustered_info = version_info.child_get_string("is-clustered")
    if clustered_info:
        return "7mode" if clustered_info.lower() == "false" else "clustermode"

    # Looks like the is-clustered attribute is not set, e.g. NetApp 7-Mode Version 8.0
    version_string = version_info.child_get_string("version").lower()
    # TODO: Needs improvement. Unfortunately the version info string does not provide
    # exact info whether its a 7mode or a clustermode system
    # Possible approach: Query a class which does not exist in 7-mode and evaluate response
    if "NetApp Release 7.3.5.1".lower() in version_string:
        return "7mode"
    return "7mode" if "7-mode" in version_string else "clustermode"

    # DEBUG
    # version_info = query(args, server, "system-api-list")


def fetch_license_information(args, server):
    # Some sections are not queried when a license is missing
    try:
        server.suppress_errors = True
        licenses: Dict[str, Dict[str, Dict[str, str]]] = {
            "v1": {},
            "v1_disabled": {},
            "v2": {},
            "v2_disabled": {},
        }
        license_info = query(args, server, "license-list-info")
        if license_info:
            licenses["v1"] = create_dict(license_info, custom_key=["service"], is_counter=False)
            for license_, values in licenses["v1"].items():
                if values.get("is-licensed", "") == "false":
                    licenses["v1_disabled"][license_] = values

        # The v2 license info is not used, yet
        licensev2_info = query(args, server, "license-v2-list-info")
        if licensev2_info:
            licenses["v2"] = create_dict(licensev2_info, custom_key=["package"], is_counter=False)
        return licenses
    finally:
        server.suppress_errors = False


def fetch_nodes(args, server):
    nodes = []

    if args.legacy:
        node_query = NaElement("system-get-node-info-iter")  # pylint: disable=undefined-variable
        node_list = server.invoke_elem(node_query)
        for instance in node_list.child_get("attributes-list").children_get():
            nodes.append(instance.child_get_string("system-name"))
        return nodes

    # This query may fail for unknown reasons. Some clustermode systems report 0 results
    response = server.get_response(["system-get-node-info-iter", []])
    if response.results_status() == "failed":
        return []

    nodename_field = "system-name"
    attr_list = response.get_results().child_get("attributes-list")

    # Fallback query to determine the available node names
    if not attr_list:
        response = server.get_response(["system-node-get-iter", []])
        if response.results_status() == "failed":
            return []

        attr_list = response.get_results().child_get("attributes-list")
        nodename_field = "node"

    for instance in attr_list.children_get():
        nodes.append(instance.child_get_string(nodename_field))
    return nodes


def process_clustermode(args, server, netapp_mode, licenses):
    nodes = fetch_nodes(args, server)

    process_vserver_status(args, server)
    process_vserver_traffic(args, server, netapp_mode)
    process_interfaces(args, server, netapp_mode)
    process_ports(args, server, netapp_mode)
    process_fibrechannel_ports(args, server, netapp_mode)
    process_cpu(args, server)

    # Cluster info
    # TODO: check is missing
    ha_partners = {}  # Used later on by environmental sensors
    if "cf" not in licenses["v1_disabled"]:
        cluster_status = query_nodes(args, server, nodes, "cf-status", node_attribute="node")
        if cluster_status:
            print("<<<netapp_api_cm_cluster:sep(9)>>>")
            for node, entry in cluster_status.items():
                # Small trick to improve formatting
                if args.legacy:
                    container = NaElement("container")  # pylint: disable=undefined-variable
                    container.child_add(entry)
                else:
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
                print("%s\t%s\t%s" % (node[10:], current_time, node_current_time))

    # Disk
    disks = query(args, server, "storage-disk-get-iter")
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
    volumes = query(args, server, "volume-get-iter")
    if "volumes" in args.no_counters:
        volume_counters = None
    else:
        volume_counters = query_counters(args, server, netapp_mode, "volume")
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
    aggregations = query(args, server, "aggr-get-iter")
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
    luns = query(args, server, "lun-get-iter")
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
    diag_status = query(args, server, "diagnosis-status-get")
    if diag_status:
        print("<<<netapp_api_status>>>")
        print(format_config(diag_status, "status", "status"))

    # NetApp System Version/Info
    system_version = query(args, server, "system-get-version", return_toplevel_node=True)
    system_info = query(args, server, "system-get-node-info-iter")
    if system_version:
        print("<<<netapp_api_info:sep(9)>>>")
        print(format_as_key_value(system_version))
        if system_info:
            child_dict = create_dict(system_info, custom_key="system-name", is_counter=False)
            for key, values in child_dict.items():
                print(format_dict(values, prefix="node %s" % key, as_line=True))

    # Snapmirror / Snapvault lag-time
    snapmirror_info = query(args, server, "snapmirror-get-iter")
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
    environment_info = query_nodes(args, server, nodes, "storage-shelf-environment-list-info")
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
                        node = shelf.child_get(what)
                        print(format_config(node, what, shelf_id))

    # Controller Status
    environment = query(args, server, "environment-sensors-get-iter")
    if environment:
        print("<<<netapp_api_environment:sep(9)>>>")
        print(format_config(environment, "sensor-name", "sensor-name"))

    # Qtree quota usage
    quota_info = query(args, server, "quota-report-iter")
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
    luns = query(args, server, "lun-get-iter")
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


def process_vserver_status(args, server):
    vservers = query(args, server, "vserver-get-iter")
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


def process_vserver_traffic(args, server, netapp_mode):
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
        result = query_counters(args, server, netapp_mode, what)
        if result:
            result_dict = create_dict(result)
            for value in result_dict.values():
                print(format_dict(value, prefix="protocol %s" % what, as_line=True))


def process_interfaces(args, server, netapp_mode):
    interfaces = query(args, server, "net-interface-get-iter")
    ports = query(args, server, "net-port-get-iter")
    if_counters = query_counters(args, server, netapp_mode, "lif")

    if interfaces:
        print("<<<netapp_api_if:sep(9)>>>")
        extra_info = {}
        interface_dict = create_dict(interfaces, custom_key="interface-name", is_counter=False)
        port_dict = create_dict(ports, custom_key=["node", "port"], is_counter=False)
        if_counters_dict = create_dict(if_counters, custom_key="instance_name")

        # Process counters
        # NetApp clustermode reports sent_data instead of send_data..
        for key, values in if_counters_dict.items():
            for old, new in [
                ("sent_data", "send_data"),
                ("sent_packet", "send_packet"),
                ("sent_errors", "send_errors"),
            ]:
                values[new] = values[old]
                del values[old]

        extra_counter_info = {}
        for key, values in if_counters_dict.items():
            if ":" in key:
                _vserver, name = key.split(":", 1)
            else:
                name = key
            extra_counter_info[name] = values

        # Process ports
        extra_port_info = {}
        for the_port, port_values in port_dict.items():
            port_name = port_values.get("port")
            port_node = port_values.get("node")

            node, port = the_port.split("|")
            for if_key, if_values in interface_dict.items():
                port = if_values.get("current-port")
                node = if_values.get("current-node")
                if port_name == port and port_node == node:
                    extra_port_info[if_key] = port_values

        extra_info = extra_counter_info
        for key, values in extra_port_info.items():
            extra_info.setdefault(key, {})
            extra_info[key].update(values)

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
                ],
            )
        )


def process_ports(args, server, netapp_mode):
    ports = query(args, server, "net-port-get-iter")
    if ports:
        print("<<<netapp_api_ports:sep(9)>>>")
        print(format_config(ports, "port", ["node", "port"]))


def process_fibrechannel_ports(args, server, netapp_mode):
    fcp_counters = query_counters(args, server, netapp_mode, "fcp_lif")
    fcp_ports = query(args, server, "fcp-interface-get-iter")
    fcp_adapter = query(args, server, "fcp-adapter-get-iter")

    if fcp_counters:
        print("<<<netapp_api_fcp:sep(9)>>>")
        port_dict = create_dict(fcp_adapter, custom_key="port-name", is_counter=False)
        fcp_counter_dict = create_dict(fcp_counters, custom_key="instance_name")

        for values in fcp_counter_dict.values():
            if values["port_wwpn"] in port_dict:
                values.update(port_dict[values["port_wwpn"]])

        print(format_config(fcp_ports, "fcp", "interface-name", extra_info=fcp_counter_dict))


def process_cpu(args, server):
    # CPU Util for both nodes
    node_info = query(args, server, "system-get-node-info-iter")
    system_info = query(args, server, "system-node-get-iter")
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


def process_7mode(args, server, netapp_mode, licenses):
    # Interfaces
    interfaces = query(args, server, "net-ifconfig-get")
    if_counters = query_counters(args, server, netapp_mode, "ifnet")
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
    system_counters = query_counters(args, server, netapp_mode, "system")
    if system_counters:
        print("<<<netapp_api_cpu:sep(9)>>>")
        dict_counters = create_dict(system_counters)
        print(format_dict(dict_counters.get("system"), report=["cpu_busy", "num_processors"]))

    # Volumes
    volumes = query(args, server, "volume-list-info")
    if "volumes" in args.no_counters:
        volume_counters = None
    else:
        volume_counters = query_counters(args, server, netapp_mode, "volume")
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
    aggregations = query(args, server, "aggr-list-info")
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
    print("<<<netapp_api_snapshots:sep(9)>>>")
    for volume in volumes.children_get():
        # Small trick improve formatting
        if args.legacy:
            container = NaElement("container")  # pylint: disable=undefined-variable
            container.child_add(volume)
        else:
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
        protocol_counters = query_counters(args, server, netapp_mode, what)
        if protocol_counters:
            protocol_dict = create_dict(protocol_counters)
            print(
                format_dict(
                    protocol_dict[key],
                    report=["instance_name", "%s_read_ops" % what, "%s_write_ops" % what],
                    prefix="protocol %s" % key,
                    as_line=True,
                )
            )

    # Diagnosis status
    diag_status = query(args, server, "diagnosis-status-get")
    if diag_status:
        print("<<<netapp_api_status>>>")
        print(format_config(diag_status, "status", "status"))

    # Disks
    disk_info = query(args, server, "disk-list-info")
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
    vfiler_info = query(args, server, "vfiler-list-info")
    vfiler_names = [""]  # default is no vfiler
    if vfiler_info:
        print("<<<netapp_api_vf_status:sep(9)>>>")
        for vfiler in vfiler_info.children_get():
            name = vfiler.child_get_string("name")
            vfiler_names.append(name)
            response = server.invoke("vfiler-get-status", "vfiler", name)
            print("%s\t%s" % (name, response.child_get_string("status")))

    # Snapvaults
    if "sv_ontap_sec" not in licenses["v1_disabled"]:
        print("<<<netapp_api_snapvault:sep(9)>>>")
        for vfiler in vfiler_names:
            server.set_vfiler(vfiler)
            response = server.invoke("snapvault-secondary-relationship-status-list-iter-start")
            records = response.child_get_string("records")
            if not records or records == "0":
                continue
            tag = response.child_get_string("tag")
            response = server.invoke(
                "snapvault-secondary-relationship-status-list-iter-next",
                "maximum",
                records,
                "tag",
                tag,
            )
            print(
                format_config(
                    response.child_get("status-list"),
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
        data = response.children_get()
        if not data or len(data) <= 1:
            continue
        data = data[1]
        print(
            format_config(
                data,
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
    vfiler_counters = query_counters(args, server, netapp_mode, "vfiler")
    if vfiler_counters:
        print("<<<netapp_api_vf_stats:sep(9)>>>")
        vfiler_dict = create_dict(vfiler_counters)
        for key, values in vfiler_dict.items():
            print(format_dict(values, prefix="vfiler %s" % key, as_line=True))

    # NetApp System Version/Info
    system_info = query(args, server, "system-get-info")
    system_version = query(args, server, "system-get-version", return_toplevel_node=True)
    if system_info:
        print("<<<netapp_api_info:sep(9)>>>")
        print(format_as_key_value(system_info))
        print(format_as_key_value(system_version))

    # 7Mode Cluster info
    if "cf" not in licenses["v1_disabled"]:
        cluster_status = query(args, server, "cf-status", return_toplevel_node=True)
        if cluster_status:
            print("<<<netapp_api_cluster:sep(9)>>>")
            print(format_as_key_value(cluster_status))

            if system_info:
                system_name = system_info.child_get_string("system-name")
                print("<<<netapp_api_systemtime:sep(9)>>>")
                node_current_time = cluster_status.child_get_string("current-time")
                current_time = int(time.time())
                print("%s\t%s\t%s" % (system_name, current_time, node_current_time))

    # Sensors: Temp, Fan, PSU
    # Definition: all sensors are always monitored by one of the filers
    # We choose this filer by an alphanumerical compare
    system_name = system_info.child_get_string("system-name")
    partner_system_name = system_info.child_get_string("partner-system-name")
    if not partner_system_name or system_name < partner_system_name:
        environ_info = query(args, server, "storage-shelf-environment-list-info")
        if environ_info:
            for channel in environ_info.children_get():
                shelf_list = channel.child_get("shelf-environ-shelf-list")
                if shelf_list:
                    for shelf in shelf_list.children_get():
                        shelf_id = shelf.child_get_string("shelf-id")
                        for what, section in [
                            ("power-supply-list", "netapp_api_psu"),
                            ("cooling-element-list", "netapp_api_fan"),
                            ("temp-sensor-list", "netapp_api_temp"),
                        ]:
                            print("<<<%s:sep(9)>>>" % section)
                            node = shelf.child_get(what)
                            print(format_config(node, what, shelf_id))

    # License information
    print("<<<netapp_api_licenses:sep(9)>>>")
    licensev2_info = query(args, server, "license-v2-list-info")
    if licensev2_info:
        print(format_config(licensev2_info, "license", "package"))

    # Qtree quota usage
    quota_info = query(args, server, "quota-report")
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


def connect(args):
    try:
        if args.legacy:
            if args.debug:
                print("Running in legacy mode")
            server = NaServer(args.host_address, 1, 8)  # pylint: disable=undefined-variable
            server.set_admin_user(args.user, args.secret)
            server.set_timeout(args.timeout)
            server.set_transport_type("HTTPS")
            server.set_server_cert_verification(False)
            if args.dump_xml:
                server.set_debug_style("NA_PRINT_DONT_PARSE")
        else:
            server = NetAppConnection(args.host_address, args.user, args.secret)
            if args.debug:
                print("Running in optimized mode")
                server.debug = True

        return server

    except Exception:
        if args.debug:
            raise
        sys.stderr.write(
            "Cannot connect to NetApp Server. Maybe you provided wrong "
            "credentials. Please check your connection settings and try "
            "again."
        )
        sys.exit(1)


# .
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+

SectionType = List[str]

section_errors: SectionType = []


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = parse_arguments(argv)

    try:
        server = connect(args)
        netapp_mode = fetch_netapp_mode(args, server)
        licenses = fetch_license_information(args, server)

        if netapp_mode == "clustermode":
            process_clustermode(args, server, netapp_mode, licenses)
        else:
            process_7mode(args, server, netapp_mode, licenses)

        return 0

    except Exception as exc:
        # Shouldn't happen at all...
        server.add_error_message("Agent Exception (contact developer): %s" % exc)
        if args.debug:
            raise
        return 1
    finally:
        output_error_section(args, server)


if __name__ == "__main__":
    sys.exit(main())
