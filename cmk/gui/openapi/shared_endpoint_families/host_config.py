#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

HOST_CONFIG_FAMILY = EndpointFamily(
    name="Hosts",
    description=(
        """

A host is an object that is monitored by Checkmk, for example, a server or a network device.
A host belongs to a certain folder, is usually connected to a data source (agent or SNMP) and
provides one or more services.

A cluster host is a special host type containing the nodes the cluster consists of and having
the services assigned that are provided by the cluster.

You can find an introduction to hosts in the
[Checkmk guide](https://docs.checkmk.com/latest/en/wato_hosts.html).

Please note that every host always resides in a folder. The folder is included twice
in the host's links: Once based upon the canonical path and once based upon the folder's
unique id. You can never remove a host from a folder, just move it to a different one.

### Host and Folder attributes

Every host and folder can have "attributes" set, which determine the behavior of Checkmk. Each
host inherits all attributes of its folder and the folder's parent folders. So setting an SNMP
community in a folder is equivalent to setting the same on all hosts in said folder.

Some host endpoints allow one to view the "effective attributes", which is an aggregation of all
attributes up to the root.

### Relations

A host_config object can have the following relations present in `links`:

 * `self` - The host itself.
 * `urn:com.checkmk:rels/folder_config` - The folder object this host resides in.
 * `urn:org.restfulobjects:rels/update` - The endpoint to update this host.
 * `urn:org.restfulobjects:rels/delete` - The endpoint to delete this host.

"""
    ),
    doc_group="Setup",
)
