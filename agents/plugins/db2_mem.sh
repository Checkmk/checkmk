#!/bin/bash

INSTANCES=$(ps -ef | grep db2sysc | awk '{print $1}' | sort -u | grep -v root)

for INSTANCE in $INSTANCES; do
    echo "<<<db2_mem>>>"
    echo "Instance $INSTANCE"
    su - $INSTANCE -c "db2pd -dbptnmem " | egrep '(Memory Limit|HWM usage)'
done

