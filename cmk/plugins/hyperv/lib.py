#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-

#
# the parse functions should be adapted to json output from the agent scripts
# it would be way better than the current output
#


def hyperv_vm_convert(string_table):
    parsed = {}
    for line in string_table:
        parsed[line[0]] = " ".join(line[1:])

    return parsed


counter_translation = {
    "durchschnittl. warteschlangenlänge der datenträger-lesevorgänge": "avg. disk read queue length",
    "durchschnittl. warteschlangenlänge der datenträger-schreibvorgänge": "avg. disk write queue length",
    "mittlere sek./lesevorgänge": "avg. disk sec/read",
    "mittlere sek./schreibvorgänge": "avg. disk sec/write",
    "lesevorgänge/s": "disk reads/sec",
    "schreibvorgänge/s": "disk writes/sec",
    "bytes gelesen/s": "disk read bytes/sec",
    "bytes geschrieben/s": "disk write bytes/sec",
}


def parse_hyperv_io(string_table):
    parsed = {}
    for line in string_table:
        value = line[-1]
        data = " ".join(line[:-1])
        _empty, _empty2, host, lun, name = data.split("\\", 4)
        if name in counter_translation.keys():
            name = counter_translation[name]
        if lun not in parsed:
            parsed[lun] = {}
        parsed[lun][name] = value
        parsed[lun]["node"] = host
    return parsed


def parse_hyperv(string_table):
    datatypes = {
        "vhd": "vhd.name",
        "nic": "nic.name",
        "checkpoints": "checkpoint.name",
        "cluster.number_of_nodes": "cluster.node.name",
        "cluster.number_of_csv": "cluster.csv.name",
        "cluster.number_of_disks": "cluster.disk.name",
        "cluster.number_of_vms": "cluster.vm.name",
        "cluster.number_of_roles": "cluster.role.name",
        "cluster.number_of_networks": "cluster.network.name",
    }

    parsed = {}
    if len(string_table) == 0:
        return parsed

    datatype = datatypes.get(string_table[0][0])
    element = ""
    start = False
    counter = 1
    for line in string_table:
        if line[0] == datatype:
            if start is True:
                counter += 1
            else:
                start = True
            if datatype == "nic.name":
                element = " ".join(line[1:]) + f" {counter}"
            else:
                element = " ".join(line[1:])
            parsed[element] = {}
        elif start is True:
            parsed[element][line[0]] = " ".join(line[1:])

    return parsed
