#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
r"""
Migrate RRDs metadata which are based on mountpoint names to static name 'fs_used'
==================================================================================

- Find all active services that use uses df.include in their check.
- Go through every info file, either cmc infos or Nagios XML files
- Update the metric names from a mountpoint to fs_used in info files
- For Nagios, correspondingly rename rrd files and update journal
- Activate a config flag that fs_used is the new metric name

WARN: DELETE THIS FOR CMK 1.8, THIS ONLY migrates 1.6->1.7
"""

import os
import logging
import xml.etree.ElementTree as ET

from pathlib import Path

import cmk.base.autochecks  # pylint: disable=cmk-module-layer-violation
import cmk.base.config as config  # pylint: disable=cmk-module-layer-violation
import cmk.base.check_api as check_api  # pylint: disable=cmk-module-layer-violation
from cmk.utils.type_defs import CheckPluginName

import cmk.base.rrd  # pylint: disable=cmk-module-layer-violation
try:
    import cmk.base.cee.rrd  # pylint: disable=cmk-module-layer-violation
except ImportError:
    pass

import cmk.utils
import cmk.utils.debug

logger = logging.getLogger("RRD INFO Metric Migration")

CHECKS_USING_DF_INCLUDE = list(
    map(CheckPluginName, [
        "3par_capacity", "3par_cpgs", "3par_cpgs_usage", "3par_system", "3par_volumes", "ceph_df",
        "datapower_fs", "db2_logsizes", "dell_compellent_folder", "df", "df_netapp", "df_netapp32",
        "df_netscaler", "df_zos", "emc_datadomain_fs", "emc_isilon_ifs", "emc_isilon_quota",
        "emcvnx_raidgroups_capacity", "emcvnx_raidgroups_capacity_contiguous",
        "esx_vsphere_counters_ramdisk", "esx_vsphere_datastores", "fast_lta_silent_cubes_capacity",
        "fast_lta_volumes", "hitachi_hnas_span", "hitachi_hnas_volume", "hp_msa_volume_df", "hr_fs",
        "ibm_svc_mdiskgrp", "k8s_stats_fs", "libelle_business_shadow_archive_dir", "lvm_vgs",
        "mgmt_hr_fs", "netapp_api_aggr", "netapp_api_luns", "netapp_api_qtree_quota",
        "netapp_api_volumes", "nimble_volumes", "oracle_asm_diskgroup", "prism_storage_pools",
        "sap_hana_data_volume", "sap_hana_diskusage", "scaleio_pd", "scaleio_sds",
        "scaleio_storage_pool", "scaleio_system", "storeonce_clusterinfo_space",
        "storeonce_servicesets_capacity", "ucd_disk", "vms_diskstat_df", "vnx_quotas", "zfsget",
        "zpool"
    ]))


def get_hostnames(config_cache):
    return config_cache.all_active_hosts()


def get_info_file(hostname, servicedesc, source):
    if source == 'cmc':
        host_dir = cmk.base.cee.rrd.rrd_cmc_host_dir(hostname)
        servicefile = cmk.utils.pnp_cleanup(servicedesc)
        return os.path.join(host_dir, servicefile + '.info')
    return cmk.base.rrd.xml_path_for(hostname, servicedesc)


def get_metrics(filepath, source):
    if source == 'cmc':
        return cmk.base.cee.rrd.read_existing_metrics(filepath)

    root = ET.parse(filepath).getroot()
    return [x.text for x in root.findall('.//NAME')]


def update_files(hostname, servicedesc, item, source):

    filepath = get_info_file(hostname, servicedesc, source)
    if not os.path.exists(filepath):
        return False

    metrics = get_metrics(filepath, source)
    perfvar = cmk.utils.pnp_cleanup(item)

    update_condition = perfvar in metrics and 'fs_used' not in metrics
    logger.info('Analyzing %s', filepath)
    if update_condition:
        if source == 'cmc':
            r_metrics = ['fs_used' if x == perfvar else x for x in metrics]
            cmk.base.cee.rrd.create_cmc_rrd_info_file(hostname, servicedesc, r_metrics)
        else:
            update_pnp_info_files(perfvar, 'fs_used', filepath)

        logger.info("   Updated ")

    elif metrics.count('fs_used') == 1 and perfvar not in metrics:
        logger.debug('   Already in desired format')
    else:
        logger.error(
            'RRD files for host %s and service %s stored in files:\n  - %s\n  - %s\n'
            "are messed up. Please restore them both from backup.",
            hostname,
            servicedesc,
            filepath,
            filepath.replace(".info", ".rrd"),
        )

    return False


def update_journal(rrdfile, rrdfilenew):
    journaldir = Path(cmk.utils.paths.omd_root, 'var/rrdcached/')
    for filepath in journaldir.iterdir():
        logger.info('- Updating journal file %s', filepath)
        new_file = filepath.with_suffix(filepath.suffix + '.new')
        try:
            with filepath.open('r', encoding="utf-8") as old_jou, new_file.open(
                    'w', encoding="utf-8") as new_jou:
                for line in old_jou:
                    if rrdfile in line:
                        line = line.replace(rrdfile, rrdfilenew)
                    new_jou.write(line)
        except Exception:
            new_file.unlink()
            raise
        finally:
            if new_file.exists():
                filepath.unlink()
                new_file.rename(filepath)


def update_pnp_info_files(perfvar, newvar, filepath):
    """Update all files related to the service described in filepath

    - Change DATASOURCE: NAME & LABEL to newvar
    - Update Nagios perfdata strings
    - Rename matching rrdfile to use newvar
    - For all journal files, replace rrdfile with new file"""

    rrdfile, rrdfilenew = cmk.base.rrd.update_metric_pnp_xml_info_file(perfvar, newvar, filepath)
    os.rename(rrdfile, rrdfilenew)
    logger.info("Renamed %s -> %s", rrdfile, rrdfilenew)
    update_journal(rrdfile, rrdfilenew)


def update_service_info(config_cache, hostnames):
    pnp_files_present = False
    check_variables = config.get_check_variables()

    for hostname in hostnames:
        for service in cmk.base.autochecks.parse_autochecks_file(
                hostname,
                config.service_description,
                check_variables,
        ):
            if service.check_plugin_name in CHECKS_USING_DF_INCLUDE:
                update_files(hostname, service.description, service.item, 'cmc')
                pnp_files_present |= update_files(hostname, service.description, service.item,
                                                  'pnp4nagios')


def update():
    config.load_all_agent_based_plugins(check_api.get_check_api_context)
    config.load()

    config_cache = config.get_config_cache()
    update_service_info(config_cache, get_hostnames(config_cache))


def main():
    cmk.utils.debug.enable()

    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)

    update()


if __name__ == '__main__':
    main()
