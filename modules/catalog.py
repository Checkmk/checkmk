#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

manpage_catalog_titles = {
    "hw"       : "Appliances, other dedicated Hardware",
        "environment" : "Environmental sensors",
            "akcp"       : "AKCP",
            "allnet"     : "ALLNET",
            "betternet"  : "better networks",
            "carel"      : "CAREL",
            "eaton"      : "Eaton",
            "emerson"    : "EMERSON",
            "hwg"        : "HW group",
            "rittal"     : "Rittal",
            "sensatronics" : "Sensatronics",
            "stulz"      : "STULZ",
            "wut"        : "Wiesemann & Theis",
            "wagner"     : "WAGNER Group",
        "other"       : "Other devices",
        "network"     : "Networking (Switches, Routers, etc.)",
            "alcatel"    : "Alcatel",
            "avm"        : "AVM",
            "bintec"     : "Bintec",
            "cbl"        : "Communication by light (CBL)",
            "cisco"      : "Cisco Systems (also IronPort)",
            "casa"       : "Casa",
            "decru"      : "Decru",
            "dell"       : "DELL",
            "f5"         : "F5 Networks",
            "fortinet"   : "Fortinet",
            "genua"      : "genua",
            "h3c"        : "H3C Technologies (also 3Com)",
            "hp"         : "Hewlett-Packard (HP)",
            "juniper"    : "Juniper Networks",
            "kemp"       : "KEMP",
            "lancom"     : "LANCOM Systems GmbH",
            "mikrotik"   : "MikroTik",
            "netgear"    : "Netgear",
            "qnap"       : "QNAP Systems",
            "riverbed"   : "Riverbed Technology",
            "symantec"   : "Symantec",
            "viprinet"   : "Viprinet",
            "bluecoat"   : "Blue Coat Systems",
            "tplink"     : "TP-LINK",
        "power"       : "Power supplies and PDUs",
            "apc"        : "APC",
            "gude"       : "Gude",
        "printer"     : "Printers",
        "server"      : "Servers (management boards, blade enclosures)",
            "ibm"        : "IBM",
        "storagehw"   : "Storage (filers, SAN, tape libs)",
            "brocade"    : "Brocade",
            "fastlta"    : "FAST LTA",
            "fujitsu"    : "Fujitsu",
            "mcdata"     : "McDATA",
            "netapp"     : "NetApp",
            "hitachi"    : "Hitachi",
            "emc"        : "EMC",
            "qlogic"     : "QLogic",
        "phone"       : "Telephony",

    "app"      : "Applications",
        "apache"        : "Apache Webserver",
        "db2"           : "IBM DB2",
        "citrix"        : "Citrix",
        "exchange"      : "Microsoft Exchange",
        "java"          : "Java (Tomcat, Weblogic, JBoss, etc.)",
        "libelle"       : "Libelle Business Shadow",
        "mailman"       : "Mailman",
        "mssql"         : "Microsoft SQL Server",
        "mysql"         : "MySQL",
        "omd"           : "Open Monitoring Distribution (OMD)",
        "oracle"        : "ORACLE Database",
        "postfix"       : "Postfix",
        "postgresql"    : "PostgreSQL",
        "qmail"         : "qmail",
        "sap"           : "SAP R/3",
        "tsm"           : "IBM Tivoli Storage Manager (TSM)",
        "unitrends"     : "Unitrends",

    "os"       : "Operating Systems",
        "aix"           : "AIX",
        "freebsd"       : "FreeBSD",
        "hpux"          : "HP-UX",
        "linux"         : "Linux",
        "macosx"        : "Mac OS X",
        "netbsd"        : "NetBSD",
        "openbsd"       : "OpenBSD",
        "openvms"       : "OpenVMS",
        "snmp"          : "SNMP based generic and hardware checks",
        "solaris"       : "Solaris",
        "vsphere"       : "VMWare ESX (via vSphere)",
        "windows"       : "Microsoft Windows",

        "hardware"    : "Hardware Sensors",
        "kernel"      : "CPU, Memory and Kernel Performance",
        "ps"          : "Processes, Services and Jobs",
        "files"       : "Files and Logfiles",
        "services"    : "Specific Daemons and Operating System Services",
        "networking"  : "Networking",
        "misc"        : "Miscellaneous",
        "storage"     : "Filesystems, Disks and RAID",

    "agentless" : "Networking checks without agent",
    "generic"  : "Generic check plugins",
    "unsorted" : "Uncategorized",
}
