#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2015             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# Copyright by Mathias Kettner and Mathias Kettner GmbH.  All rights reserved.
#
# Check_MK is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.
#
# Check_MK is  distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY;  without even the implied warranty of
# MERCHANTABILITY  or  FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have  received  a copy of the  GNU  General Public
# License along with Check_MK.  If  not, email to mk@mathias-kettner.de
# or write to the postal address provided at www.mathias-kettner.de

import time
from lib import *
import defaults

loaded_with_language = False
multisite_cronjobs = []

lock_file = defaults.tmp_dir + "/cron.lastrun"

# Load all view plugins
def load_plugins():
    global loaded_with_language
    if loaded_with_language == current_language:
        return

    global multisite_cronjobs
    multisite_cronjobs = []
    load_web_plugins("cron", globals())

    loaded_with_language = current_language


# Page called by some external trigger (usually cron job in OMD site)
# Note: this URL is being called *without* any login. We have no
# user. Everyone can call this! We must not read any URL variables.
def page_run_cron():
    now = time.time()
    # Prevent cron jobs from being run too often, also we need
    # locking in order to prevent overlapping runs
    if os.path.exists(lock_file):
        last_run = os.stat(lock_file).st_mtime
        if time.time() - last_run < 59:
            raise MKGeneralException("Cron called too early. Skipping.")
    file(lock_file, "w") # touches the file
    aquire_lock(lock_file)

    for cron_job in multisite_cronjobs:
        cron_job()
