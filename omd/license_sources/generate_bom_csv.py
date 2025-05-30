#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import csv
import json
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import IO, NamedTuple

LINKS = {
    "0BSD": "http://landley.net/toybox/license.html",
    "Apache-2.0": "https://opensource.org/licenses/Apache-2.0",
    "Artistic-1.0": "https://opensource.org/licenses/Artistic-1.0",
    "Artistic-1.0-Perl": "http://dev.perl.org/licenses/artistic.html",
    "Artistic-2.0": "http://www.perlfoundation.org/artistic_license_2_0",
    "BSD-2-Clause": "https://opensource.org/licenses/BSD-2-Clause",
    "BSD-3-Clause": "https://opensource.org/licenses/BSD-3-Clause",
    "BSD-4-Clause-UC": "http://www.freebsd.org/copyright/license.html",
    "BSL-1.0": "https://opensource.org/licenses/BSL-1.0",
    "BlueOak-1.0.0": "https://blueoakcouncil.org/license/1.0.0",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/legalcode",
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",
    "CDDL-1.0": "https://opensource.org/licenses/cddl1",
    "CNRI-Python-GPL-Compatible": "http://www.python.org/download/releases/1.6.1/download_win/",
    "Caldera": "http://www.lemis.com/grog/UNIX/ancient-source-all.pdf",
    "EPL-2.0": "https://www.eclipse.org/legal/epl-2.0",
    "GPL-1.0-or-later": "https://www.gnu.org/licenses/old-licenses/gpl-1.0-standalone.html",
    "GPL-2.0": "https://www.gnu.org/licenses/old-licenses/gpl-2.0-standalone.html",
    "GPL-2.0-only": "https://www.gnu.org/licenses/old-licenses/gpl-2.0-standalone.html",
    "GPL-2.0-or-later": "https://www.gnu.org/licenses/old-licenses/gpl-2.0-standalone.html",
    "GPL-3.0": "https://www.gnu.org/licenses/gpl-3.0-standalone.html",
    "GPL-3.0-or-later": "https://www.gnu.org/licenses/gpl-3.0-standalone.html",
    "HPND": "https://opensource.org/licenses/HPND",
    "ISC": "https://opensource.org/licenses/ISC",
    "LGPL-2.1": "https://www.gnu.org/licenses/old-licenses/lgpl-2.1-standalone.html",
    "LGPL-2.1-only": "https://www.gnu.org/licenses/old-licenses/lgpl-2.1-standalone.html",
    "LGPL-2.1-or-later": "https://www.gnu.org/licenses/old-licenses/lgpl-2.1-standalone.html",
    "LGPL-3.0": "https://www.gnu.org/licenses/lgpl-3.0-standalone.html",
    "LGPL-3.0-only": "https://www.gnu.org/licenses/lgpl-3.0-standalone.html",
    "LGPL-3.0-or-later": "https://www.gnu.org/licenses/lgpl-3.0-standalone.html",
    "MIT": "https://opensource.org/licenses/MIT",
    "MIT-0": "https://github.com/aws/mit-0",
    "MIT-CMU": "https://github.com/python-pillow/Pillow/blob/fffb426092c8db24a5f4b6df243a8a3c01fb63cd/LICENSE",
    "MPL-1.1": "http://www.mozilla.org/MPL/MPL-1.1.html",
    "MPL-2.0": "https://opensource.org/licenses/MPL-2.0",
    "OFL-1.1": "https://opensource.org/license/OFL-1.1",
    "OpenSSL": "http://www.openssl.org/source/license.html",
    "PSF-2.0": "https://opensource.org/licenses/Python-2.0",
    "Python-2.0": "https://opensource.org/licenses/Python-2.0",
    "TCL": "https://fedoraproject.org/wiki/Licensing/TCL",
    "UPL-1.0": "https://opensource.org/license/UPL",
    "Unicode-3.0": "https://www.unicode.org/license.txt",
    "Unicode-DFS-2016": "https://www.unicode.org/license.txt",
    "Unlicense": "https://opensource.org/licenses/unlicense",
    "WTFPL": "https://spdx.org/licenses/WTFPL.html",
    "ZPL-2.1": "https://old.zope.dev/Resources/ZPL/",
    "Zlib": "https://opensource.org/license/Zlib",
    "xinetd": "https://fedoraproject.org/wiki/Licensing/Xinetd_License",
}


class CsvRow(NamedTuple):
    name: str
    version: str
    license: str
    path: str

    def to_csv_row(self) -> tuple:
        return (
            self.name,
            self.version,
            self.license,
            _links_for_license(self.license),
            self.path,
            "",  # comment
        )


def _split_expression(expression: str) -> Iterator[str]:
    """split the license or the expression to the main licenses

    IMHO we should not add links, we mostly/only use standard licenses,
    everybody should be able to search them"""

    if expression.startswith("(") and expression.endswith(")"):
        expression = expression[1:-1]

    if " AND " in expression:
        for sub_expression in expression.split(" AND "):
            yield from _split_expression(sub_expression)
    elif " OR " in expression:
        for sub_expression in expression.split(" OR "):
            yield from _split_expression(sub_expression)
    elif " WITH " in expression:
        yield expression.split(" WITH ", 1)[0]
    else:
        yield expression.strip()


def _links_for_license(license_str: str) -> str:
    return "\n".join(LINKS[id_] for id_ in _split_expression(license_str) if id_ in LINKS)


def _get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bom", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def _license_from_bom(component_info: dict) -> str | None:
    """extract the license or expression from the BOM"""

    if "licenses" not in component_info:
        return None

    license_info = component_info["licenses"]
    if len(license_info) != 1:
        raise NotImplementedError(f"{license_info!r}")
    i = license_info[0]
    if "license" in i:
        return i["license"]["id"]
    if "expression" in i:
        return i["expression"]
    raise NotImplementedError(f"{license_info!r}")


def _path_from_bom(component_info: dict) -> str:
    """extract and concat paths from the bom"""

    paths = []
    for property_ in component_info["properties"]:
        if property_["name"] == "path":
            paths.append(property_["value"])
    return "\n".join(paths)


def _get_csv_sections(bom_info: dict) -> dict[str, list[CsvRow]]:
    """convert the bom_info to csv rows and add them to the correct section

    This aims mostly to be as close as possible/reasonable to the previous structure of the
    Licenses.csv.
    """
    csv_sections: dict[str, list[CsvRow]] = {
        "": [],
        "Icons": [],
        "JavaScript and CSS": [],
        "JavaScript dependencies": [],
    }

    for component in bom_info["components"]:
        license_ = _license_from_bom(component)
        if license_ is None:
            logging.warning("No license for %s %s", component["name"], component.get("purl", ""))
            continue

        if component.get("purl", "").startswith("pkg:pypi/"):
            csv_sections[""].append(
                CsvRow(
                    name=f"Python module: {component['name']}",
                    version=component["version"],
                    license=license_,
                    path="",
                )
            )
        elif component.get("purl", "").startswith("pkg:npm/"):
            csv_sections["JavaScript dependencies"].append(
                CsvRow(
                    name=component["name"],
                    version=component["version"],
                    license=license_,
                    path="",
                )
            )
        elif component.get("purl", "").startswith("pkg:cpan/") or component["name"] in (
            "Archive-Zip",
            "LWP-Protocol-https",
            "XML-LibXML",
        ):
            csv_sections[""].append(
                CsvRow(
                    name=f"Perl module: {component['name']}",
                    version=component["version"],
                    license=license_,
                    path="",
                )
            )
        elif component.get("purl", "").startswith("pkg:cargo/"):
            csv_sections[""].append(
                CsvRow(
                    name=f"Rust module: {component['name']}",
                    version=component["version"],
                    license=license_,
                    path="",
                )
            )
        elif component["name"] in ("kubernetes-logo", "nuvola-icons"):
            csv_sections["Icons"].append(
                CsvRow(
                    name=component["name"],
                    version="",
                    license=license_,
                    path=_path_from_bom(component),
                )
            )
        elif _path_from_bom(component).startswith("web/htdocs/"):
            csv_sections["JavaScript and CSS"].append(
                CsvRow(
                    name=component["name"],
                    version=component["version"],
                    license=license_,
                    path=_path_from_bom(component),
                )
            )
        else:
            csv_sections[""].append(
                CsvRow(
                    name=component["name"],
                    version=component["version"],
                    license=license_,
                    path=p if (p := _path_from_bom(component)) != "WORKSPACE" else "",
                )
            )
    return csv_sections


def _check_links(bom_info: dict) -> None:
    """make sure all licenses in the BOM have a link in the global LINKS"""

    licenses: set[str] = set()
    for l in {_license_from_bom(component) for component in bom_info["components"]}:
        if l is None:
            continue
        licenses.update(_split_expression(l))

    links_missing = False
    for l in licenses:
        if l not in LINKS:
            logging.error("No link for %s in LINKS", l)
            links_missing = True

    if links_missing:
        sys.exit("There are links to licenses missing")


def _write_csv(csv_sections: dict[str, list[CsvRow]], csv_file: IO[str]) -> None:
    """write the sections as csv to stdout"""
    writer = csv.writer(csv_file, lineterminator="\n")
    writer.writerow(
        ("Name", "Version", "License", "Link License Text", "Repository path", "Comment")
    )
    for section, rows in csv_sections.items():
        if section != "":
            writer.writerow(("", "", "", "", "", ""))
            writer.writerow((section, "", "", "", "", ""))
        for row in sorted(rows, key=lambda x: (x[0].lower(), *x[1:])):
            writer.writerow(row.to_csv_row())


def _main() -> None:
    logging.basicConfig()

    args = _get_args()

    with args.bom.open() as bom_file:
        bom_info = json.load(bom_file)

    _check_links(bom_info)

    with args.out.open("w") as csv_file:
        _write_csv(_get_csv_sections(bom_info), csv_file)


if __name__ == "__main__":
    _main()
