#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module handles the manual pages of Checkmk checks

These man pages are meant to document the individual checks of Checkmk and are
used as base for the list of supported checks and catalogs of checks.

These man pages are in a Checkmk specific format an not real Linux/Unix man pages.
"""

import os
import re
import subprocess
import sys
from collections import defaultdict
from io import StringIO
from pathlib import Path
from typing import Final, Iterable, Literal, Mapping, NamedTuple, Optional, Sequence, TextIO, Union

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.check_utils import maincheckify
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.i18n import _

# Obviously, this type is brilliant and the whole situation must not be improved.
_ManPageValue = Union[str, Sequence[tuple[str, str]], Mapping[str, Union[str, Sequence[str]]]]

# The destiction between ManPage and Manpage header is not clear to me.
# I think we should just always parse the whole thing.
ManPage = Mapping[Literal["header"], _ManPageValue]


class ManPageHeader(NamedTuple):
    name: str
    path: str
    description: str
    title: str
    agents: Union[str, Sequence[str]]
    license: str
    distribution: str
    catalog: Sequence[str]


ManPageCatalogPath = tuple[str, ...]

ManPageCatalog = Mapping[ManPageCatalogPath, Sequence[ManPageHeader]]

CATALOG_TITLES: Final = {
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
    "mobileiron": "Mobileiron",
}

# TODO: Do we need a more generic place for this?
CHECK_MK_AGENTS: Final = {
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
    "mobileiron": "Mobileiron",
}


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


def all_man_pages(man_page_dirs: Optional[Iterable[Path]] = None) -> Mapping[str, str]:
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


def load_man_page_catalog() -> ManPageCatalog:
    catalog: dict[ManPageCatalogPath, list[ManPageHeader]] = defaultdict(list)
    for name, path in all_man_pages().items():
        try:
            parsed = _parse_man_page_header(name, Path(path))
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            parsed = _create_fallback_man_page(name, Path(path), str(e))

        if parsed.catalog[0] == "os":
            for agent in parsed.agents:
                catalog[("os", agent, *parsed.catalog[1:])].append(parsed)
        else:
            catalog[tuple(parsed.catalog)].append(parsed)

    return catalog


def print_man_page_browser(cat: ManPageCatalogPath = ()) -> None:
    catalog = load_man_page_catalog()

    entries = catalog.get(cat, [])
    subtree_names = _manpage_catalog_subtree_names(catalog, cat)

    if entries and subtree_names:
        sys.stderr.write(
            str("ERROR: Catalog path %s contains man pages and subfolders.\n") % ("/".join(cat))
        )

    if entries:
        _manpage_browse_entries(cat, entries)

    elif subtree_names:
        _manpage_browser_folder(catalog, cat, subtree_names)


def _manpage_catalog_subtree_names(
    catalog: ManPageCatalog, category: ManPageCatalogPath
) -> list[str]:
    subtrees = set()
    for this_category in catalog.keys():
        if this_category[: len(category)] == category and len(this_category) > len(category):
            subtrees.add(this_category[len(category)])

    return list(subtrees)


def _manpage_num_entries(catalog: ManPageCatalog, cat: ManPageCatalogPath) -> int:
    num = 0
    for c, e in catalog.items():
        if c[: len(cat)] == cat:
            num += len(e)
    return num


def _manpage_browser_folder(
    catalog: ManPageCatalog, cat: ManPageCatalogPath, subtrees: Iterable[str]
) -> None:
    titles = []
    for e in subtrees:
        title = CATALOG_TITLES.get(e, e)
        count = _manpage_num_entries(catalog, cat + (e,))
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
            _("Back") if cat else _("Quit"),
        )
        if x[0]:
            index = int(x[1])
            subcat = titles[index - 1][1]
            print_man_page_browser(cat + (subcat,))
        else:
            break


def _manpage_browse_entries(cat: Iterable[str], entries: Iterable[ManPageHeader]) -> None:
    checks: list[tuple[str, str]] = []
    for e in entries:
        checks.append((e.title, e.name))
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


def _manpage_display_header(cat: Iterable[str]) -> str:
    return " -> ".join([CATALOG_TITLES.get(e, e) for e in cat])


def _dialog_menu(
    title: str,
    text: str,
    choices: Sequence[tuple[str, str]],
    defvalue: str,
    oktext: str,
    canceltext: str,
) -> tuple[bool, bytes]:
    args = ["--ok-label", oktext, "--cancel-label", canceltext]
    if defvalue is not None:
        args += ["--default-item", defvalue]
    args += ["--title", title, "--menu", text, "0", "0", "0"]  # "20", "60", "17" ]
    for txt, value in choices:
        args += [txt, value]
    return _run_dialog(args)


def _run_dialog(args: Sequence[str]) -> tuple[bool, bytes]:
    completed_process = subprocess.run(
        ["dialog", "--shadow", *args],
        env={"TERM": os.getenv("TERM", "linux"), "LANG": "de_DE.UTF-8"},
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed_process.returncode == 0, completed_process.stderr


def _create_fallback_man_page(name: str, path: Path, error_message: str) -> ManPageHeader:
    with path.open(encoding="utf-8") as fp:
        return ManPageHeader(
            name=name,
            path=str(path),
            description=fp.read().strip(),
            title=_("%s: Cannot parse man page: %s") % (name, error_message),
            agents="",
            license="unknown",
            distribution="unknown",
            catalog=["generic"],
        )


def _parse_man_page_header(name: str, path: Path) -> ManPageHeader:
    with path.open(encoding="utf-8") as fp:
        parsed = _parse_to_raw_header(path, fp)

    try:
        return ManPageHeader(
            name=name,
            path=str(path),
            title=str(parsed["title"]),
            agents=parsed["agents"].replace(" ", "").split(","),
            license=parsed["license"],
            distribution=parsed["distribution"],
            description=parsed["description"],
            catalog=parsed["catalog"].split("/"),
        )
    except KeyError as key:
        raise ValueError(f"Section {key} missing in man page of {name}")


# TODO: accepting the path here would make things a bit easier.
def load_man_page(name: str, man_page_dirs: Optional[Iterable[Path]] = None) -> Optional[ManPage]:
    path = man_page_path(name, man_page_dirs)
    if path is None:
        return None

    with path.open(encoding=str("utf-8")) as fp:
        header_raw = _parse_to_raw(path, fp)

    # Watch out, the value of "header" is *not* of type ManPageHeader, it may
    # contain discovery and item!
    return {
        "header": {
            "catalog": "unsorted",  # fallback!
            **header_raw,
            "agents": [a.strip() for a in header_raw["agents"].split(",")],
        }
    }


def _parse_to_raw_header(path: Path, lines: Iterable[str]) -> Mapping[str, str]:
    parsed: dict[str, str] = {}
    key = ""
    for lineno, line in enumerate(lines, start=1):
        line = line.rstrip()
        if not line:
            parsed[key] += "\n\n"
        elif line[0] == " ":
            parsed[key] += "\n" + line.strip()
        elif line[0] == "[":
            break  # End of header
        elif ":" in line:
            key, rest = line.split(":", 1)
            parsed[key] = rest.strip()
        else:
            msg = "ERROR: Invalid line %d in man page %s:\n%s" % (lineno, path, line)
            if cmk.utils.debug.enabled():
                raise ValueError(msg)
            sys.stderr.write("%s\n" % msg)
            break

    return {k: v.strip() for k, v in parsed.items()}


def _parse_to_raw(path: Path, lines: Iterable[str]) -> Mapping[str, str]:

    current_section: list[tuple[str, str]] = []
    current_variable = None
    empty_line_count = 0

    for lineno, line in enumerate(lines):
        try:
            if line.startswith(" ") and line.strip() != "":  # continuation line
                empty_line_count = 0
                if current_variable:
                    name, curval = current_section[-1]
                    if curval.strip() == "":
                        current_section[-1] = (name, line.strip())
                    else:
                        current_section[-1] = (name, curval + "\n" + line.strip())
                else:
                    raise Exception
                continue

            line = line.strip()
            if line == "":
                empty_line_count += 1
                if empty_line_count == 1 and current_variable:
                    name, curval = current_section[-1]
                    current_section[-1] = (name, curval + "\n\n")
                continue
            empty_line_count = 0

            current_variable, restofline = line.split(":", 1)
            current_section.append((current_variable, restofline.strip()))

        except Exception as e:
            raise MKGeneralException("Syntax error in %s line %d (%s).\n" % (path, lineno + 1, e))

    return {k: v.strip() for k, v in current_section}


class ManPageRenderer:
    def __init__(self, name: str) -> None:
        self.name = name
        man_page = load_man_page(name)
        if not man_page:
            raise MKGeneralException("No manpage for %s. Sorry.\n" % self.name)

        header = man_page["header"]
        assert isinstance(header, dict)

        # Force the correct type. Hope we can clean this up later.
        self._title = str(header["title"])
        self._distro = (
            "official part of Check_MK"
            if header["distribution"] == "check_mk"
            else str(header["distribution"])
        )
        self._agents = [str(a) for a in header["agents"]]
        self._license = str(header["license"])
        self._description = str(header["description"])
        self._item = str(item) if (item := header.get("item")) else None
        self._discovery = str(header.get("discovery", "No discovery supported."))

    def paint(self) -> None:
        try:
            self._paint_man_page()
        except Exception as e:
            sys.stdout.write(str("ERROR: Invalid check manpage %s: %s\n") % (self.name, e))

    def _paint_man_page(self) -> None:
        self._print_header()
        self._print_manpage_title(self._title)

        self._print_begin_splitlines()

        ags = [CHECK_MK_AGENTS.get(agent, agent.upper()) for agent in self._agents]
        self._print_info_line("Distribution:            ", self._distro)
        self._print_info_line("License:                 ", self._license)
        self._print_info_line("Supported Agents:        ", ", ".join(ags))
        self._print_end_splitlines()

        self._print_empty_line()
        self._print_textbody(self._description)
        if self._item:
            self._print_subheader("Item")
            self._print_textbody(self._item)

        self._print_subheader("Discovery")
        self._print_textbody(self._discovery)
        self._print_empty_line()
        self._flush()

    def _flush(self) -> None:
        raise NotImplementedError()

    def _print_header(self) -> None:
        raise NotImplementedError()

    def _print_manpage_title(self, title: str) -> None:
        raise NotImplementedError()

    def _print_info_line(self, left: str, right: str) -> None:
        raise NotImplementedError()

    def _print_subheader(self, line: str) -> None:
        raise NotImplementedError()

    def _print_line(self, line: str, attr: Optional[str] = None, no_markup: bool = False) -> None:
        raise NotImplementedError()

    def _print_begin_splitlines(self) -> None:
        pass

    def _print_end_splitlines(self) -> None:
        pass

    def _print_empty_line(self) -> None:
        raise NotImplementedError()

    def _print_textbody(self, text: str) -> None:
        raise NotImplementedError()


def _console_stream() -> TextIO:
    if os.path.exists("/usr/bin/less") and sys.stdout.isatty():
        # NOTE: We actually want to use subprocess.Popen here, but the tty is in
        # a horrible state after rendering the man page if we do that. Why???
        return os.popen(str("/usr/bin/less -S -R -Q -u -L"), "w")  # nosec
    return sys.stdout


class ConsoleManPageRenderer(ManPageRenderer):
    def __init__(self, name: str) -> None:
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

    def _flush(self) -> None:
        self.__output.flush()

    def _markup(self, line: str, attr: str) -> str:
        # Replaces braces in the line but preserves the inner braces
        return re.sub("(?<!{){", self._tty_color, re.sub("(?<!})}", tty.normal + attr, line))

    def _print_header(self) -> None:
        pass

    def _print_manpage_title(self, title: str) -> None:
        self._print_splitline(
            self._title_color_left, "%-25s" % self.name, self._title_color_right, title
        )

    def _print_info_line(self, left: str, right: str) -> None:
        self._print_splitline(self._header_color_left, left, self._header_color_right, right)

    def _print_subheader(self, line: str) -> None:
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

    def _print_line(self, line: str, attr: Optional[str] = None, no_markup: bool = False) -> None:
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

    def _print_splitline(self, attr1: str, left: str, attr2: str, right: str) -> None:
        self.__output.write(attr1 + " " + left)
        self.__output.write(attr2)
        self.__output.write(self._markup(right, attr2))
        self.__output.write(" " * (self.__width - 1 - len(left) - self._print_len(right)))
        self.__output.write(tty.normal + "\n")

    def _print_empty_line(self) -> None:
        self._print_line("", tty.colorset(7, 4))

    def _print_len(self, word: str) -> int:
        # In case of double braces remove only one brace for counting the length
        netto = word.replace("{{", "x").replace("}}", "x").replace("{", "").replace("}", "")
        netto = re.sub("\033[^m]+m", "", netto)
        return len(netto)

    def _wrap_text(self, text: str, width: int, attr: str = tty.colorset(7, 4)) -> Sequence[str]:
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

    def _justify(self, line: str, width: int) -> str:
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

    def _fillup(self, line: str, width: int) -> str:
        printlen = self._print_len(line)
        if printlen < width:
            line += " " * (width - printlen)
        return line

    def _print_textbody(self, text: str) -> None:
        wrapped = self._wrap_text(text, self.__width - 2)
        attr = tty.colorset(7, 4)
        for line in wrapped:
            self._print_line(line, attr)


class NowikiManPageRenderer(ManPageRenderer):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.__output = StringIO()

    def _flush(self) -> None:
        pass

    def index_entry(self) -> str:
        return '<tr><td class="tt">%s</td><td>[check_%s|%s]</td></tr>\n' % (
            self.name,
            self.name,
            self._title,
        )

    def render(self) -> str:
        self.paint()
        return self.__output.getvalue()

    def _markup(self, line: str, ignored: Optional[str] = None) -> str:
        # preserve the inner { and } in double braces and then replace the braces left
        return (
            line.replace("{{", "{&#123;")
            .replace("}}", "&#125;}")
            .replace("{", "<tt>")
            .replace("}", "</tt>")
        )

    def _print_header(self) -> None:
        self.__output.write("TI:Check manual page of %s\n" % self.name)
        # It does not make much sense to print the date of the HTML generation
        # of the man page here. More useful would be the Checkmk version where
        # the plugin first appeared. But we have no access to that - alas.
        # self.__output.write("DT:%s\n" % (time.strftime("%Y-%m-%d")))
        self.__output.write("SA:check_plugins_catalog,check_plugins_list\n")

    def _print_manpage_title(self, title: str) -> None:
        self.__output.write("<b>%s</b>\n" % title)

    def _print_info_line(self, left: str, right: str) -> None:
        self.__output.write("<tr><td>%s</td><td>%s</td></tr>\n" % (left, right))

    def _print_subheader(self, line: str) -> None:
        self.__output.write("H2:%s\n" % line)

    def _print_line(self, line: str, attr: Optional[str] = None, no_markup: bool = False) -> None:
        if no_markup:
            self.__output.write("%s\n" % line)
        else:
            self.__output.write("%s\n" % self._markup(line))

    def _print_begin_splitlines(self):
        self.__output.write("<table>\n")

    def _print_end_splitlines(self) -> None:
        self.__output.write("</table>\n")

    def _print_empty_line(self) -> None:
        self.__output.write("\n")

    def _print_textbody(self, text: str) -> None:
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
