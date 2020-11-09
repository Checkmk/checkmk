#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
import getopt
import socket
import traceback
from typing import Any, Dict, Optional, List, Tuple, Union

import snap7  # type: ignore[import]
from snap7.common import Snap7Library  # type: ignore[import]
from snap7.snap7types import S7AreaCT, S7AreaDB, S7AreaMK, S7AreaPA, S7AreaPE, S7AreaTM  # type: ignore[import]


def usage():
    sys.stderr.write("""Check_MK Siemens PLC Agent

USAGE: agent_siemens_plc [OPTIONS] HOSTSPECS...
       agent_siemens_plc -h

HOSTSPECS:
  A HOSTSPEC specifies the hosts to contact and the data to fetch
  from each host. A hostspec is built of minimum 5 ";"
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
                                needs to be unique within a group of VALUETYPES.

OPTIONS:
  -h, --help                    Show this help message and exit
  -t, --timeout SEC             Set the network timeout to <SEC> seconds.
                                Default is 10 seconds. Note: the timeout is not
                                applied to the whole check, instead it is used for
                                each network connect.
  --debug                       Debug mode: let Python exceptions come through
""")


def get_dint(_bytearray, byte_index):
    """
    Get int value from bytearray.

    double int are represented in four bytes
    """
    byte3 = _bytearray[byte_index + 3]
    byte2 = _bytearray[byte_index + 2]
    byte1 = _bytearray[byte_index + 1]
    byte0 = _bytearray[byte_index]
    return byte3 + (byte2 << 8) + (byte1 << 16) + (byte0 << 32)


def area_name_to_area_id(name):
    return {
        'db': S7AreaDB,
        'input': S7AreaPE,
        'output': S7AreaPA,
        'merker': S7AreaMK,
        'timer': S7AreaTM,
        'counter': S7AreaCT,
    }[name]


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    short_options = 'h:t:d'
    long_options = ['help', 'timeout=', 'debug']

    devices: List[Dict[str, Any]] = []
    opt_debug = False
    opt_timeout = 10

    try:
        opts, args = getopt.getopt(sys_argv, short_options, long_options)
    except getopt.GetoptError as err:
        sys.stderr.write("%s\n" % err)
        return 1

    for o, a in opts:
        if o in ['--debug']:
            opt_debug = True
        elif o in ['-t', '--timeout']:
            opt_timeout = int(a)
        elif o in ['-h', '--help']:
            usage()
            sys.exit(0)

    if not args:
        sys.stderr.write("ERROR: You missed to provide the needed arguments.\n")
        usage()
        return 1

    for arg in args:
        parts = arg.split(';')
        if len(parts) < 6:
            sys.stderr.write("ERROR: Not enough arguments: %s\n" % arg)
            usage()
            return 1

        values = []
        for spec in parts[5:]:
            p = spec.split(',')
            if len(p) != 5:
                sys.stderr.write("ERROR: Invalid value specified: %s\n" % spec)
                usage()
                return 1

            if ':' in p[0]:
                area_name, db_number = p[0].split(':')
                area: Tuple[str, Optional[int]] = (area_name, int(db_number))
            elif p[0] in ["merker", "input", "output", "counter", "timer"]:
                area = (p[0], None)
            else:
                area = ("db", int(p[0]))

            byte, bit = map(int, p[1].split('.'))

            if ':' in p[2]:
                typename, size_str = p[2].split(':')
                datatype: Union[Tuple[str, int], str] = (typename, int(size_str))
            else:
                datatype = p[2]

            # area, address, datatype, valuetype, ident
            values.append((area, (byte, bit), datatype, p[3], p[4]))

        devices.append({
            'host_name': parts[0],
            'host_address': parts[1],
            'rack': int(parts[2]),
            'slot': int(parts[3]),
            'port': int(parts[4]),
            'values': values,
        })

    socket.setdefaulttimeout(opt_timeout)

    datatypes = {
        # type-name   size(bytes) parse-function
        # A size of None means the size is provided by configuration
        'dint': (4, lambda data, offset, size, bit: get_dint(data, offset)),
        'real': (8, lambda data, offset, size, bit: snap7.util.get_real(data, offset)),
        'bit': (1, lambda data, offset, size, bit: snap7.util.get_bool(data, offset, bit)),
        # str currently handles "zeichen" (character?) formated strings. For byte coded strings
        # we would have to use get_string(data, offset-1)) from snap7.utils
        'str': (None, lambda data, offset, size, bit: data[offset:offset + size]),
    }

    # The dynamic library detection of Snap7Library using ctypes.util.find_library does not work for
    # some reason. Load the library from our standard path.
    Snap7Library(lib_location="%s/lib/libsnap7.so" % os.environ["OMD_ROOT"])

    unhandled_error = False
    for device in devices:
        try:
            client = snap7.client.Client()
            client.connect(device['host_address'], device['rack'], device['slot'], device['port'])

            sys.stdout.write("<<<siemens_plc_cpu_state>>>\n")
            sys.stdout.write(client.get_cpu_state() + "\n")

            sys.stdout.write("<<<siemens_plc>>>\n")
            # We want to have a minimum number of reads. We try to only use
            # a single read and detect the memory area to fetch dynamically
            # based on the configured values
            addresses: Dict = {}
            start_address = None
            end_address = None
            for area, (byte, bit), datatype, valuetype, ident in device['values']:
                if isinstance(datatype, tuple):
                    size: Optional[int] = datatype[1]
                else:
                    size = datatypes[datatype][0]
                addresses.setdefault(area, [None, None])
                start_address, end_address = addresses[area]

                if start_address is None or byte < start_address:
                    addresses[area][0] = byte

                # TODO: Is the None case correct?
                end = byte + (0 if size is None else size)
                if end_address is None or end > end_address:
                    addresses[area][1] = end

            # Now fetch the data from each db number
            data = {}
            for (area_name, db_number), (start, end) in addresses.items():
                area_id = area_name_to_area_id(area_name)
                data[(area_name, db_number)] = client.read_area(area_id,
                                                                db_number,
                                                                start,
                                                                size=end - start)

            # Now loop all values to be fetched and extract the data
            # from the bytes fetched above
            for (area_name, db_number), (byte, bit), datatype, valuetype, ident in device['values']:
                if isinstance(datatype, tuple):
                    typename, size = datatype
                    parse_func = datatypes[typename][1]
                else:
                    size, parse_func = datatypes[datatype]

                start, end = addresses[(area_name, db_number)]
                fetched_data = data[(area_name, db_number)]

                value = parse_func(fetched_data, byte - start, size, bit)
                sys.stdout.write("%s %s %s %s\n" % (device['host_name'], valuetype, ident, value))
        except Exception:
            sys.stderr.write('%s: Unhandled error: %s' %
                             (device['host_name'], traceback.format_exc()))
            if opt_debug:
                raise
            unhandled_error = True

    return 1 if unhandled_error else 0
