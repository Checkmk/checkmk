#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple

from six import ensure_str

import cmk.utils
import cmk.utils.paths
from cmk.utils.type_defs import HostName, MetricName

RRDServiceName = str


def rrd_pnp_host_dir(hostname: HostName) -> str:
    # We need /opt here because of bug in rrdcached
    return str(cmk.utils.paths.rrd_multiple_dir / cmk.utils.pnp_cleanup(hostname))


def xml_path_for(hostname: HostName, servicedesc: RRDServiceName = "_HOST_") -> str:
    host_dir = rrd_pnp_host_dir(hostname)
    return host_dir + "/" + cmk.utils.pnp_cleanup(servicedesc) + ".xml"


def text_attr(node: ET.Element, attr_name: str) -> Optional[str]:
    attr = node.find(attr_name)
    if attr is None:
        raise AttributeError()
    return attr.text


def set_text_attr(node: ET.Element, attr_name: str, value: Optional[str]) -> None:
    attr = node.find(attr_name)
    if attr is None:
        raise AttributeError()
    attr.text = value


def write_xml(element: ET.Element, filepath: str) -> None:
    with Path(filepath).open("w", encoding="utf-8") as fid:
        fid.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
        # TODO: Can be set to encoding="unicode" with Python3
        # ? with UTF-8 encoding the argument of ensure_str seems to be of type bytes, with unicode encoding-str
        fid.write(
            ensure_str(  # pylint: disable= six-ensure-str-bin-call
                ET.tostring(element, method="html", encoding="UTF-8")
            )
            + "\n"
        )


def update_metric_pnp_xml_info_file(
    perfvar: MetricName, newvar: MetricName, filepath: str
) -> Tuple[str, str]:
    """Update xml file related to the service described in filepath

    - Change DATASOURCE: NAME & LABEL to newvar
    - Update Nagios perfdata strings
    - Change new filename of

    Return 2-tuple RRDFILE to be renamed and new filename"""

    root = ET.parse(filepath).getroot()
    label = None
    for metric in root.iter("DATASOURCE"):
        if text_attr(metric, "NAME") == perfvar:
            set_text_attr(metric, "NAME", newvar)
            label = text_attr(metric, "LABEL")
            set_text_attr(metric, "LABEL", newvar)

            rrdfile = text_attr(metric, "RRDFILE")
            if rrdfile is None:
                raise TypeError()
            rrdfilenew = rrdfile.replace(perfvar + ".rrd", newvar + ".rrd")
            set_text_attr(metric, "RRDFILE", rrdfilenew)
            break

    if rrdfile is None:
        raise TypeError()

    for perfdata in ["NAGIOS_PERFDATA", "NAGIOS_SERVICEPERFDATA"]:
        if label:
            perfstr = text_attr(root, perfdata)
            if perfstr is None:
                raise TypeError()
            set_text_attr(root, perfdata, perfstr.replace(label + "=", newvar + "=", 1))

    write_xml(root, filepath)

    return rrdfile, rrdfilenew
