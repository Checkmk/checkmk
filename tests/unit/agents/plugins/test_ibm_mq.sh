#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Tests the ibm_mq agent script.
#
# Daniel Steinmann, Swisscom, April 2018

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
IBM_PLUGIN_PATH="${DIR}/../../../../agents/plugins/ibm_mq"
SHUNIT2="${DIR}/../../../shunit2"

test_load_config() {
    MK_CONFDIR=${SHUNIT_TMPDIR}
    cat <<EOF >"${MK_CONFDIR}/ibm_mq.cfg"
ONLY_QM="FOO BAR"
SKIP_QM="FAULTY TOWER"
EOF
    load_config
    assertEquals "FOO BAR" "$ONLY_QM"
    assertEquals "FAULTY TOWER" "$SKIP_QM"
    unset ONLY_QM SKIP_QM
    rm "${MK_CONFDIR}/ibm_mq.cfg"
}


test_is_qm_monitored_no_config() {
    is_qm_monitored foo
    assertEquals 0 $?
}


test_is_qm_monitored_ONLY_QM() {
    ONLY_QM="bar tee"

    is_qm_monitored tee
    assertEquals 0 $?

    result=$(is_qm_monitored foo 2>&1)
    assertEquals 1 $?
    assertEquals "foo: Ignored because ONLY_QM: bar tee" "${result}"
}


test_is_qm_monitored_SKIP_QM() {
    SKIP_QM="foo bar"

    is_qm_monitored tee
    assertEquals 0 $?

    result=$(is_qm_monitored bar 2>&1)
    assertEquals 1 $?
    assertEquals "bar: Ignored because SKIP_QM: foo bar" "${result}"
}


test_is_qm_monitored_full_config() {
    ONLY_QM="bar tee"
    SKIP_QM="foo bar"

    is_qm_monitored tee
    assertEquals 0 $?

    result=$(is_qm_monitored UNKNOWN 2>&1)
    assertEquals 1 $?
    assertEquals "UNKNOWN: Ignored because ONLY_QM: bar tee" "${result}"

    result=$(is_qm_monitored bar 2>&1)
    assertEquals 1 $?
    assertEquals "bar: Ignored because SKIP_QM: foo bar" "${result}"
}


test_monitored_qm() {
    ONLY_QM="BAR TEE"
    mock_dspmq="QMNAME(TEE)                                           STATUS(RUNNING)"
    actual=$(. "$IBM_PLUGIN_PATH" | sed 's/NOW([^)]*)/NOW(timestamp)/')
    expected="\
<<<ibm_mq_plugin:sep(58)>>>
version: 1.6.0
dspmq: OK
runmqsc: OK
<<<ibm_mq_channels:sep(10)>>>
QMNAME(TEE)                                           STATUS(RUNNING) NOW(timestamp)

<<<ibm_mq_queues:sep(10)>>>
QMNAME(TEE)                                           STATUS(RUNNING) NOW(timestamp)

<<<ibm_mq_managers:sep(10)>>>
QMNAME(TEE)                                           STATUS(RUNNING)"
    assertEquals "$expected" "$actual"
}


test_excluded_qm() {
    ONLY_QM="FOO BAR"
    mock_dspmq="QMNAME(TEE)                                           STATUS(RUNNING)"
    actual=$(. "$IBM_PLUGIN_PATH" 2>&1)
    expected="\
<<<ibm_mq_plugin:sep(58)>>>
version: 1.6.0
dspmq: OK
runmqsc: OK
TEE: Ignored because ONLY_QM: FOO BAR
<<<ibm_mq_managers:sep(10)>>>
QMNAME(TEE)                                           STATUS(RUNNING)"
    assertEquals "$expected" "$actual"
}


oneTimeSetUp() {
    . "$IBM_PLUGIN_PATH" 1>/dev/null
}


# Mocks
dspmq() {
    echo "$mock_dspmq"
}

runmqsc() {
    echo "$mock_runmqsc"
}


. "$SHUNIT2"
