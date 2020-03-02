#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# This script updates the loading of the library
# The file jenkins-lib-loader/jenkins-template.groovy is used
# Only jenkins files, that already load the library are affected
# Please check the changes in git and commit them

for FILE in *.jenkins; do
    if $(grep '^// jenkins-libs loaded' $FILE > /dev/null); then
        sed -i '0,/^\/\/ jenkins-libs loaded$/d' $FILE
        cat jenkins-lib-loader/jenkins-template.groovy > $FILE.tmp
        cat $FILE >> $FILE.tmp
        mv $FILE.tmp $FILE
    fi
done
