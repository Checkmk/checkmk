#!/bin/bash

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
