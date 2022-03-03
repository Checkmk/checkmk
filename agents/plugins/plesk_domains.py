#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

__version__ = "2.0.0p22"

# Lists all domains configured in plesk
#
# <<<plesk_domains>>>
# <domain>

import sys
try:
    import MySQLdb  # type: ignore[import] # pylint: disable=import-error
except ImportError as e:
    sys.stdout.write(
        "<<<plesk_domains>>>\n%s. Please install missing module via pip install <module>." % e)
    sys.exit(0)

try:
    db = MySQLdb.connect(
        host='localhost',
        db='psa',
        user='admin',
        passwd=open('/etc/psa/.psa.shadow').read().strip(),
        charset='utf8',
    )
except MySQLdb.Error as e:
    sys.stderr.write("MySQL-Error %d: %s\n" % (e.args[0], e.args[1]))
    sys.exit(1)

cursor = db.cursor()
cursor.execute('SELECT name FROM domains')
sys.stdout.write('<<<plesk_domains>>>\n')
sys.stdout.write("%s\n" % '\n'.join([d[0] for d in cursor.fetchall()]))
cursor.close()
