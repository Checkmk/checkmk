#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK vSphere Special Agent"""

import argparse
import collections
import json
import re
import socket
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import datetime, timedelta
from typing import Any
from xml.dom import minidom

# TODO: minicompat include internal impl details. But NodeList is only defined there for <3.11
from xml.dom.minicompat import NodeList

import dateutil.parser
import requests
import urllib3

import cmk.utils.password_store
import cmk.utils.paths

import cmk.special_agents.v0_unstable.misc as utils
from cmk.special_agents.v0_unstable.request_helper import HostnameValidationAdapter

#   .--defines-------------------------------------------------------------.
#   |                      _       __ _                                    |
#   |                   __| | ___ / _(_)_ __   ___  ___                    |
#   |                  / _` |/ _ \ |_| | '_ \ / _ \/ __|                   |
#   |                 | (_| |  __/  _| | | | |  __/\__ \                   |
#   |                  \__,_|\___|_| |_|_| |_|\___||___/                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

__version__ = "2.4.0p21"

USER_AGENT = f"checkmk-special-vsphere-{__version__}"

AGENT_TMP_PATH = cmk.utils.paths.tmp_dir / "agents/agent_vsphere"

REQUESTED_COUNTERS_KEYS = (
    "disk.numberReadAveraged",
    "disk.numberWriteAveraged",
    "disk.read",
    "disk.write",
    "disk.deviceLatency",
    "net.usage",
    "net.packetsRx",
    "net.packetsTx",
    "net.received",
    "net.transmitted",
    "net.droppedRx",
    "net.droppedTx",
    "net.bytesRx",
    "net.bytesTx",
    "net.broadcastRx",
    "net.broadcastTx",
    "net.multicastRx",
    "net.multicastTx",
    "net.errorsRx",
    "net.errorsTx",
    "net.unknownProtos",
    "mem.swapused",
    "mem.swapin",
    "mem.swapout",
    "sys.uptime",
    "sys.resourceMemConsumed",
    "datastore.read",
    "datastore.write",
    "datastore.totalReadLatency",
    "datastore.totalWriteLatency",
    "datastore.sizeNormalizedDatastoreLatency",
    "datastore.datastoreReadIops",
    "datastore.datastoreWriteIops",
)

COOKIE_MAX_AGE_HOURS = 4


class SoapTemplates:
    # fmt: off
    SYSTEMINFO = (
        '<ns1:RetrieveServiceContent xsi:type="ns1:RetrieveServiceContentRequestType">'
        '  <ns1:_this type="ServiceInstance">ServiceInstance</ns1:_this>'
        '</ns1:RetrieveServiceContent>'
    )
    LOGIN = (
        '<ns1:Login xsi:type="ns1:LoginRequestType">'
        '  <ns1:_this type="SessionManager">%(sessionManager)s</ns1:_this>'
        '  <ns1:userName>%%(username)s</ns1:userName>'
        '  <ns1:password>%%(password)s</ns1:password>'
        '</ns1:Login>'
    )
    SYSTEMTIME = (
        '<ns1:CurrentTime xsi:type="ns1:CurrentTimeRequestType">'
        '  <ns1:_this type="ServiceInstance">ServiceInstance</ns1:_this>'
        '</ns1:CurrentTime>'
    )
    HOSTSYSTEMS = (
        '<ns1:RetrievePropertiesEx xsi:type="ns1:RetrievePropertiesExRequestType">'
        '  <ns1:_this type="PropertyCollector">%(propertyCollector)s</ns1:_this>'
        '  <ns1:specSet>'
        '    <ns1:propSet>'
        '      <ns1:type>HostSystem</ns1:type>'
        '      <ns1:pathSet>name</ns1:pathSet>'
        '    </ns1:propSet>'
        '    <ns1:objectSet>'
        '      <ns1:obj type="Folder">%(rootFolder)s</ns1:obj>'
        '      <ns1:skip>false</ns1:skip>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>visitFolders</ns1:name>'
        '        <ns1:type>Folder</ns1:type>'
        '        <ns1:path>childEntity</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>dcToHf</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>dcToVmf</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>crToH</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>crToRp</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>dcToDs</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>hToVm</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>rpToVm</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToVmf</ns1:name><ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>vmFolder</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToDs</ns1:name><ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>datastore</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToHf</ns1:name><ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>hostFolder</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToH</ns1:name>'
        '        <ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>host</ns1:path><ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToRp</ns1:name><ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>resourcePool</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>rpToRp</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>rpToVm</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '         <ns1:name>rpToRp</ns1:name><ns1:type>ResourcePool</ns1:type>'
        '         <ns1:path>resourcePool</ns1:path><ns1:skip>false</ns1:skip>'
        '         <ns1:selectSet><ns1:name>rpToRp</ns1:name></ns1:selectSet>'
        '         <ns1:selectSet><ns1:name>rpToVm</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '         <ns1:name>hToVm</ns1:name><ns1:type>HostSystem</ns1:type>'
        '         <ns1:path>vm</ns1:path><ns1:skip>false</ns1:skip>'
        '         <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>rpToVm</ns1:name><ns1:type>ResourcePool</ns1:type>'
        '        <ns1:path>vm</ns1:path><ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '    </ns1:objectSet>'
        '  </ns1:specSet><ns1:options></ns1:options>'
        '</ns1:RetrievePropertiesEx>'
    )
    DATASTORES = (
        '<ns1:RetrievePropertiesEx xsi:type="ns1:RetrievePropertiesExRequestType">'
        '  <ns1:_this type="PropertyCollector">%(propertyCollector)s</ns1:_this>'
        '  <ns1:specSet>'
        '    <ns1:propSet>'
        '      <ns1:type>Datastore</ns1:type>'
        '      <ns1:pathSet>name</ns1:pathSet>'
        '      <ns1:pathSet>summary.freeSpace</ns1:pathSet>'
        '      <ns1:pathSet>summary.capacity</ns1:pathSet>'
        '      <ns1:pathSet>summary.uncommitted</ns1:pathSet>'
        '      <ns1:pathSet>summary.url</ns1:pathSet>'
        '      <ns1:pathSet>summary.accessible</ns1:pathSet>'
        '      <ns1:pathSet>summary.type</ns1:pathSet>'
        '      <ns1:pathSet>summary.maintenanceMode</ns1:pathSet>'
        '    </ns1:propSet>'
        '    <ns1:objectSet><ns1:obj type="Folder">%(rootFolder)s</ns1:obj>'
        '      <ns1:skip>false</ns1:skip>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>visitFolders</ns1:name>'
        '        <ns1:type>Folder</ns1:type>'
        '        <ns1:path>childEntity</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>dcToHf</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>dcToVmf</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>crToH</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>crToRp</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>dcToDs</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>hToVm</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>rpToVm</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToVmf</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>vmFolder</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToDs</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>datastore</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToHf</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>hostFolder</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToH</ns1:name>'
        '        <ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>host</ns1:path><ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToRp</ns1:name><ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>resourcePool</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>rpToRp</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>rpToVm</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>rpToRp</ns1:name><ns1:type>ResourcePool</ns1:type>'
        '        <ns1:path>resourcePool</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>rpToRp</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>rpToVm</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>hToVm</ns1:name><ns1:type>HostSystem</ns1:type>'
        '        <ns1:path>vm</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>rpToVm</ns1:name><ns1:type>ResourcePool</ns1:type>'
        '        <ns1:path>vm</ns1:path><ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '    </ns1:objectSet>'
        '  </ns1:specSet><ns1:options></ns1:options>'
        '</ns1:RetrievePropertiesEx>'
    )
    LICENSESUSED = (
        '<ns1:RetrievePropertiesEx xsi:type="ns1:RetrievePropertiesExRequestType">'
        '  <ns1:_this type="PropertyCollector">%(propertyCollector)s</ns1:_this>'
        '  <ns1:specSet>'
        '    <ns1:propSet>'
        '      <ns1:type>LicenseManager</ns1:type>'
        '      <all>0</all>'
        '      <ns1:pathSet>licenses</ns1:pathSet>'
        '    </ns1:propSet>'
        '    <ns1:objectSet>'
        '      <ns1:obj type="LicenseManager">%(licenseManager)s</ns1:obj>'
        '    </ns1:objectSet>'
        '  </ns1:specSet>'
        '  <ns1:options/>'
        '</ns1:RetrievePropertiesEx>'
    )
    PERFCOUNTERSUMMARY = (
        '<ns1:QueryPerfProviderSummary xsi:type="ns1:QueryPerfProviderSummaryRequestType">'
        '  <ns1:_this type="PerformanceManager">%(perfManager)s</ns1:_this>'
        '  <ns1:entity type="HostSystem">%%(esxhost)s</ns1:entity>'
        '</ns1:QueryPerfProviderSummary>'
    )
    PERFCOUNTERSYNTAX = (
        '<ns1:QueryPerfCounter xsi:type="ns1:QueryPerfCounterRequestType">'
        '  <ns1:_this type="PerformanceManager">%(perfManager)s</ns1:_this>%%(counters)s'
        '</ns1:QueryPerfCounter>'
    )
    PERFCOUNTERAVAIL = (
        '<ns1:QueryAvailablePerfMetric xsi:type="ns1:QueryAvailablePerfMetricRequestType">'
        '  <ns1:_this type="PerformanceManager">%(perfManager)s</ns1:_this>'
        '  <ns1:entity type="HostSystem">%%(esxhost)s</ns1:entity>'
        '  <ns1:intervalId>20</ns1:intervalId>'
        '</ns1:QueryAvailablePerfMetric>'
    )
    PERFCOUNTERDATA = (
        '<ns1:QueryPerf xsi:type="ns1:QueryPerfRequestType">'
        '  <ns1:_this type="PerformanceManager">%(perfManager)s</ns1:_this>'
        '  <ns1:querySpec>'
        '    <ns1:entity type="HostSystem">%%(esxhost)s</ns1:entity>'
        '    <ns1:maxSample>%%(samples)s</ns1:maxSample>%%(counters)s'
        '    <ns1:intervalId>20</ns1:intervalId>'
        '  </ns1:querySpec>'
        '</ns1:QueryPerf>'
    )
    NETWORKSYSTEM = (
        '<ns1:RetrievePropertiesEx xsi:type="ns1:RetrievePropertiesExRequestType">'
        '  <ns1:_this type="PropertyCollector">%(propertyCollector)s</ns1:_this>'
        '  <ns1:specSet>'
        '    <ns1:propSet>'
        '      <ns1:type>HostNetworkSystem</ns1:type><all>0</all>'
        '      <ns1:pathSet>networkInfo</ns1:pathSet>'
        '    </ns1:propSet>'
        '    <ns1:objectSet>'
        '      <ns1:obj type="HostNetworkSystem">networkSystem</ns1:obj>'
        '    </ns1:objectSet>'
        '  </ns1:specSet><ns1:options></ns1:options>'
        '</ns1:RetrievePropertiesEx>'
    )
    ESXHOSTDETAILS = (
        '<ns1:RetrievePropertiesEx xsi:type="ns1:RetrievePropertiesExRequestType">'
        '  <ns1:_this type="PropertyCollector">%(propertyCollector)s</ns1:_this>'
        '  <ns1:specSet>'
        '    <ns1:propSet>'
        '      <ns1:type>HostSystem</ns1:type>'
        '      <ns1:pathSet>summary.quickStats.overallMemoryUsage</ns1:pathSet>'
        '      <ns1:pathSet>hardware.cpuPkg</ns1:pathSet>'
        '      <ns1:pathSet>hardware.pciDevice</ns1:pathSet>'
        '      <ns1:pathSet>runtime.powerState</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.overallCpuUsage</ns1:pathSet>'
        '      <ns1:pathSet>hardware.biosInfo.biosVersion</ns1:pathSet>'
        '      <ns1:pathSet>hardware.biosInfo.releaseDate</ns1:pathSet>'
        '      <ns1:pathSet>hardware.cpuInfo.hz</ns1:pathSet>'
        '      <ns1:pathSet>hardware.cpuInfo.numCpuThreads</ns1:pathSet>'
        '      <ns1:pathSet>hardware.cpuInfo.numCpuPackages</ns1:pathSet>'
        '      <ns1:pathSet>hardware.cpuInfo.numCpuCores</ns1:pathSet>'
        '      <ns1:pathSet>config.storageDevice.multipathInfo</ns1:pathSet>'
        '      <ns1:pathSet>hardware.systemInfo.model</ns1:pathSet>'
        '      <ns1:pathSet>hardware.systemInfo.uuid</ns1:pathSet>'
        '      <ns1:pathSet>hardware.systemInfo.otherIdentifyingInfo</ns1:pathSet>'
        '      <ns1:pathSet>hardware.systemInfo.vendor</ns1:pathSet>'
        '      <ns1:pathSet>name</ns1:pathSet>'
        '      <ns1:pathSet>overallStatus</ns1:pathSet>'
        '      <ns1:pathSet>runtime.healthSystemRuntime.systemHealthInfo.numericSensorInfo</ns1:pathSet>'
        '      <ns1:pathSet>runtime.healthSystemRuntime.hardwareStatusInfo.storageStatusInfo</ns1:pathSet>'
        '      <ns1:pathSet>runtime.healthSystemRuntime.hardwareStatusInfo.cpuStatusInfo</ns1:pathSet>'
        '      <ns1:pathSet>runtime.healthSystemRuntime.hardwareStatusInfo.memoryStatusInfo</ns1:pathSet>'
        '      <ns1:pathSet>runtime.inMaintenanceMode</ns1:pathSet>'
        '      <ns1:pathSet>hardware.memorySize</ns1:pathSet>'
        '      <ns1:pathSet>config.product.vendor</ns1:pathSet>'
        '      <ns1:pathSet>config.product.licenseProductName</ns1:pathSet>'
        '      <ns1:pathSet>config.product.osType</ns1:pathSet>'
        '      <ns1:pathSet>config.product.version</ns1:pathSet>'
        '      <ns1:pathSet>config.product.build</ns1:pathSet>'
        '    </ns1:propSet>'
        '    <ns1:objectSet>'
        '      <ns1:obj type="Folder">%(rootFolder)s</ns1:obj><ns1:skip>false</ns1:skip>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>visitFolders</ns1:name>'
        '        <ns1:type>Folder</ns1:type><ns1:path>childEntity</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>dcToHf</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>dcToVmf</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>crToH</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>crToRp</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>dcToDs</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>hToVm</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>rpToVm</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToVmf</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>vmFolder</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToDs</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>datastore</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToHf</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>hostFolder</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToH</ns1:name>'
        '        <ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>host</ns1:path><ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToRp</ns1:name>'
        '        <ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>resourcePool</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>rpToRp</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>rpToVm</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>rpToRp</ns1:name>'
        '        <ns1:type>ResourcePool</ns1:type>'
        '        <ns1:path>resourcePool</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>rpToRp</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>rpToVm</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>hToVm</ns1:name>'
        '        <ns1:type>HostSystem</ns1:type>'
        '        <ns1:path>vm</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>rpToVm</ns1:name>'
        '        <ns1:type>ResourcePool</ns1:type>'
        '        <ns1:path>vm</ns1:path><ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '    </ns1:objectSet>'
        '  </ns1:specSet><ns1:options></ns1:options>'
        '</ns1:RetrievePropertiesEx>'
    )
    VMDETAILS = (
        '<ns1:RetrievePropertiesEx xsi:type="ns1:RetrievePropertiesExRequestType">'
        '  <ns1:_this type="PropertyCollector">%(propertyCollector)s</ns1:_this>'
        '  <ns1:specSet>'
        '    <ns1:propSet>'
        '      <ns1:type>VirtualMachine</ns1:type>'
        '      <ns1:pathSet>summary.config.ftInfo.role</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.consumedOverheadMemory</ns1:pathSet>'
        '      <ns1:pathSet>config.hardware.numCPU</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.overallCpuDemand</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.distributedCpuEntitlement</ns1:pathSet>'
        '      <ns1:pathSet>runtime.host</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.distributedMemoryEntitlement</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.uptimeSeconds</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.sharedMemory</ns1:pathSet>'
        '      <ns1:pathSet>config.hardware.memoryMB</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.privateMemory</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.balloonedMemory</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.staticMemoryEntitlement</ns1:pathSet>'
        '      <ns1:pathSet>runtime.powerState</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.overallCpuUsage</ns1:pathSet>'
        '      <ns1:pathSet>config.hardware.numCoresPerSocket</ns1:pathSet>'
        '      <ns1:pathSet>config.hardware.device</ns1:pathSet>'
        '      <ns1:pathSet>config.template</ns1:pathSet>'
        '      <ns1:pathSet>guest.toolsVersion</ns1:pathSet>'
        '      <ns1:pathSet>guestHeartbeatStatus</ns1:pathSet>'
        '      <ns1:pathSet>name</ns1:pathSet>'
        '      <ns1:pathSet>summary.guest.hostName</ns1:pathSet>'
        '      <ns1:pathSet>config.guestFullName</ns1:pathSet>'  # Guest OS
        '      <ns1:pathSet>config.version</ns1:pathSet>'  # Compatibility
        '      <ns1:pathSet>config.uuid</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.compressedMemory</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.swappedMemory</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.guestMemoryUsage</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.staticCpuEntitlement</ns1:pathSet>'
        '      <ns1:pathSet>summary.quickStats.hostMemoryUsage</ns1:pathSet>'
        '      <ns1:pathSet>snapshot.rootSnapshotList</ns1:pathSet>'
        '      <ns1:pathSet>config.datastoreUrl</ns1:pathSet>'
        '      <ns1:pathSet>guest.toolsVersionStatus</ns1:pathSet>'
        '    </ns1:propSet>'
        '    <ns1:objectSet><ns1:obj type="Folder">%(rootFolder)s</ns1:obj><ns1:skip>false</ns1:skip>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>visitFolders</ns1:name>'
        '        <ns1:type>Folder</ns1:type>'
        '        <ns1:path>childEntity</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>dcToHf</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>dcToVmf</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>crToH</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>crToRp</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>dcToDs</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>hToVm</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>rpToVm</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToVmf</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>vmFolder</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToDs</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>datastore</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToHf</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>hostFolder</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToH</ns1:name>'
        '        <ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>host</ns1:path><ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToRp</ns1:name>'
        '        <ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>resourcePool</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>rpToRp</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>rpToVm</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>rpToRp</ns1:name>'
        '        <ns1:type>ResourcePool</ns1:type>'
        '        <ns1:path>resourcePool</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>rpToRp</ns1:name></ns1:selectSet>'
        '        <ns1:selectSet><ns1:name>rpToVm</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>hToVm</ns1:name>'
        '        <ns1:type>HostSystem</ns1:type>'
        '        <ns1:path>vm</ns1:path><ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet><ns1:name>visitFolders</ns1:name></ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>rpToVm</ns1:name>'
        '        <ns1:type>ResourcePool</ns1:type>'
        '        <ns1:path>vm</ns1:path><ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '    </ns1:objectSet>'
        '  </ns1:specSet><ns1:options></ns1:options>'
        '</ns1:RetrievePropertiesEx>'
    )
    CONTINUETOKEN = (
        '<ns1:ContinueRetrievePropertiesEx xsi:type="ns1:ContinueRetrievePropertiesExRequestType">'
        '  <ns1:_this type="PropertyCollector">%(propertyCollector)s</ns1:_this>'
        '  <ns1:token>%%(token)s</ns1:token>'
        '</ns1:ContinueRetrievePropertiesEx>'
    )
    DATACENTERS = (
        '<ns1:RetrievePropertiesEx xsi:type="ns1:RetrievePropertiesExRequestType">'
        '  <ns1:_this type="PropertyCollector">%(propertyCollector)s</ns1:_this>'
        '  <ns1:specSet>'
        '    <ns1:propSet>'
        '      <ns1:type>Datacenter</ns1:type>'
        '      <ns1:pathSet>name</ns1:pathSet>'
        '    </ns1:propSet>'
        '    <ns1:objectSet>'
        '      <ns1:obj type="Folder">%(rootFolder)s</ns1:obj>'
        '      <ns1:skip>false</ns1:skip>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>visitFolders</ns1:name>'
        '        <ns1:type>Folder</ns1:type>'
        '        <ns1:path>childEntity</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>dcToHf</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>dcToVmf</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>crToH</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>crToRp</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>dcToDs</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>hToVm</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToVm</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToVmf</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>vmFolder</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToDs</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>datastore</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToHf</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>hostFolder</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToH</ns1:name>'
        '        <ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>host</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToRp</ns1:name>'
        '        <ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>resourcePool</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToRp</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToVm</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>rpToRp</ns1:name>'
        '        <ns1:type>ResourcePool</ns1:type>'
        '        <ns1:path>resourcePool</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToRp</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToVm</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>hToVm</ns1:name>'
        '        <ns1:type>HostSystem</ns1:type>'
        '        <ns1:path>vm</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>rpToVm</ns1:name>'
        '        <ns1:type>ResourcePool</ns1:type>'
        '        <ns1:path>vm</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '    </ns1:objectSet>'
        '  </ns1:specSet>'
        '  <ns1:options/>'
        '</ns1:RetrievePropertiesEx>'
    )
    CLUSTERSOFDATACENTER = (
        '<ns1:RetrievePropertiesEx xsi:type="ns1:RetrievePropertiesExRequestType">'
        '  <ns1:_this type="PropertyCollector">propertyCollector</ns1:_this>'
        '  <ns1:specSet>'
        '    <ns1:propSet>'
        '      <ns1:type>ClusterComputeResource</ns1:type>'
        '      <ns1:pathSet>name</ns1:pathSet>'
        '    </ns1:propSet>'
        '    <ns1:objectSet>'
        '      <ns1:obj type="Datacenter">%%(datacenter)s</ns1:obj>'
        '      <ns1:skip>false</ns1:skip>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>visitFolders</ns1:name>'
        '        <ns1:type>Folder</ns1:type>'
        '        <ns1:path>childEntity</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>dcToHf</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>dcToVmf</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>crToH</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>crToRp</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>dcToDs</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>hToVm</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToVm</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToVmf</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>vmFolder</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToDs</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>datastore</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToHf</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>hostFolder</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToH</ns1:name>'
        '        <ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>host</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToRp</ns1:name>'
        '        <ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>resourcePool</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToRp</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToVm</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>rpToRp</ns1:name>'
        '        <ns1:type>ResourcePool</ns1:type>'
        '        <ns1:path>resourcePool</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToRp</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToVm</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>hToVm</ns1:name>'
        '        <ns1:type>HostSystem</ns1:type>'
        '        <ns1:path>vm</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>rpToVm</ns1:name>'
        '        <ns1:type>ResourcePool</ns1:type>'
        '        <ns1:path>vm</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '    </ns1:objectSet>'
        '  </ns1:specSet>'
        '  <ns1:options/>'
        '</ns1:RetrievePropertiesEx>'
    )
    ESXHOSTSOFCLUSTER = (
        '<ns1:RetrievePropertiesEx xsi:type="ns1:RetrievePropertiesExRequestType">'
        '  <ns1:_this type="PropertyCollector">propertyCollector</ns1:_this>'
        '  <ns1:specSet>'
        '    <ns1:propSet>'
        '      <ns1:type>HostSystem</ns1:type>'
        '      <ns1:pathSet>name</ns1:pathSet>'
        '    </ns1:propSet>'
        '    <ns1:objectSet>'
        '      <ns1:obj type="ClusterComputeResource">%%(clustername)s</ns1:obj>'
        '      <ns1:skip>false</ns1:skip>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>visitFolders</ns1:name>'
        '        <ns1:type>Folder</ns1:type>'
        '        <ns1:path>childEntity</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>dcToHf</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>dcToVmf</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>crToH</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>crToRp</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>dcToDs</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>hToVm</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToVm</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToVmf</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>vmFolder</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToDs</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>datastore</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>dcToHf</ns1:name>'
        '        <ns1:type>Datacenter</ns1:type>'
        '        <ns1:path>hostFolder</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToH</ns1:name>'
        '        <ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>host</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>crToRp</ns1:name>'
        '        <ns1:type>ComputeResource</ns1:type>'
        '        <ns1:path>resourcePool</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToRp</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToVm</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>rpToRp</ns1:name>'
        '        <ns1:type>ResourcePool</ns1:type>'
        '        <ns1:path>resourcePool</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToRp</ns1:name>'
        '        </ns1:selectSet>'
        '        <ns1:selectSet>'
        '          <ns1:name>rpToVm</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>hToVm</ns1:name>'
        '        <ns1:type>HostSystem</ns1:type>'
        '        <ns1:path>vm</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '        <ns1:selectSet>'
        '          <ns1:name>visitFolders</ns1:name>'
        '        </ns1:selectSet>'
        '      </ns1:selectSet>'
        '      <ns1:selectSet xsi:type="ns1:TraversalSpec">'
        '        <ns1:name>rpToVm</ns1:name>'
        '        <ns1:type>ResourcePool</ns1:type>'
        '        <ns1:path>vm</ns1:path>'
        '        <ns1:skip>false</ns1:skip>'
        '      </ns1:selectSet>'
        '    </ns1:objectSet>'
        '  </ns1:specSet>'
        '  <ns1:options/>'
        '</ns1:RetrievePropertiesEx>'
    )
    # fmt: on

    def __init__(self, system_fields: Mapping[str, str]) -> None:
        super().__init__()
        self.login = SoapTemplates.LOGIN % system_fields
        self.systemtime = SoapTemplates.SYSTEMTIME % system_fields
        self.hostsystems = SoapTemplates.HOSTSYSTEMS % system_fields
        self.datastores = SoapTemplates.DATASTORES % system_fields
        self.licensesused = SoapTemplates.LICENSESUSED % system_fields
        self.perfcountersummary = SoapTemplates.PERFCOUNTERSUMMARY % system_fields
        self.perfcountersyntax = SoapTemplates.PERFCOUNTERSYNTAX % system_fields
        self.perfcounteravail = SoapTemplates.PERFCOUNTERAVAIL % system_fields
        self.perfcounterdata = SoapTemplates.PERFCOUNTERDATA % system_fields
        self.networksystem = SoapTemplates.NETWORKSYSTEM % system_fields
        self.esxhostdetails = SoapTemplates.ESXHOSTDETAILS % system_fields
        self.vmdetails = SoapTemplates.VMDETAILS % system_fields
        self.continuetoken = SoapTemplates.CONTINUETOKEN % system_fields
        self.datacenters = SoapTemplates.DATACENTERS % system_fields
        self.clustersofdatacenter = SoapTemplates.CLUSTERSOFDATACENTER % system_fields
        self.esxhostsofcluster = SoapTemplates.ESXHOSTSOFCLUSTER % system_fields


# .
#   .--args----------------------------------------------------------------.
#   |                                                                      |
#   |                          __ _ _ __ __ _ ___                          |
#   |                         / _` | '__/ _` / __|                         |
#   |                        | (_| | | | (_| \__ \                         |
#   |                         \__,_|_|  \__, |___/                         |
#   |                                   |___/                              |
#   '----------------------------------------------------------------------'


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    # flags
    parser.add_argument(
        "--debug", action="store_true", help="""Debug mode: let Python exceptions come through"""
    )
    parser.add_argument(
        "--no-cert-check",
        action="store_true",
        help="""Disables the checking of the servers ssl certificate""",
    )
    parser.add_argument(
        "--cert-server-name",
        help="""Expect this as the servers name in the ssl certificate. Overrides '--no-cert-check'.""",
    )
    parser.add_argument(
        "-D",
        "--direct",
        action="store_true",
        help="""Assume a directly queried host system (no vCenter). In this we expect data about
        only one HostSystem to be found and do not create piggy host data for that host.""",
    )
    parser.add_argument(
        "-P",
        "--skip-placeholder-vm",
        action="store_true",
        help="""Skip placeholder virtualmachines. These backup vms are created by the Site
        Recovery Manager (SRM) and are identified by not having any assigned virtual disks.""",
    )

    # optional arguments
    parser.add_argument(
        "--vcrtrace",
        "--tracefile",
        action=utils.vcrtrace(before_record_request=ESXConnection.filter_request),
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=60,
        help="""Set the network timeout to vSphere to SECS seconds. The timeout is not only
        applied to the connection, but also to each individual subquery.""",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=443,
        help="""Alternative port number (default is 443 for the https connection).""",
    )
    parser.add_argument(
        "-S",
        "--spaces",
        choices=("cut", "underscore"),
        default="underscore",
        help="""How to handle spaces in host names. "cut": cut everyting after the first space,
        "underscore": replace with underscores. Default is "underscore".""",
    )
    parser.add_argument(
        "-i",
        "--modules",
        type=lambda s: s.split(","),
        default=["hostsystem", "virtualmachine", "datastore", "counters", "licenses"],
        help="""Modules to query. This is a comma separated list of hostsystem, virtualmachine,
        datastore, counters and licenses. Default is to query all modules.""",
    )
    parser.add_argument(
        "--vm_piggyname",
        choices=("hostname", "alias"),
        default="alias",
        help="""Here you can specify whether the virtual machines HOSTNAME or the ESX system
        ALIAS name for this machine should be used on creating piggyback data""",
    )
    parser.add_argument(
        "--vm_pwr_display",
        choices=("vm", "esxhost", "host"),
        default="host",
        help="""Specifies where the virtual machines power state should be shown. Default (host)
        is on the queried vCenter or ESX-Host. Possible WHERE options: esxhost - show
        on ESX host, vm - show on virtual machine, host - show on vCenter.""",
    )
    parser.add_argument(
        "--host_pwr_display",
        choices=("vm", "esxhost", "host"),
        default="host",
        help="""Specifies where the ESX hosts power state should be shown. Default (host)
        is on the queried vCenter or ESX-Host. Possible options: esxhost - show on ESX host,
        vm - show on virtual machine, host - show on vCenter.""",
    )
    parser.add_argument(
        "--snapshots-on-host",
        action="store_true",
        help="""If provided, virtual machine snapshots summary service will be generated on the ESX
        host. By default, it will only be created for the vCenter.""",
    )
    parser.add_argument(
        "-H",
        "--hostname",
        default=None,
        help="""Specify a host name. This is necessary if this is different from HOST.
        It is being used when outputting the hosts power state.""",
    )

    # optional arguments (from a coding point of view - should some of them be mandatory?)
    parser.add_argument("-u", "--user", default=None, help="""Username for vSphere login""")
    parser.add_argument(
        "-s", "--secret", default=None, help="""Secret/Password for vSphere login"""
    )

    # positional arguments
    parser.add_argument(
        "host_address", metavar="HOST", help="""Host name or IP address of VMware HostSystem"""
    )

    return parser.parse_args(argv)


# .
#   .--Connection----------------------------------------------------------.
#   |             ____                       _   _                         |
#   |            / ___|___  _ __  _ __   ___| |_(_) ___  _ __              |
#   |           | |   / _ \| '_ \| '_ \ / _ \ __| |/ _ \| '_ \             |
#   |           | |__| (_) | | | | | | |  __/ |_| | (_) | | | |            |
#   |            \____\___/|_| |_|_| |_|\___|\__|_|\___/|_| |_|            |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class ESXCookieInvalid(RuntimeError):
    pass


class ESXSession(requests.Session):
    """Encapsulates the Sessions with the ESX system"""

    ENVELOPE = (
        "<SOAP-ENV:Envelope"
        ' xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"'
        ' xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"'
        ' xmlns:ZSI="http://www.zolera.com/schemas/ZSI/"'
        ' xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/"'
        ' xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"'
        ' xmlns:xsd="http://www.w3.org/2001/XMLSchema"'
        ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<SOAP-ENV:Header></SOAP-ENV:Header>"
        '<SOAP-ENV:Body xmlns:ns1="urn:vim25">%s</SOAP-ENV:Body>'
        "</SOAP-ENV:Envelope>"
    )

    def __init__(self, address: str, port: int, *, cert_check: bool | str = True) -> None:
        super().__init__()

        if address.count(":") == 0:
            service = f"https://{address}:{port}"
        else:
            service = f"https://[{address}]:{port}"
        if cert_check is False:
            # Watch out: we must provide the verify keyword to every individual request call!
            # Else it will be overwritten by the REQUESTS_CA_BUNDLE env variable
            self.verify = False
            urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)
        elif isinstance(cert_check, str):
            self.mount(service, HostnameValidationAdapter(cert_check))

        self._post_url = f"{service}/sdk"
        self.headers.update(
            {
                "Content-Type": 'text/xml; charset="utf-8"',
                "SOAPAction": "urn:vim25/5.0",
                "User-Agent": USER_AGENT,
            }
        )

    def postsoap(self, request: str) -> requests.Response:
        soapdata = ESXSession.ENVELOPE % request
        # Watch out: we must provide the verify keyword to every individual request call!
        # Else it will be overwritten by the REQUESTS_CA_BUNDLE env variable
        return super().post(self._post_url, data=soapdata, verify=self.verify)


class ESXConnection:
    """Encapsulates the API calls to the ESX system"""

    ESCAPED_CHARS = {"&": "&amp;", ">": "&gt;", "<": "&lt;", "'": "&apos;", '"': "&quot;"}

    @staticmethod
    def filter_request(request):
        """Used for VCR. Filter password"""
        if b"<ns1:password>" in request.body:
            request.body = b"login request filtered out"
        return request

    @staticmethod
    def _escape_xml(text: str) -> str:
        return "".join(ESXConnection.ESCAPED_CHARS.get(c, c) for c in text)

    @staticmethod
    def _check_not_authenticated(text: str) -> None:
        if "NotAuthenticatedFault" in text:
            raise ESXCookieInvalid("No longer authenticated")

    def __init__(self, address: str, port: int, opt: argparse.Namespace) -> None:
        super().__init__()

        AGENT_TMP_PATH.mkdir(parents=True, exist_ok=True)

        self._server_cookie_path = AGENT_TMP_PATH / ("%s.cookie" % address)
        self._perf_samples_path = AGENT_TMP_PATH / ("%s.timer" % address)
        self._perf_samples: None | int = None

        self._session = ESXSession(
            address, port, cert_check=opt.cert_server_name or not opt.no_cert_check
        )
        self.system_info = self._fetch_systeminfo()
        self._soap_templates = SoapTemplates(self.system_info)

    def _fetch_systeminfo(self) -> dict[str, str]:
        """Retrieve basic data, which requires no login"""
        system_info = {}

        # Globals of ESX System. These settings are available after the first "systeminfo" query
        systemfields = [
            "apiVersion",
            "name",
            "rootFolder",
            "perfManager",
            "sessionManager",
            "licenseManager",
            "propertyCollector",
            "version",
            "build",
            "vendor",
            "osType",
        ]

        response = self._session.postsoap(SoapTemplates.SYSTEMINFO)
        for entry in systemfields:
            element = get_pattern(f"<{entry}.*>(.*)</{entry}>", response.text)
            if element:
                system_info[entry] = element[0]

        if not system_info:
            raise SystemExit(
                "Cannot get system info from vSphere server. Please check the IP and"
                "SSL certificate (if applicable) and try again. This error is not"
                " related to the login credentials. Response: [%s] %s"
                % (response.status_code, response.reason)
            )

        return system_info

    def query_server(self, method: str, **kwargs: str) -> str:
        payload = getattr(self._soap_templates, method) % kwargs

        response_data = []
        while True:
            response = self._session.postsoap(payload)
            response_data.append(response.text)
            self._check_not_authenticated(response_data[-1][:512])
            # Look for a <token>0</token> field.
            # If it exists not all data was transmitted and we need to start a
            # ContinueRetrievePropertiesExResponse query...
            token = re.findall("<token>(.*)</token>", response_data[-1][:512])
            if not token:
                break
            payload = self._soap_templates.continuetoken % {"token": token[0]}

        return "".join(response_data)

    @property
    def perf_samples(self) -> int:
        """Return and cache the needed number of real-time samples

        One real-time sample is 20 seconds. We set the time delta hard cap to 1 hour,
        an ESX system does not offer more than one hour of real time samples, anyway.
        """
        if self._perf_samples is not None:
            return self._perf_samples

        try:
            delta = min(3600.0, time.time() - self._perf_samples_path.stat().st_mtime)
        except OSError:
            delta = 60.0
        finally:
            self._perf_samples_path.touch()

        self._perf_samples = max(1, int(delta / 20.0))
        return self._perf_samples

    def login(self, user: str, password: str) -> None:
        if self._is_cookie_valid():
            self._session.headers["Cookie"] = self._server_cookie_path.read_text(encoding="utf-8")
            return

        auth = {"username": self._escape_xml(user), "password": self._escape_xml(password)}
        response = self._session.postsoap(self._soap_templates.login % auth)

        if response.status_code != 200:
            raise SystemExit(
                f"Cannot login to vSphere Server (reason: [{response.status_code}] {response.reason}). "
                "Please check the credentials."
            )

        if not (server_cookie := response.headers.get("set-cookie")):
            return

        self._server_cookie_path.write_text(server_cookie, encoding="utf-8")
        self._session.headers["Cookie"] = server_cookie

    def _is_cookie_valid(self) -> bool:
        if not self._server_cookie_path.exists():
            return False
        cookie_mtime = datetime.fromtimestamp(self._server_cookie_path.stat().st_mtime)
        return datetime.now() - cookie_mtime < timedelta(hours=COOKIE_MAX_AGE_HOURS)

    def delete_server_cookie(self) -> None:
        self._server_cookie_path.unlink(missing_ok=True)


# .
#   .--Counters------------------------------------------------------------.
#   |           ____                  _                                    |
#   |          / ___|___  _   _ _ __ | |_ ___ _ __ ___                     |
#   |         | |   / _ \| | | | '_ \| __/ _ \ '__/ __|                    |
#   |         | |__| (_) | |_| | | | | ||  __/ |  \__ \                    |
#   |          \____\___/ \__,_|_| |_|\__\___|_|  |___/                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def fetch_available_counters(
    connection: ESXConnection, hostsystems: Mapping[str, str]
) -> dict[str, dict[str, list[str]]]:
    counters_available_by_host: dict[str, dict[str, list[str]]] = {}
    for host in hostsystems:
        counter_avail_response = connection.query_server("perfcounteravail", esxhost=host)
        elements = get_pattern(
            "<counterId>([0-9]*)</counterId><instance>([^<]*)", counter_avail_response
        )

        data = counters_available_by_host.setdefault(host, {})
        for counter, instance in elements:
            data.setdefault(counter, []).append(instance)

    return counters_available_by_host


def fetch_counters_syntax(
    connection: ESXConnection, counter_ids: set[str]
) -> dict[str, dict[str, str]]:
    counters_list = ["<ns1:counterId>%s</ns1:counterId>" % id_ for id_ in counter_ids]

    response_text = connection.query_server("perfcountersyntax", counters="".join(counters_list))

    elements = get_pattern(
        "<returnval><key>(.*?)</key>.*?<key>(.*?)</key>.*?"
        "<key>(.*?)</key>.*?<key>(.*?)</key>.*?",
        response_text,
    )

    return {
        id_: {"key": ".".join((group, name)), "name": name, "group": group, "unit": unit}
        for id_, name, group, unit in elements
    }


def fetch_extra_interface_counters(connection: ESXConnection, opt: argparse.Namespace) -> list[str]:
    # Get additional interface counter info, this only works when querying ESX hosts
    # TODO: get this info from the vcenter
    if not opt.direct:
        return []

    net_extra_info = []
    networksystem_response = connection.query_server("networksystem")
    nic_objects = get_pattern("<pnic><key>(.*?)</pnic>", networksystem_response)
    for nic in nic_objects:
        nic_if = get_pattern("(.*?)</key><device>(.*?)</device>(.*)<mac>(.*?)</mac>", nic)
        if not nic_if:
            continue
        _unused, device, bandwidth_block, mac = nic_if[0]
        net_extra_info.append(f"net.macaddress|{device}|{mac}|mac")
        bandwidth = get_pattern("</driver><linkSpeed><speedMb>(.*?)</speedMb>", bandwidth_block)
        try:
            net_extra_info.append(f"net.bandwidth|{device}|{int(bandwidth[0]) * 1000000}|bytes")
        except (ValueError, IndexError):
            net_extra_info.append("net.state|%s|2|state" % device)
        else:
            net_extra_info.append("net.state|%s|1|state" % device)

    return net_extra_info


def fetch_counters(
    connection: ESXConnection, host: str, counters_selected: Sequence[tuple[str, list[str]]]
) -> list[tuple[str, str, list[str]]]:
    counter_data: list[str] = []
    for entry, instances in counters_selected:
        counter_data.extend(
            "<ns1:metricId><ns1:counterId>%s</ns1:counterId><ns1:instance>%s</ns1:instance>"
            "</ns1:metricId>" % (entry, instance)
            for instance in instances
        )

    response_text = connection.query_server(
        "perfcounterdata",
        esxhost=host,
        counters="".join(counter_data),
        samples=str(connection.perf_samples),
    )

    # Python regex only supports up to 100 match groups in a regex..
    # We are only extracting the whole value line and split it later on
    # This is a perfect candidate for "Catastrophic Backtracking" :)
    # Someday we should replace all of these get_pattern calls with
    # one of these new and fancy xml parsers I've heard from
    elements: list[tuple[str, str, str]] = get_pattern(
        "<id><counterId>(.*?)</counterId><instance>(.*?)</instance></id>(%s)"
        % ("<value>.*?</value>" * connection.perf_samples),
        response_text,
    )
    counters_value = []
    for id_, instance, valuestring in elements:
        values = get_pattern("<value>(.*?)</value>", valuestring)
        counters_value.append((id_, instance, values))

    return counters_value


def get_section_counters(
    connection: ESXConnection,
    hostsystems: Mapping[str, str],
    datastores: Mapping[str, Mapping[str, str]],
    opt: argparse.Namespace,
) -> list[str]:
    section_lines = []
    counters_available_by_host = fetch_available_counters(connection, hostsystems)
    counters_available_all = {
        counter  #
        for by_host in counters_available_by_host.values()  #
        for counter in by_host.keys()
    }

    net_extra_info = fetch_extra_interface_counters(connection, opt)
    counters_description = fetch_counters_syntax(connection, counters_available_all)

    for host in hostsystems:
        counters_avail = counters_available_by_host[host]

        counters_selected = [
            (id_, instances)
            for id_, instances in counters_avail.items()
            if counters_description.get(id_, {}).get("key") in REQUESTED_COUNTERS_KEYS
        ]

        counters_value = fetch_counters(connection, host, counters_selected)

        counters_output = {}
        for id_, instance, counter_values in counters_value:
            desc = counters_description.get(id_)
            if not desc:
                continue
            counters_output[(desc["group"], desc["name"], instance)] = (
                "#".join(counter_values),
                desc["unit"],
            )

        # Add datastore name to counters
        for key, values in datastores.items():
            counters_output[("datastore", "name", key)] = (values.get("name", ""), "string")

        if not opt.direct:
            section_lines.append("<<<<%s>>>>" % convert_hostname(hostsystems[host], opt))
        section_lines.append("<<<esx_vsphere_counters:sep(124)>>>")
        section_lines += [
            "%s.%s|%s|%s|%s" % (key + value) for key, value in sorted(counters_output.items())
        ]

        section_lines += net_extra_info  # TODO: explain why this is sent to every host

    if not opt.direct:
        section_lines.append("<<<<>>>>")

    return section_lines


# .
#   .--Hostsystem----------------------------------------------------------.
#   |         _   _           _                 _                          |
#   |        | | | | ___  ___| |_ ___ _   _ ___| |_ ___ _ __ ___           |
#   |        | |_| |/ _ \/ __| __/ __| | | / __| __/ _ \ '_ ` _ \          |
#   |        |  _  | (_) \__ \ |_\__ \ |_| \__ \ ||  __/ | | | | |         |
#   |        |_| |_|\___/|___/\__|___/\__, |___/\__\___|_| |_| |_|         |
#   |                                 |___/                                |
#   '----------------------------------------------------------------------'


def _iter_dicts(keys: Sequence[str], data: str) -> Iterator[dict[str, str]]:
    pattern = ".*?".join(f"<{key}>(.*?)</{key}>" for key in keys)
    matches = re.finditer(pattern, data, re.DOTALL)
    for match in matches:
        yield dict(zip(keys, match.groups()))


def eval_sensor_info(
    _hostname: str, _current_propname: str, propset: str
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    elements = (
        "name",
        "label",
        "summary",
        "key",
        "currentReading",
        "unitModifier",
        "baseUnits",
        "sensorType",
    )
    return {}, {d["name"]: d for d in _iter_dicts(elements, propset)}


def eval_hardwarestatus_info(
    _hostname: str, _current_propname: str, propset: str
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    elements = ("name", "label", "summary", "key")
    return {}, {d["name"]: d for d in _iter_dicts(elements, propset)}


def eval_multipath_info(
    _hostname: str, current_propname: str, multipath_propset: str
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    multipath_infos = get_pattern("<id>(.*?)</id>.*?((?:<path>.*?</path>)+)", multipath_propset)
    properties: dict[str, list[str]] = {}
    for vml_id, xml_paths in multipath_infos:
        # The Lun ID is part of the VML ID: https://kb.vmware.com/s/article/2078730
        lun_id = vml_id[10:-12]

        # Some devices (e.g. Marvell Processor or local devices) may not have a LUN ID.
        # It should be ok to skip them, see SUP-7220
        if not lun_id:
            continue

        for path_name, path_state in get_pattern(
            "<name>(.*?)</name>.*?<state>(.*?)</state>", xml_paths
        ):
            properties.setdefault(current_propname, []).append(f"{lun_id} {path_name} {path_state}")
    return properties, {}


def eval_propset_block(
    _hostname: str, current_propname: str, elements: Sequence[str], id_key: str, propset: str
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    properties: dict[str, list[str]] = {}
    for entries in _iter_dicts(elements, propset):
        for key, value in entries.items():
            properties.setdefault(f"{current_propname}.{key}.{entries[id_key]}", []).append(value)
    return properties, {}


def eval_cpu_pkg(
    hostname: str, current_propname: str, cpu_pkg_propset: str
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    return eval_propset_block(
        hostname,
        current_propname,
        ("index", "vendor", "hz", "busHz", "description"),
        "index",
        cpu_pkg_propset,
    )


def eval_pci_device(
    hostname: str, current_propname: str, pci_propset: str
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    return eval_propset_block(
        hostname, current_propname, ("id", "vendorName", "deviceName"), "id", pci_propset
    )


def eval_systeminfo_other(
    _hostname: str, _current_propname: str, propset: str
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    data = get_pattern("<identifierValue>(.*?)</identifierValue>.*?<key>(.*?)</key>", propset)

    keys_counter: Counter[str] = collections.Counter()
    properties = {}
    for value, key in data:
        idx = keys_counter[key]
        keys_counter[key] += 1
        properties["hardware.systemInfo.otherIdentifyingInfo.%s.%d" % (key, idx)] = [value]
    return properties, {}


EVAL_FUNCTIONS: Mapping[
    str, Callable[[str, str, str], tuple[dict[str, list[str]], dict[str, Any]]]
] = {
    "config.storageDevice.multipathInfo": eval_multipath_info,
    "runtime.healthSystemRuntime.systemHealthInfo.numericSensorInfo": eval_sensor_info,
    "runtime.healthSystemRuntime.hardwareStatusInfo.storageStatusInfo": eval_hardwarestatus_info,
    "runtime.healthSystemRuntime.hardwareStatusInfo.cpuStatusInfo": eval_hardwarestatus_info,
    "runtime.healthSystemRuntime.hardwareStatusInfo.memoryStatusInfo": eval_hardwarestatus_info,
    "hardware.cpuPkg": eval_cpu_pkg,
    "hardware.pciDevice": eval_pci_device,
    "hardware.systemInfo.otherIdentifyingInfo": eval_systeminfo_other,
}


def fetch_hostsystem_data(
    connection: ESXConnection,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    esxhostdetails_response = connection.query_server("esxhostdetails")
    hostsystems_objects = get_pattern("<objects>(.*?)</objects>", esxhostdetails_response)

    hostsystems_properties: dict[str, dict[Any, Any]] = {}
    hostsystems_sensors: dict[str, dict[Any, Any]] = {}
    for entry in hostsystems_objects:
        hostname = get_pattern('<obj type="HostSystem">(.*)</obj>', entry[:512])[0]
        hostsystems_properties[hostname] = {}
        hostsystems_sensors[hostname] = {}

        elements = get_pattern("<propSet><name>(.*?)</name><val.*?>(.*?)</val></propSet>", entry)
        for current_propname, value in elements:
            eval_func = EVAL_FUNCTIONS.get(current_propname)
            if eval_func:
                properties, sensors = eval_func(hostname, current_propname, value)
                hostsystems_properties[hostname].update(properties)
                hostsystems_sensors[hostname].update(sensors)
            else:
                hostsystems_properties[hostname].setdefault(current_propname, []).append(value)

    return hostsystems_properties, hostsystems_sensors


def get_sections_hostsystem_sensors(
    hostsystems_properties: Mapping[str, Mapping[str, Any]],
    hostsystems_sensors: Mapping[str, Mapping[str, Any]],
    opt: argparse.Namespace,
) -> list[str]:
    # TODO: improve error handling: check if multiple results
    section_lines = []
    for hostname, properties in hostsystems_properties.items():
        if not opt.direct:
            section_lines.append("<<<<%s>>>>" % convert_hostname(properties["name"][0], opt))

        section_lines.append("<<<esx_vsphere_hostsystem>>>")
        for key, data in sorted(properties.items()):
            section_lines.append("{} {}".format(key, " ".join(data)))

        section_lines.append("<<<esx_vsphere_sensors:sep(59)>>>")
        for key, data in sorted(hostsystems_sensors[hostname].items()):
            if data["key"].lower() in ("green", "unknown"):
                continue
            section_lines.append(
                "%s;%s;%s;%s;%s;%s;%s;%s;%s"
                % (
                    data["name"].replace(";", "_"),
                    data.get("baseUnits", ""),
                    data.get("currentReading", ""),
                    data.get("sensorType", ""),
                    data.get("unitModifier", ""),
                    data.get("rateUnits", ""),
                    data["key"],
                    data["label"],
                    data["summary"].replace(";", "_"),
                )
            )

    if not opt.direct:
        section_lines.append("<<<<>>>>")

    return section_lines


# .
#   .--Objects-------------------------------------------------------------.
#   |                    ___  _     _           _                          |
#   |                   / _ \| |__ (_) ___  ___| |_ ___                    |
#   |                  | | | | '_ \| |/ _ \/ __| __/ __|                   |
#   |                  | |_| | |_) | |  __/ (__| |_\__ \                   |
#   |                   \___/|_.__// |\___|\___|\__|___/                   |
#   |                            |__/                                      |
#   '----------------------------------------------------------------------'


def get_vm_power_states(
    vms: Mapping[str, Mapping[str, str]], hostsystems: Mapping[str, str], opt: argparse.Namespace
) -> list[str]:
    piggy_data: dict[str, list[Any]] = {}
    for used_hostname, vm_data in vms.items():
        runtime_host = vm_data.get("runtime.host", "")  # Can we drop the .get() here?
        running_on = hostsystems.get(runtime_host, runtime_host)
        power_state = vm_data.get("runtime.powerState")
        object_type = "template" if vm_data.get("config.template") == "true" else "virtualmachine"
        vm_info = f"{object_type}\t{used_hostname}\t{running_on}\t{power_state}"

        if opt.vm_pwr_display == "vm":
            piggy_data.setdefault(used_hostname, []).append(vm_info)
        elif opt.vm_pwr_display == "esxhost" and not opt.direct:
            piggy_data.setdefault(running_on, []).append(vm_info)
        piggy_data.setdefault("", []).append(vm_info)

    return _format_piggybacked_objects_sections(piggy_data)


def _get_vms_by_hostsystem(
    vms: Mapping[str, Mapping[str, str]], hostsystems: Mapping[str, str]
) -> dict[str, list[str]]:
    vms_by_hostsys: dict[str, list[Any]] = {}
    for vm_name, vm_data in vms.items():
        runtime_host = vm_data.get("runtime.host", "")  # Can we drop the .get() here?
        running_on = hostsystems.get(runtime_host, runtime_host)
        vms_by_hostsys.setdefault(running_on, []).append(vm_name)
    return vms_by_hostsys


def get_hostsystem_power_states(
    vms: Mapping[str, Mapping[str, str]],
    hostsystems: Mapping[str, str],
    hostsystems_properties: Mapping[str, Mapping[str, Any]],
    opt: argparse.Namespace,
) -> list[str]:
    vms_by_hostsys = _get_vms_by_hostsystem(vms, hostsystems)

    override_hostname = None
    if opt.hostname and opt.direct and opt.host_pwr_display != "vm":
        override_hostname = opt.hostname

    piggy_data: dict[str, list[str]] = {}
    for data in hostsystems_properties.values():
        orig_hostname = data["name"][0]
        used_hostname = override_hostname or convert_hostname(orig_hostname, opt)
        power_state = data["runtime.powerState"][0]
        host_info = f"hostsystem\t{used_hostname}\t\t{power_state}"
        if opt.host_pwr_display == "vm":
            for vm_name in vms_by_hostsys.get(orig_hostname, []):
                piggy_data.setdefault(vm_name, []).append(host_info)
        else:
            piggy_data.setdefault("", []).append(host_info)
            if opt.host_pwr_display == "esxhost" and not opt.direct:
                piggy_data.setdefault(used_hostname, []).append(host_info)

    return _format_piggybacked_objects_sections(piggy_data)


def _format_piggybacked_objects_sections(piggy_data: Mapping[str, Sequence[str]]) -> list[str]:
    output = []
    for piggy_target, info in piggy_data.items():
        output += ["<<<<%s>>>>" % piggy_target, "<<<esx_vsphere_objects:sep(9)>>>", *info]
    return output + ["<<<<>>>>"]


# .
#   .--unsorted------------------------------------------------------------.
#   |                                       _           _                  |
#   |            _   _ _ __  ___  ___  _ __| |_ ___  __| |                 |
#   |           | | | | '_ \/ __|/ _ \| '__| __/ _ \/ _` |                 |
#   |           | |_| | | | \__ \ (_) | |  | ||  __/ (_| |                 |
#   |            \__,_|_| |_|___/\___/|_|   \__\___|\__,_|                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def convert_hostname(hostname: str, opt: argparse.Namespace) -> str:
    if opt.spaces == "cut":
        return hostname.split()[0]
    return hostname.replace(" ", "_")


def get_pattern(pattern: str, line: str) -> list:
    return re.findall(pattern, line, re.DOTALL) if line else []


# snapshot.rootSnapshotList.summary 871 1605626114 poweredOn SnapshotName| 834 1605632160 poweredOff Snapshotname2
def get_section_snapshot_summary(
    vms: Mapping[str, Mapping[str, str]], systime: int | None
) -> Sequence[str]:
    snapshots = []
    for vm in vms.values():
        if raw_snapshots := vm.get("snapshot.rootSnapshotList"):
            snapshots.extend(
                [
                    raw_snapshot.split(" ", 3) + vm["name"].split()
                    for raw_snapshot in raw_snapshots.split("|")
                ]
            )

    return ["<<<esx_vsphere_snapshots_summary:sep(0)>>>"] + [
        json.dumps(
            {
                "time": int(snapshot[1]),
                "systime": systime,
                "state": snapshot[2],
                "name": snapshot[3],
                "vm": snapshot[4],
            }
        )
        for snapshot in snapshots
    ]


def _make_unix_time(raw_time: str) -> float:
    return dateutil.parser.isoparse(raw_time).timestamp()


def get_systemtime(connection: ESXConnection, debug: bool) -> float | None:
    try:
        response = connection.query_server("systemtime")
        raw_systime = get_pattern("<returnval>(.*)</returnval>", response)[0]
    except (IndexError, Exception):
        if debug:
            raise
        return None

    return _make_unix_time(raw_systime)


def is_placeholder_vm(devices: str) -> bool:
    elements = get_pattern('<VirtualDevice xsi:type="([^"]+)', devices)
    if "VirtualDisk" not in elements:
        return True
    return False


def eval_virtual_device(info: str, _datastores: Mapping[str, Mapping[str, str]]) -> str:
    response = []
    virtual_devices = get_pattern("<VirtualDevice (.*?)</VirtualDevice>", info)
    search_pattern = (
        "<(label)>(.*?)</label>.*?"
        "<(summary)>(.*?)</summary>.*?"
        "<(startConnected)>(.*?)</startConnected>.*?"
        "<(allowGuestControl)>(.*?)</allowGuestControl>.*?"
        "<(connected)>(.*?)</connected>.*?"
        "<(status)>(.*?)</status>"
    )
    for virtual_device in virtual_devices:
        try:
            type_info = get_pattern('type="(.*?)"', virtual_device)[0]
            device_info = get_pattern(search_pattern, virtual_device)[0]
        except IndexError:
            continue
        device_txt = "|".join("%s %s" % p for p in zip(device_info[0::2], device_info[1::2]))  #
        response.append(f"virtualDeviceType {type_info}|{device_txt}")

    return "@@".join(response)


def eval_snapshot_list(info: str, _datastores: Mapping[str, Mapping[str, str]]) -> str:
    response = []
    snapshot_info = get_pattern(
        "<name>(.*?)</name>.*?<id>(.*?)</id><createTime>(.*?)</createTime><state>(.*?)</state>",
        info,
    )
    for entry in snapshot_info:
        try:
            # 2013-11-06T15:39:39.347543Z
            creation_time = int(_make_unix_time(entry[2]))
        except ValueError:
            creation_time = 0
        response.append(
            "{} {} {} {}".format(entry[1], creation_time, entry[3], entry[0].replace("|", " "))
        )
    return "|".join(response)


def eval_datastores(info: str, datastores: Mapping[str, Mapping[str, str]]) -> str:
    datastore_urls = get_pattern("<name>(.*?)</name><url>(.*?)</url>", info)
    response = []
    for name, _url in datastore_urls:
        for datastore in datastores.values():
            if name == datastore["name"]:
                vm_datastore = []
                for key, value in datastore.items():
                    if key != "name":
                        key = key.split(".")[1]
                    vm_datastore.append(f"{key} {value}")
                response.append("|".join(vm_datastore))
                break
        else:
            # No matching datastore was found. At least add the name
            response.append("name %s" % name)
    return "@@".join(response)


def fetch_host_systems(connection: ESXConnection) -> dict[str, str]:
    hostsystems_response = connection.query_server("hostsystems")
    elements = get_pattern(
        '<obj type="HostSystem">(.*?)</obj>.*?<val xsi:type="xsd:string">(.*?)</val>',
        hostsystems_response,
    )

    # On some ESX systems the cookie login does not work as expected, when the agent_vsphere
    # is called only once or twice a day. The cookie is somehow outdated, but there is no
    # authentification failed message. Instead, the query simply returns an empty data set..
    # We try to detect this here (there is always a hostsystem) and raise a MKQueryServerException
    # which forces a new login
    if not elements:
        raise ESXCookieInvalid("Login cookie is no longer valid")

    return dict(elements)


def fetch_datastores(connection: ESXConnection) -> dict[str, dict[str, str]]:
    datastores_response = connection.query_server("datastores")
    elements = get_pattern(
        '<objects><obj type="Datastore">(.*?)</obj>(.*?)</objects>', datastores_response
    )
    datastores: dict[str, dict[str, Any]] = {}
    for datastore, content in elements:
        entries = get_pattern("<name>(.*?)</name><val xsi:type.*?>(.*?)</val>", content)
        datastores[datastore] = {}
        for name, value in entries:
            datastores[datastore][name] = value
    return datastores


def get_section_datastores(datastores: Mapping[str, Mapping[str, str]]) -> list[str]:
    section_lines = ["<<<esx_vsphere_datastores:sep(9)>>>"]
    for _key, data in sorted(datastores.items()):
        section_lines.append("[%s]" % data.get("name"))
        for ds_key in sorted(data.keys()):
            if ds_key == "name":
                continue
            section_lines.append("{}\t{}".format(ds_key.split(".")[1], data[ds_key]))
    return section_lines


def _get_text(node: NodeList[minidom.Element]) -> str:
    first = node.item(0)
    if first is None:
        raise ValueError("Node has no item")
    child = first.firstChild
    if child is None or not isinstance(child, minidom.Text):
        raise ValueError("Node has no text")
    return child.data


def get_section_licenses(connection: ESXConnection) -> list[str]:
    section_lines = ["<<<esx_vsphere_licenses:sep(9)>>>"]
    licenses_response = connection.query_server("licensesused")
    root_node = minidom.parseString(licenses_response)
    licenses_node = root_node.getElementsByTagName("LicenseManagerLicenseInfo")
    for license_node in licenses_node:
        total = _get_text(license_node.getElementsByTagName("total"))
        if total == "0":
            continue
        name = _get_text(license_node.getElementsByTagName("name"))
        used = _get_text(license_node.getElementsByTagName("used"))
        section_lines.append(f"{name}\t{used} {total}")
    return section_lines


def fetch_virtual_machines(
    connection: ESXConnection,
    hostsystems: Mapping[str, str],
    datastores: Mapping[str, Mapping[str, str]],
    opt: argparse.Namespace,
) -> tuple[dict[str, dict[str, str]], dict[str, list[str]]]:
    vms: dict[str, dict[str, str]] = {}
    vm_esx_host: dict[str, list[str]] = {}

    # <objects><propSet><name>...</name><val ..>...</val></propSet></objects>
    vmdetails_response = connection.query_server("vmdetails")

    elements = get_pattern("<objects>(.*?)</objects>", vmdetails_response)
    for entry in elements:
        vm_data = dict(get_pattern("<name>(.*?)</name><val.*?>(.*?)</val>", entry))
        if opt.skip_placeholder_vm and is_placeholder_vm(vm_data.get("config.hardware.device", "")):
            continue

        if vm_data.get("summary.config.ftInfo.role") == "2":
            continue  # This response coming from the passive fault-tolerance node

        if "runtime.host" in vm_data:
            vm_data["runtime.host"] = hostsystems.get(
                vm_data["runtime.host"], vm_data["runtime.host"]
            )

            vm_esx_host.setdefault(vm_data["runtime.host"], []).append(vm_data["name"])
        else:
            sys.stderr.write(
                f"Could not find a host for vm '{vm_data['name']}'. Is this vm currently cloned?\n"
            )

        transform_functions = {
            "snapshot.rootSnapshotList": eval_snapshot_list,
            "config.datastoreUrl": eval_datastores,
            "config.hardware.device": eval_virtual_device,
        }
        for key, transform in transform_functions.items():
            if key in vm_data:
                vm_data[key] = transform(vm_data[key], datastores)

        if (
            opt.vm_piggyname == "hostname"
            and (host_name := vm_data.get("summary.guest.hostName"))
            and not host_name.startswith(".")
        ):
            vm_name = convert_hostname(host_name, opt)
        else:
            vm_name = convert_hostname(vm_data["name"], opt)
        vms[vm_name] = vm_data

    return vms, vm_esx_host


def get_section_vm(vms: Mapping[str, Mapping[str, str]], systime: int | None) -> Sequence[str]:
    section_lines = []
    for vm_name, vm_data in sorted(vms.items()):
        if vm_data.get("name"):
            section_lines += [
                "<<<<%s>>>>" % vm_name,
                "<<<esx_vsphere_vm>>>",
            ]
            section_lines.extend("%s %s" % entry for entry in sorted(vm_data.items()))
            if systime is not None:
                section_lines.append(f"systime {systime}")
    section_lines += ["<<<<>>>>"]
    return section_lines


def get_section_virtual_machines(vms: dict[str, dict[str, str]]) -> list[str]:
    section_lines = ["<<<esx_vsphere_virtual_machines:sep(0)>>>"]
    section_lines.extend(
        json.dumps(
            {
                "vm_name": vm_name,
                "hostsystem": vm_data.get("runtime.host", ""),
                "powerstate": vm_data.get("runtime.powerState", ""),
                "guest_os": vm_data.get("config.guestFullName", ""),
                "compatibility": vm_data.get("config.version", ""),
                "uuid": vm_data.get("config.uuid", ""),
            },
            separators=(",", ":"),
        )
        for vm_name, vm_data in sorted(vms.items())
    )
    return section_lines


def get_sections_clusters(
    connection: ESXConnection,
    vm_esx_host: Mapping[str, Sequence[str]],
    opt: argparse.Namespace,
) -> list[str]:
    section_lines = []
    response = connection.query_server("datacenters")
    datacenters = get_pattern('<objects><obj type="Datacenter">(.*?)</obj>', response)
    for datacenter in datacenters:
        response = connection.query_server("clustersofdatacenter", datacenter=datacenter)
        clusters = get_pattern(
            '<objects><obj type="ClusterComputeResource">(.*?)</obj>.*?string">(.*?)</val>'
            "</propSet></objects>",
            response,
        )

        section_lines.append("<<<esx_vsphere_clusters:sep(9)>>>")
        for cluster in clusters:
            response = connection.query_server("esxhostsofcluster", clustername=cluster[0])
            cluster_vms: list[str] = []
            hosts = get_pattern(
                '<objects><obj type="HostSystem">.*?string">(.*?)</val></propSet></objects>',
                response,
            )
            for host in hosts:
                cluster_vms.extend(vm_esx_host.get(host, []))
            section_lines += [
                "{}\thostsystems\t{}\t{}".format(datacenter, cluster[1], "\t".join(hosts)),
                "%s\tvms\t%s\t%s"
                % (
                    datacenter,
                    cluster[1],
                    "\t".join(convert_hostname(cvm, opt) for cvm in cluster_vms),
                ),
            ]

    return section_lines


def fetch_data(connection: ESXConnection, opt: argparse.Namespace) -> list[str]:
    output = []

    output.append("<<<esx_systeminfo>>>")
    output += ["%s %s" % entry for entry in connection.system_info.items()]

    #############################
    # Determine available host systems
    #############################
    hostsystems = fetch_host_systems(connection)

    ###########################
    # Licenses
    ###########################
    if "licenses" in opt.modules:
        output += get_section_licenses(connection)

    ###########################
    # Datastores
    ###########################
    # We need the datastore info later on in the virtualmachines and counter sections
    datastores = fetch_datastores(connection)
    if "datastore" in opt.modules:
        output += get_section_datastores(datastores)

    ###########################
    # Counters
    ###########################
    if "counters" in opt.modules:
        output += get_section_counters(connection, hostsystems, datastores, opt)

    ###########################
    # Hostsystem
    ###########################
    if "hostsystem" in opt.modules:
        hostsystems_properties, hostsystems_sensors = fetch_hostsystem_data(connection)
        output += get_sections_hostsystem_sensors(hostsystems_properties, hostsystems_sensors, opt)

    ###########################
    # Virtual machines
    ###########################
    systime = get_systemtime(connection, bool(opt.debug))
    local_time = time.time()

    if "virtualmachine" in opt.modules:
        vms, vm_esx_host = fetch_virtual_machines(connection, hostsystems, datastores, opt)
        output += get_section_vm(vms, int(systime) if systime is not None else None)
        output += get_section_virtual_machines(vms)

        if not opt.direct or opt.snapshots_on_host:
            output += get_section_snapshot_summary(
                vms, int(systime) if systime is not None else None
            )
    else:
        vms, vm_esx_host = {}, {}

    if not opt.direct:
        output += get_sections_clusters(connection, vm_esx_host, opt)

    ###########################
    # Objects
    ###########################
    output += get_vm_power_states(vms, hostsystems, opt)
    if "hostsystem" in opt.modules:
        output += get_hostsystem_power_states(vms, hostsystems, hostsystems_properties, opt)

    if systime is not None:
        output += ["<<<systemtime>>>", f"{systime} {local_time}"]

    return output


# .
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        cmk.utils.password_store.replace_passwords()
        argv = sys.argv[1:]

    opt = parse_arguments(argv)

    socket.setdefaulttimeout(opt.timeout)

    try:
        esx_connection = ESXConnection(opt.host_address, opt.port, opt)

        esx_connection.login(opt.user, opt.secret)
        try:
            vsphere_output = fetch_data(esx_connection, opt)
        except ESXCookieInvalid:
            esx_connection.delete_server_cookie()
            esx_connection.login(opt.user, opt.secret)
            vsphere_output = fetch_data(esx_connection, opt)

    except Exception as exc:
        if opt.debug:
            raise
        sys.stderr.write("%s\n" % exc)
        return 1

    sys.stdout.writelines("%s\n" % line for line in vsphere_output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
