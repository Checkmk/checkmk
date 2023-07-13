#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.emc import DETECT_ISILON

check_info["emc_isilon"] = LegacyCheckDefinition(
    detect=DETECT_ISILON,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.12124.1.1",
            oids=["1", "2", "5", "6"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.12124.2.1",
            oids=["1", "2"],
        ),
    ],
)


#   .--ClusterHealth------------------------------------------------------.


def inventory_emc_isilon_clusterhealth(info):
    return [(None, None)]


def check_emc_isilon_clusterhealth(item, _no_params, info):
    status = int(info[0][0][1])
    statusmap = ("ok", "attn", "down", "invalid")
    if status >= len(statusmap):
        return 3, "ClusterHealth reports unidentified status %s" % status

    if status == 0:
        rc = 0
    else:
        rc = 2
    return rc, "ClusterHealth reports status %s" % statusmap[status]


check_info["emc_isilon.clusterhealth"] = LegacyCheckDefinition(
    service_name="Cluster Health",
    sections=["emc_isilon"],
    discovery_function=inventory_emc_isilon_clusterhealth,
    check_function=check_emc_isilon_clusterhealth,
)

# .
#   .--NodeHealth------------------------------------------------------.


def inventory_emc_isilon_nodehealth(info):
    return [(None, None)]


def check_emc_isilon_nodehealth(item, _no_params, info):
    status = int(info[1][0][1])
    statusmap = ("ok", "attn", "down", "invalid")
    nodename = info[1][0][0]
    if status >= len(statusmap):
        return 3, "nodeHealth reports unidentified status %s" % status

    if status == 0:
        rc = 0
    else:
        rc = 2
    return rc, "nodeHealth for %s reports status %s" % (nodename, statusmap[status])


check_info["emc_isilon.nodehealth"] = LegacyCheckDefinition(
    service_name="Node Health",
    sections=["emc_isilon"],
    discovery_function=inventory_emc_isilon_nodehealth,
    check_function=check_emc_isilon_nodehealth,
)

# .
#   .--Nodes------------------------------------------------------.


def inventory_emc_isilon_nodes(info):
    return [(None, None)]


def check_emc_isilon_nodes(item, _no_params, info):
    _cluster_name, _cluster_health, configured_nodes, online_nodes = info[0][0]
    if configured_nodes == online_nodes:
        rc = 0
    else:
        rc = 2
    return rc, "Configured Nodes: %s / Online Nodes: %s" % (configured_nodes, online_nodes)


check_info["emc_isilon.nodes"] = LegacyCheckDefinition(
    service_name="Nodes",
    sections=["emc_isilon"],
    discovery_function=inventory_emc_isilon_nodes,
    check_function=check_emc_isilon_nodes,
)

# .
#   .--Cluster- and Node Name-------------------------------------------.


def inventory_emc_isilon_names(info):
    return [(None, None)]


def check_emc_isilon_names(item, _no_params, info):
    return 0, "Cluster Name is %s, Node Name is %s" % (info[0][0][0], info[1][0][0])


check_info["emc_isilon.names"] = LegacyCheckDefinition(
    service_name="Isilon Info",
    sections=["emc_isilon"],
    discovery_function=inventory_emc_isilon_names,
    check_function=check_emc_isilon_names,
)

# .
