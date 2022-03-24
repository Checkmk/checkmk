#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

__version__ = "2.1.0b4"

# Monitors FTP backup spaces of plesk domains.
# Data format
#
# <<<plesk_backups>>>
# <domain> <age-of-newest-file> <size-of-newest-file> <total-size>

import datetime
import sys
import time

# Bandit complains about insecure protocol (B321). THis is the only possible protocol. Allow it.
from ftplib import FTP  # nosec

try:
    from typing import Any, List
except ImportError:
    pass

try:
    import MySQLdb  # type: ignore[import] # pylint: disable=import-error
except ImportError as e:
    sys.stdout.write(
        "<<<plesk_backups>>>\n%s. Please install missing module via pip install <module>." % e
    )
    sys.exit(0)


def connect():
    # Fix pylint issues in case MySQLdb is not present

    try:
        return MySQLdb.connect(
            host="localhost",
            db="psa",
            user="admin",
            passwd=open("/etc/psa/.psa.shadow").read().strip(),
            charset="utf8",
        )
    except MySQLdb.Error as exc:
        sys.stderr.write("MySQL-Error %d: %s\n" % (exc.args[0], exc.args[1]))
        sys.exit(1)


def get_domains():
    cursor = db.cursor()
    cursor2 = db.cursor()

    cursor.execute("SELECT id, name FROM domains")
    domain_collection = {}
    for this_domain_id, this_domain in cursor.fetchall():
        cursor2.execute(
            "SELECT param, value FROM BackupsSettings "
            "WHERE id = %d AND type = 'domain'" % this_domain_id
        )
        params = dict(cursor2.fetchall())
        domain_collection[this_domain] = params

    cursor2.close()
    cursor.close()
    return domain_collection


#
# MAIN
#

db = connect()

# 1. Virtual Hosts / Domains auflisten
# 2. Backupkonfiguration herausfinden
domains = get_domains()

# 3. Per FTP verbinden
#   4. Alter und Größe der neuesten Datei herausfinden
#   5. Größe aller Dateien in Summe herausfinden
#
# 6. Neuer Monat?
#   7. Auf FTP neues Verzeichnis anlegen: <kunde>_2012<monat>
#   8. Konfiguration in Plesk anpassen
output = ["<<<plesk_backups>>>"]
for domain, p in domains.items():
    try:
        if not p:
            output.append("%s 4" % domain)  # Backup nicht konfiguriert
            continue

        # Bandit complains about insecure protocol (B321). THis is the only possible protocol. Allow it.
        ftp = FTP(  # nosec
            p["backup_ftp_settinghost"],
            p["backup_ftp_settinglogin"],
            p["backup_ftp_settingpassword"],
        )

        # Zeilen holen
        files = []  # type: List[str]
        ftp.retrlines("LIST %s" % p["backup_ftp_settingdirectory"], callback=files.append)
        # example line:
        # -rw----r--   1 b091045  cust     13660160 Dec  3 01:50 bla_v8_bla-v8.bla0.net_1212030250.tar

        # Zeilen formatieren
        last_backup = None
        backups = []
        for line in files:
            parts = line.split()
            if parts[-1].endswith(".tar"):
                dt = datetime.datetime(*time.strptime(parts[-1][-14:-4], "%y%m%d%H%M")[0:5])
                backup = (parts[-1], dt, int(parts[-5]))

                if not last_backup or dt > last_backup[1]:
                    last_backup = backup
                backups.append(backup)

        if not backups:
            output.append("%s 5" % domain)  # Keine Sicherungen vorhanden
            continue

        # Get total size of all files on FTP
        f = []  # type: List[Any]

        def get_size(ftp_conn, base_dir, l=None):
            if l and l.split()[-1] in [".", ".."]:
                return 0

            size = 0
            if not l or l[0] == "d":
                # pylint: disable=cell-var-from-loop
                subdir = "/" + l.split()[-1] if l else ""
                dir_files = []  # type: List[str]
                ftp_conn.retrlines("LIST %s%s" % (base_dir, subdir), callback=dir_files.append)
                for ln in dir_files:
                    size += get_size(ftp_conn, "%s%s" % (base_dir, subdir), ln)
            else:
                size += int(l.split()[-5])
            return size

        total_size = get_size(ftp, "")
        if last_backup:
            output.append(
                "%s 0 %s %d %d"
                % (domain, last_backup[1].strftime("%s"), last_backup[2], total_size)
            )

    except Exception as e:
        output.append("%s 2 %s" % (domain, e))

# Write cache and output
sys.stdout.write("%s\n" % "\n".join(output))
