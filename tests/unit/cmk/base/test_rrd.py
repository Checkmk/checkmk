#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest

import cmk.base.rrd as rrd

NAGIOS_SERVICE_XML_MULTIPLE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<NAGIOS>
  <DATASOURCE>
    <TEMPLATE>check_mk-cpu.loads</TEMPLATE>
    <RRDFILE>/omd/sites/raw/var/pnp4nagios/perfdata/localhost/CPU_load_load1.rrd</RRDFILE>
    <RRD_STORAGE_TYPE>MULTIPLE</RRD_STORAGE_TYPE>
    <RRD_HEARTBEAT>8460</RRD_HEARTBEAT>
    <IS_MULTI>0</IS_MULTI>
    <DS>1</DS>
    <NAME>load1</NAME>
    <LABEL>load1</LABEL>
    <UNIT></UNIT>
    <ACT>0.93</ACT>
    <WARN>40</WARN>
    <WARN_MIN></WARN_MIN>
    <WARN_MAX></WARN_MAX>
    <WARN_RANGE_TYPE></WARN_RANGE_TYPE>
    <CRIT>80</CRIT>
    <CRIT_MIN></CRIT_MIN>
    <CRIT_MAX></CRIT_MAX>
    <CRIT_RANGE_TYPE></CRIT_RANGE_TYPE>
    <MIN>0</MIN>
    <MAX>8</MAX>
  </DATASOURCE>
  <DATASOURCE>
    <TEMPLATE>check_mk-cpu.loads</TEMPLATE>
    <RRDFILE>/omd/sites/raw/var/pnp4nagios/perfdata/localhost/CPU_load_load5.rrd</RRDFILE>
    <RRD_STORAGE_TYPE>MULTIPLE</RRD_STORAGE_TYPE>
    <RRD_HEARTBEAT>8460</RRD_HEARTBEAT>
    <IS_MULTI>0</IS_MULTI>
    <DS>1</DS>
    <NAME>load5</NAME>
    <LABEL>load5</LABEL>
    <UNIT></UNIT>
    <ACT>0.87</ACT>
    <WARN>40</WARN>
    <WARN_MIN></WARN_MIN>
    <WARN_MAX></WARN_MAX>
    <WARN_RANGE_TYPE></WARN_RANGE_TYPE>
    <CRIT>80</CRIT>
    <CRIT_MIN></CRIT_MIN>
    <CRIT_MAX></CRIT_MAX>
    <CRIT_RANGE_TYPE></CRIT_RANGE_TYPE>
    <MIN>0</MIN>
    <MAX>8</MAX>
  </DATASOURCE>
  <DATASOURCE>
    <TEMPLATE>check_mk-cpu.loads</TEMPLATE>
    <RRDFILE>/omd/sites/raw/var/pnp4nagios/perfdata/localhost/CPU_load_load15.rrd</RRDFILE>
    <RRD_STORAGE_TYPE>MULTIPLE</RRD_STORAGE_TYPE>
    <RRD_HEARTBEAT>8460</RRD_HEARTBEAT>
    <IS_MULTI>0</IS_MULTI>
    <DS>1</DS>
    <NAME>load15</NAME>
    <LABEL>load15</LABEL>
    <UNIT></UNIT>
    <ACT>0.62</ACT>
    <WARN>40</WARN>
    <WARN_MIN></WARN_MIN>
    <WARN_MAX></WARN_MAX>
    <WARN_RANGE_TYPE></WARN_RANGE_TYPE>
    <CRIT>80</CRIT>
    <CRIT_MIN></CRIT_MIN>
    <CRIT_MAX></CRIT_MAX>
    <CRIT_RANGE_TYPE></CRIT_RANGE_TYPE>
    <MIN>0</MIN>
    <MAX>8</MAX>
  </DATASOURCE>
  <RRD>
    <RC>0</RC>
    <TXT>successful updated</TXT>
  </RRD>
  <NAGIOS_AUTH_HOSTNAME>localhost</NAGIOS_AUTH_HOSTNAME>
  <NAGIOS_AUTH_SERVICEDESC>CPU load</NAGIOS_AUTH_SERVICEDESC>
  <NAGIOS_CHECK_COMMAND>check_mk-cpu.loads</NAGIOS_CHECK_COMMAND>
  <NAGIOS_DATATYPE>SERVICEPERFDATA</NAGIOS_DATATYPE>
  <NAGIOS_DISP_HOSTNAME>localhost</NAGIOS_DISP_HOSTNAME>
  <NAGIOS_DISP_SERVICEDESC>CPU load</NAGIOS_DISP_SERVICEDESC>
  <NAGIOS_HOSTNAME>localhost</NAGIOS_HOSTNAME>
  <NAGIOS_MULTI_PARENT></NAGIOS_MULTI_PARENT>
  <NAGIOS_PERFDATA>load1=0.93;40;80;0;8 load5=0.87;40;80;0;8 load15=0.62;40;80;0;8 </NAGIOS_PERFDATA>
  <NAGIOS_RRDFILE></NAGIOS_RRDFILE>
  <NAGIOS_SERVICECHECKCOMMAND>check_mk-cpu.loads</NAGIOS_SERVICECHECKCOMMAND>
  <NAGIOS_SERVICEDESC>CPU_load</NAGIOS_SERVICEDESC>
  <NAGIOS_SERVICEPERFDATA>load1=0.93;40;80;0;8 load5=0.87;40;80;0;8 load15=0.62;40;80;0;8</NAGIOS_SERVICEPERFDATA>
  <NAGIOS_SERVICESTATETYPE>1</NAGIOS_SERVICESTATETYPE>
  <NAGIOS_TIMET>1562743359</NAGIOS_TIMET>
  <NAGIOS_XMLFILE>/omd/sites/raw/var/pnp4nagios/perfdata/localhost/CPU_load.xml</NAGIOS_XMLFILE>
  <XML>
   <VERSION>4</VERSION>
  </XML>
</NAGIOS>\n"""

NAGIOS_SERVICE_XML_MULTIPLE_METRIC_RENAME = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<NAGIOS>
  <DATASOURCE>
    <TEMPLATE>check_mk-cpu.loads</TEMPLATE>
    <RRDFILE>/omd/sites/raw/var/pnp4nagios/perfdata/localhost/CPU_load_shortterm.rrd</RRDFILE>
    <RRD_STORAGE_TYPE>MULTIPLE</RRD_STORAGE_TYPE>
    <RRD_HEARTBEAT>8460</RRD_HEARTBEAT>
    <IS_MULTI>0</IS_MULTI>
    <DS>1</DS>
    <NAME>shortterm</NAME>
    <LABEL>shortterm</LABEL>
    <UNIT></UNIT>
    <ACT>0.93</ACT>
    <WARN>40</WARN>
    <WARN_MIN></WARN_MIN>
    <WARN_MAX></WARN_MAX>
    <WARN_RANGE_TYPE></WARN_RANGE_TYPE>
    <CRIT>80</CRIT>
    <CRIT_MIN></CRIT_MIN>
    <CRIT_MAX></CRIT_MAX>
    <CRIT_RANGE_TYPE></CRIT_RANGE_TYPE>
    <MIN>0</MIN>
    <MAX>8</MAX>
  </DATASOURCE>
  <DATASOURCE>
    <TEMPLATE>check_mk-cpu.loads</TEMPLATE>
    <RRDFILE>/omd/sites/raw/var/pnp4nagios/perfdata/localhost/CPU_load_load5.rrd</RRDFILE>
    <RRD_STORAGE_TYPE>MULTIPLE</RRD_STORAGE_TYPE>
    <RRD_HEARTBEAT>8460</RRD_HEARTBEAT>
    <IS_MULTI>0</IS_MULTI>
    <DS>1</DS>
    <NAME>load5</NAME>
    <LABEL>load5</LABEL>
    <UNIT></UNIT>
    <ACT>0.87</ACT>
    <WARN>40</WARN>
    <WARN_MIN></WARN_MIN>
    <WARN_MAX></WARN_MAX>
    <WARN_RANGE_TYPE></WARN_RANGE_TYPE>
    <CRIT>80</CRIT>
    <CRIT_MIN></CRIT_MIN>
    <CRIT_MAX></CRIT_MAX>
    <CRIT_RANGE_TYPE></CRIT_RANGE_TYPE>
    <MIN>0</MIN>
    <MAX>8</MAX>
  </DATASOURCE>
  <DATASOURCE>
    <TEMPLATE>check_mk-cpu.loads</TEMPLATE>
    <RRDFILE>/omd/sites/raw/var/pnp4nagios/perfdata/localhost/CPU_load_load15.rrd</RRDFILE>
    <RRD_STORAGE_TYPE>MULTIPLE</RRD_STORAGE_TYPE>
    <RRD_HEARTBEAT>8460</RRD_HEARTBEAT>
    <IS_MULTI>0</IS_MULTI>
    <DS>1</DS>
    <NAME>load15</NAME>
    <LABEL>load15</LABEL>
    <UNIT></UNIT>
    <ACT>0.62</ACT>
    <WARN>40</WARN>
    <WARN_MIN></WARN_MIN>
    <WARN_MAX></WARN_MAX>
    <WARN_RANGE_TYPE></WARN_RANGE_TYPE>
    <CRIT>80</CRIT>
    <CRIT_MIN></CRIT_MIN>
    <CRIT_MAX></CRIT_MAX>
    <CRIT_RANGE_TYPE></CRIT_RANGE_TYPE>
    <MIN>0</MIN>
    <MAX>8</MAX>
  </DATASOURCE>
  <RRD>
    <RC>0</RC>
    <TXT>successful updated</TXT>
  </RRD>
  <NAGIOS_AUTH_HOSTNAME>localhost</NAGIOS_AUTH_HOSTNAME>
  <NAGIOS_AUTH_SERVICEDESC>CPU load</NAGIOS_AUTH_SERVICEDESC>
  <NAGIOS_CHECK_COMMAND>check_mk-cpu.loads</NAGIOS_CHECK_COMMAND>
  <NAGIOS_DATATYPE>SERVICEPERFDATA</NAGIOS_DATATYPE>
  <NAGIOS_DISP_HOSTNAME>localhost</NAGIOS_DISP_HOSTNAME>
  <NAGIOS_DISP_SERVICEDESC>CPU load</NAGIOS_DISP_SERVICEDESC>
  <NAGIOS_HOSTNAME>localhost</NAGIOS_HOSTNAME>
  <NAGIOS_MULTI_PARENT></NAGIOS_MULTI_PARENT>
  <NAGIOS_PERFDATA>shortterm=0.93;40;80;0;8 load5=0.87;40;80;0;8 load15=0.62;40;80;0;8 </NAGIOS_PERFDATA>
  <NAGIOS_RRDFILE></NAGIOS_RRDFILE>
  <NAGIOS_SERVICECHECKCOMMAND>check_mk-cpu.loads</NAGIOS_SERVICECHECKCOMMAND>
  <NAGIOS_SERVICEDESC>CPU_load</NAGIOS_SERVICEDESC>
  <NAGIOS_SERVICEPERFDATA>shortterm=0.93;40;80;0;8 load5=0.87;40;80;0;8 load15=0.62;40;80;0;8</NAGIOS_SERVICEPERFDATA>
  <NAGIOS_SERVICESTATETYPE>1</NAGIOS_SERVICESTATETYPE>
  <NAGIOS_TIMET>1562743359</NAGIOS_TIMET>
  <NAGIOS_XMLFILE>/omd/sites/raw/var/pnp4nagios/perfdata/localhost/CPU_load.xml</NAGIOS_XMLFILE>
  <XML>
   <VERSION>4</VERSION>
  </XML>
</NAGIOS>\n"""


@pytest.mark.parametrize(
    "perfvar, newvar, xml_file, result",
    [
        (
            "load1",
            "shortterm",
            NAGIOS_SERVICE_XML_MULTIPLE,
            NAGIOS_SERVICE_XML_MULTIPLE_METRIC_RENAME,
        )
    ],
)
def test_update_metric_pnp_xml_info_file(tmp_path, perfvar, newvar, xml_file, result):
    filepath = tmp_path / "pnp.xml"
    with filepath.open("w") as fid:
        fid.write(xml_file)

    rrdfiles = rrd.update_metric_pnp_xml_info_file(perfvar, newvar, filepath.as_posix())
    with filepath.open("r") as fid:
        new = fid.read()

    assert new == result

    prefix_len = len(os.path.commonprefix(rrdfiles))
    assert rrdfiles[0][prefix_len:] == perfvar + ".rrd"
    assert rrdfiles[1][prefix_len:] == newvar + ".rrd"
