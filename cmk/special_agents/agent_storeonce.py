#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import getopt
import re
import sys
import xml.etree.ElementTree as ET

import requests
import urllib3  # type: ignore[import]


def usage():
    sys.stderr.write(
        """Check_MK StoreOnce

USAGE: agent_storeonce [OPTIONS] HOST

OPTIONS:
  -h, --help                    Show this help message and exit
  --address                     Host address
  --user                        Username
  --password                    Password
  --no-cert-check               Disable certificate check
"""
    )
    sys.exit(1)


#   .--defines-------------------------------------------------------------.
#   |                      _       __ _                                    |
#   |                   __| | ___ / _(_)_ __   ___  ___                    |
#   |                  / _` |/ _ \ |_| | '_ \ / _ \/ __|                   |
#   |                 | (_| |  __/  _| | | | |  __/\__ \                   |
#   |                  \__,_|\___|_| |_|_| |_|\___||___/                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

cluster_xml = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>Information about D2D Clusters</title>
    </head>
    <body>
        <div class="cluster">
            <table class="properties">
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="propertyName applianceName">Appliance Name</td>
                        <td class="propertyValue">HPCZ25132LTD</td>
                    </tr>
                    <tr>
                        <td class="propertyName networkName">Network Name</td>
                        <td class="propertyValue">10.14.66.54</td>
                    </tr>
                    <tr>
                        <td class="propertyName serialNumber">Serial Number</td>
                        <td class="propertyValue">CZ25132LTD</td>
                    </tr>
                    <tr>
                        <td class="propertyName softwareVersion">Software Version</td>
                        <td class="propertyValue">3.15.1-1636.1</td>
                    </tr>
                    <tr>
                        <td class="propertyName productClass">Product Class</td>
                        <td class="propertyValue">HPE StoreOnce 4700 Backup</td>
                    </tr>
                    <tr>
                        <td class="propertyName capacity">Total Capacity</td>
                        <td class="propertyValue">75952.808613643</td>
                    </tr>
                    <tr>
                        <td class="propertyName freeSpace">Free Space</td>
                        <td class="propertyValue">54779.424806667</td>
                    </tr>
                    <tr>
                        <td class="propertyName userDataStored">User Data Stored</td>
                        <td class="propertyValue">287270.12052552</td>
                    </tr>
                    <tr>
                        <td class="propertyName sizeOnDisk">Size On Disk</td>
                        <td class="propertyValue">18318.204265065</td>
                    </tr>
                    <tr>
                        <td class="propertyName capacityBytes">Total Capacity (bytes)</td>
                        <td class="propertyValue numeric">75952808613643</td>
                    </tr>
                    <tr>
                        <td class="propertyName freeBytes">Free Space (bytes)</td>
                        <td class="propertyValue numeric">54779424806667</td>
                    </tr>
                    <tr>
                        <td class="propertyName userBytes">User Data Stored (bytes)</td>
                        <td class="propertyValue numeric">287270120525521</td>
                    </tr>
                    <tr>
                        <td class="propertyName diskBytes">Size On Disk (bytes)</td>
                        <td class="propertyValue numeric">18318204265065</td>
                    </tr>
                    <tr>
                        <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                        <td class="propertyValue">15.682220613369749</td>
                    </tr>
                    <tr>
                        <td class="propertyName healthLevel">Cluster Health Level</td>
                        <td class="propertyValue numeric">1</td>
                    </tr>
                    <tr>
                        <td class="propertyName health">Cluster Health</td>
                        <td class="propertyValue">OK</td>
                    </tr>
                    <tr>
                        <td class="propertyName status">Cluster Status</td>
                        <td class="propertyValue">Running</td>
                    </tr>
                    <tr>
                        <td class="propertyName repHealthLevel">Replication Health Level</td>
                        <td class="propertyValue numeric">1</td>
                    </tr>
                    <tr>
                        <td class="propertyName repHealth">Replication Health</td>
                        <td class="propertyValue">OK</td>
                    </tr>
                    <tr>
                        <td class="propertyName repStatus">Replication Status</td>
                        <td class="propertyValue">Running</td>
                    </tr>
                    <tr>
                        <td class="propertyName uptimeSeconds">Uptime Seconds</td>
                        <td class="propertyValue">3533210</td>
                    </tr>
                    <tr>
                        <td class="propertyName sysContact">sysContact</td>
                        <td class="propertyValue"></td>
                    </tr>
                    <tr>
                        <td class="propertyName sysLocation">sysLocation</td>
                        <td class="propertyValue"></td>
                    </tr>
                    <tr>
                        <td class="propertyName isMixedCluster">isMixedCluster</td>
                        <td class="propertyValue">false</td>
                    </tr>
                </tbody>
            </table>
            <table class="servicesets">
                <caption>Service Sets</caption>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Health</th>
                        <th>URL</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td class="ssid">1</td>
                        <td class="summaryHealthLevel numeric">1</td>
                        <td class="detailUrl">/cluster/servicesets/1</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </body>
</html>"""

servicesets_xml = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>List of D2D Service Sets</title>
    </head>
    <body>
        <div class="servicesets">
            <div class="serviceset">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">ServiceSet Name</td>
                            <td class="propertyValue">Service Set 1</td>
                        </tr>
                        <tr>
                            <td class="propertyName alias">ServiceSet Alias</td>
                            <td class="propertyValue">SET1</td>
                        </tr>
                        <tr>
                            <td class="propertyName serialNumber">Serial Number</td>
                            <td class="propertyValue">CZ25132LTD01</td>
                        </tr>
                        <tr>
                            <td class="propertyName softwareVersion">Software Version</td>
                            <td class="propertyValue">3.15.1-1636.1</td>
                        </tr>
                        <tr>
                            <td class="propertyName productClass">Product Class</td>
                            <td class="propertyValue">HPE StoreOnce 4700 Backup</td>
                        </tr>
                        <tr>
                            <td class="propertyName capacityBytes">Capacity in bytes</td>
                            <td class="propertyValue numeric">75952808613643</td>
                        </tr>
                        <tr>
                            <td class="propertyName freeBytes">Free Space in bytes</td>
                            <td class="propertyValue numeric">54779424806667</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">User Data Stored in bytes</td>
                            <td class="propertyValue numeric">287270120525521</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">Size On Disk in bytes</td>
                            <td class="propertyValue numeric">18318204265065</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Deduplication Ratio</td>
                            <td class="propertyValue">15.68222061337</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">ServiceSet Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">ServiceSet Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">ServiceSet Status</td>
                            <td class="propertyValue">Running</td>
                        </tr>
                        <tr>
                            <td class="propertyName repHealthLevel">Replication Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName repHealth">Replication Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName repStatus">Replication Status</td>
                            <td class="propertyValue">Running</td>
                        </tr>
                        <tr>
                            <td class="propertyName overallHealthLevel">Overall Health Level</td>
                            <td class="propertyValue">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName overallHealth">Overall Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName overallStatus">Overall Status</td>
                            <td class="propertyValue">Running</td>
                        </tr>
                        <tr>
                            <td class="propertyName housekeepingHealthLevel">Housekeeping Health Level</td>
                            <td class="propertyValue">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName housekeepingHealth">Housekeeping Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName housekeepingStatus">Housekeeping Status</td>
                            <td class="propertyValue">Running</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryNode">Primary Node</td>
                            <td class="propertyValue">hpcz25132ltd</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryNode">Secondary Node</td>
                            <td class="propertyValue"></td>
                        </tr>
                        <tr>
                            <td class="propertyName activeNode">Active Node</td>
                            <td class="propertyValue">hpcz25132ltd</td>
                        </tr>
                    </tbody>
                </table>
                <table class="ipaddresses">
                    <caption>IP Addresses</caption>
                    <thead>
                        <tr>
                            <th>IP</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="ip">10.14.66.54</td>
                        </tr>
                        <tr>
                            <td class="ip">10.14.86.54</td>
                        </tr>
                    </tbody>
                </table>
                <table class="statusnotes">
                    <caption>Status Notes</caption>
                    <thead>
                        <tr>
                            <th>Message</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
                <table class="services">
                    <caption>Services</caption>
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>Health</th>
                            <th>URL</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="id">VTL</td>
                            <td class="summaryHealthLevel numeric">1</td>
                            <td class="url">/cluster/servicesets/1/services/vtl</td>
                        </tr>
                        <tr>
                            <td class="id">NAS</td>
                            <td class="summaryHealthLevel numeric">1</td>
                            <td class="url">/cluster/servicesets/1/services/nas</td>
                        </tr>
                        <tr>
                            <td class="id">CAT</td>
                            <td class="summaryHealthLevel numeric">1</td>
                            <td class="url">/cluster/servicesets/1/services/cat</td>
                        </tr>
                        <tr>
                            <td class="id">REP</td>
                            <td class="summaryHealthLevel numeric">1</td>
                            <td class="url">/cluster/servicesets/1/services/rep</td>
                        </tr>
                        <tr>
                            <td class="id">RMC</td>
                            <td class="summaryHealthLevel numeric">-1</td>
                            <td class="url">/cluster/servicesets/1/services/rmc</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </body>
</html>"""

stores_xml = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>List of CAT Stores</title>
    </head>
    <body>
        <div class="stores">
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">VM_WinSrv_Store</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue">Catalyst Store for Windows based Server</td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1434446799</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">348</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">2084.090996956</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">638.528567373</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">3.2</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">3.2</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2015-06-16T09:26:39Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2015-06-16T09:26:39Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">2084090996956</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">638528567373</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">348</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">3080</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">0000014DFBB121BB2954110834BAD600</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/0</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">VM_WinSrv2k12R2_Store</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue">Catalyst Store 2</td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1442488868</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">95</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">99.525367854</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">175.128207209</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">0.5</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">0.5</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2015-09-17T11:21:08Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2015-09-17T11:21:08Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">99525367854</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">175128207209</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">95</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">8636</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">3207</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">0000014FDB095E4FF643B037BA9FB700</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/2</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">VM_WinSrv2k8R2_Store</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue">Catalyst Store 3</td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1442488883</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">29</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">16.717657097</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">28.496991456</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">0.5</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">0.5</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2015-09-17T11:21:23Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2015-09-17T11:21:23Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">16717657097</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">28496991456</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">29</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">1816</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">0000014FDB0997E7D25DE43A4D856300</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">3</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/3</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">3</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">VM_Linux_Store</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue">Catalyst Store 4</td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1442488894</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">61</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">62.672731874</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">106.446348195</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">0.5</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">0.5</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2015-09-17T11:21:34Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2015-09-17T11:21:34Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">62672731874</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">106446348195</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">61</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">3784</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">0000014FDB09C5A025C32042A4D99C00</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">4</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/4</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">4</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">VM_WinClient_Store</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue">Catalyst Store 5</td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1442488913</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">74</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">277.369569295</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">229.196009842</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">1.2</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">1.2</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2015-09-17T11:21:53Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2015-09-17T11:21:53Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">277369569295</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">229196009842</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">74</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">3568</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">0000014FDB0A0DB33C95755A90D25A00</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">5</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/5</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">5</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">Phys_WinServ</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue">Catalyst Store 6</td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1442581342</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">31</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">2122.625736909</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">369.833222386</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">5.7</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">5.7</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2015-09-18T13:02:22Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2015-09-18T13:02:22Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">2122625736909</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">369833222386</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">31</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">91</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">0000014FE08C67BEA7EBE4C101853400</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">6</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/6</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">6</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">Phys_WinServ_Remote</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue">Catalyst Store 7</td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1443423749</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">141</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">58.827449693</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">31.820645962</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">1.8</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">1.8</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2015-09-28T07:02:29Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2015-09-28T07:02:29Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">58827449693</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">31820645962</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">141</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">105</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">0000015012C2852D8255A9740ABD5A00</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">7</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/7</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">7</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">Phys_MSSQL01</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue">MS SQL Server 2014 DB Backup</td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1446474937</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">85707</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">20101.830723148</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">1092.558653605</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">18.3</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">18.3</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2015-11-02T14:35:37Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2015-11-02T14:35:37Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">20101830723148</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">1092558653605</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">85707</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">180818</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">00000150C89FF2A9C31152779D43BA00</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">8</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/8</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">8</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">DEOKO04_SO1_VM_RH_7</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue"></td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1484824229</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">422</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">6400.445353789</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">127.180141151</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">50.3</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">50.3</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2017-01-19T11:10:29Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2017-01-19T11:10:29Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">6400445353789</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">127180141151</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">422</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">422</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">00000159B66BB709A0DCEF0AF3953F30</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">9</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/9</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">9</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">DEOKO04_SO1_VM_WinSrv_2k8</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue"></td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1484827537</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">1365</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">22474.17033675</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">1561.494631172</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">14.3</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">14.3</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2017-01-19T12:05:37Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2017-01-19T12:05:37Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">22474170336750</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">1561494631172</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">1365</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">1365</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">00000159B69E302FA108B25119A0F11B</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">10</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/10</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">10</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">DEOKO04_SO1_VM_Win_10</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue"></td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1484827546</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">218</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">1189.033153668</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">50.45275833</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">23.5</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">23.5</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2017-01-19T12:05:46Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2017-01-19T12:05:46Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">1189033153668</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">50452758330</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">218</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">218</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">00000159B69E53FAB44F8376645AE0BB</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">11</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/11</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">11</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">DEOKO04_SO1_VM_WinSrv_2k12</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue"></td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1484827555</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">4267</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">69139.783729574</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">3227.358905215</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">21.4</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">21.4</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2017-01-19T12:05:55Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2017-01-19T12:05:55Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">69139783729574</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">3227358905215</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">4267</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">4267</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">00000159B69E74D4DF4BED42A325B80C</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">12</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/12</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">12</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">DEOKO04_SO1_VM_WinSrv_2k16</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue"></td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1484827563</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">0.0</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">0.007095096</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">0.0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">0.0</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2017-01-19T12:06:03Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2017-01-19T12:06:03Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">7095096</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">00000159B69E947AF483010796F6DC4B</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">13</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/13</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">13</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">DEOKO04_SO1_VM_Other</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue"></td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1484827573</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">2552</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">28589.331990787</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">2356.462353263</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">12.1</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">12.1</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2017-01-19T12:06:13Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2017-01-19T12:06:13Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">28589331990787</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">2356462353263</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">2552</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">2552</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">00000159B69EBE0EA9A4983C8025AE29</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">14</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/14</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">14</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">DEOKO04_SO1_VM_Win_7</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue"></td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1484827920</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">2722</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">52060.999707535</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">2502.105802133</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">20.8</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">20.8</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2017-01-19T12:12:00Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2017-01-19T12:12:00Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">52060999707535</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">2502105802133</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">2722</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">2722</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">00000159B6A408E2E2D2CD5D0CA92425</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">15</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/15</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">15</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">DEOKO04_SO1_Phys_WinSrv_2k12</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue"></td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1484892749</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">1116</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">16293.562322478</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">458.51547515</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">35.5</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">35.5</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2017-01-20T06:12:29Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2017-01-20T06:12:29Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">16293562322478</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">458515475150</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">1116</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">1116</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">00000159BA813D7BB509BF75622EA270</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">16</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/16</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">16</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">DEOKO04_SO1_Phys_Win_7</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue"></td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1484892767</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">0.0</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">0.007095096</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">0.0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">0.0</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2017-01-20T06:12:47Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2017-01-20T06:12:47Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">7095096</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">00000159BA8183B0D5724FDD300E4E02</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">17</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/17</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">17</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">DEOKO04_SO1_Phys_RH_7</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue"></td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1484892787</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">357</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">13577.956605657</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">449.735149616</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">30.1</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">30.1</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2017-01-20T06:13:07Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2017-01-20T06:13:07Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">13577956605657</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">449735149616</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">357</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">366</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">00000159BA81D1755AA437291D3425D2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">18</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/18</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="store">
                <table class="properties">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">Store ID</td>
                            <td class="propertyValue numeric">18</td>
                        </tr>
                        <tr>
                            <td class="propertyName name">Name</td>
                            <td class="propertyValue">DEOKO04_SO1_Data_SFS004</td>
                        </tr>
                        <tr>
                            <td class="propertyName description">Description</td>
                            <td class="propertyValue"></td>
                        </tr>
                        <tr>
                            <td class="propertyName ssid">ServiceSet ID</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName creationTimeUTC">Creation Time UTC</td>
                            <td class="propertyValue numeric">1484892807</td>
                        </tr>
                        <tr>
                            <td class="propertyName healthLevel">Health Level</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName health">Health</td>
                            <td class="propertyValue">OK</td>
                        </tr>
                        <tr>
                            <td class="propertyName status">Status</td>
                            <td class="propertyValue">Online</td>
                        </tr>
                        <tr>
                            <td class="propertyName version">Version</td>
                            <td class="propertyValue numeric">2</td>
                        </tr>
                        <tr>
                            <td class="propertyName numberOfCatalystItems">Number Of Catalyst Items</td>
                            <td class="propertyValue numeric">54</td>
                        </tr>
                        <tr>
                            <td class="propertyName userdatastored">User Data Stored</td>
                            <td class="propertyValue">50725.746348722</td>
                        </tr>
                        <tr>
                            <td class="propertyName sizeondisk">Size On Disk</td>
                            <td class="propertyValue">4751.0680519</td>
                        </tr>
                        <tr>
                            <td class="propertyName deduperatio">Dedupe Ratio</td>
                            <td class="propertyValue">10.6</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupeRatio">Dedupe Ratio</td>
                            <td class="propertyValue">10.6</td>
                        </tr>
                        <tr>
                            <td class="propertyName created">Creation On</td>
                            <td class="propertyValue">2017-01-20T06:13:27Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName modified">Last Modified</td>
                            <td class="propertyValue">2017-01-20T06:13:27Z</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicy">primaryTransferPolicy</td>
                            <td class="propertyValue numeric">1</td>
                        </tr>
                        <tr>
                            <td class="propertyName primaryTransferPolicyString">primaryTransferPolicyString</td>
                            <td class="propertyValue">Low Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicy">secondaryTransferPolicy</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secondaryTransferPolicyString">secondaryTransferPolicyString</td>
                            <td class="propertyValue">High Bandwidth</td>
                        </tr>
                        <tr>
                            <td class="propertyName userDataSizeLimitBytes">userDataSizeLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dedupedDataSizeOnDiskLimitBytes">dedupedDataSizeOnDiskLimitBytes</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName dataJobRetentionDays">dataJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName inboundCopyJobRetentionDays">inboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName outboundCopyJobRetentionDays">outboundCopyJobRetentionDays</td>
                            <td class="propertyValue numeric">90</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeVariableBlockDedupe">supportStorageModeVariableBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeFixedBlockDedupe">supportStorageModeFixedBlockDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportStorageModeNoDedupe">supportStorageModeNoDedupe</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteSparse">supportWriteSparse</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportWriteInPlace">supportWriteInPlace</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportRawReadWrite">supportRawReadWrite</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectOpeners">supportMultipleObjectOpeners</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportMultipleObjectWrites">supportMultipleObjectWrites</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName supportCloneExtent">supportCloneExtent</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName userBytes">userBytes</td>
                            <td class="propertyValue numeric">50725746348722</td>
                        </tr>
                        <tr>
                            <td class="propertyName diskBytes">diskBytes</td>
                            <td class="propertyValue numeric">4751068051900</td>
                        </tr>
                        <tr>
                            <td class="propertyName numItems">numItems</td>
                            <td class="propertyValue numeric">54</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDataJobs">numDataJobs</td>
                            <td class="propertyValue numeric">54</td>
                        </tr>
                        <tr>
                            <td class="propertyName numOriginCopyJobs">numOriginCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName numDestinationCopyJobs">numDestinationCopyJobs</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName isOnline">Is online</td>
                            <td class="propertyValue">true</td>
                        </tr>
                        <tr>
                            <td class="propertyName encryption">is store encrypted</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeId">secure erase mode</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                        <tr>
                            <td class="propertyName secureEraseModeDescription">secure erase mode description</td>
                            <td class="propertyValue">Secure_Erase_NoPassCount</td>
                        </tr>
                        <tr>
                            <td class="propertyName isTeamed">isTeamed</td>
                            <td class="propertyValue">false</td>
                        </tr>
                        <tr>
                            <td class="propertyName teamUUID">teamUUID</td>
                            <td class="propertyValue">00000159BA8221E31CD32C817AB08657</td>
                        </tr>
                        <tr>
                            <td class="propertyName numTeamMembers">numTeamMembers</td>
                            <td class="propertyValue numeric">0</td>
                        </tr>
                    </tbody>
                </table>
                <table class="dedupeStore">
                    <caption>Dedupe Store</caption>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="propertyName id">dedupe Store Id</td>
                            <td class="propertyValue numeric">19</td>
                        </tr>
                        <tr>
                            <td class="propertyName url">dedupe Store URI</td>
                            <td class="propertyValue">/cluster/servicesets/1/services/dedupe/stores/19</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </body>
</html>"""

# .


def query(url, args_dict, opt_cert):
    if not opt_cert:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.get(
        url, auth=(args_dict["username"], args_dict["password"]), verify=opt_cert
    )
    raw_xml = response.text
    # Remove namespace nonsense
    raw_xml = re.sub(' xmlns="[^"]+"', "", raw_xml, count=1)
    xml_instance = ET.fromstring(raw_xml)
    return xml_instance


def process_cluster_info(args_dict, opt_demo, opt_cert):
    output_lines = ["<<<storeonce_clusterinfo:sep(9)>>>"]
    xml_instance = query_cluster_info(args_dict, opt_demo, opt_cert)
    tbody = xml_instance.find("body").find("div").find("table").find("tbody")
    for child in tbody:
        name = child[0].text
        value = child[1].text
        output_lines.append("%s\t%s" % (name, value))
    return output_lines


def query_cluster_info(args_dict, opt_demo, opt_cert):
    if opt_demo:
        raw_xml = re.sub(' xmlns="[^"]+"', "", cluster_xml, count=1)
        return ET.fromstring(raw_xml)
    url = "https://%(address)s/storeonceservices/cluster/" % args_dict
    return query(url, args_dict, opt_cert)


serviceset_ids = set()


def process_servicesets(args_dict, opt_demo, opt_cert):
    output_lines = ["<<<storeonce_servicesets:sep(9)>>>"]
    xml_instance = query_servicesets(args_dict, opt_demo, opt_cert)
    servicesets = xml_instance.find("body").find("div")
    for element in servicesets:
        tbody = element.find("table").find("tbody")
        serviceset_id = tbody[0][1].text
        serviceset_ids.add(serviceset_id)
        output_lines.append("[%s]" % serviceset_id)
        for child in tbody:
            name = child[0].text
            value = child[1].text
            output_lines.append("%s\t%s" % (name, value))
    return output_lines


def query_servicesets(args_dict, opt_demo, opt_cert):
    if opt_demo:
        raw_xml = re.sub(' xmlns="[^"]+"', "", servicesets_xml, count=1)
        return ET.fromstring(raw_xml)
    url = "https://%(address)s/storeonceservices/cluster/servicesets/" % args_dict
    return query(url, args_dict, opt_cert)


def process_stores_info(args_dict, opt_demo, opt_cert):
    output_lines = ["<<<storeonce_stores:sep(9)>>>"]
    for serviceset_id in serviceset_ids:
        xml_instance = query_stores_info(serviceset_id, args_dict, opt_demo, opt_cert)
        stores = xml_instance.find("body").find("div")
        for element in stores:
            tbody = element.find("table").find("tbody")
            store_id = tbody[0][1].text
            output_lines.append("[%s/%s]" % (serviceset_id, store_id))
            serviceset_ids.add(serviceset_id)
            for child in tbody:
                name = child[0].text
                value = child[1].text
                output_lines.append("%s\t%s" % (name, value))
    return output_lines


def query_stores_info(serviceset_id, args_dict, opt_demo, opt_cert):
    if opt_demo:
        raw_xml = re.sub(' xmlns="[^"]+"', "", stores_xml, count=1)
        return ET.fromstring(raw_xml)
    url = (
        "https://%(address)s/storeonceservices/cluster/servicesets/" % args_dict
        + "%s/services/cat/stores/" % serviceset_id
    )
    return query(url, args_dict, opt_cert)


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    short_options = "h"
    long_options = ["help", "username=", "password=", "address=", "demo", "no-cert-check"]

    try:
        opts, _args = getopt.getopt(sys_argv, short_options, long_options)
    except getopt.GetoptError as err:
        sys.stderr.write("%s\n" % err)
        return 1

    output_lines = []
    opt_demo = False
    opt_cert = True
    args_dict = {}

    for o, a in opts:
        if o in ["--address"]:
            args_dict["address"] = a
        elif o in ["--username"]:
            args_dict["username"] = a
        elif o in ["--password"]:
            args_dict["password"] = a
        elif o in ["--demo"]:
            opt_demo = True
        elif o in ["--no-cert-check"]:
            opt_cert = False
        elif o in ["-h", "--help"]:
            usage()

    try:
        # Get cluster info
        output_lines.extend(process_cluster_info(args_dict, opt_demo, opt_cert))

        # Get servicesets
        output_lines.extend(process_servicesets(args_dict, opt_demo, opt_cert))

        # Get stores info
        output_lines.extend(process_stores_info(args_dict, opt_demo, opt_cert))

        sys.stdout.write("\n".join(output_lines) + "\n")
    except Exception as e:
        sys.stderr.write("Connection error: %s" % e)
        return 1
