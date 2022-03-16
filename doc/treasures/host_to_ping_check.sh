#!/bin/sh
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

find . -name _HOST_\* | sed -re 's/(\S*)_HOST_(\S*)/\1_HOST_\2 \1PING\2/' | xargs -n 2 cp
