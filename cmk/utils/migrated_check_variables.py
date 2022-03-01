#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
When migrating a check plugin to the new check API the corresponding check context
and check variables potentially needed to resolve the parameters saved in the autochecks
file will not be present any more. You can add those variables here, in oder to be able
to resolve the variables in saved autochecks.

This will also have the effect, that variables defined in a *.mk file in etc/check_mk/conf.d
will be considered.

For example: When migrating the check plugin `icom_repeater` we must add the following line
to this module, in order to be able to read and parse the autochecks discovered pre checkmk
1.7:

icom_ps_volt_default_levels = (13.5, 13.2, 14.1, 14.4)

"""

apc_ats_output_default_levels = {"output_voltage_max": (240, 250), "load_perc_max": (85, 95)}

# The plugin cisco_asa_svcsessions does not exist anymore (checkmk.com/de/werk/11150)
# Still we need to be able to load the autochecks file.
cisco_asa_svc_default_levels: dict = {}

# chrony:
ntp_default_levels = (10, 200.0, 500.0)  # stratum, ms sys_time_offset_offset

# hr_mem (amongst others)
memused_default_levels = (150.0, 200.0)

ruckus_spot_ap_default_levels: dict = {}

fortigate_memory_base_default_levels = {
    "levels": (70.0, 80.0),
}

# hp_proliant_power: see werk 10857
hp_prolaint_power_default_levels = None  # yes, P R O L A I N T

# hp_msa: see werk 11761
hp_msa_controller_cpu_default_levels = (80.0, 90.0)

# if.include
# These HostRulespecs are deprecated as of v2.0. However, for compatibility reasons, we must not
# delete these variable.
if_disable_if64_hosts: list = []
if_groups: list = []
# Obsolete variables, but needed as contained in autochecks of older checks. We need to keep this up
# for a few years/decades...
if_default_error_levels = (0.01, 0.1)
if_default_traffic_levels = None, None
if_default_average = None

# netapp_api_vf_stats
netapp_api_vf_stats_cpu_util_default_levels = (90.0, 95.0)

# ps
ps_default_levels = {"levels": (1, 1, 99999, 99999)}

# services
services_default_levels = {
    "states": [("running", None, 0)],
    "else": 2,
    "additional_servicenames": [],
}
services_summary_default_levels = {"ignored": [], "state_if_stopped": 0}

tcp_conn_stats_default_levels: dict = {}

# oracle_tablespaces
oracle_tablespaces_default_levels = (10.0, 5.0)
oracle_tablespaces_check_autoext = True

winperf_cpu_default_levels: dict = {}  # winperf_processor.util

# cpu_loads
cpuload_default_levels = (5.0, 10.0)
# cpu_threads
cpu_threads_default_levels = {"levels": (2000, 4000)}

# checkpoint_connections
checkpoint_connections_default_levels = (40000, 50000)

# esx_vsphere_hostsystem_mem_usage
esx_host_mem_default_levels = (80.0, 90.0)

# pdu_gude
pdu_gude_default_levels = {
    "V": (220, 210),
    "A": (15, 16),
    "W": (3500, 3600),
}

# jenkins_jobs

MAP_JOB_STATES = {
    "aborted": {"state": 0, "info": "Aborted"},
    "blue": {"state": 0, "info": "Success"},
    "disabled": {"state": 0, "info": "Disabled"},
    "notbuilt": {"state": 0, "info": "Not built"},
    "red": {"state": 2, "info": "Failed"},
    "yellow": {"state": 1, "info": "Unstable"},
}

MAP_BUILD_STATES = {
    "success": 0,  # no errors
    "unstable": 1,  # some errors but not fatal
    "failure": 2,  # fatal error
    "aborted": 0,  # manually aborted
    "null": 1,  # module was not built
    "none": 0,  # running
}

# ucd_cpu_load, hpux_cpu, statgrab_load
cpuload_default_levels = (5.0, 10.0)

# blade_bx_load
blade_bx_cpuload_default_levels = (5, 20)

# mcafee_emailgateway_cpuload
mcafee_emailgateway_cpuload_default_levels = (5.0, 10.0)

# arbor_peakflow_sp, arbor_peakflow_tms, arbor_pravail
arbor_cpuload_default_levels = (5.0, 10.0)
