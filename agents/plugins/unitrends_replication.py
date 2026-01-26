#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

__version__ = "2.4.0p21"

import sys
import time
from urllib.request import urlopen
from xml.dom import minidom

# TODO: minicompat include internal impl details. But NodeList is only defined there for <3.11
from xml.dom.minicompat import NodeList

now = int(time.time())
start = now - 24 * 60 * 60
end = now
dpu = 1

url = (
    "http://localhost/recoveryconsole/bpl/syncstatus.php?type=replicate&arguments=start:%s,end:%s&sid=%s&auth=1:"
    % (start, end, dpu)
)

xml = urlopen(url)  # nosec B310 # BNS:28af27 # pylint: disable=consider-using-with


def _get_text(node: NodeList[minidom.Element]) -> str:
    first = node.item(0)
    if first is None:
        raise ValueError("Node has no item")
    child = first.firstChild
    if child is None or not isinstance(child, minidom.Text):
        raise ValueError("Node has no text")
    return child.data


sys.stdout.write("<<<unitrends_replication:sep(124)>>>\n")
dom = minidom.parse(xml)
for item in dom.getElementsByTagName("SecureSyncStatus"):
    application_node = item.getElementsByTagName("Application")
    if application_node:
        application = application_node[0].attributes["Name"].value
    else:
        application = "N/A"
    result = _get_text(item.getElementsByTagName("Result"))
    completed = _get_text(item.getElementsByTagName("Complete"))
    targetname = _get_text(item.getElementsByTagName("TargetName"))
    instancename = _get_text(item.getElementsByTagName("InstanceName"))
    sys.stdout.write(
        "%s|%s|%s|%s|%s\n" % (application, result, completed, targetname, instancename)
    )
