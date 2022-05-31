#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# type: ignore[import]

__version__ = "2.1.0p1"

###################################################
# plugin to retrieve data from tinkerforge devices.
#
# please note that for this plugin to work, the tinkerforge api has to be installed
#  (included in OMD, otherwise get it from http://download.tinkerforge.com/bindings/python/)
# Also, if the tinkerforge device is connected directly to the computer via usb,
# the brick deamon has to be installed and running: http://download.tinkerforge.com/tools/brickd/)
#
# This has been designed to also work as a special agent. In this case the following configuration
# settings have to be provided on the command line

#######################################################
# sample configuration (/etc/check_mk/tinkerforge.cfg):
#
# host = "localhost"
# port = 4223
# segment_display_uid = "abc"         # uid of the sensor to display on the 7-segment display
# segment_display_brightness = 2      # brightness of the 7-segment display (0-7)
#
# to find the uid of a sensor, either use brickv or run the plugin
# manually. plugin output looks like this:
#   temperature,Ab3d5F.a.xyz,2475
# xyz is the uid you're looking for. It's always the last of the dot-separated sensor path
# (Ab3d5F is the id of the master brick to which the sensor is connected, a is the port
#  to which the sensor is connected)

##################
# developer notes:
#
# Support for individual bricklets has to be added in init_device_handlers.
#  Currently the bricklets included in the Starter Kit: Server Room Monitoring are
#  implemented

# Don't have tinkerforge module during tests. So disable those checks
# pylint: disable=import-error

import os
import sys
import time
from optparse import OptionParser  # pylint: disable=deprecated-module

try:
    from typing import List
except ImportError:
    pass


def install():
    dest = os.path.dirname(os.path.realpath(__file__))
    sys.stdout.write("installing tinkerforge python api to %s\n" % dest)
    if os.path.exists(os.path.join(dest, "tinkerforge")):
        sys.stdout.write("already installed\n")
        return 1

    if sys.version_info[0] >= 3:
        from io import BytesIO
        from urllib.request import urlopen  # pylint: disable=no-name-in-module
    else:
        from urllib2 import urlopen
        from cStringIO import StringIO as BytesIO
    import shutil
    from zipfile import ZipFile

    url = "http://download.tinkerforge.com/bindings/python/tinkerforge_python_bindings_latest.zip"
    response = urlopen(url)
    buf = BytesIO(response.read())
    with ZipFile(buf) as z:

        extract_files = [f for f in z.namelist() if f.startswith("source/tinkerforge")]
        z.extractall(dest, extract_files)

    shutil.move(os.path.join(dest, "source", "tinkerforge"), os.path.join(dest, "tinkerforge"))
    shutil.rmtree(os.path.join(dest, "source"))

    return 0


DEFAULT_SETTINGS = {
    "host": "localhost",
    "port": 4223,
    "segment_display_uid": None,
    "segment_display_brightness": 2,
}

# globals
segment_display_value = None
segment_display_unit = ""
segment_display = None


def id_to_string(identifier):
    return "%s.%s.%s" % (identifier.connected_uid, identifier.position, identifier.uid)


def print_generic(settings, sensor_type, ident, factor, unit, *values):
    if ident.uid == settings["segment_display_uid"]:
        global segment_display_value, segment_display_unit
        segment_display_value = int(values[0] * factor)
        segment_display_unit = unit
    sys.stdout.write(
        "%s,%s,%s\n" % (sensor_type, id_to_string(ident), ",".join([str(val) for val in values]))
    )


def print_ambient_light(conn, settings, uid):
    from tinkerforge.bricklet_ambient_light import BrickletAmbientLight

    br = BrickletAmbientLight(uid, conn)
    print_generic(settings, "ambient", br.get_identity(), 0.01, "L", br.get_illuminance())


def print_ambient_light_v2(conn, settings, uid):
    from tinkerforge.bricklet_ambient_light_v2 import BrickletAmbientLightV2

    br = BrickletAmbientLightV2(uid, conn)
    print_generic(settings, "ambient", br.get_identity(), 0.01, "L", br.get_illuminance())


def print_temperature(conn, settings, uid):
    from tinkerforge.bricklet_temperature import BrickletTemperature

    br = BrickletTemperature(uid, conn)
    print_generic(
        settings, "temperature", br.get_identity(), 0.01, "\N{DEGREE SIGN}C", br.get_temperature()
    )


def print_temperature_ext(conn, settings, uid):
    from tinkerforge.bricklet_ptc import BrickletPTC

    br = BrickletPTC(uid, conn)
    print_generic(
        settings,
        "temperature.ext",
        br.get_identity(),
        0.01,
        "\N{DEGREE SIGN}C",
        br.get_temperature(),
    )


def print_humidity(conn, settings, uid):
    from tinkerforge.bricklet_humidity import BrickletHumidity

    br = BrickletHumidity(uid, conn)
    print_generic(settings, "humidity", br.get_identity(), 0.1, "RH", br.get_humidity())


def print_master(conn, settings, uid):
    from tinkerforge.brick_master import BrickMaster

    br = BrickMaster(uid, conn)
    print_generic(
        settings,
        "master",
        br.get_identity(),
        1.0,
        "",
        br.get_stack_voltage(),
        br.get_stack_current(),
        br.get_chip_temperature(),
    )


def print_motion_detector(conn, settings, uid):
    from tinkerforge.bricklet_motion_detector import BrickletMotionDetector

    br = BrickletMotionDetector(uid, conn)
    print_generic(settings, "motion", br.get_identity(), 1.0, "", br.get_motion_detected())


def display_on_segment(conn, settings, text):
    #        0x01
    #       ______
    #      |      |
    # 0x20 |      | 0x02
    #      |______|
    #      | 0x40 |
    # 0x10 |      | 0x04
    #      |______|
    #        0x08

    CHARACTERS = {
        "0": 0x3F,
        "1": 0x06,
        "2": 0x5B,
        "3": 0x4F,
        "4": 0x66,
        "5": 0x6D,
        "6": 0x7D,
        "7": 0x07,
        "8": 0x7F,
        "9": 0x6F,
        "C": 0x39,
        "H": 0x74,
        "L": 0x38,
        "R": 0x50,
        "\N{DEGREE SIGN}": 0x63,
    }

    from tinkerforge.bricklet_segment_display_4x7 import BrickletSegmentDisplay4x7

    br = BrickletSegmentDisplay4x7(segment_display, conn)
    segments = []  # type: List
    for letter in text:
        if len(segments) >= 4:
            break
        if letter in CHARACTERS:
            segments.append(CHARACTERS[letter])

    # align to the right
    segments = [0] * (4 - len(segments)) + segments

    br.set_segments(segments, settings["segment_display_brightness"], False)


def init_device_handlers():
    device_handlers = {}

    # storing the dev_id is not necessary but may save a little time as otherwise the module
    # needs to be imported just to find out this id. If the bricklet is present the module
    # gets imported anyway of course
    for dev_id, module_name, clazz, handler in [
        (13, "brick_master", "BrickMaster", print_master),
        (21, "bricklet_ambient_light", "BrickletAmbientLight", print_ambient_light),
        (259, "bricklet_ambient_light_v2", "BrickletAmbientLightV2", print_ambient_light_v2),
        (216, "bricklet_temperature", "BrickletTemperature", print_temperature),
        (226, "bricklet_ptc", "BrickletPTC", print_temperature_ext),
        (27, "bricklet_humidity", "BrickletHumidity", print_humidity),
        (233, "bricklet_motion_detector", "BrickletMotionDetector", print_motion_detector),
    ]:
        if dev_id is not None:
            device_handlers[dev_id] = handler
        else:
            module = __import__("tinkerforge." + module_name)
            sub_module = module.__dict__[module_name]
            device_handlers[sub_module.__dict__[clazz].DEVICE_IDENTIFIER] = handler

    return device_handlers


def enumerate_callback(
    conn,
    device_handlers,
    settings,
    uid,
    connected_uid,
    position,
    hardware_version,
    firmware_version,
    device_identifier,
    enumeration_type,
):
    if device_identifier == 237:
        global segment_display
        segment_display = uid
    elif device_identifier in device_handlers:
        device_handlers[device_identifier](conn, settings, uid)


def read_config(env):
    settings = DEFAULT_SETTINGS
    cfg_path = os.path.join(os.getenv("MK_CONFDIR", "/etc/check_mk"), "tinkerforge.cfg")

    if os.path.isfile(cfg_path):
        with open(cfg_path) as opened_file:
            exec(opened_file.read(), settings, settings)
    return settings


def main():

    # host = "localhost"
    # port = 4223
    # segment_display_uid = "abc"         # uid of the sensor to display on the 7-segment display
    # segment_display_brightness = 2      # brightness of the 7-segment display (0-7)

    settings = read_config(os.environ)
    parser = OptionParser()
    parser.add_option(
        "--host",
        dest="host",
        default=settings["host"],
        help="host/ipaddress of the tinkerforge device",
        metavar="ADDRESS",
    )
    parser.add_option(
        "--port",
        dest="port",
        default=settings["port"],
        type=int,
        help="port of the tinkerforge device",
        metavar="PORT",
    )
    parser.add_option(
        "--segment_display_uid",
        dest="uid",
        default=settings["segment_display_uid"],
        help="uid of the bricklet which will be displayed in the 7-segment display",
        metavar="UID",
    )
    parser.add_option(
        "--segment_display_brightness",
        type=int,
        dest="brightness",
        default=settings["segment_display_brightness"],
        help="brightness of the 7-segment display (0-7)",
    )
    parser.add_option(
        "--install",
        action="store_true",
        help="install tinkerforge python api to same directory as the plugin",
    )

    options = parser.parse_args()[0]

    settings = {
        "host": options.host,
        "port": options.port,
        "segment_display_uid": options.uid,
        "segment_display_brightness": options.brightness,
    }

    if options.install:
        return install()

    try:
        from tinkerforge.ip_connection import IPConnection
    except ImportError:
        sys.stdout.write("<<<tinkerforge:sep(44)>>>\n")
        sys.stdout.write("master,0.0.0,tinkerforge api isn't installed\n")
        return 1

    conn = IPConnection()
    conn.connect(settings["host"], settings["port"])

    device_handlers = init_device_handlers()

    try:
        sys.stdout.write("<<<tinkerforge:sep(44)>>>\n")

        cb = lambda uid, connected_uid, position, hardware_version, firmware_version, device_identifier, enumeration_type: enumerate_callback(
            conn,
            device_handlers,
            settings,
            uid,
            connected_uid,
            position,
            hardware_version,
            firmware_version,
            device_identifier,
            enumeration_type,
        )

        conn.register_callback(IPConnection.CALLBACK_ENUMERATE, cb)
        conn.enumerate()

        # bricklets respond asynchronously in callbacks and we have no way of knowing
        # what bricklets to expect
        time.sleep(0.1)

        if segment_display is not None:
            if segment_display_value is not None:
                display_on_segment(
                    conn, settings, "%d%s" % (segment_display_value, segment_display_unit)
                )
            else:
                display_on_segment(conn, settings, "")
    finally:
        conn.disconnect()


if __name__ == "__main__":
    main()
