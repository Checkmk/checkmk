#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import os
import socket
import sys
import traceback
from typing import Dict, Optional, Tuple, Union

import snap7  # type: ignore[import]
from snap7.common import Snap7Library  # type: ignore[import]
from snap7.snap7types import S7AreaCT, S7AreaDB, S7AreaMK, S7AreaPA, S7AreaPE, S7AreaTM  # type: ignore[import]

DATATYPES = {
    # type-name   size(bytes) parse-function
    # A size of None means the size is provided by configuration
    'dint': (4, lambda data, offset, size, bit: _get_dint(data, offset)),
    'real': (8, lambda data, offset, size, bit: snap7.util.get_real(data, offset)),
    'bit': (1, lambda data, offset, size, bit: snap7.util.get_bool(data, offset, bit)),
    # str currently handles "zeichen" (character?) formated strings. For byte coded strings
    # we would have to use get_string(data, offset-1)) from snap7.utils
    'str': (None, lambda data, offset, size, bit: data[offset:offset + size]),
}

HOSTSPEC_HELP_TEXT = '''HOSTSPECS:
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
                                needs to be unique within a group of VALUETYPES.'''


def parse_spec(hostspec):
    '''
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
    '''
    parts = hostspec.split(';')
    values = []
    for spec in parts[5:]:
        p = spec.split(',')
        if len(p) != 5:
            sys.stderr.write("ERROR: Invalid value specified: %s\n" % spec)
            return 1

        if ':' in p[0]:
            area_name, db_number = p[0].split(':')
            db_number = int(db_number)
        elif p[0] in ["merker", "input", "output", "counter", "timer"]:
            area_name, db_number = p[0], None
        else:
            area_name, db_number = "db", int(p[0])
        value = {
            'area_name': area_name,
            'db_number': db_number,
        }

        byte, bit = map(int, p[1].split('.'))  # address
        value.update({
            'byte': byte,
            'bit': bit,
        })

        if ':' in p[2]:
            typename, size_str = p[2].split(':')
            datatype: Union[Tuple[str, int], str] = (typename, int(size_str))
        else:
            datatype = p[2]
        value.update({
            'datatype': datatype,
        })

        value.update({
            'valuetype': p[3],
            'ident': p[4],
        })

        values.append(value)

    return {
        'host_name': parts[0],
        'host_address': parts[1],
        'rack': int(parts[2]),
        'slot': int(parts[3]),
        'port': int(parts[4]),
        'values': values,
    }


def parse_arguments(sys_argv):
    parser = argparse.ArgumentParser('Checkmk Siemens PLC Agent',
                                     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--hostspec',
                        '-s',
                        action='append',
                        type=parse_spec,
                        required=True,
                        help=(HOSTSPEC_HELP_TEXT))
    parser.add_argument('--timeout',
                        '-t',
                        type=int,
                        default=10,
                        help=('Set the network timeout to <SEC> seconds. '
                              'Default is 10 seconds.\n'
                              'Note: the timeout is not applied to the whole check, instead it\n'
                              'is used for each network connect.'))
    parser.add_argument('--verbose', '-v', action='count', default=0)
    parser.add_argument('--debug',
                        action='store_true',
                        help='Debug mode: let Python exceptions raise through')

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
        'db': S7AreaDB,
        'input': S7AreaPE,
        'output': S7AreaPA,
        'merker': S7AreaMK,
        'timer': S7AreaTM,
        'counter': S7AreaCT,
    }[area_name]


def _addresses_from_device(device):
    # We want to have a minimum number of reads. We try to only use
    # a single read and detect the memory area to fetch dynamically
    # based on the configured values
    addresses: Dict = {}
    start_address = None
    end_address = None
    for device_value in device['values']:
        datatype = device_value['datatype']
        if isinstance(datatype, tuple):
            size: Optional[int] = datatype[1]
        else:
            size = DATATYPES[datatype][0]

        area = device_value['area_name'], device_value['db_number']
        addresses.setdefault(area, [None, None])
        start_address, end_address = addresses[area]

        byte = device_value['byte']
        if start_address is None or byte < start_address:
            addresses[area][0] = byte

        # TODO: Is the None case correct?
        end = byte + (0 if size is None else size)
        if end_address is None or end > end_address:
            addresses[area][1] = end

    return addresses


def _cast_values(device, addresses, data):
    values = []
    for device_value in device['values']:
        datatype = device_value['datatype']
        if isinstance(datatype, tuple):
            typename, size = datatype
            parse_func = DATATYPES[typename][1]
        else:
            size, parse_func = DATATYPES[datatype]

        area_name = device_value['area_name']
        db_number = device_value['db_number']
        # the pylint warning below will be refactored out later
        start, end = addresses[(area_name, db_number)]  # pylint: disable=unused-variable
        fetched_data = data[(area_name, db_number)]

        value = parse_func(fetched_data, device_value['byte'] - start, size, device_value['bit'])

        values.append((device_value['valuetype'], device_value['ident'], value))

    return values


def main(sys_argv=None):

    args = parse_arguments(sys_argv or sys.argv[1:])

    socket.setdefaulttimeout(args.timeout)

    # The dynamic library detection of Snap7Library using ctypes.util.find_library does not work for
    # some reason. Load the library from our standard path.
    Snap7Library(lib_location="%s/lib/libsnap7.so" % os.environ["OMD_ROOT"])

    client = snap7.client.Client()

    devices = args.hostspec
    for device in devices:
        try:
            client.connect(device['host_address'], device['rack'], device['slot'], device['port'])

            cpu_state = client.get_cpu_state()

            addresses = _addresses_from_device(device)

            data = {}
            for (area_name, db_number), (start, end) in addresses.items():
                area_id = _area_name_to_area_id(area_name)
                data[(area_name, db_number)] = client.read_area(area_id,
                                                                db_number,
                                                                start,
                                                                size=end - start)

            sys.stdout.write("<<<siemens_plc_cpu_state>>>\n")
            sys.stdout.write(cpu_state + "\n")

            sys.stdout.write("<<<siemens_plc>>>\n")
            for valuetype, ident, value in _cast_values(device, addresses, data):
                sys.stdout.write("%s %s %s %s\n" % (device['host_name'], valuetype, ident, value))

        except Exception:
            sys.stderr.write('%s: Unhandled error: %s' %
                             (device['host_name'], traceback.format_exc()))
            if args.debug:
                raise


if __name__ == '__main__':
    main()
