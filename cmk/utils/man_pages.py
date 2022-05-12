#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module handles the manual pages of Check_MK checks. These man
pages are meant to document the individual checks of Check_MK and are
used as base for the list of supported checks and catalogs of checks.

These man pages are in a Check_MK specific format an not real
Linux/Unix man pages"""

import os
import re
import subprocess
import sys
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.check_utils import maincheckify
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _

ManPage = Dict[str, Any]
ManPageCatalogPath = Tuple[str, ...]

catalog_titles = {
    "hw": "Appliances, other dedicated Hardware",
    "environment": "Environmental sensors",
    "acme": "ACME",
    "akcp": "AKCP",
    "allnet": "ALLNET",
    "avtech": "AVTECH",
    "bachmann": "Bachmann",
    "betternet": "better networks",
    "bosch": "Bosch",
    "carel": "CAREL",
    "climaveneta": "Climaveneta",
    "didactum": "Didactum",
    "eaton": "Eaton",
    "emerson": "EMERSON",
    "emka": "EMKA Electronic Locking & Monitoring",
    "eltek": "ELTEK",
    "epson": "Epson",
    "hwg": "HW group",
    "ispro": "Interseptor Pro",
    "infratec_plus": "Infratec Plus",
    "kentix": "Kentix",
    "knuerr": "Knuerr",
    "maykg": "May KG Elektro-Bauelemente",
    "nti": "Network Technologies Inc.",
    "orion": "ORION",
    "raritan": "Raritan",
    "rittal": "Rittal",
    "sensatronics": "Sensatronics",
    "socomec": "Socomec",
    "stulz": "STULZ",
    "teracom": "Teracom",
    "tinkerforge": "Tinkerforge",
    "vutlan": "Vutlan EMS",
    "wagner": "WAGNER Group",
    "wut": "Wiesemann & Theis",
    "time": "Clock Devices",
    "hopf": "Hopf",
    "meinberg": "Meinberg",
    "network": "Networking (Switches, Routers, etc.)",
    "aerohive": "Aerohive Networking",
    "adva": "ADVA Optical Networking",
    "alcatel": "Alcatel",
    "arbor": "Arbor",
    "arista": "Arista Networks",
    "arris": "ARRIS",
    "aruba": "Aruba Networks",
    "avaya": "Avaya",
    "avm": "AVM",
    "bintec": "Bintec",
    "bluecat": "BlueCat Networks",
    "bluecoat": "Blue Coat Systems",
    "casa": "Casa",
    "cbl": "Communication by light (CBL)",
    "checkpoint": "Checkpoint",
    "cisco": "Cisco Systems (also IronPort)",
    "ciena": "Ciena Corporation",
    "decru": "Decru",
    "dell": "DELL",
    "docsis": "DOCSIS",
    "enterasys": "Enterasys Networks",
    "ewon": "Ewon",
    "f5": "F5 Networks",
    "fireeye": "FireEye",
    "fortinet": "Fortinet",
    "geist": "GEIST",
    "genua": "genua",
    "h3c": "H3C Technologies (also 3Com)",
    "hp": "Hewlett-Packard (HP)",
    "hpe": "Hewlett Packard Enterprise",
    "huawei": "Huawei",
    "hwgroup": "HW Group",
    "ibm": "IBM",
    "icom": "ICOM",
    "infoblox": "Infoblox",
    "intel": "Intel",
    "innovaphone": "Innovaphone",
    "juniper": "Juniper Networks",
    "kemp": "KEMP",
    "lancom": "LANCOM Systems GmbH",
    "mikrotik": "MikroTik",
    "moxa": "MOXA",
    "netextreme": "Extreme Network",
    "netgear": "Netgear",
    "palo_alto": "Palo Alto Networks",
    "pandacom": "Pan Dacom",
    "papouch": "PAPOUCH",
    "perle": "PERLE",
    "qnap": "QNAP Systems",
    "riverbed": "Riverbed Technology",
    "safenet": "SafeNet",
    "salesforce": "Salesforce",
    "symantec": "Symantec",
    "seh": "SEH",
    "servertech": "Server Technology",
    "siemens": "Siemens",
    "sophos": "Sophos",
    "supermicro": "Super Micro Computer",
    "stormshield": "Stormshield",
    "tplink": "TP-LINK",
    "viprinet": "Viprinet",
    "power": "Power supplies and PDUs",
    "apc": "APC",
    "cps": "Cyber Power System Inc.",
    "gude": "Gude",
    "janitza": "Janitza electronics",
    "printer": "Printers",
    "mail": "Mail appliances",
    "artec": "ARTEC",
    "server": "Server hardware, blade enclosures",
    "storagehw": "Storage (filers, SAN, tape libs)",
    "atto": "ATTO",
    "brocade": "Brocade",
    "bdt": "BDT",
    "ddn_s2a": "DDN S2A",
    "emc": "EMC",
    "fastlta": "FAST LTA",
    "fujitsu": "Fujitsu",
    "mcdata": "McDATA",
    "netapp": "NetApp",
    "nimble": "Nimble Storage",
    "hitachi": "Hitachi",
    "oraclehw": "Oracle",
    "qlogic": "QLogic",
    "quantum": "Quantum",
    "synology": "Synology Inc.",
    "phone": "Telephony",
    "app": "Applications",
    "ad": "Active Directory",
    "alertmanager": "Alertmanager",
    "apache": "Apache Webserver",
    "activemq": "Apache ActiveMQ",
    "barracuda": "Barracuda",
    "checkmk": "Checkmk Monitoring System",
    "citrix": "Citrix",
    "couchbase": "Couchbase",
    "db2": "IBM DB2",
    "dotnet": "dotNET",
    "elasticsearch": "Elasticsearch",
    "entersekt": "Entersekt",
    "exchange": "Microsoft Exchange",
    "graylog": "Graylog",
    "haproxy": "HAProxy Loadbalancer",
    "iis": "Microsoft Internet Information Service",
    "informix": "IBM Informix",
    "java": "Java (Tomcat, Weblogic, JBoss, etc.)",
    "jenkins": "Jenkins",
    "jira": "Jira",
    "kaspersky": "Kaspersky Lab",
    "libelle": "Libelle Business Shadow",
    "lotusnotes": "IBM Lotus Domino",
    "mongodb": "MongoDB",
    "mailman": "Mailman",
    "mcafee": "McAfee",
    "mssql": "Microsoft SQL Server",
    "mysql": "MySQL",
    "msoffice": "MS Office",
    "netscaler": "Citrix Netscaler",
    "nginx": "NGINX",
    "nullmailer": "Nullmailer",
    "nutanix": "Nutanix",
    "cmk": "Checkmk",
    "opentextfuse": "OpenText Fuse Management Central",
    "oracle": "ORACLE Database",
    "plesk": "Plesk",
    "pfsense": "pfsense",
    "postfix": "Postfix",
    "postgresql": "PostgreSQL",
    "prometheus": "Prometheus",
    "proxmox": "Proxmox",
    "qmail": "qmail",
    "rabbitmq": "RabbitMQ",
    "redis": "Redis",
    "robotframework": "Robot Framework",
    "ruckus": "Ruckus Spot",
    "sap": "SAP R/3",
    "sap_hana": "SAP HANA",
    "sansymphony": "Datacore SANsymphony",
    "silverpeak": "Silver Peak",
    "skype": "Skype",
    "splunk": "Splunk",
    "sshd": "SSH Daemon",
    "tsm": "IBM Tivoli Storage Manager (TSM)",
    "unitrends": "Unitrends",
    "vnx": "VNX NAS",
    "websphere_mq": "WebSphere MQ",
    "zerto": "Zerto",
    "ibm_mq": "IBM MQ",
    "pulse_secure": "Pulse Secure",
    "os": "Operating Systems",
    "aix": "AIX",
    "freebsd": "FreeBSD",
    "hpux": "HP-UX",
    "linux": "Linux",
    "macosx": "Mac OS X",
    "netbsd": "NetBSD",
    "openbsd": "OpenBSD",
    "openvms": "OpenVMS",
    "snmp": "SNMP",
    "solaris": "Solaris",
    "vsphere": "VMWare ESX (via vSphere)",
    "windows": "Microsoft Windows",
    "z_os": "IBM zOS Mainframes",
    "hardware": "Hardware Sensors",
    "kernel": "CPU, Memory and Kernel Performance",
    "ps": "Processes, Services and Jobs",
    "files": "Files and Logfiles",
    "services": "Specific Daemons and Operating System Services",
    "networking": "Networking",
    "misc": "Miscellaneous",
    "storage": "Filesystems, Disks and RAID",
    "cloud": "Cloud Based Environments",
    "azure": "Microsoft Azure",
    "aws": "Amazon Web Services",
    "quanta": "Quanta Cloud Technology",
    "datadog": "Datadog",
    "containerization": "Containerization",
    "cadvisor": "cAdvisor",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "lxc": "Linux Container",
    "agentless": "Networking checks without agent",
    "generic": "Generic check plugins",
    "unsorted": "Uncategorized",
    "zertificon": "Zertificon",
    "mqtt": "MQTT",
    "smb_share": "SMB Share",
    "gcp": "Google Cloud Platform",
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
    "vnx_quotas": "VNX Quotas",
}

_manpage_catalog: Dict[ManPageCatalogPath, List[Dict]] = {}


def _get_man_page_dirs() -> Sequence[Path]:
    # first match wins
    return [
        cmk.utils.paths.local_check_manpages_dir,
        Path(cmk.utils.paths.check_manpages_dir),
    ]


def man_page_exists(name: str) -> bool:
    return man_page_path(name) is not None


def _is_valid_basename(name: str) -> bool:
    return not name.startswith(".") and not name.endswith("~")


def man_page_path(name: str, man_page_dirs: Optional[Iterable[Path]] = None) -> Optional[Path]:
    if not _is_valid_basename(name):
        return None

    if man_page_dirs is None:
        man_page_dirs = _get_man_page_dirs()

    for basedir in man_page_dirs:
        # check plugins pre 1.7 could have dots in them. be nice and find those.
        p = basedir / (name if name.startswith("check-mk") else maincheckify(name))
        if p.exists():
            return p
    return None


def all_man_pages(man_page_dirs: Optional[Iterable[Path]] = None) -> Dict[str, str]:
    if man_page_dirs is None:
        man_page_dirs = _get_man_page_dirs()

    manuals = {}
    for basedir in man_page_dirs:
        if basedir.exists():
            for file_path in basedir.iterdir():
                if file_path.name not in manuals and _is_valid_basename(file_path.name):
                    manuals[file_path.name] = str(file_path)
    return manuals


def print_man_page_table() -> None:
    table = []
    for name, path in sorted(all_man_pages().items()):
        try:
            table.append([name, get_title_from_man_page(Path(path))])
        except MKGeneralException as e:
            sys.stderr.write(str("ERROR: %s" % e))

    tty.print_table([str("Check type"), str("Title")], [tty.bold, tty.normal], table)


def get_title_from_man_page(path: Path) -> str:
    with path.open(encoding="utf-8") as fp:
        for line in fp:
            if line.startswith("title:"):
                return line.split(":", 1)[1].strip()
    raise MKGeneralException(_("Invalid man page: Failed to get the title"))


def man_page_catalog_titles():
    return catalog_titles


def load_man_page_catalog() -> Dict[ManPageCatalogPath, List[Dict]]:
    catalog: Dict[ManPageCatalogPath, List[Dict]] = {}
    for name, path in all_man_pages().items():
        try:
            parsed = _parse_man_page_header(name, Path(path))
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            parsed = _create_fallback_man_page(name, Path(path), e)
        cat = parsed.get("catalog", ["unsorted"])
        cats = (
            [[cat[0]] + [agent] + cat[1:] for agent in parsed["agents"]]
            if cat[0] == "os"
            else [cat]
        )
        for c in cats:
            catalog.setdefault(tuple(c), []).append(parsed)
    return catalog


def print_man_page_browser(cat=()):
    # typxe: (ManPageCatalogPath) -> None
    global _manpage_catalog
    _manpage_catalog = load_man_page_catalog()

    entries = _manpage_catalog_entries(_manpage_catalog, cat)
    subtree_names = _manpage_catalog_subtree_names(_manpage_catalog, cat)

    if entries and subtree_names:
        sys.stderr.write(
            str("ERROR: Catalog path %s contains man pages and subfolders.\n") % ("/".join(cat))
        )

    if entries:
        _manpage_browse_entries(cat, entries)

    elif subtree_names:
        _manpage_browser_folder(cat, subtree_names)


def _manpage_catalog_entries(catalog, category):
    return catalog.get(category, [])


def _manpage_catalog_subtree_names(catalog, category):
    subtrees = set([])
    for this_category in catalog.keys():
        if this_category[: len(category)] == category and len(this_category) > len(category):
            subtrees.add(this_category[len(category)])

    return list(subtrees)


def _manpage_num_entries(cat):
    num = 0
    for c, e in _manpage_catalog.items():
        if c[: len(cat)] == cat:
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
        x = _dialog_menu(
            _("Man Page Browser"),
            _manpage_display_header(cat),
            choices,
            "0",
            _("Enter"),
            cat and _("Back") or _("Quit"),
        )
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
        x = _dialog_menu(
            _("Man Page Browser"),
            _manpage_display_header(cat),
            choices,
            "0",
            _("Show Manpage"),
            _("Back"),
        )
        if x[0]:
            index = int(x[1]) - 1
            name = checks[index][1]
            ConsoleManPageRenderer(name).paint()
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
    completed_process = subprocess.run(
        ["dialog", "--shadow"] + args,
        env={"TERM": os.getenv("TERM", "linux"), "LANG": "de_DE.UTF-8"},
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed_process.returncode == 0, completed_process.stderr


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
    key = ""
    with path.open(encoding="utf-8") as fp:
        for lineno, line in enumerate(fp, start=1):
            line = line.rstrip()
            if not line:
                parsed[key] += "\n\n"
            elif line[0] == " ":
                parsed[key] += "\n" + line.lstrip()
            elif line[0] == "[":
                break  # End of header
            elif ":" in line:
                key, rest = line.split(":", 1)
                parsed[key] = rest.lstrip()
            else:
                msg = "ERROR: Invalid line %d in man page %s:\n%s" % (lineno, path, line)
                if cmk.utils.debug.enabled():
                    raise ValueError(msg)
                sys.stderr.write("%s\n" % msg)
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


# TODO: accepting the path here would make things a bit easier.
def load_man_page(name: str, man_page_dirs: Optional[Iterable[Path]] = None) -> Optional[ManPage]:
    path = man_page_path(name, man_page_dirs)
    if path is None:
        return None

    man_page: ManPage = {}
    current_section: List[Tuple[str, str]] = []
    current_variable = None
    man_page["header"] = current_section
    empty_line_count = 0

    with path.open(encoding=str("utf-8")) as fp:
        for lineno, line in enumerate(fp):
            try:
                if line.startswith(" ") and line.strip() != "":  # continuation line
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

                if line[0] == "[" and line[-1] == "]":
                    section_header = line[1:-1]
                    current_section, current_variable = [], None
                    man_page[section_header] = current_section
                else:
                    current_variable, restofline = line.split(":", 1)
                    current_section.append((current_variable, restofline.lstrip()))

            except Exception as e:
                raise MKGeneralException(
                    "Syntax error in %s line %d (%s).\n" % (path, lineno + 1, e)
                )

    header: Dict[str, Any] = {}
    for key, value in man_page["header"]:
        header[key] = value.strip()
    header["agents"] = [a.strip() for a in header["agents"].split(",")]

    if "catalog" not in header:
        header["catalog"] = "unsorted"
    man_page["header"] = header

    return man_page


class ManPageRenderer:
    def __init__(self, name):
        self.name = name
        man_page = load_man_page(name)
        if not man_page:
            raise MKGeneralException("No manpage for %s. Sorry.\n" % self.name)
        self._header = man_page["header"]

    def paint(self):
        try:
            self._paint_man_page()
        except Exception as e:
            sys.stdout.write(str("ERROR: Invalid check manpage %s: %s\n") % (self.name, e))

    def _paint_man_page(self):
        self._print_header()
        self._print_manpage_title(self._header["title"])

        self._print_begin_splitlines()
        distro = (
            "official part of Check_MK"
            if self._header["distribution"] == "check_mk"
            else self._header["distribution"]
        )
        ags = [check_mk_agents.get(agent, agent.upper()) for agent in self._header["agents"]]
        self._print_info_line("Distribution:            ", distro)
        self._print_info_line("License:                 ", self._header["license"])
        self._print_info_line("Supported Agents:        ", ", ".join(ags))
        self._print_end_splitlines()

        self._print_empty_line()
        self._print_textbody(self._header["description"])
        if "item" in self._header:
            self._print_subheader("Item")
            self._print_textbody(self._header["item"])

        self._print_subheader("Discovery")
        self._print_textbody(self._header.get("discovery", "No discovery supported."))
        self._print_empty_line()
        self._flush()

    def _flush(self):
        raise NotImplementedError()

    def _print_header(self):
        raise NotImplementedError()

    def _print_manpage_title(self, title):
        raise NotImplementedError()

    def _print_info_line(self, left, right):
        raise NotImplementedError()

    def _print_subheader(self, line):
        raise NotImplementedError()

    def _print_line(self, line, attr=None, no_markup=False):
        raise NotImplementedError()

    def _print_begin_splitlines(self):
        pass

    def _print_end_splitlines(self):
        pass

    def _print_empty_line(self):
        raise NotImplementedError()

    def _print_textbody(self, text):
        raise NotImplementedError()


def _console_stream():
    if os.path.exists("/usr/bin/less") and sys.stdout.isatty():
        # NOTE: We actually want to use subprocess.Popen here, but the tty is in
        # a horrible state after rendering the man page if we do that. Why???
        return os.popen(str("/usr/bin/less -S -R -Q -u -L"), "w")  # nosec
    return sys.stdout


class ConsoleManPageRenderer(ManPageRenderer):
    def __init__(self, name):
        super().__init__(name)
        self.__output = _console_stream()
        # NOTE: We must use instance variables for the TTY stuff because TTY-related
        # stuff might have been changed since import time, consider e.g. pytest.
        self.__width = tty.get_size()[1]
        self._tty_color = tty.white + tty.bold
        self._normal_color = tty.normal + tty.colorset(7, 4)
        self._title_color_left = tty.colorset(0, 7, 1)
        self._title_color_right = tty.colorset(0, 7)
        self._subheader_color = tty.colorset(7, 4, 1)
        self._header_color_left = tty.colorset(0, 2)
        self._header_color_right = tty.colorset(7, 2, 1)

    def _flush(self):
        self.__output.flush()

    def _markup(self, line, attr):
        # Replaces braces in the line but preserves the inner braces
        return re.sub("(?<!{){", self._tty_color, re.sub("(?<!})}", tty.normal + attr, line))

    def _print_header(self):
        pass

    def _print_manpage_title(self, title):
        self._print_splitline(
            self._title_color_left, "%-25s" % self.name, self._title_color_right, title
        )

    def _print_info_line(self, left, right):
        self._print_splitline(self._header_color_left, left, self._header_color_right, right)

    def _print_subheader(self, line):
        self._print_empty_line()
        self.__output.write(
            self._subheader_color
            + " "
            + tty.underline
            + line.upper()
            + self._normal_color
            + (" " * (self.__width - 1 - len(line)))
            + tty.normal
            + "\n"
        )

    def _print_line(self, line, attr=None, no_markup=False):
        if attr is None:
            attr = self._normal_color

        if no_markup:
            text = line
            l = len(line)
        else:
            text = self._markup(line, attr)
            l = self._print_len(line)

        self.__output.write(attr + " ")
        self.__output.write(text)
        self.__output.write(" " * (self.__width - 2 - l))
        self.__output.write(" " + tty.normal + "\n")

    def _print_splitline(self, attr1, left, attr2, right):
        self.__output.write(attr1 + " " + left)
        self.__output.write(attr2)
        self.__output.write(self._markup(right, attr2))
        self.__output.write(" " * (self.__width - 1 - len(left) - self._print_len(right)))
        self.__output.write(tty.normal + "\n")

    def _print_empty_line(self):
        self._print_line("", tty.colorset(7, 4))

    def _print_len(self, word):
        # In case of double braces remove only one brace for counting the length
        netto = word.replace("{{", "x").replace("}}", "x").replace("{", "").replace("}", "")
        netto = re.sub("\033[^m]+m", "", netto)
        return len(netto)

    def _wrap_text(self, text, width, attr=tty.colorset(7, 4)):
        wrapped = []
        line = ""
        col = 0
        for word in text.split():
            if word == "<br>":
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
                    line += " "
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
        spaces = float(line.count(" "))
        newline = ""
        x = 0.0
        s = 0.0
        words = line.split()
        newline = words[0]
        for word in words[1:]:
            newline += " "
            x += 1.0
            while s / x < need_spaces / spaces:  # fixed: true-division
                newline += " "
                s += 1
            newline += word
        return newline

    def _fillup(self, line, width):
        printlen = self._print_len(line)
        if printlen < width:
            line += " " * (width - printlen)
        return line

    def _print_textbody(self, text):
        wrapped = self._wrap_text(text, self.__width - 2)
        attr = tty.colorset(7, 4)
        for line in wrapped:
            self._print_line(line, attr)


class NowikiManPageRenderer(ManPageRenderer):
    def __init__(self, name):
        super().__init__(name)
        self.__output = StringIO()

    def _flush(self):
        pass

    def index_entry(self):
        return '<tr><td class="tt">%s</td><td>[check_%s|%s]</td></tr>\n' % (
            self.name,
            self.name,
            self._header["title"],
        )

    def render(self):
        self.paint()
        return self.__output.getvalue()

    def _markup(self, line, ignored=None):
        # preserve the inner { and } in double braces and then replace the braces left
        return (
            line.replace("{{", "{&#123;")
            .replace("}}", "&#125;}")
            .replace("{", "<tt>")
            .replace("}", "</tt>")
        )

    def _print_header(self):
        self.__output.write("TI:Check manual page of %s\n" % self.name)
        # It does not make much sense to print the date of the HTML generation
        # of the man page here. More useful would be the Checkmk version where
        # the plugin first appeared. But we have no access to that - alas.
        # self.__output.write("DT:%s\n" % (time.strftime("%Y-%m-%d")))
        self.__output.write("SA:check_plugins_catalog,check_plugins_list\n")

    def _print_manpage_title(self, title):
        self.__output.write("<b>%s</b>\n" % title)

    def _print_info_line(self, left, right):
        self.__output.write("<tr><td>%s</td><td>%s</td></tr>\n" % (left, right))

    def _print_subheader(self, line):
        self.__output.write("H2:%s\n" % line)

    def _print_line(self, line, attr=None, no_markup=False):
        if no_markup:
            self.__output.write("%s\n" % line)
        else:
            self.__output.write("%s\n" % self._markup(line))

    def _print_begin_splitlines(self):
        self.__output.write("<table>\n")

    def _print_end_splitlines(self):
        self.__output.write("</table>\n")

    def _print_empty_line(self):
        self.__output.write("\n")

    def _print_textbody(self, text):
        self.__output.write("%s\n" % self._markup(text))


if __name__ == "__main__":
    import argparse

    _parser = argparse.ArgumentParser(prog="man_pages", description="show manual pages for checks")
    _parser.add_argument("checks", metavar="NAME", nargs="*", help="name of a check")
    _parser.add_argument(
        "-r",
        "--renderer",
        choices=["console", "nowiki"],
        default="console",
        help="use the given renderer (default: console)",
    )
    _args = _parser.parse_args()
    cmk.utils.paths.local_check_manpages_dir = Path(__file__).parent.parent.parent / str("checkman")
    for check in _args.checks:
        try:
            print("----------------------------------------", check)
            if _args.renderer == "console":
                ConsoleManPageRenderer(check).paint()
            else:
                print(NowikiManPageRenderer(check).render())
        except MKGeneralException as _e:
            print(_e)
