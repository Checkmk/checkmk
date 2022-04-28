#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import logging
import os
import socket
import sys
from itertools import groupby
from typing import Optional, Tuple, Union

import snap7  # type: ignore[import]
from snap7.common import Snap7Exception, Snap7Library  # type: ignore[import]
from snap7.snap7types import (  # type: ignore[import]
    S7AreaCT,
    S7AreaDB,
    S7AreaMK,
    S7AreaPA,
    S7AreaPE,
    S7AreaTM,
)

from cmk.special_agents.utils.agent_common import SectionWriter

# prevent snap7 logger to log errors directly to console
snap7.common.logger.setLevel(logging.CRITICAL + 10)

DATATYPES = {
    # type-name   size(bytes) parse-function
    # A size of None means the size is provided by configuration
    "dint": (4, lambda data, offset, size, bit: _get_dint(data, offset)),
    "real": (8, lambda data, offset, size, bit: snap7.util.get_real(data, offset)),
    "bit": (1, lambda data, offset, size, bit: snap7.util.get_bool(data, offset, bit)),
    # str currently handles "zeichen" (character?) formated strings. For byte coded strings
    # we would have to use get_string(data, offset-1)) from snap7.utils
    "str": (None, lambda data, offset, size, bit: data[offset : offset + size]),
}

HOSTSPEC_HELP_TEXT = """HOSTSPECS:
  A HOSTSPEC specifies the hosts to contact and the data to fetch
  from each host. A hostspec is built of minimum 6 ";"
  separated items, which are:

  HOST_NAME                     Logical name of the PLC
  HOST_ADDRESS                  Host name or IP address of the PLC
  RACK
  SLOT
  PORT                          The TCP port to communicate with
  VALUES                        One or several VALUES as defined below.
                                The values themselfs are separated by ";"

VALUES:
  A value is specified by the following single data fields, which are
  concatenated by a ",":

    AREA[:DB_NUMBER]            Identifier of the memory area to fetch (db, input,
                                output, merker, timer or counter), plus the optional
                                numeric identifier of the DB separeated by a ":".
    ADDRESS                     Memory address to read
    DATATYPE                    The datatype of the value to read
    VALUETYPE                   The logical type of the value
    IDENT                       An identifier of your choice. This identifier
                                is used by the Check_MK checks to access
                                and identify the single values. The identifier
                                needs to be unique within a group of VALUETYPES."""


def parse_spec(hostspec):
    """
    >>> parse_spec('4fcm;10.2.90.20;0;2;102;merker,5.3,bit,flag,Filterturm_Sammelstoerung_Telefon')
    {\
'host_name': '4fcm', \
'host_address': '10.2.90.20', \
'rack': 0, \
'slot': 2, \
'port': 102, \
'values': [{\
'area_name': 'merker', \
'db_number': None, \
'byte': 5, \
'bit': 3, \
'datatype': 'bit', \
'valuetype': 'flag', \
'ident': 'Filterturm_Sammelstoerung_Telefon'}]\
}
    """
    parts = hostspec.split(";")
    values = []
    for spec in parts[5:]:
        p = spec.split(",")
        if len(p) != 5:
            print("ERROR: Invalid value specified: %s" % spec, file=sys.stderr)
            return 1

        if ":" in p[0]:
            area_name, db_number = p[0].split(":")
            db_number = int(db_number)
        elif p[0] in ["merker", "input", "output", "counter", "timer"]:
            area_name, db_number = p[0], None
        else:
            area_name, db_number = "db", int(p[0])
        value = {
            "area_name": area_name,
            "db_number": db_number,
        }

        byte, bit = map(int, p[1].split("."))  # address
        value.update(
            {
                "byte": byte,
                "bit": bit,
            }
        )

        if ":" in p[2]:
            typename, size_str = p[2].split(":")
            datatype: Union[Tuple[str, int], str] = (typename, int(size_str))
        else:
            datatype = p[2]
        value.update(
            {
                "datatype": datatype,
            }
        )

        value.update(
            {
                "valuetype": p[3],
                "ident": p[4],
            }
        )

        values.append(value)

    return {
        "host_name": parts[0],
        "host_address": parts[1],
        "rack": int(parts[2]),
        "slot": int(parts[3]),
        "port": int(parts[4]),
        "values": values,
    }


def parse_arguments(sys_argv):
    parser = argparse.ArgumentParser(
        "Checkmk Siemens PLC agent", formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "--hostspec",
        "-s",
        action="append",
        type=parse_spec,
        required=True,
        help=(HOSTSPEC_HELP_TEXT),
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=10,
        help=(
            "Set the network timeout to <SEC> seconds. "
            "Default is 10 seconds.\n"
            "Note: the timeout is not applied to the whole check, instead it\n"
            "is used for each network connect."
        ),
    )
    parser.add_argument("--verbose", "-v", action="count", default=0)
    parser.add_argument(
        "--debug", action="store_true", help="Debug mode: let Python exceptions raise through"
    )

    return parser.parse_args(sys_argv)


def _get_dint(_bytearray, byte_index):
    """
    Get int value from bytearray.

    double int are represented in four bytes
    """
    byte3 = _bytearray[byte_index + 3]
    byte2 = _bytearray[byte_index + 2]
    byte1 = _bytearray[byte_index + 1]
    byte0 = _bytearray[byte_index]
    return byte3 + (byte2 << 8) + (byte1 << 16) + (byte0 << 32)


def _area_name_to_area_id(area_name):
    return {
        "db": S7AreaDB,
        "input": S7AreaPE,
        "output": S7AreaPA,
        "merker": S7AreaMK,
        "timer": S7AreaTM,
        "counter": S7AreaCT,
    }[area_name]


def _addresses_from_area_values(values):
    # We want to have a minimum number of reads. We try to only use
    # a single read and detect the memory area to fetch dynamically
    # based on the configured values
    start_address = None
    end_address = None
    for device_value in values:
        byte = device_value["byte"]
        if start_address is None or byte < start_address:
            start_address = byte

        datatype = device_value["datatype"]
        if isinstance(datatype, tuple):
            size: Optional[int] = datatype[1]
        else:
            size = DATATYPES[datatype][0]

        # TODO: Is the None case correct?
        end = byte + (0 if size is None else size)
        if end_address is None or end > end_address:
            end_address = end

    return start_address, end_address


def _cast_values(values, start_address, area_value):
    cast_values = []
    for device_value in values:
        datatype = device_value["datatype"]
        if isinstance(datatype, tuple):
            typename, size = datatype
            parse_func = DATATYPES[typename][1]
        else:
            size, parse_func = DATATYPES[datatype]

        value = parse_func(
            area_value,
            device_value["byte"] - start_address,
            size,
            device_value["bit"],
        )

        cast_values.append((device_value["valuetype"], device_value["ident"], value))

    return cast_values


def _group_device_values(device):
    """A device can have multiple sets of values. Group them by area name and db_number,
    so that the start and end address of the memroy area can be determined and only needs
    to be fetched once form the client.

    >>> [(i, list(j)) for i, j in _group_device_values({'values': [
    ... {'area_name': 'merker', 'db_number': None, 'arbitrary_values': 15},
    ... {'area_name': 'timer', 'db_number': None, 'arbitrary_values': 60},
    ... {'area_name': 'merker', 'db_number': None, 'arbitrary_values': 32}
    ... ]})]
    [\
(('merker', None), [{'area_name': 'merker', 'db_number': None, 'arbitrary_values': 15}, {'area_name': 'merker', 'db_number': None, 'arbitrary_values': 32}]), \
(('timer', None), [{'area_name': 'timer', 'db_number': None, 'arbitrary_values': 60}])\
]
    """
    yield from groupby(
        sorted(
            device["values"],
            key=lambda d: (
                d["area_name"],
                d["db_number"],
            ),
        ),
        lambda d: (
            d["area_name"],
            d["db_number"],
        ),
    )


def _snap7error(hostname, custom_text, raw_error_message):
    error_message = str(raw_error_message).replace("b' ", "'")
    return f"Host {hostname}: {custom_text}: {error_message}"


def main(sys_argv=None):

    args = parse_arguments(sys_argv or sys.argv[1:])

    socket.setdefaulttimeout(args.timeout)

    # The dynamic library detection of Snap7Library using ctypes.util.find_library does not work for
    # some reason. Load the library from our standard path.
    Snap7Library(lib_location="%s/lib/libsnap7.so" % os.environ["OMD_ROOT"])

    client = snap7.client.Client()

    for device in args.hostspec:

        hostname = device["host_name"]

        try:
            client.connect(device["host_address"], device["rack"], device["slot"], device["port"])
        except Snap7Exception as e:
            print(_snap7error(hostname, "Error connecting to device", e), file=sys.stderr)
            continue

        try:
            cpu_state = client.get_cpu_state()
        except Snap7Exception as e:
            cpu_state = None
            print(_snap7error(hostname, "Error reading device CPU state", e), file=sys.stderr)

        parsed_area_values = []
        for (area_name, db_number), iter_values in _group_device_values(device):
            values = list(iter_values)
            start_address, end_address = _addresses_from_area_values(values)
            try:
                area_value = client.read_area(
                    _area_name_to_area_id(area_name),
                    db_number,
                    start_address,
                    size=end_address - start_address,
                )
            except Snap7Exception as e:
                print(_snap7error(hostname, "Error reading data area", e), file=sys.stderr)
                continue

            parsed_area_values.extend(_cast_values(values, start_address, area_value))

        with SectionWriter("siemens_plc_cpu_state", None) as writer:
            if cpu_state is not None:
                writer.append(cpu_state)

        with SectionWriter("siemens_plc", None) as writer:
            for values in parsed_area_values:
                writer.append("%s %s %s %s" % (hostname, *values))


if __name__ == "__main__":
    main()
