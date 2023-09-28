#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import cmk.base.plugins.agent_based.utils.hp_msa as hp_msa

# TODO
# Use 'status-numeric' instead of 'status' field regardless of language.
# See for state mapping: https://support.hpe.com/hpsc/doc/public/display?docId=emr_na-a00017709en_us

hp_msa_state_map = {
    "Up": (0, "up"),
    "OK": (0, "OK"),
    "Warning": (1, "warning"),
    "Degraded": (1, "degraded"),
    "Error": (2, "error"),
    "Not Present": (2, "not present"),
    "Fault": (2, "fault"),
    "Unknown": (3, "unknown"),
}

parse_hp_msa = hp_msa.parse_hp_msa


def inventory_hp_msa_health(parsed):
    return [(key, None) for key in parsed]


def check_hp_msa_health(item, _no_params, parsed):
    if item in parsed:
        infotexts = []
        health_state, health_state_readable = hp_msa_state_map[parsed[item]["health"]]
        health_info = "Status: %s" % health_state_readable
        if health_state and parsed[item].get("health-reason", ""):
            health_info += " (%s)" % parsed[item]["health-reason"]

        infotexts.append(health_info)

        # extra info of volumes
        if parsed[item]["item_type"] == "volumes":
            volume_info = parsed[item].get("container-name", "")
            if volume_info:
                if parsed[item].get("raidtype", ""):
                    volume_info += " (%s)" % parsed[item]["raidtype"]
                infotexts.append("container name: %s" % volume_info)

        # extra info of disks
        elif parsed[item]["item_type"] == "drives":
            for disk_info in ["serial-number", "vendor", "model", "description", "size"]:
                if parsed[item].get(disk_info, ""):
                    infotexts.append(
                        "%s: %s"
                        % (
                            disk_info.replace("-", " "),
                            parsed[item][disk_info].replace("GB", " GB"),
                        )
                    )

            if parsed[item].get("rpm", ""):
                infotexts.append("speed: %s RPM" % (parsed[item]["rpm"]))

        return health_state, ", ".join(infotexts)
    return None
