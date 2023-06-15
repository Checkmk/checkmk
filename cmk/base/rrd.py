#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import xml.etree.ElementTree as ET
from pathlib import Path

import cmk.utils
import cmk.utils.paths
from cmk.utils.hostaddress import HostName

RRDServiceName = str


def rrd_pnp_host_dir(hostname: HostName) -> str:
    # We need /opt here because of bug in rrdcached
    return str(cmk.utils.paths.rrd_multiple_dir / cmk.utils.pnp_cleanup(hostname))


def xml_path_for(hostname: HostName, servicedesc: RRDServiceName = "_HOST_") -> str:
    host_dir = rrd_pnp_host_dir(hostname)
    return host_dir + "/" + cmk.utils.pnp_cleanup(servicedesc) + ".xml"


def text_attr(node: ET.Element, attr_name: str) -> str | None:
    attr = node.find(attr_name)
    if attr is None:
        raise AttributeError()
    return attr.text


def set_text_attr(node: ET.Element, attr_name: str, value: str | None) -> None:
    attr = node.find(attr_name)
    if attr is None:
        raise AttributeError()
    attr.text = value


def write_xml(element: ET.Element, filepath: str) -> None:
    Path(filepath).write_text(
        (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            + ET.tostring(element, method="html", encoding="unicode")
            + "\n"
        ),
        encoding="utf-8",
    )
