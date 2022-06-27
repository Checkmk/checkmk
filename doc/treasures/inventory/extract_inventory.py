#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Author: Goetz Golla, gg@mathias-kettner.de

# This script extracts data of the hardware inventory to csv files

# TODO: Fix the horrible mix between local/global naming.
# pylint: disable=redefined-outer-name

import hashlib
import os
import re
import sys
import time
from typing import Any, Dict

relations = {
    "devices": {
        "columns": (
            ("@hostname", "import_id"),  # special functions start with "@"
            ("!sla", "import_data_source_id"),  # fixed value is prepended with "!"
            ("!default", "import_org_level_2_id"),
            ("@hostname", "device_key"),
            ("hardware.system.manufacturer", "device_manufacturer"),
            ("hardware.system.family", "device_model"),
            ("hardware.system.serial", "serial_number"),
            ("software.os.name", "operating_system"),
            ("@inventory_date", "inventory_date"),
            ("software.os.install_date", "installation_date"),
            ("hardware.cpu.sockets", "cpu_socket_count"),
            ("hardware.cpu.cpus", "cpu_chip_count"),
            ("hardware.cpu.cores", "cpu_core_count"),
            ("hardware.cpu.max_speed", "cpu_speed"),
            ("hardware.cpu.model", "cpu_name"),
        ),
        "filter": {},
        "converter": {
            "software.os.install_date": lambda val: time.strftime("%Y-%m-%d", time.localtime(val)),
            "@inventory_date": lambda val: time.strftime("%Y-%m-%d", time.localtime(val)),
            "hardware.cpu.max_speed": lambda val: val / 1000000.0,  # hz in mhz
        },
    },
    "inv_raw_arp": {
        "columns": (
            ("software.packages:*.+@hostname+vendor+name+version", "import_id"),
            ("software.packages:*.vendor", "publisher"),
            ("software.packages:*.name", "product"),
            ("software.packages:*.version", "product_version"),
            ("@hostname", "import_device_id"),
        ),
        "filter": {
            "software.packages:*.package_type": "registry",  # nur aus registry
        },
        "converter": {},
    },
    "inv_raw_file": {
        "columns": (
            ("software.packages:*.+@hostname+name+path", "import_id"),
            ("software.packages:*.name", "file_name"),
            ("software.packages:*.size", "file_size"),
            ("software.packages:*.path", "file_path"),
            ("software.packages:*.vendor", "publisher"),
            ("software.packages:*.summary", "product"),
            ("software.packages:*.version", "product_version"),
            ("@hostname", "import_device_id"),
        ),
        "filter": {
            "software.packages:*.package_type": "exe",  # nur exe files
        },
        "converter": {},
    },
    "inv_raw_generic(OS)": {
        "columns": (
            ("software.os.name", "generic_key"),
            ("@hostname", "import_id"),
        ),
        "filter": {},
        "converter": {},
    },
    "inv_raw_generic(Linux)": {
        "columns": (
            ("software.packages:*.+@hostname+name+version", "import_id"),
            ("software.packages:*.name", "name"),
            ("software.packages:*.version", "product_version"),
            ("@hostname", "import_device_id"),
        ),
        "filter": {
            "software.packages:*.package_type": "deb",  # nur exe files
        },
        "converter": {},
    },
}  # type: Dict[str, Dict[str, Any]]

omd_root = os.environ["OMD_ROOT"]

# both directories need to have a trailing slash "/" !
inv_dir = "%s/var/check_mk/inventory/" % omd_root
out_dir = "/var/tmp/"

if not omd_root:
    print("This script is only executable as site user")
    sys.exit(1)


def is_list(relation) -> bool:
    list_start = ""
    if isinstance(relation, dict):  # filter and converter are dicts, check them too
        relation = relation.keys()
    for field in relation:
        if not field.startswith("@"):
            if ":*" in field:
                is_list = True
                list_start = field.split(":")[0]
            else:
                is_list = False
            break
    for field in relation:
        if (
            (is_list != (":*" in field) or not field.startswith(list_start))
            and not field.startswith("@")
            and not field.startswith("!")
        ):
            print("bad definition of relation, must be list or dict, not both:")
            sys.exit(1)
    return list_start


def filt_it(package, relation):
    filt_start = is_list(relation["filter"])
    elements = [col[0] for col in relation["columns"]]
    list_start = is_list(elements)
    if filt_start != list_start:  # do not filter if filter does not fit
        return False
    for field in relation["filter"].keys():
        if field:
            should_be = relation["filter"][field]
            field = re.sub(list_start + ":\\*.", "", field)
            for item in field.split("."):
                value = package[item]
                if type(value) in (str, int, float) and re.search(should_be, value):

                    return False
    return True


def convert_it(c_relation, item, field):
    for c_field in c_relation.keys():
        if c_field == field:
            item = c_relation[field](item)  # apply the function defined to item
    return item


def print_line(out_rel, items):
    outtxt = '", "'.join(map(str, items))
    out_rel.write('"')
    out_rel.write("%s" % outtxt)
    out_rel.write('"\n')


# special values starting with a "@"
def special_value(item, hostname):
    if item == "@hostname":
        return hostname
    if item == "@inventory_date":
        return inventory_date[hostname]
    return ""


def no_list_get(hostname, field):
    out_line = ""
    if field.startswith("!"):
        out_line = re.sub("^!", "", field)
    else:
        subtree = all_data[hostname]
        for item in field.split("."):
            if item.startswith("@"):  # take subtree from special_value
                subtree = special_value(item, hostname)
            else:
                try:
                    subtree = subtree[item]
                except Exception:
                    break
            if type(subtree) in (str, int, float):
                out_line = convert_it(relations[ofs]["converter"], subtree, field)
    return out_line


def list_get(hostname, list_start):
    items = []
    subtree = all_data[hostname]
    for item in list_start.split("."):
        try:
            subtree = subtree[item]
        except Exception:
            print("   %s does not exist in database of host" % item)
    if isinstance(subtree, list):
        for package in subtree:
            if filt_it(package, relations[ofs]):
                continue
            for field in elements:
                if field:
                    field = re.sub(list_start + ":\\*.", "", field)
                    for item in field.split("."):
                        if item.startswith("@"):  # take subtree vom special_value
                            value = special_value(item, hostname)
                        else:
                            try:
                                value = package[item]
                            except Exception:
                                break
                    if type(value) in (str, int, float):
                        items.append(value)
                else:
                    items.append("")
    return items


# extract all data
all_data = {}
inventory_date = {}
for hostname in os.listdir(inv_dir):
    # ignore gziped files and invisible files in directory for now
    if hostname.endswith(".gz") or hostname.startswith("."):
        continue
    fn = inv_dir + hostname
    if os.path.isfile(fn):
        a = eval(open(fn, "r").read())
        all_data[hostname] = a
        inventory_date[hostname] = os.path.getmtime(fn)

# loop over all relations, create an output file for each relation
for ofs in relations:
    ofn = out_dir + ofs
    out_rel = open(ofn, "w")
    titles = [col[1] for col in relations[ofs]["columns"]]
    print_line(out_rel, titles)
    elements = [col[0] for col in relations[ofs]["columns"]]
    list_start = is_list(elements)
    if list_start == "":
        for hostname in all_data:
            print("creating relation %s for %s" % (ofs, hostname))
            items = []
            for field in elements:
                items.append(no_list_get(hostname, field))
            print_line(out_rel, items)
        out_rel.close()
    else:
        for hostname in all_data:
            print("creating relation %s for %s" % (ofs, hostname))
            subtree = all_data[hostname]
            for item in list_start.split("."):
                try:
                    subtree = subtree[item]
                except Exception:
                    print("   %s does not exist in database of host" % item)
            if isinstance(subtree, list):
                for package in subtree:
                    if filt_it(package, relations[ofs]):
                        continue
                    items = []
                    for field in elements:
                        if field:
                            field = re.sub(list_start + ":\\*.", "", field)
                            concat = ""
                            for item in field.split("."):
                                if item.startswith("@"):  # take subtree vom special_value
                                    value = special_value(item, hostname)
                                elif item.startswith("+"):
                                    for item2 in item.split("+"):
                                        if item2:
                                            if item2.startswith(
                                                "@"
                                            ):  # take subtree vom special_value
                                                concat += special_value(item2, hostname)
                                            else:
                                                try:
                                                    concat += package[item2]
                                                except Exception:
                                                    continue
                                    value = hashlib.md5(concat.encode("utf-8")).hexdigest()
                                else:
                                    try:
                                        value = package[item]
                                    except Exception:
                                        items.append("")
                                        break
                                if type(value) in (str, int, float):
                                    items.append(value)
                        else:
                            items.append("")
                    print_line(out_rel, items)
        out_rel.close()
