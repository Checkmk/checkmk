#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module handles the manual pages of Checkmk checks

These man pages are meant to document the individual checks of Checkmk and are
used as base for the list of supported checks and catalogs of checks.

These man pages are in a Checkmk specific format an not real Linux/Unix man pages.
"""

# mypy: disable-error-code="comparison-overlap"

import os
import re
import subprocess
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Final

import cmk.ccc.debug
from cmk.ccc import tty
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.i18n import _


@dataclass
class ManPage:
    name: str
    path: Path
    title: str
    agents: Sequence[str]
    catalog: Sequence[str]
    license: str
    distribution: str
    description: str
    item: str | None
    discovery: str | None
    cluster: str | None

    @classmethod
    def fallback(cls, path: Path, name: str, msg: str, content: str) -> "ManPage":
        return cls(
            name=name,
            path=path,
            title=_("%s: Cannot parse manual page: %s") % (name, msg),
            agents=[],
            catalog=["generic"],
            license="unknown",
            distribution="unknown",
            description=content,
            item=None,
            discovery=None,
            cluster=None,
        )


ManPageCatalogPath = tuple[str, ...]

ManPageCatalog = Mapping[ManPageCatalogPath, Sequence[ManPage]]

CATALOG_TITLES: Final = {
    "acme": "ACME",
    "activemq": "Apache ActiveMQ",
    "ad": "Active Directory",
    "adva": "ADVA Optical Networking",
    "aerohive": "Aerohive Networking",
    "agentless": "Networking checks without agent",
    "aix": "AIX",
    "akcp": "AKCP",
    "alcatel": "Alcatel",
    "alertmanager": "Alertmanager",
    "allnet": "ALLNET",
    "apache": "Apache Webserver",
    "apc": "APC",
    "app": "Applications",
    "arbor": "Arbor",
    "arista": "Arista Networks",
    "arris": "ARRIS",
    "artec": "ARTEC",
    "aruba": "Aruba Networks",
    "atto": "ATTO",
    "avaya": "Avaya",
    "avm": "AVM",
    "avtech": "AVTECH",
    "aws": "Amazon Web Services",
    "aws_status": "Amazon Web Service (AWS) Status",
    "azure": "Azure",
    "azure_status": "Azure Status",
    "bachmann": "Bachmann",
    "barracuda": "Barracuda",
    "bazel_cache": "Bazel Remote Cache",
    "bdt": "BDT",
    "betternet": "better networks",
    "bintec": "Bintec",
    "bluecat": "BlueCat Networks",
    "bluecoat": "Blue Coat Systems",
    "bosch": "Bosch",
    "brocade": "Brocade",
    "cadvisor": "cAdvisor",
    "carel": "CAREL",
    "casa": "Casa",
    "cbl": "Communication by light (CBL)",
    "checkmk": "Checkmk Monitoring System",
    "checkpoint": "Check Point",
    "ciena": "Ciena Corporation",
    "cisco": "Cisco Systems (also IronPort)",
    "citrix": "Citrix",
    "climaveneta": "Climaveneta",
    "cloud": "Cloud Based Environments",
    "cmk": "Checkmk",
    "containerization": "Containerization",
    "couchbase": "Couchbase",
    "cps": "Cyber Power System Inc.",
    "custom_query_metric_backend": "Custom query (metric backend)",
    "datadog": "Datadog",
    "db2": "IBM DB2",
    "ddn_s2a": "DDN S2A",
    "decru": "Decru",
    "dell": "DELL",
    "didactum": "Didactum",
    "docker": "Docker",
    "docsis": "DOCSIS",
    "dotnet": "dotNET",
    "eaton": "Eaton",
    "elasticsearch": "Elasticsearch",
    "eltek": "ELTEK",
    "emc": "EMC",
    "emerson": "EMERSON",
    "emka": "EMKA Electronic Locking & Monitoring",
    "enterasys": "Enterasys Networks",
    "entersekt": "Entersekt",
    "environment": "Environmental sensors",
    "epson": "Epson",
    "ewon": "Ewon",
    "exchange": "Microsoft Exchange",
    "f5": "F5 Networks",
    "fastlta": "FAST LTA",
    "files": "Files and Logfiles",
    "fireeye": "FireEye",
    "fortinet": "Fortinet",
    "freebsd": "FreeBSD",
    "fujitsu": "Fujitsu",
    "gcp": "Google Cloud Platform",
    "gcp_status": "Google Cloud Platform (GCP) Status",
    "geist": "GEIST",
    "generic": "Generic check plug-ins",
    "genua": "genua",
    "gerrit": "Gerrit",
    "graylog": "Graylog",
    "gude": "Gude",
    "h3c": "H3C Technologies (also 3Com)",
    "haproxy": "HAProxy Loadbalancer",
    "hardware": "Hardware Sensors",
    "hitachi": "Hitachi",
    "hopf": "Hopf",
    "hpe": "Hewlett Packard Enterprise",
    "hp": "Hewlett-Packard (HP)",
    "hpux": "HP-UX",
    "huawei": "Huawei",
    "hw": "Appliances, other dedicated Hardware",
    "hwg": "HW group",
    "hwgroup": "HW Group",
    "ibm": "IBM",
    "ibm_mq": "IBM MQ",
    "icom": "ICOM",
    "iis": "Microsoft Internet Information Service",
    "infoblox": "Infoblox",
    "informix": "IBM Informix",
    "infratec_plus": "Infratec Plus",
    "innovaphone": "Innovaphone",
    "intel": "Intel",
    "ispro": "Interseptor Pro",
    "ivantineurons": "Ivanti Neurons for MDM (formerly MobileIron Cloud)",
    "janitza": "Janitza electronics",
    "java": "Java (Tomcat, Weblogic, JBoss, etc.)",
    "jenkins": "Jenkins",
    "jira": "Jira",
    "juniper": "Juniper Networks",
    "kaspersky": "Kaspersky Lab",
    "kemp": "KEMP",
    "kentix": "Kentix",
    "kernel": "CPU, Memory and Kernel Performance",
    "knuerr": "Knuerr",
    "kubernetes": "Kubernetes",
    "lancom": "LANCOM Systems GmbH",
    "libelle": "Libelle Business Shadow",
    "linux": "Linux",
    "lotusnotes": "IBM Lotus Domino",
    "lxc": "Linux Container",
    "macosx": "Mac OS X",
    "mail": "Mail appliances",
    "mailman": "Mailman",
    "maykg": "May KG Elektro-Bauelemente",
    "mcafee": "McAfee",
    "mcdata": "McDATA",
    "meinberg": "Meinberg",
    "metric_backend": "Metric Backend",
    "mikrotik": "MikroTik",
    "misc": "Miscellaneous",
    "mongodb": "MongoDB",
    "moxa": "MOXA",
    "mqtt": "MQTT",
    "msoffice": "MS Office",
    "mssql": "Microsoft SQL Server",
    "mysql": "MySQL",
    "netapp": "NetApp",
    "netbsd": "NetBSD",
    "netextreme": "Extreme Network",
    "netgear": "Netgear",
    "netscaler": "Citrix Netscaler",
    "networking": "Networking",
    "network": "Networking (Switches, Routers, etc.)",
    "nginx": "NGINX",
    "nimble": "Nimble Storage",
    "nti": "Network Technologies Inc.",
    "nullmailer": "Nullmailer",
    "nutanix": "Nutanix",
    "openbsd": "OpenBSD",
    "opentextfuse": "OpenText Fuse Management Central",
    "openvms": "OpenVMS",
    "oraclehw": "Oracle",
    "oracle": "ORACLE Database",
    "orion": "ORION",
    "os": "Operating Systems",
    "otel": "OpenTelemetry (experimental)",
    "palo_alto": "Palo Alto Networks",
    "pandacom": "Pan Dacom",
    "papouch": "PAPOUCH",
    "perle": "PERLE",
    "pfsense": "pfsense",
    "phone": "Telephony",
    "plesk": "Plesk",
    "podman": "Podman",
    "postfix": "Postfix",
    "postgresql": "PostgreSQL",
    "power": "Power supplies and PDUs",
    "primekey": "Primekey",
    "printer": "Printers",
    "prometheus": "Prometheus",
    "proxmox": "Proxmox",
    "ps": "Processes, Services and Jobs",
    "pulse_secure": "Pulse Secure",
    "pure_storage": "Pure Storage",
    "qlogic": "QLogic",
    "qmail": "qmail",
    "qnap": "QNAP Systems",
    "quanta": "Quanta Cloud Technology",
    "quantum": "Quantum",
    "rabbitmq": "RabbitMQ",
    "raritan": "Raritan",
    "redfish": "Redfish",
    "redis": "Redis",
    "rittal": "Rittal",
    "riverbed": "Riverbed Technology",
    "robotframework": "Robot Framework",
    "ruckus": "Ruckus Spot",
    "safenet": "SafeNet",
    "salesforce": "Salesforce",
    "sansymphony": "Datacore SANsymphony",
    "sap_hana": "SAP HANA",
    "sap": "SAP R/3",
    "seh": "SEH",
    "sensatronics": "Sensatronics",
    "server": "Server hardware, blade enclosures",
    "servertech": "Server Technology",
    "services": "Specific Daemons and Operating System Services",
    "siemens": "Siemens",
    "silverpeak": "Silver Peak",
    "skype": "Skype",
    "smb_share": "SMB Share",
    "snmp": "SNMP",
    "socomec": "Socomec",
    "solaris": "Solaris",
    "sophos": "Sophos",
    "splunk": "Splunk",
    "sshd": "SSH Daemon",
    "storage": "Filesystems, Disks and RAID",
    "storagehw": "Storage (filers, SAN, tape libs)",
    "stormshield": "Stormshield",
    "stulz": "STULZ",
    "supermicro": "Super Micro Computer",
    "symantec": "Symantec",
    "synology": "Synology Inc.",
    "synthetic_monitoring": "Synthetic Monitoring",
    "teracom": "Teracom",
    "time": "Clock Devices",
    "tinkerforge": "Tinkerforge",
    "tplink": "TP-LINK",
    "tsm": "IBM Tivoli Storage Manager (TSM)",
    "unitrends": "Unitrends",
    "unsorted": "Uncategorized",
    "viprinet": "Viprinet",
    "virtual": "Virtualization",
    "vnx": "VNX NAS",
    "vsphere": "VMware ESX (via vSphere)",
    "vutlan": "Vutlan EMS",
    "wagner": "WAGNER Group",
    "windows": "Microsoft Windows",
    "wut": "Wiesemann & Theis",
    "zertificon": "Zertificon",
    "zerto": "Zerto",
    "z_os": "IBM zOS Mainframes",
}

# TODO: Do we need a more generic place for this?
CHECK_MK_AGENTS: Final = {
    "aix": "AIX",
    "linux": "Linux",
    "mobileiron": "Ivanti Neurons for MDM (formerly MobileIron Cloud)",
    "nutanix": "Nutanix",
    "openvms": "OpenVMS",
    "redfish": "Redfish",
    "snmp": "SNMP",
    "solaris": "Solaris",
    "vms": "VMS",
    "vnx_quotas": "VNX Quotas",
    "vsphere": "vSphere",
    "windows": "Windows",
}


def _is_valid_basename(name: str) -> bool:
    return not name.startswith(".") and not name.endswith("~") and not name == "OWNERS"


def make_man_page_path_map(
    plugin_families: Mapping[str, Sequence[str]],
    group_subdir: str,
) -> Mapping[str, Path]:
    families_man_paths = [
        os.path.join(p, group_subdir) for _family, paths in plugin_families.items() for p in paths
    ]
    return {
        name: Path(dir, name)
        for source in reversed(families_man_paths)
        for dir, _subdirs, files in os.walk(source)
        for name in files
        if _is_valid_basename(name)
    }


def print_man_page_table(man_page_path_map: Mapping[str, Path]) -> None:
    table = []
    for name, path in sorted(man_page_path_map.items()):
        try:
            table.append([name, get_title_from_man_page(path)])
        except MKGeneralException as e:
            sys.stderr.write(str(f"ERROR: {e}"))

    tty.print_table(["Check type", "Title"], [tty.bold, tty.normal], table)


def get_title_from_man_page(path: Path) -> str:
    with path.open(encoding="utf-8") as fp:
        for line in fp:
            if line.startswith("title:"):
                return line.split(":", 1)[1].strip()
    raise MKGeneralException(_("Invalid manual page: Failed to get the title"))


def load_man_page_catalog(
    plugin_families: Mapping[str, Sequence[str]], group_subdir: str
) -> ManPageCatalog:
    man_page_path_map = make_man_page_path_map(plugin_families, group_subdir)
    catalog: dict[ManPageCatalogPath, list[ManPage]] = defaultdict(list)
    for name, path in man_page_path_map.items():
        parsed = parse_man_page(name, path)
        for entry in _make_catalog_entries(parsed.catalog, parsed.agents):
            catalog[entry].append(parsed)

    return catalog


def _make_catalog_entries(
    pages_catalog: Sequence[str], agents: Sequence[str]
) -> Sequence[tuple[str, ...]]:
    if pages_catalog[0] == "os":
        return [("os", agent, *pages_catalog[1:]) for agent in agents]

    # See SUP-20129, e.g. custom mkps can have definitions in wrong format
    # use 'generic' in this case
    if len(pages_catalog) == 1 and "generic" not in pages_catalog:
        return [tuple(["generic"])]

    return [tuple(pages_catalog)]


def print_man_page_browser(
    catalog: ManPageCatalog,
    cat: ManPageCatalogPath = (),
) -> None:
    entries = {man_page.name: man_page for man_page in catalog.get(cat, [])}
    subtree_names = _manpage_catalog_subtree_names(catalog, cat)

    if entries and subtree_names:
        sys.stderr.write(
            "ERROR: Catalog path %s contains man pages and subfolders.\n" % ("/".join(cat))
        )

    if entries:
        _manpage_browse_entries(cat, entries)

    elif subtree_names:
        _manpage_browser_folder(catalog, cat, subtree_names)


def _manpage_catalog_subtree_names(
    catalog: ManPageCatalog, category: ManPageCatalogPath
) -> list[str]:
    subtrees = {
        this_category[len(category)]
        for this_category in catalog.keys()
        if this_category[: len(category)] == category and len(this_category) > len(category)
    }
    return list(subtrees)


def _manpage_num_entries(catalog: ManPageCatalog, cat: ManPageCatalogPath) -> int:
    return sum(len(e) for c, e in catalog.items() if c[: len(cat)] == cat)


def _manpage_browser_folder(
    catalog: ManPageCatalog,
    cat: ManPageCatalogPath,
    subtrees: Iterable[str],
) -> None:
    titles = []
    for e in subtrees:
        title = CATALOG_TITLES.get(e, e)
        if count := _manpage_num_entries(catalog, cat + (e,)):
            title += f" ({count})"
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
            print_man_page_browser(catalog, cat + (subcat,))
        else:
            break


def _manpage_browse_entries(cat: Iterable[str], entries: Mapping[str, ManPage]) -> None:
    checks = sorted(entries.values(), key=lambda m: (m.title, m.name))

    choices = [(str(num), mp.title) for num, mp in enumerate(checks, start=1)]

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
            write_output(ConsoleManPageRenderer(checks[index]).render_page())
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


def parse_man_page(name: str, path: Path) -> ManPage:
    with path.open(encoding="utf-8") as fp:
        content = fp.read()

    try:
        parsed = _parse_to_raw(path, content)
        return ManPage(
            name=name,
            path=path,
            title=str(parsed["title"]),
            agents=parsed["agents"].replace(" ", "").split(","),
            license=parsed["license"],
            distribution=parsed["distribution"],
            description=parsed["description"],
            catalog=parsed["catalog"].split("/"),
            item=parsed.get("item"),
            discovery=parsed.get("discovery") or parsed.get("inventory"),
            cluster=parsed.get("cluster"),
        )
    except (KeyError, MKGeneralException) as msg:
        if cmk.ccc.debug.enabled():
            raise
        return ManPage.fallback(
            name=name,
            path=path,
            content=content,
            msg=str(msg),
        )


def _parse_to_raw(path: Path, content: str) -> Mapping[str, str]:
    parsed: dict[str, list[str]] = defaultdict(list)
    current: list[str] = []

    for no, line in enumerate(content.splitlines(), start=1):
        if not line.strip() or line.startswith(" "):  # continuation line
            current.append(line.strip())
            continue

        try:
            key, rest = line.split(":", 1)
        except ValueError as exc:
            raise MKGeneralException(f"Syntax error in {path} line {no} ({exc}).\n")

        current = parsed[key]
        current.append(rest.strip())

    return {k: "\n".join(v).strip() for k, v in parsed.items()}


def write_output(rendered_page: str) -> None:
    if sys.stdout.isatty():
        with suppress(FileNotFoundError):
            subprocess.run(
                ["/usr/bin/less", "-S", "-R", "-Q", "-u", "-L"],
                input=rendered_page,
                encoding="utf8",
                check=False,
            )
            return
    sys.stdout.write(rendered_page)


class ManPageRenderer:
    def __init__(self, man_page: ManPage) -> None:
        self.name = man_page.name
        self._page = man_page

    def render_page(self) -> str:
        self._print_header()
        self._print_manpage_title(self._page.title)

        self._print_begin_splitlines()

        ags = [CHECK_MK_AGENTS.get(agent, agent.upper()) for agent in self._page.agents]
        self._print_info_line(
            "Distribution:            ", _format_distribution(self._page.distribution)
        )
        self._print_info_line("License:                 ", self._page.license)
        self._print_info_line("Supported Agents:        ", ", ".join(ags))
        self._print_end_splitlines()

        self._print_empty_line()
        self._print_textbody(self._page.description)

        if self._page.item:
            self._print_subheader("Item")
            self._print_textbody(self._page.item)

        if self._page.discovery:
            self._print_subheader("Discovery")
            self._print_textbody(self._page.discovery)

        self._print_empty_line()
        return self._get_value()

    def _get_value(self) -> str:
        raise NotImplementedError()

    def _print_header(self) -> None:
        raise NotImplementedError()

    def _print_manpage_title(self, title: str) -> None:
        raise NotImplementedError()

    def _print_info_line(self, left: str, right: str) -> None:
        raise NotImplementedError()

    def _print_subheader(self, line: str) -> None:
        raise NotImplementedError()

    def _print_line(self, line: str, *, color: str | None = None, no_markup: bool = False) -> None:
        raise NotImplementedError()

    def _print_begin_splitlines(self) -> None:
        pass

    def _print_end_splitlines(self) -> None:
        pass

    def _print_empty_line(self) -> None:
        raise NotImplementedError()

    def _print_textbody(self, text: str) -> None:
        raise NotImplementedError()


def _format_distribution(distr: str) -> str:
    match distr:
        case "check_mk":
            return "Official part of Checkmk"
        case "check_mk_cloud":
            return "Official part of Checkmk Cloud Edition"
        case _:
            return distr


class ConsoleManPageRenderer(ManPageRenderer):
    def __init__(self, man_page: ManPage) -> None:
        super().__init__(man_page)
        self._buffer: list[str] = []
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

    def _get_value(self) -> str:
        return "".join(self._buffer)

    def _patch_braces(self, line: str, *, color: str) -> str:
        """Replace braces in the line with a colors
        { -> self._tty_color
        } -> cmk.utils.tty.normal + attr
        All consequent braces except first one are ignored
        Examples:
        '{{{TEXT}}}' -> '<self._tty_color>{{TEXT<tty.normal><attr>}}'
        '{{TEXT}}'   -> '<self._tty_color>{TEXT<tty.normal><attr>}'
        '{TEXT}'     -> '<self._tty_color>TEXT<tty.normal><attr>'
        """
        return re.sub("(?<!{){", self._tty_color, re.sub("(?<!})}", tty.normal + color, line))

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
        self._buffer.append(
            self._subheader_color
            + " "
            + tty.underline
            + line.upper()
            + self._normal_color
            + (" " * (self.__width - 1 - len(line)))
            + tty.normal
            + "\n"
        )

    def _print_line(self, line: str, *, color: str | None = None, no_markup: bool = False) -> None:
        if color is None:
            color = self._normal_color

        if no_markup:
            text = line
            l = len(line)
        else:
            text = self._patch_braces(line, color=color)
            l = self._print_len(line)

        self._buffer.append(f"{color} ")
        self._buffer.append(text)
        self._buffer.append(" " * (self.__width - 2 - l))
        self._buffer.append(f" {tty.normal}\n")

    def _print_splitline(self, attr1: str, left: str, color: str, right: str) -> None:
        self._buffer.append(f"{attr1} {left}")
        self._buffer.append(color)
        self._buffer.append(self._patch_braces(right, color=color))
        self._buffer.append(" " * (self.__width - 1 - len(left) - self._print_len(right)))
        self._buffer.append(tty.normal + "\n")

    def _print_empty_line(self) -> None:
        self._print_line("", color=tty.colorset(7, 4))

    def _print_len(self, word: str) -> int:
        # In case of double braces remove only one brace for counting the length
        netto = word.replace("{{", "x").replace("}}", "x").replace("{", "").replace("}", "")
        netto = re.sub("\033[^m]+m", "", netto)
        return len(netto)

    def _wrap_text(self, text: str, width: int, color: str = tty.colorset(7, 4)) -> Sequence[str]:
        wrapped: list[str] = []
        line = ""
        col = 0
        for word in text.split():
            if word == "<br>":
                if line != "":
                    wrapped.extend((self._fillup(line, width), self._fillup("", width)))
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
                line += self._patch_braces(word, color=color)
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
        color = tty.colorset(7, 4)
        for line in wrapped:
            self._print_line(line, color=color)


class NowikiManPageRenderer(ManPageRenderer):
    def __init__(self, man_page: ManPage) -> None:
        super().__init__(man_page)
        self.__output = StringIO()

    def _get_value(self) -> str:
        return self.__output.getvalue()

    def _print_header(self) -> None:
        self.__output.write("TI:Check manual page of %s\n" % self.name)
        # It does not make much sense to print the date of the HTML generation
        # of the man page here. More useful would be the Checkmk version where
        # the plug-in first appeared. But we have no access to that - alas.
        # self.__output.write("DT:%s\n" % (time.strftime("%Y-%m-%d")))
        self.__output.write("SA:check_plugins_catalog,check_plugins_list\n")

    def _print_manpage_title(self, title: str) -> None:
        self.__output.write(f"<b>{title}</b>\n")

    def _print_info_line(self, left: str, right: str) -> None:
        self.__output.write(f"<tr><td>{left}</td><td>{right}</td></tr>\n")

    def _print_subheader(self, line: str) -> None:
        self.__output.write(f"H2:{line}\n")

    def _print_line(self, line: str, *, color: str | None = None, no_markup: bool = False) -> None:
        content = line if no_markup else _apply_markup(line)
        self.__output.write(f"{content}\n")

    def _print_begin_splitlines(self) -> None:
        self.__output.write("<table>\n")

    def _print_end_splitlines(self) -> None:
        self.__output.write("</table>\n")

    def _print_empty_line(self) -> None:
        self.__output.write("\n")

    def _print_textbody(self, text: str) -> None:
        self.__output.write(f"{_apply_markup(text)}\n")


def _apply_markup(line: str) -> str:
    """Replace bracers with markup
    '{{' -> '<tt>&#123;'
    '{' -> '<tt>'
    '}}' -> '&#125;</tt>'
    '}' -> '</tt>'
    """
    return (
        line.replace("{{", "{&#123;")
        .replace("}}", "&#125;}")
        .replace("{", "<tt>")
        .replace("}", "</tt>")
    )


_SerializableManPageDerivative = dict[str, str | dict[str, str] | list[dict[str, str]] | None]


def man_pages_for_website_export(
    plugin_families: Mapping[str, Sequence[str]],
    group_subdir: str,
) -> dict[str, _SerializableManPageDerivative]:
    """This is called from `scripts/create_man_pages.py` of the websites-essentials repo!

    The result should be json serializable.
    """
    return {
        name: _extend_categorization_info(parse_man_page(name, path))
        for name, path in make_man_page_path_map(plugin_families, group_subdir).items()
    }


def _extend_categorization_info(man_page: ManPage) -> _SerializableManPageDerivative:
    return {
        "name": man_page.name,
        "path": str(man_page.path),
        "title": man_page.title,
        "agents": {agent: CHECK_MK_AGENTS.get(agent, agent.title()) for agent in man_page.agents},
        "catalog": [
            {category: CATALOG_TITLES.get(category, category.title()) for category in categories}
            for categories in _make_catalog_entries(man_page.catalog, man_page.agents)
        ],
        "license": man_page.license,
        "distribution": man_page.distribution,
        "description": man_page.description,
        "item": man_page.item,
        "discovery": man_page.discovery,
        "cluster": man_page.cluster,
    }
