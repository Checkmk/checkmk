#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

AGENT_LINUX="${UNIT_SH_AGENTS_DIR}/check_mk_agent.linux"

# shellcheck source=../../agents/check_mk_agent.linux
MK_SOURCE_AGENT="true" source "$AGENT_LINUX"

oneTimeSetUp() {
    touch "${SHUNIT_TMPDIR}/existing_py2_plugin_2.py"
    chmod +x "${SHUNIT_TMPDIR}/existing_py2_plugin_2.py"
    touch "${SHUNIT_TMPDIR}/existing_py3_plugin.py"
    chmod +x "${SHUNIT_TMPDIR}/existing_py3_plugin.py"

    mkdir "${SHUNIT_TMPDIR}/execute"
    printf "#!/bin/sh\necho '<<<foobar>>>'\n" >"${SHUNIT_TMPDIR}/execute/foobar.sh"
    chmod +x "${SHUNIT_TMPDIR}/execute/foobar.sh"
}

test_get_plugin_interpreter_non_python_plugin() {
    assertEquals "$(get_plugin_interpreter './foobar.sh')" ""
}

test_plugin_execution() {
    PLUGINSDIR="${SHUNIT_TMPDIR}/execute"
    set_up_profiling

    assertEquals "<<<foobar>>>" "$(run_plugins)"
}

test_get_plugin_interpreter_no_py_present() {
    INTERPRETER="$(get_plugin_interpreter "${SHUNIT_TMPDIR}/existing_py2_plugin.py")" && fail
    assertEquals "" "${INTERPRETER}"

    NO_PYTHON="no python found"
    INTERPRETER="$(get_plugin_interpreter "${SHUNIT_TMPDIR}/some_plugin.py")" && fail
    assertContains "${INTERPRETER}" "<<<check_mk>>>"
    assertContains "${INTERPRETER}" "FailedPythonPlugins: "
}

test_get_plugin_interpreter_py2_present() {
    NO_PYTHON=""
    PYTHON2="my_py2"
    PYTHON3=""

    INTERPRETER="$(get_plugin_interpreter "${SHUNIT_TMPDIR}/existing_py2_plugin.py")" && fail
    assertEquals "" "${INTERPRETER}"

    INTERPRETER="$(get_plugin_interpreter "${SHUNIT_TMPDIR}/some_py2_plugin_2.py")" || fail
    assertEquals "my_py2" "${INTERPRETER}"

    INTERPRETER="$(get_plugin_interpreter "${SHUNIT_TMPDIR}/existing_py3_plugin_2.py")" || fail
    assertEquals "my_py2" "${INTERPRETER}"
}

test_get_plugin_interpreter_py3_present() {
    NO_PYTHON=""
    PYTHON2=""
    PYTHON3="my_py3"

    INTERPRETER="$(get_plugin_interpreter "${SHUNIT_TMPDIR}/existing_py2_plugin.py")" || fail
    assertEquals "my_py3" "${INTERPRETER}"

    INTERPRETER="$(get_plugin_interpreter "${SHUNIT_TMPDIR}/some_py2_plugin_2.py")" && fail
    assertContains "${INTERPRETER}" "<<<check_mk>>>"
    assertContains "${INTERPRETER}" "FailedPythonPlugins: "

    INTERPRETER="$(get_plugin_interpreter "${SHUNIT_TMPDIR}/existing_py3_plugin_2.py")" && fail
    assertEquals "" "${INTERPRETER}"
}

test_get_plugin_interpreter_both_present() {
    NO_PYTHON=""
    PYTHON2="my_py2"
    PYTHON3="my_py3"

    INTERPRETER="$(get_plugin_interpreter "${SHUNIT_TMPDIR}/existing_py2_plugin.py")" || fail
    assertEquals "my_py3" "${INTERPRETER}"

    INTERPRETER="$(get_plugin_interpreter "${SHUNIT_TMPDIR}/some_py2_plugin_2.py")" || fail
    assertEquals "my_py2" "${INTERPRETER}"

    INTERPRETER="$(get_plugin_interpreter "${SHUNIT_TMPDIR}/existing_py3_plugin_2.py")" && fail
    assertEquals "" "${INTERPRETER}"

    INTERPRETER="$(get_plugin_interpreter "${SHUNIT_TMPDIR}/some_py3_plugin.py")" || fail
    assertEquals "my_py3" "${INTERPRETER}"
}

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
