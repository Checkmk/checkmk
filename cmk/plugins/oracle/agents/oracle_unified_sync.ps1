# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$CMK_VERSION = "2.5.0b1"

& $env:MK_PLUGINSDIR\packages\mk-oracle\mk-oracle.exe -c $env:MK_CONFDIR/oracle.yml --filter sync