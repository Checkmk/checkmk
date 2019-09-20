#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""This module handles the manual pages of Check_MK checks. These man
pages are meant to document the individual checks of Check_MK and are
used as base for the list of supported checks and catalogs of checks.

These man pages are in a Check_MK specific format an not real
Linux/Unix man pages"""
from __future__ import division

import os
import re
import sys
import StringIO
import subprocess

# Explicitly check for Python 3 (which is understood by mypy)
if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _

catalog_titles = {
    "hw"       : "Appliances, other dedicated Hardware",
        "environment" : "Environmental sensors",
            "acme"         : "ACME",
            "akcp"         : "AKCP",
            "allnet"       : "ALLNET",
            "avtech"       : "AVTECH",
            "bachmann"     : "Bachmann",
            "betternet"    : "better networks",
            "bosch"        : "Bosch",
            "carel"        : "CAREL",
            "climaveneta"  : "Climaveneta",
            "didactum"     : "Didactum",
            "eaton"        : "Eaton",
            "emerson"      : "EMERSON",
            "eltek"        : "ELTEK",
            "epson"        : "Epson",
            "hwg"          : "HW group",
            "ispro"        : "Interseptor Pro",
            "infratec_plus": "Infratec Plus",
            "kentix"       : "Kentix",
            "knuerr"       : "Knuerr",
            "maykg"        : "May KG Elektro-Bauelemente",
            "nti"          : "Network Technologies Inc.",
            "orion"        : "ORION",
            "raritan"      : "Raritan",
            "rittal"       : "Rittal",
            "sensatronics" : "Sensatronics",
            "socomec"      : "Socomec",
            "stulz"        : "STULZ",
            "teracom"      : "Teracom",
            "wagner"       : "WAGNER Group",
            "wut"          : "Wiesemann & Theis",
            "emka"         : "EMKA Electronic Locking & Monitoring",
            "tinkerforge"  : "Tinkerforge",
        "other"       : "Other devices",
        "time"        : "Clock Devices",
            "meinberg"   : "Meinberg",
            "hopf"       : "Hopf",
        "network"     : "Networking (Switches, Routers, etc.)",
            "aerohive"    : "Aerohive Networking",
            "adva"        : "ADVA Optical Networking",
            "alcatel"     : "Alcatel",
            "arbor"       : "Arbor",
            "arris"       : "ARRIS",
            "aruba"       : "Aruba Networks",
            "avaya"       : "Avaya",
            "avm"         : "AVM",
            "bintec"      : "Bintec",
            "bluecat"     : "BlueCat Networks",
            "bluecoat"    : "Blue Coat Systems",
            "casa"        : "Casa",
            "cbl"         : "Communication by light (CBL)",
            "checkpoint"  : "Checkpoint",
            "cisco"       : "Cisco Systems (also IronPort)",
            "decru"       : "Decru",
            "dell"        : "DELL",
            "enterasys"   : "Enterasys Networks",
            "f5"          : "F5 Networks",
            "fireeye"     : "FireEye",
            "fortinet"    : "Fortinet",
            "geist"       : "GEIST",
            "genua"       : "genua",
            "h3c"         : "H3C Technologies (also 3Com)",
            "hp"          : "Hewlett-Packard (HP)",
            "hpe"         : "Hewlett Packard Enterprise",
            "huawei"      : "Huawei",
            "hwgroup"     : "HW Group",
            "ibm"         : "IBM",
            "icom"        : "ICOM",
            "infoblox"    : "Infoblox",
            "intel"       : "Intel",
            "innovaphone" : "Innovaphone",
            "juniper"     : "Juniper Networks",
            "kemp"        : "KEMP",
            "lancom"      : "LANCOM Systems GmbH",
            "mikrotik"    : "MikroTik",
            "moxa"        : "MOXA",
            "netextreme"  : "Extreme Network",
            "netgear"     : "Netgear",
            "palo_alto"   : "Palo Alto Networks",
            "pandacom"    : "Pan Dacom",
            "papouch"     : "PAPOUCH",
            "perle"       : "PERLE",
            "qnap"        : "QNAP Systems",
            "riverbed"    : "Riverbed Technology",
            "safenet"     : "SafeNet",
            "salesforce"  : "Salesforce",
            "symantec"    : "Symantec",
            "seh"         : "SEH",
            "servertech"  : "Server Technology",
            "siemens"     : "Siemens",
            "sophos"      : "Sophos",
            "supermicro"  : "Super Micro Computer",
            "stormshield" : "Stormshield",
            "tplink"      : "TP-LINK",
            "viprinet"    : "Viprinet",
        "power"       : "Power supplies and PDUs",
            "apc"        : "APC",
            "cps"        : "Cyber Power System Inc.",
            "gude"       : "Gude",
            "janitza"    : "Janitza electronics",
        "printer"     : "Printers",
        "server"      : "Server hardware, blade enclosures",
        "storagehw"   : "Storage (filers, SAN, tape libs)",
            "atto"       : "ATTO",
            "brocade"    : "Brocade",
            "bdt"        : "BDT",
            "fastlta"    : "FAST LTA",
            "fujitsu"    : "Fujitsu",
            "mcdata"     : "McDATA",
            "netapp"     : "NetApp",
            "nimble"     : "Nimble Storage",
            "hitachi"    : "Hitachi",
            "emc"        : "EMC",
            "qlogic"     : "QLogic",
            "quantum"    : "Quantum",
            "oraclehw"   : "ORACLE",
            "synology"   : "Synology Inc.",
        "phone"       : "Telephony",

    "app"      : "Applications",
        "ad"            : "Active Directory",
        "apache"        : "Apache Webserver",
        "activemq"      : "Apache ActiveMQ",
        "artec"         : "ARTEC",
        "db2"           : "IBM DB2",
        "elasticsearch" : "Elasticsearch",
        "jenkins"       : "Jenkins",
        "splunk"        : "Splunk",
        "mongodb"       : "MongoDB",
        "citrix"        : "Citrix",
        "netscaler"     : "Citrix Netscaler",
        "exchange"      : "Microsoft Exchange",
        "haproxy"       : "HAProxy Loadbalancer",
        "informix"      : "IBM Informix",
        "java"          : "Java (Tomcat, Weblogic, JBoss, etc.)",
        "libelle"       : "Libelle Business Shadow",
        "lotusnotes"    : "IBM Lotus Domino",
        "mailman"       : "Mailman",
        "mssql"         : "Microsoft SQL Server",
        "mysql"         : "MySQL",
        "msoffice"      : "MS Office",
        "nginx"         : "NGINX",
        "nullmailer"    : "Nullmailer",
        "nutanix"       : "Nutanix",
        "omd"           : "Open Monitoring Distribution (OMD)",
        "check_mk"      : "Check_MK Monitoring System",
        "oracle"        : "ORACLE Database",
        "plesk"         : "Plesk",
        "pfsense"       : "pfsense",
        "postfix"       : "Postfix",
        "postgresql"    : "PostgreSQL",
        "qmail"         : "qmail",
        "ruckus"        : "Ruckus Spot",
        "sap"           : "SAP R/3",
        "sap_hana"      : "SAP HANA",
        "tsm"           : "IBM Tivoli Storage Manager (TSM)",
        "unitrends"     : "Unitrends",
        "sansymphony"   : "Datacore SANsymphony",
        "sshd"          : "SSH Daemon",
        "kaspersky"     : "Kaspersky Lab",
        "mcafee"        : "McAfee",
        "barracuda"     : "Barracuda",
        "vnx"           : "VNX NAS",
        "websphere_mq"  : "WebSphere MQ",

    "os"       : "Operating Systems",
        "aix"           : "AIX",
        "freebsd"       : "FreeBSD",
        "hpux"          : "HP-UX",
        "linux"         : "Linux",
        "macosx"        : "Mac OS X",
        "netbsd"        : "NetBSD",
        "openbsd"       : "OpenBSD",
        "openvms"       : "OpenVMS",
        "snmp"          : "SNMP",
        "solaris"       : "Solaris",
        "vsphere"       : "VMWare ESX (via vSphere)",
        "windows"       : "Microsoft Windows",
        "z_os"          : "IBM zOS Mainframes",

        "hardware"    : "Hardware Sensors",
        "kernel"      : "CPU, Memory and Kernel Performance",
        "ps"          : "Processes, Services and Jobs",
        "files"       : "Files and Logfiles",
        "services"    : "Specific Daemons and Operating System Services",
        "networking"  : "Networking",
        "misc"        : "Miscellaneous",
        "storage"     : "Filesystems, Disks and RAID",
    "cloud"    : "Cloud Based Environments",
        "azure"       : "Microsoft Azure",
        "aws"         : "Amazon Web Services",
        "quanta"      : "Quanta Cloud Technology",
    "containerization" : "Containerization",
        "docker"       : "Docker",
        "kubernetes"   : "Kubernetes",
        "lxc"          : "Linux Container",
    "agentless": "Networking checks without agent",
    "generic"  : "Generic check plugins",
    "unsorted" : "Uncategorized",
}  # yapf: disable

# TODO: Do we need a more generic place for this?
check_mk_agents = {
    "vms": "VMS",
    "linux": "Linux",
    "aix": "AIX",
    "solaris": "Solaris",
    "windows": "Windows",
    "snmp": "SNMP",
    "openvms": "OpenVMS",
    "vsphere": "vSphere",
    "nutanix": "Nutanix",
    "emcvnx": "EMC VNX",
    "vnx_quotas": "VNX Quotas"
}

_manpage_catalog = {}  # type: ignore


def man_page_exists(name):
    return man_page_path(name) is not None


def man_page_path(name):
    if name[0] != "." and name[-1] != "~":
        for basedir in [
                cmk.utils.paths.local_check_manpages_dir,
                Path(cmk.utils.paths.check_manpages_dir)
        ]:
            p = basedir / name
            if p.exists():
                return p
    return None


def all_man_pages():
    manuals = {}

    for basedir in [
            Path(cmk.utils.paths.check_manpages_dir), cmk.utils.paths.local_check_manpages_dir
    ]:
        if not basedir.exists():
            continue

        for file_path in basedir.iterdir():
            if file_path.name.startswith(".") or file_path.name.endswith("~"):
                continue

            manuals[file_path.name] = str(file_path)

    return manuals


def print_man_page_table():
    table = []
    for name, path in sorted(all_man_pages().items()):
        try:
            table.append((name, _get_title_from_man_page(Path(path))))
        except MKGeneralException as e:
            sys.stderr.write("ERROR: %s" % e)

    tty.print_table(['Check type', 'Title'], [tty.bold, tty.normal], table)


def _get_title_from_man_page(path):
    with path.open(encoding="utf-8") as fp:
        for line in fp:
            if line.startswith("title:"):
                return line.split(":", 1)[1].strip()
    raise MKGeneralException(_("Invalid man page: Failed to get the title"))


def man_page_catalog_titles():
    return catalog_titles


def load_man_page_catalog():
    catalog = {}
    for name, path in all_man_pages().items():
        try:
            parsed = _parse_man_page_header(name, Path(path))
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            parsed = _create_fallback_man_page(name, Path(path), e)

        if parsed.get("catalog"):
            cat = parsed["catalog"]
        else:
            cat = ["unsorted"]

        if cat[0] == "os":
            for agent in parsed["agents"]:
                acat = [cat[0]] + [agent] + cat[1:]
                catalog.setdefault(tuple(acat), []).append(parsed)
        else:
            catalog.setdefault(tuple(cat), []).append(parsed)

    return catalog


def print_man_page_browser(cat=()):
    global _manpage_catalog
    _manpage_catalog = load_man_page_catalog()

    entries = _manpage_catalog_entries(_manpage_catalog, cat)
    subtree_names = _manpage_catalog_subtree_names(_manpage_catalog, cat)

    if entries and subtree_names:
        sys.stderr.write("ERROR: Catalog path %s contains man pages and subfolders.\n" %
                         ("/".join(cat)))

    if entries:
        _manpage_browse_entries(cat, entries)

    elif subtree_names:
        _manpage_browser_folder(cat, subtree_names)


def _manpage_catalog_entries(catalog, category):
    return catalog.get(category, [])


def _manpage_catalog_subtree_names(catalog, category):
    subtrees = set([])
    for this_category in catalog.keys():
        if this_category[:len(category)] == category and len(this_category) > len(category):
            subtrees.add(this_category[len(category)])

    return list(subtrees)


def _manpage_num_entries(cat):
    num = 0
    for c, e in _manpage_catalog.items():
        if c[:len(cat)] == cat:
            num += len(e)
    return num


def _manpage_browser_folder(cat, subtrees):
    titles = []
    for e in subtrees:
        title = catalog_titles.get(e, e)
        count = _manpage_num_entries(cat + (e,))
        if count:
            title += " (%d)" % count
        titles.append((title, e))
    titles.sort()

    choices = [(str(n + 1), t[0]) for n, t in enumerate(titles)]

    while True:
        x = _dialog_menu(_("Man Page Browser"), _manpage_display_header(cat), choices, "0",
                         _("Enter"), cat and _("Back") or _("Quit"))
        if x[0]:
            index = int(x[1])
            subcat = titles[index - 1][1]
            print_man_page_browser(cat + (subcat,))
        else:
            break


def _manpage_browse_entries(cat, entries):
    checks = []
    for e in entries:
        checks.append((e["title"], e["name"]))
    checks.sort()

    choices = [(str(n + 1), c[0]) for n, c in enumerate(checks)]

    while True:
        x = _dialog_menu(_("Man Page Browser"), _manpage_display_header(cat), choices, "0",
                         _("Show Manpage"), _("Back"))
        if x[0]:
            index = int(x[1]) - 1
            name = checks[index][1]
            print_man_page(name)
        else:
            break


def _manpage_display_header(cat):
    return " -> ".join([catalog_titles.get(e, e) for e in cat])


def _dialog_menu(title, text, choices, defvalue, oktext, canceltext):
    args = ["--ok-label", oktext, "--cancel-label", canceltext]
    if defvalue is not None:
        args += ["--default-item", defvalue]
    args += ["--title", title, "--menu", text, "0", "0", "0"]  # "20", "60", "17" ]
    for txt, value in choices:
        args += [txt, value]
    return _run_dialog(args)


def _run_dialog(args):
    env = {"TERM": os.getenv("TERM", "linux"), "LANG": "de_DE.UTF-8"}
    p = subprocess.Popen(["dialog", "--shadow"] + args, env=env, stderr=subprocess.PIPE)
    response = p.stderr.read()
    return os.waitpid(p.pid, 0)[1] == 0, response


def _create_fallback_man_page(name, path, error_message):
    with path.open(encoding="utf-8") as fp:
        return {
            "name": name,
            "path": str(path),
            "description": fp.read().strip(),
            "title": _("%s: Cannot parse man page: %s") % (name, error_message),
            "agents": "",
            "license": "unknown",
            "distribution": "unknown",
            "catalog": ["generic"],
        }


def _parse_man_page_header(name, path):
    parsed = {
        "name": name,
        "path": str(path),
    }
    key = None
    lineno = 0
    with path.open(encoding="utf-8") as fp:
        for line in fp:
            line = line.rstrip()
            lineno += 1
            try:
                if not line:
                    parsed[key] += "\n\n"
                elif line[0] == ' ':
                    parsed[key] += "\n" + line.lstrip()
                elif line[0] == '[':
                    break  # End of header
                else:
                    key, rest = line.split(":", 1)
                    parsed[key] = rest.lstrip()
            except Exception:
                if cmk.utils.debug.enabled():
                    raise
                sys.stderr.write("ERROR: Invalid line %d in man page %s\n%s" % (lineno, path, line))
                break

    # verify mandatory keys. FIXME: This list may be incomplete
    for key in [
            "title",
            "agents",
            "license",
            "distribution",
            "description",
    ]:
        if key not in parsed:
            raise Exception("Section %s missing in man page of %s" % (key, name))

    parsed["agents"] = parsed["agents"].replace(" ", "").split(",")

    if parsed.get("catalog"):
        parsed["catalog"] = parsed["catalog"].split("/")

    return parsed


def load_man_page(name):
    path = man_page_path(name)
    if path is None:
        return

    man_page = {}
    current_section = []
    current_variable = None
    man_page['header'] = current_section
    empty_line_count = 0

    with path.open(encoding="utf-8") as fp:
        for lineno, line in enumerate(fp):
            try:
                if line.startswith(' ') and line.strip() != "":  # continuation line
                    empty_line_count = 0
                    if current_variable:
                        name, curval = current_section[-1]
                        if curval.strip() == "":
                            current_section[-1] = (name, line.rstrip()[1:])
                        else:
                            current_section[-1] = (name, curval + "\n" + line.rstrip()[1:])
                    else:
                        raise Exception
                    continue

                line = line.strip()
                if line == "":
                    empty_line_count += 1
                    if empty_line_count == 1 and current_variable:
                        name, curval = current_section[-1]
                        current_section[-1] = (name, curval + "\n<br>\n")
                    continue
                empty_line_count = 0

                if line[0] == '[' and line[-1] == ']':
                    section_header = line[1:-1]
                    current_section, current_variable = [], None
                    man_page[section_header] = current_section
                else:
                    current_variable, restofline = line.split(':', 1)
                    current_section.append((current_variable, restofline.lstrip()))

            except Exception as e:
                raise MKGeneralException("Syntax error in %s line %d (%s).\n" %
                                         (path, lineno + 1, e))

    header = {}
    for key, value in man_page['header']:
        header[key] = value.strip()
    header["agents"] = [a.strip() for a in header["agents"].split(",")]

    if 'catalog' not in header:
        header['catalog'] = ['unsorted']
    man_page['header'] = header

    return man_page


def print_man_page(name):
    renderer = ConsoleManPageRenderer(name)
    renderer.init_output()
    renderer.paint()


class ManPageRenderer(object):
    def __init__(self, name):
        self.name = name
        self.output = sys.stdout
        self.width = tty.get_size()[1]

        bg_color = 4
        fg_color = 7
        self._tty_color = tty.white + tty.bold
        self._normal_color = tty.normal + tty.colorset(fg_color, bg_color)
        self._title_color_left = tty.colorset(0, 7, 1)
        self._title_color_right = tty.colorset(0, 7)
        self._subheader_color = tty.colorset(fg_color, bg_color, 1)
        self._header_color_left = tty.colorset(0, 2)
        self._header_color_right = tty.colorset(7, 2, 1)
        self._parameters_color = tty.colorset(6, 4, 1)
        self._examples_color = tty.colorset(6, 4, 1)

        self._load()

    def _load(self):
        self.man_page = load_man_page(self.name)
        if not self.man_page:
            raise MKGeneralException("No manpage for %s. Sorry.\n" % self.name)

    def paint(self):
        try:
            self._paint_man_page()
        except Exception as e:
            sys.stdout.write("ERROR: Invalid check manpage %s: %s\n" % (self.name, e))

    def _paint_man_page(self):
        self._print_header()
        header = self.man_page['header']

        self._print_manpage_title(header['title'])

        ags = []
        for agent in header['agents']:
            ags.append(check_mk_agents.get(agent, agent.upper()))

        self._print_begin_splitlines()

        distro = header['distribution']
        if distro == 'check_mk':
            distro = "official part of Check_MK"
        self._print_splitline(self._header_color_left, "Distribution:            ",
                              self._header_color_right, distro)

        self._print_splitline(self._header_color_left, "License:                 ",
                              self._header_color_right, header['license'])
        self._print_splitline(self._header_color_left, "Supported Agents:        ",
                              self._header_color_right, ", ".join(ags))

        self._print_end_splitlines()

        self._print_empty_line()
        self._print_textbody(header['description'])
        if 'item' in header:
            self._print_subheader("Item")
            self._print_textbody(header['item'])

        self._print_subheader("Discovery")
        if 'inventory' in header:
            self._print_textbody(header['inventory'])
        else:
            self._print_textbody("No discovery supported.")

        self._print_empty_line()
        self.output.flush()

    def _print_header(self):
        raise NotImplementedError()

    def _print_manpage_title(self, title):
        raise NotImplementedError()

    def _print_subheader(self, line):
        raise NotImplementedError()

    def _print_line(self, line, attr=None, no_markup=False):
        raise NotImplementedError()

    def _print_begin_splitlines(self):
        pass

    def _print_end_splitlines(self):
        pass

    def _print_splitline(self, attr1, left, attr2, right):
        raise NotImplementedError()

    def _print_empty_line(self):
        raise NotImplementedError()

    def _print_textbody(self, text):
        raise NotImplementedError()

    def _print_splitwrap(self, attr1, left, attr2, text):
        raise NotImplementedError()

    def _begin_table(self, titles):
        raise NotImplementedError()

    def _end_table(self):
        raise NotImplementedError()

    def _begin_main_mk(self):
        raise NotImplementedError()

    def _end_main_mk(self):
        raise NotImplementedError()


class ConsoleManPageRenderer(ManPageRenderer):
    def init_output(self):
        if os.path.exists("/usr/bin/less") and sys.stdout.isatty():
            self.output = os.popen("/usr/bin/less -S -R -Q -u -L", "w")

    def _markup(self, line, attr):
        # Replaces braces in the line but preserves the inner braces
        return re.sub('(?<!{){', self._tty_color, re.sub('(?<!})}', tty.normal + attr, line))

    def _print_header(self):
        pass

    def _print_manpage_title(self, title):
        self._print_splitline(self._title_color_left, "%-25s" % self.name, self._title_color_right,
                              title)

    def _print_subheader(self, line):
        self._print_empty_line()
        self.output.write(self._subheader_color + " " + tty.underline + line.upper() +
                          self._normal_color + (" " *
                                                (self.width - 1 - len(line))) + tty.normal + "\n")

    def _print_line(self, line, attr=None, no_markup=False):
        if attr is None:
            attr = self._normal_color

        if no_markup:
            text = line
            l = len(line)
        else:
            text = self._markup(line, attr)
            l = self._print_len(line)

        self.output.write(attr + " ")
        self.output.write(text)
        self.output.write(" " * (self.width - 2 - l))
        self.output.write(" " + tty.normal + "\n")

    def _print_splitline(self, attr1, left, attr2, right):
        self.output.write(attr1 + " " + left)
        self.output.write(attr2)
        self.output.write(self._markup(right, attr2))
        self.output.write(" " * (self.width - 1 - len(left) - self._print_len(right)))
        self.output.write(tty.normal + "\n")

    def _print_empty_line(self):
        self._print_line("", tty.colorset(7, 4))

    def _print_len(self, word):
        # In case of double braces remove only one brace for counting the length
        netto = word.replace('{{', 'x').replace('}}', 'x').replace("{", "").replace("}", "")
        netto = re.sub("\033[^m]+m", "", netto)
        return len(netto)

    def _wrap_text(self, text, width, attr=tty.colorset(7, 4)):
        wrapped = []
        line = ""
        col = 0
        for word in text.split():
            if word == '<br>':
                if line != "":
                    wrapped.append(self._fillup(line, width))
                    wrapped.append(self._fillup("", width))
                    line = ""
                    col = 0
            else:
                netto = self._print_len(word)
                if line != "" and netto + col + 1 > width:
                    wrapped.append(self._justify(line, width))
                    col = 0
                    line = ""
                if line != "":
                    line += ' '
                    col += 1
                line += self._markup(word, attr)
                col += netto
        if line != "":
            wrapped.append(self._fillup(line, width))

        # remove trailing empty lines
        while wrapped[-1].strip() == "":
            wrapped = wrapped[:-1]
        return wrapped

    def _justify(self, line, width):
        need_spaces = float(width - self._print_len(line))
        spaces = float(line.count(' '))
        newline = ""
        x = 0.0
        s = 0.0
        words = line.split()
        newline = words[0]
        for word in words[1:]:
            newline += ' '
            x += 1.0
            while s / x < need_spaces / spaces:  # fixed: true-division
                newline += ' '
                s += 1
            newline += word
        return newline

    def _fillup(self, line, width):
        printlen = self._print_len(line)
        if printlen < width:
            line += " " * (width - printlen)
        return line

    def _print_textbody(self, text):
        wrapped = self._wrap_text(text, self.width - 2)
        attr = tty.colorset(7, 4)
        for line in wrapped:
            self._print_line(line, attr)

    def _print_splitwrap(self, attr1, left, attr2, text):
        wrapped = self._wrap_text(left + attr2 + text, self.width - 2)
        self.output.write(attr1 + " " + wrapped[0] + " " + tty.normal + "\n")
        for line in wrapped[1:]:
            self.output.write(attr2 + " " + line + " " + tty.normal + "\n")

    def _begin_table(self, titles):
        pass

    def _end_table(self):
        pass

    def _begin_main_mk(self):
        pass

    def _end_main_mk(self):
        pass


class NowikiManPageRenderer(ManPageRenderer):
    def __init__(self, name):
        super(NowikiManPageRenderer, self).__init__(name)
        self.output = StringIO.StringIO()

    def index_entry(self):
        return "<tr><td class=\"tt\">%s</td><td>[check_%s|%s]</td></tr>\n" % \
                  (self.name, self.name, self.man_page["header"]["title"])

    def render(self):
        self.paint()
        return self.output.getvalue()

    def _markup(self, line, ignored=None):
        # preserve the inner { and } in double braces and then replace the braces left
        return line.replace('{{', '{&#123;') \
                   .replace('}}', '&#125;}') \
                   .replace("{", "<tt>") \
                   .replace("}", "</tt>")

    def _print_header(self):
        self.output.write("TI:Check manual page of %s\n" % self.name)
        # It does not make much sense to print the date of the HTML generation
        # of the man page here. More useful would be the Check_MK version where
        # the plugin first appeared. But we have no access to that - alas.
        # self.output.write("DT:%s\n" % (time.strftime("%Y-%m-%d")))
        self.output.write("SA:check_plugins_catalog,check_plugins_list\n")

    def _print_manpage_title(self, title):
        self.output.write("<b>%s</b>\n" % title)

    def _print_subheader(self, line):
        self.output.write("H2:%s\n" % line)

    def _print_line(self, line, attr=None, no_markup=False):
        if no_markup:
            self.output.write("%s\n" % line)
        else:
            self.output.write("%s\n" % self._markup(line))

    def _print_begin_splitlines(self):
        self.output.write("<table>\n")

    def _print_end_splitlines(self):
        self.output.write("</table>\n")

    def _print_splitline(self, attr1, left, attr2, right):
        self.output.write("<tr><td>%s</td><td>%s</td></tr>\n" % (left, right))

    def _print_empty_line(self):
        self.output.write("\n")

    def _print_textbody(self, text):
        self.output.write("%s\n" % self._markup(text))

    def _print_splitwrap(self, attr1, left, attr2, text):
        if '(' in left:
            name, typ = left.split('(', 1)
            name = name.strip()
            typ = typ.strip()[:-2]
        else:
            name = left
            typ = ""
        self.output.write("<tr><td class=tt>%s</td>"
                          "<td>%s</td><td>%s</td></tr>\n" % (name, typ, self._markup(text)))

    def _begin_table(self, titles):
        self.output.write("<table><tr>")
        self.output.write("".join(["<th>%s</th>" % t for t in titles]))
        self.output.write("</tr>\n")

    def _end_table(self):
        self.output.write("</table>\n")

    def _begin_main_mk(self):
        self.output.write("F+:main.mk\n")

    def _end_main_mk(self):
        self.output.write("F-:\n")
