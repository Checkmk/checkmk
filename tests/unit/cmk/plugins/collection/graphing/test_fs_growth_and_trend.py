#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.graphing.v1 import metrics, translations
from cmk.graphing.v1.translations import Translation
from cmk.plugins.collection.graphing.fs_growth_and_trend import metric_fs_growth, metric_fs_trend
from cmk.plugins.collection.graphing.mem_growth import metric_mem_growth
from cmk.plugins.collection.graphing.mem_trend import metric_mem_trend
from cmk.plugins.collection.graphing.translations import (
    translation_cisco_cpu_memory_cisco_sys_mem,
    translation_cisco_mem_cisco_mem_asa_cisco_mem_asa64,
)
from cmk.plugins.collection.graphing.translations import (
    translation_df_db2_logsizes_esx_vsphere_datastores_netapp_ontap_aggr_vms_df_vms_diskstat_df_disk_df_netapp_df_netapp32_zfsget_hr_fs_oracle_asm_diskgroup_esx_vsphere_counters_ramdisk_hitachi_hnas_span_hitachi_hnas_volume_hitachi_hnas_volume_virtual_emcvnx_raidgroups_capacity_emcvnx_raidgroups_capacity_contiguous_ibm_svc_mdiskgrp_fast_lta_silent_cubes_capacity_fast_lta_volumes_libelle_business_shadow_archive_dir_netapp_ontap_luns_netapp_ontap_qtree_quota_emc_datadomain_fs_emc_isilon_quota_emc_isilon_ifs_3par_cpgs_usage_3par_capacity_3par_volumes_storeonce_clusterinfo_space_storeonce_servicesets_capacity_storeonce4x_appliances_storage_storeonce4x_cat_stores_numble_volumes_zpool_vnx_quotas_sap_hana_diskusage_fjdarye200_pools_dell_compellent_folder_nimble_volumes_ceph_df_kube_pvc_lvm_vgs_df_netscaler_prism_host_usage_prism_containers_prism_storage_pools_ucd_disk_hp_msa_volume_df as translation_filesystem_storages_df,
)

# The df/mem checks emit growth/trend in MB/day (packages/cmk-plugins/cmk/plugins/lib/size_trend.py).
_BYTES_PER_MB = 1048576


@pytest.mark.parametrize(
    "translation, raw_metric_name, metric",
    [
        pytest.param(
            translation_filesystem_storages_df, "growth", metric_fs_growth, id="df-growth"
        ),
        pytest.param(translation_filesystem_storages_df, "trend", metric_fs_trend, id="df-trend"),
        pytest.param(
            translation_cisco_mem_cisco_mem_asa_cisco_mem_asa64,
            "growth",
            metric_mem_growth,
            id="cisco-mem-growth",
        ),
        pytest.param(
            translation_cisco_mem_cisco_mem_asa_cisco_mem_asa64,
            "trend",
            metric_mem_trend,
            id="cisco-mem-trend",
        ),
        pytest.param(
            translation_cisco_cpu_memory_cisco_sys_mem,
            "growth",
            metric_mem_growth,
            id="cisco-cpu-memory-growth",
        ),
        pytest.param(
            translation_cisco_cpu_memory_cisco_sys_mem,
            "trend",
            metric_mem_trend,
            id="cisco-cpu-memory-trend",
        ),
    ],
)
def test_growth_and_trend_translation_matches_declared_unit(
    translation: Translation, raw_metric_name: str, metric: metrics.Metric
) -> None:
    assert metric.unit == metrics.Unit(metrics.IECNotation("B/d"))

    rename = translation.translations[raw_metric_name]
    assert isinstance(rename, translations.RenameToAndScaleBy)
    assert rename.metric_name == metric.name
    assert rename.factor == _BYTES_PER_MB
