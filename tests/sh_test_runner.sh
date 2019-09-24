#!/usr/bin/env bash

for f in $(find . -name "test*.sh")
do
    $f
done
