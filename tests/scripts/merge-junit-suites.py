#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Merge several junit report files (combining suites of the same name)."""

import os
import sys
from xml.etree import ElementTree

args = sys.argv[1:]
argc = len(args)

stats_only = "--stats-only" in args
print_stats = stats_only or "--stats" in args
if any(_.startswith("-") for _ in args):
    files_idx = min(args.index(_) for _ in args if not _.startswith("-"))
    files = args[files_idx : min(args.index(_, files_idx) for _ in args if _.startswith("-"))]
else:
    files = args
input_files = files if stats_only else files[0:-1]
output_file = None if stats_only else files[-1]
pytest_suite_name = (
    args[args.index("--pytest-suite-name") + 1] if "--pytest-suite-name" in args else "pytest"
)

if len(files) < 1 and stats_only:
    print("Insufficient arguments to generate statistics! Please provide one or more input files.")
    sys.exit(1)
if len(files) < 2 and not stats_only:
    print(
        "Insufficient arguments to merge reports! Please provide one or more input files and one output file."
    )
    sys.exit(1)

if not all(os.path.exists(file) for file in input_files):
    print("Please make sure all input files exist and can be read!")
    sys.exit(2)


if output_file and os.path.exists(output_file):
    print(f'Output file "{output_file}" already exists!')
    sys.exit(3)

tree = ElementTree.parse(input_files[0])
root = tree.getroot()

# merge additional source reports (if any)
for input_file in input_files[1:]:
    for _ in ElementTree.parse(input_file).getroot():
        root.append(_)

# override default pytest suite name (if specified)
if pytest_suite_name != "pytest":
    for _ in root.findall("testsuite"):
        if _.attrib.get("name") == "pytest":
            _.attrib["name"] = pytest_suite_name

suites: dict[str, dict] = {str(_.attrib.get("name")): {} for _ in root}
sum_attr = {"errors", "failures", "skipped", "tests", "time"}
set_attr = {"hostname"}
min_attr = {"timestamp"}

# merge suites of same name and get combined statistics
for suite, value in suites.items():
    nodes = root.findall(f"testsuite[@name='{suite}']")
    last_node_idx = len(nodes) - 1
    for node_idx, child in enumerate(reversed(nodes)):
        for attr in sum_attr:
            child_attr = child.attrib.get(attr)
            assert child_attr
            if child_attr.isdecimal():
                value[attr] = value.get(attr, 0) + int(child_attr)
                continue
            value[attr] = value.get(attr, 0.0) + float(child_attr)
        for attr in set_attr:
            items = value.get(attr, "").split(",") + [child.attrib.get(attr)]
            value[attr] = ", ".join({_ for _ in items if _})
        for attr in min_attr:
            val = child.attrib.get(attr)
            assert val is not None
            value[attr] = min(val, value.get(attr, val))
        if node_idx < last_node_idx:
            for grandchild in child:
                if node := root.find(f"testsuite[@name='{suite}']"):
                    node.append(grandchild)
            root.remove(child)
    for key in value:
        if node := root.find(f"testsuite[@name='{suite}']"):
            node.attrib[key] = str(value[key])
        if print_stats:
            print(f"{suite}.{key}: {value[key]}")

if output_file and not stats_only:
    tree.write(output_file)
