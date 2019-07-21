#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
Migrate RRDs metadata which are based on mountpoint names to static name 'fs_used'
==================================================================================

- Find all active services that use uses df.include in their check.
- Go through every info file, either cmc infos or Nagios XML files
- Update the metric names from a mountpoint to fs_used in info files
- For Nagios, correspondingly rename rrd files and update journal
- Activate a config flag that fs_used is the new metric name
"""

from __future__ import division, absolute_import, print_function

import argparse
import re
import sys
import os
import logging
import subprocess
from shlex import split
import xml.etree.ElementTree as ET

from pathlib2 import Path
import six

from omdlib.main import SiteContext, site_name

import cmk_base.autochecks
import cmk_base.cee.rrd
import cmk_base.config as config
import cmk_base.check_api as check_api

import cmk.utils
import cmk.utils.debug
cmk.utils.debug.enable()

config.load_all_checks(check_api.get_check_api_context)
config.load()

logger = logging.getLogger("RRD INFO Metric Migration")
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

CHECKS_USING_DF_INCLUDE = [
    "3par_capacity", "3par_cpgs", "3par_cpgs.usage", "3par_system", "3par_volumes", "ceph_df",
    "datapower_fs", "db2_logsizes", "dell_compellent_folder", "df", "df_netapp", "df_netapp32",
    "df_netscaler", "df_zos", "emc_datadomain_fs", "emc_isilon_ifs", "emc_isilon_quota",
    "emcvnx_raidgroups.capacity", "emcvnx_raidgroups.capacity_contiguous",
    "esx_vsphere_counters.ramdisk", "esx_vsphere_datastores", "fast_lta_silent_cubes.capacity",
    "fast_lta_volumes", "hitachi_hnas_span", "hitachi_hnas_volume", "hp_msa_volume.df", "hr_fs",
    "ibm_svc_mdiskgrp", "k8s_stats.fs", "libelle_business_shadow.archive_dir", "lvm_vgs",
    "mgmt_hr_fs", "netapp_api_aggr", "netapp_api_luns", "netapp_api_qtree_quota",
    "netapp_api_volumes", "nimble_volumes", "oracle_asm_diskgroup", "prism_storage_pools",
    "sap_hana_data_volume", "sap_hana_diskusage", "scaleio_pd", "scaleio_sds",
    "scaleio_storage_pool", "scaleio_system", "storeonce_clusterinfo.space",
    "storeonce_servicesets.capacity", "ucd_disk", "vms_diskstat.df", "vnx_quotas", "zfsget", "zpool"
]


def check_df_sources_include_flag():
    """Verify that df.include files are can return fs_used metric name"""
    checks_dirs = (cmk.utils.paths.local_checks_dir, cmk.utils.paths.checks_dir)
    logger.info("Looking for df.include files...")
    for path_dir in checks_dirs:
        df_file = Path(path_dir, 'df.include')
        if df_file.exists():
            logger.info("Inspecting %s", df_file)
            with df_file.open('r') as fid:
                r = fid.read()
                mat = re.search('^df_use_fs_used_as_metric_name *= *(True|False)', r, re.M)
                if not mat:
                    raise RuntimeError('df.include sources not yet ready to for new setup')
            logger.info("  Include file implements new fs_used as perfvalue")


def get_hostnames(config_cache):
    return config_cache.all_active_hosts()


def get_info_file(hostname, servicedesc, source):
    if source == 'cmc':
        host_dir = cmk_base.cee.rrd.rrd_cmc_host_dir(hostname)
        servicefile = cmk.utils.pnp_cleanup(servicedesc)
        return os.path.join(host_dir, servicefile + '.info')
    return cmk_base.cee.rrd.xml_path_for(hostname, servicedesc)


def get_metrics(filepath, source):
    if source == 'cmc':
        return cmk_base.cee.rrd.read_existing_metrics(filepath)

    root = ET.parse(filepath).getroot()
    return [x.text for x in root.findall('.//NAME')]


def update_files(args, hostname, servicedesc, item, source):

    filepath = get_info_file(hostname, servicedesc, source)
    if not os.path.exists(filepath):
        return

    metrics = get_metrics(filepath, source)
    perfvar = cmk.utils.pnp_cleanup(item)

    logger.info('Analyzing %s', filepath)
    if perfvar in metrics and 'fs_used' not in metrics:
        if args.dry_run:
            logger.info("   Will be updated ")
            return

        if source == 'cmc':
            r_metrics = ['fs_used' if x == perfvar else x for x in metrics]
            cmk_base.cee.rrd.create_cmc_rrd_info_file(hostname, servicedesc, r_metrics)
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


def update_journal(rrdfile, rrdfilenew):
    journaldir = Path(cmk.utils.paths.omd_root, 'var/rrdcached/')
    for filepath in journaldir.iterdir():
        logger.info('- Updating journal file %s', filepath)
        new_file = filepath.with_suffix(filepath.suffix + '.new')
        try:
            with filepath.open('r') as old_jou, new_file.open('w') as new_jou:
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

    rrdfile, rrdfilenew = cmk_base.cee.rrd.update_metric_pnp_xml_info_file(
        perfvar, newvar, filepath)
    os.rename(rrdfile, rrdfilenew)
    logger.info("Renamed %s -> %s", rrdfile, rrdfilenew)
    update_journal(rrdfile, rrdfilenew)


def update_service_info(config_cache, hostnames, args):
    for hostname in hostnames:
        for check_plugin_name, item, _ in config_cache.get_autochecks_of(hostname):
            if check_plugin_name in CHECKS_USING_DF_INCLUDE:
                servicedesc = config.service_description(hostname, check_plugin_name, item)
                update_files(args, hostname, servicedesc, item, 'cmc')
                update_files(args, hostname, servicedesc, item, 'pnp4nagios')


def _ask_for_confirmation_backup():
    sys.stdout.write("This migration script will update the metric names of your rrd files, "
                     "info files, and rrd chached journal.")
    while "Invalid answer":
        reply = str(
            six.moves.input("Do you have a Backup and want to proceed? [y/N]: ")).lower().strip()
        if not reply or reply[0] == 'n':
            return False
        if reply[0] == 'y':
            return True


def save_new_config():
    with open(os.path.join(cmk.utils.paths.omd_root, 'etc/check_mk/conf.d/fs_cap.mk'), 'w') as fid:
        fid.write('df_use_fs_used_as_metric_name = True\n')

    logger.info(subprocess.check_output(split('cmk -U')))


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-n', '--dry-run', action='store_true', help='Show Files to be updated')
    return parser.parse_args()


def main():

    args = parse_arguments()

    check_df_sources_include_flag()
    site = SiteContext(site_name())
    if not (site.is_stopped() or args.dry_run):
        raise RuntimeError('The site needs to be stopped to run this script')

    if not _ask_for_confirmation_backup():
        sys.exit(1)

    config_cache = config.get_config_cache()
    update_service_info(config_cache, get_hostnames(config_cache), args)

    if not args.dry_run:
        save_new_config()


if __name__ == '__main__':

    main()
