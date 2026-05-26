#!/usr/bin/env bash
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# To get this thing up and running encapsulated in a container run this script
#
# How to use
# ./bootstrap_container.sh directory_from_host new_working_directory_in_container
#

set -e -o pipefail

source_directory=$1
working_directory=$2

# most tests require to be in "/git", so make this magically happen
echo "Copy ${source_directory} to expected ${working_directory} ..."
# prepare a fake git "overlay"
cp -a ${source_directory} ${working_directory}
git config --global --add safe.directory ${working_directory}
cd ${working_directory} || exit 1
