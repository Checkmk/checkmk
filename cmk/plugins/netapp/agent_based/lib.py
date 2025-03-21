#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.plugins.netapp import models


def filter_metrocluster_items(
    section_netapp_ontap_volumes: Mapping[str, models.VolumeModel],
    section_netapp_ontap_vs_status: Mapping[str, models.SvmModel],
) -> Mapping[str, models.VolumeModel]:
    """
    As per SUP-22707 and SUP-22904
    volumes and snapshots of SVMs of subtype "sync_destination" (metrocluster)
    should not be discovered.
    """
    return {
        volume_id: volume
        for volume_id, volume in section_netapp_ontap_volumes.items()
        if (svm := section_netapp_ontap_vs_status.get(volume.svm_name))
        and svm.subtype != "sync_destination"
    }
