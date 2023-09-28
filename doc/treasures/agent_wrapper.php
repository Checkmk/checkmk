<?php
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This is a simple wrapper who call's the check_mk_agent,
# to use with curl as datasource program
# May consider using sudo here.
system("/usr/bin/check_mk_agent")

?>
