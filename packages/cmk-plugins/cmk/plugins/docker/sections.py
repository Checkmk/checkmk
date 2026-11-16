#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Final

from cmk.rulesets.v1 import Title

CONTAINER_SECTIONS: Final = {
    "docker_container_node_name": Title("Node name: Inventorize the nodes' name"),
    "docker_container_status": Title("Status: Create status and (if configured) health services"),
    "docker_container_labels": Title("Labels: Inventorize the labels"),
    "docker_container_network": Title("Network: Inventorize network configuration information"),
    "docker_container_agent": Title(
        "Checkmk agent: execute the Checkmk agent within running containers"
    ),
    "docker_container_mem": Title("Check containers memory usage"),
    "docker_container_cpu": Title("Check containers CPU utilization"),
    "docker_container_diskstat": Title("Check containers disk status"),
}


NODE_SECTIONS: Final = {
    "docker_node_info": Title(
        "Info: Daemon state and summarized count of containers and their states"
    ),
    "docker_node_disk_usage": Title("Disk usage: Information similar to 'docker system df' output"),
    "docker_node_images": Title(
        "Images: Inventorize image information such as creation time, size,"
        " labels and the amount of containers running them."
    ),
    "docker_node_network": Title("Network: Inventorize containers' network configuration"),
}
