#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

FOLDER_CONFIG_FAMILY = EndpointFamily(
    name="Folders",
    description=(
        """\
Folders are used in Checkmk to organize the hosts in a tree structure.
The root (or main) folder is always existing, other folders can be created manually.
If you build the tree cleverly you can use it to pass on attributes in a meaningful manner.

You can find an introduction to hosts including folders in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_hosts.html).

Due to HTTP escaping folders are represented with the tilde character (`~`) as the path separator.

### Host and Folder attributes

Every host and folder can have "attributes" set, which determine the behavior of Checkmk. Each
host inherits all attributes of its folder and the folder's parent folders. So setting an SNMP
community in a folder is equivalent to setting the same on all hosts in said folder.

Some host endpoints allow one to view the "effective attributes", which is an aggregation of all
attributes up to the root.

### Relations

A folder_config object can have the following relations present in `links`:

 * `self` - The folder itself.
 * `urn:org.restfulobjects:rels/update` - The endpoint to update this folder.
 * `urn:org.restfulobjects:rels/delete` - The endpoint to delete this folder.
"""
    ),
    doc_group="Setup",
)
