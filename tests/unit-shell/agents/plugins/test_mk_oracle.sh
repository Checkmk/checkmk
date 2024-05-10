#!/bin/bash
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

MK_ORACLE_PLUGIN_PATH="${UNIT_SH_PLUGINS_DIR}/mk_oracle"

#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'

setup_sqlplus() {
    # Fake the sqlplus binary
    ORACLE_HOME=${SHUNIT_TMPDIR}/ora_home
    FAKE_SQLPLUS=${ORACLE_HOME}/bin/sqlplus
    mkdir -p "${ORACLE_HOME}"/bin
    cat <<EOF >"${FAKE_SQLPLUS}"
echo "SQL*Plus: Release 19.2.3.4.5 - Production
Version 19.3.0.0.0"
EOF
    chmod +x "${FAKE_SQLPLUS}"
}

setup_su() {
    # Fake su oracle -c "CMD"
    # shellcheck disable=SC2317 # overwritten function called indirectly
    su() {
        if [[ "$1" == "oracle" && "$2" == "-c" ]]; then
            shift 2
            bash -c "$* non_root_call"
        fi
    }
}

setUp() {
    setup_su
    setup_sqlplus
}

# shellcheck disable=SC2317 # overwritten function called indirectly
oneTimeSetUp() {
    # We assume there is always an oracle user
    # shellcheck disable=SC2034 # variable unused
    ORACLE_OS_USER="oracle"

    export MK_CONFDIR=${SHUNIT_TMPDIR}
    export MK_VARDIR=${SHUNIT_TMPDIR}

    touch "$MK_VARDIR/mk_oracle.found"
    mkdir -p "$MK_CONFDIR/mk_oracle.d"

    # shellcheck disable=SC1090
    MK_SOURCE_ONLY=true . "$MK_ORACLE_PLUGIN_PATH"

    pwd() { echo "check_mk_agent/plugins"; }

    set_os_env

    # Overwrite functions from mk_oracle which cannot/won't be unit tested for now
    mk_ora_sqlplus() { true; }
    run_cached() { true; }
    do_sync_checks() { true; }
    do_async_checks() { true; }
    do_testmode() { true; }
    do_async_custom_sqls() { true; }
    do_testmode_custom_sql() { true; }

    sql_iostats() { echo "mocked-sql_iostats"; }
    sql_performance() { echo "mocked-sql_performance"; }
    sql_systemparameter() { echo "mocked-sql_systemparameter"; }
    sql_tablespaces() { echo "mocked-sql_tablespaces"; }
    sql_dataguard_stats() { echo "mocked-sql_dataguard_stats"; }
    sql_recovery_status() { echo "mocked-sql_recovery_status"; }
    sql_rman() { echo "mocked-sql_rman"; }
    sql_recovery_area() { echo "mocked-sql_recovery_area"; }
    sql_undostat() { echo "mocked-sql_undostat"; }
    sql_resumable() { echo "mocked-sql_resumable"; }
    sql_jobs() { echo "mocked-sql_jobs"; }
    sql_ts_quotas() { echo "mocked-sql_ts_quotas"; }
    sql_version() { echo "mocked-sql_version"; }
    sql_instance() { echo "mocked-sql_instance"; }
    sql_sessions() { echo "mocked-sql_sessions"; }
    sql_processes() { echo "mocked-sql_processes"; }
    sql_logswitches() { echo "mocked-sql_logswitches"; }
    sql_locks() { echo "mocked-sql_locks"; }
    sql_locks_old() { echo "mocked-sql_locks_old"; }
    sql_longactivesessions() { echo "mocked-sql_longactivesessions"; }
    sql_asm_diskgroup() { echo "mocked-sql_asm_diskgroup"; }
    tearDown
}

tearDown() {
    if [ -f "${MK_CONFDIR}/mk_oracle.cfg" ]; then
        # shellcheck disable=SC1090
        rm "${MK_CONFDIR}/mk_oracle.cfg"
    fi

    if [ -d "$MK_CONFDIR/mk_oracle.d" ]; then
        find "${MK_CONFDIR}/mk_oracle.d/" -type f -delete
    fi

    unset SYNC_SECTIONS ASYNC_SECTIONS SYNC_ASM_SECTIONS ASYNC_ASM_SECTIONS CACHE_MAXAGE OLRLOC
    unset ONLY_SIDS SKIP_SIDS EXCLUDE_MYSID EXCLUDE_OtherSID SYNC_SECTIONS_MYSID ASYNC_SECTIONS_MYSID
    unset MK_SYNC_SECTIONS_QUERY MK_ASYNC_SECTIONS_QUERY
    unset ORACLE_SID MK_SID MK_ORA_SECTIONS
    unset custom_sqls_sections custom_sqls_sids
    unset DBUSER DBUSER_MYSID SQLS_DBUSER SQLS_DBPASSWORD SQLS_DBSYSCONNECT
    unset TNS_ADMIN SIDS NUMERIC_ORACLE_VERSION_FOUR_PARTS MK_ORA_TESTVERSION NUMERIC_ORACLE_VERSION SQLS_TNSALIAS
    unset DBUSER_UT_ORACLE_SID DBUSER_ut_oracle_sid
    unset PREFIX POSTIFX PREFIX_ut_another_sid POSTFIX_ut_another_sid
}

# .

#   ---helpers-------------------------------------------------------------
setup_olrloc() {
    OLRLOC_DIR=${SHUNIT_TMPDIR}/etc
    mkdir -p "${OLRLOC_DIR}"
    OLRLOC=${OLRLOC_DIR}/olr.loc
    # Taken from https://rajat1205sharma.wordpress.com/2015/09/12/oracle-local-registry-olr-11gr2/
    cat <<EOF >"${OLRLOC}"
olrconfig_loc=/u01/app/oracle/grid/11.2.0/cdata/a_hostname.olr
crs_home=/u01/app/oracle/grid/11.2.0
EOF
}

teardown_olrloc() {
    rm -r "${OLRLOC}"
}

test_get_crs_home() {
    setup_olrloc
    crs_home="$(get_crs_home_from_olrloc "${OLRLOC}")"
    assertEquals "/u01/app/oracle/grid/11.2.0" "${crs_home}"
    teardown_olrloc
}

test_get_sqlplus_version_with_precision() {
    sqlplus_version="$(get_sqlplus_version_with_precision 5)"
    assertEquals "19.2.3.4.5" "${sqlplus_version}"

    sqlplus_version="$(get_sqlplus_version_with_precision 2)"
    assertEquals "19.2" "${sqlplus_version}"
}

test_mk_oracle_set_ora_version() {
    # Get version via sqlplus
    set_ora_version
    assertEquals "192" "${NUMERIC_ORACLE_VERSION}"
    assertEquals "19234" "${NUMERIC_ORACLE_VERSION_FOUR_PARTS}"

    # Get version with remote instances
    REMOTE_INSTANCE="<user>:<password>:<role>:<host>:<port>:<piggybackhost>:<sid>:12.3:<tnsalias>"
    set_ora_version "$(echo "${REMOTE_INSTANCE}" | cut -d":" -f8)"
    assertEquals "123" "${NUMERIC_ORACLE_VERSION}"
    assertEquals "123" "${NUMERIC_ORACLE_VERSION_FOUR_PARTS}"

    REMOTE_INSTANCE="<user>:<password>:<role>:<host>:<port>:<piggybackhost>:<sid>:12.3.4.5:<tnsalias>"
    set_ora_version "$(echo "${REMOTE_INSTANCE}" | cut -d":" -f8)"
    assertEquals "123" "${NUMERIC_ORACLE_VERSION}"
    assertEquals "12345" "${NUMERIC_ORACLE_VERSION_FOUR_PARTS}"

    # Get version from env test variable
    export MK_ORA_TESTVERSION="18.1"
    set_ora_version "${ORACLE_VERSION}"
    assertEquals "181" "${NUMERIC_ORACLE_VERSION}"
    assertEquals "181" "${NUMERIC_ORACLE_VERSION_FOUR_PARTS}"

}

#   ---load_config----------------------------------------------------------

test_mk_oracle_default_config() {
    load_config

    assertEquals "instance sessions logswitches undostat recovery_area processes recovery_status longactivesessions dataguard_stats performance locks systemparameter" "$SYNC_SECTIONS"
    assertEquals "tablespaces rman jobs resumable iostats" "$ASYNC_SECTIONS"
    assertEquals "instance processes" "$SYNC_ASM_SECTIONS"
    assertEquals "asm_diskgroup" "$ASYNC_ASM_SECTIONS"
    assertEquals "600" "$CACHE_MAXAGE"
    assertEquals "/etc/oracle/olr.loc" "$OLRLOC"
    assertEquals "1" "$MAX_TASKS"
}

test_mk_oracle_load_config() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
# Some comments
SYNC_SECTIONS="instance undostat"
ASYNC_SECTIONS="tablespaces jobs"
SYNC_ASM_SECTIONS=instance
ASYNC_ASM_SECTIONS=asm_diskgroup
CACHE_MAXAGE=300
OLRLOC=/other/path
MAX_TASKS=5
EOF

    load_config

    assertEquals "instance undostat" "$SYNC_SECTIONS"
    assertEquals "tablespaces jobs" "$ASYNC_SECTIONS"
    assertEquals "instance" "$SYNC_ASM_SECTIONS"
    assertEquals "asm_diskgroup" "$ASYNC_ASM_SECTIONS"
    assertEquals "300" "$CACHE_MAXAGE"
    assertEquals "/other/path" "$OLRLOC"
    assertEquals "5" "$MAX_TASKS"
}

test_mk_oracle_load_config_custom_all_sids() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
# custom sqls assignement
SQLS_SIDS="\$SIDS"
EOF

    export SIDS="XE MYSID"
    load_config

    #shellcheck disable=SC2154
    assertEquals "XE MYSID" "$custom_sqls_sids"
}

test_mk_oracle_load_config_sections_opt() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SQLS_SECTIONS="section1,section2,section3"
EOF

    # shellcheck disable=SC2034
    MK_ORA_SECTIONS="instance logswitches tablespaces asm_diskgroup section1 section2"
    load_config

    assertEquals " instance logswitches" "$SYNC_SECTIONS"
    assertEquals " tablespaces" "$ASYNC_SECTIONS"
    assertEquals " instance" "$SYNC_ASM_SECTIONS"
    assertEquals " asm_diskgroup" "$ASYNC_ASM_SECTIONS"
    # shellcheck disable=SC2154
    assertEquals " section1 section2" "$custom_sqls_sections"
}

#   ---skip_sids------------------------------------------------------------

test_mk_oracle_only_sids0() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
ONLY_SIDS="YourSID HisSID HerSID"
EOF

    load_config

    assertTrue 'skip_sid "MYSID"'
}

test_mk_oracle_only_sids1() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
ONLY_SIDS="MYSID YourSID HisSID HerSID"
EOF

    load_config

    assertFalse 'skip_sid "MYSID"'
}

test_mk_oracle_skip_sids0() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SKIP_SIDS="MYSID YourSID"
EOF

    load_config

    assertTrue 'skip_sid "MYSID"'
}

test_mk_oracle_skip_sids1() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SKIP_SIDS="YourSID"
EOF

    load_config

    assertFalse 'skip_sid "MYSID"'
}

test_mk_oracle_exclude_all0() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
EXCLUDE_MYSID="ALL"
EOF

    load_config

    assertTrue 'skip_sid "MYSID"'
}

test_mk_oracle_exclude_all1() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
EXCLUDE_OtherSID="ALL"
EOF

    load_config

    assertFalse 'skip_sid "MYSID"'
}

test_mk_oracle_only_vs_skip() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
ONLY_SIDS="MYSID"
SKIP_SIDS="MYSID"
EXCLUDE_MYSID="ALL"
EOF

    load_config

    assertFalse 'skip_sid "MYSID"'
}

test_mk_oracle_load_config_confd() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.d/custom_config.cfg"
DBUSER_MYSID="checkmk:password"
SYNC_SECTIONS_MYSID="instance performance"
ASYNC_SECTIONS_MYSID="tablespaces jobs"
EOF

    # Test should also fail if it reads non-cfg files
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.d/testfile"
DBUSER_MYSID="checkmk:testfilepassword"
SYNC_SECTIONS_MYSID="instance testfilesection"
ASYNC_SECTIONS_MYSID="tablespaces testfilesection2"
EOF

    load_config

    assertEquals "checkmk:password" "$DBUSER_MYSID"
    assertEquals "instance performance" "$SYNC_SECTIONS_MYSID"
    assertEquals "tablespaces jobs" "$ASYNC_SECTIONS_MYSID"
}

test_mk_oracle_noexisting_confd() {
    rmdir "${MK_CONFDIR}/mk_oracle.d"
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
DBUSER="checkmk:password"
DBUSER_MYSID="checkmk:password2"
EOF

    load_config

    assertEquals "checkmk:password" "$DBUSER"
    assertEquals "checkmk:password2" "$DBUSER_MYSID"

    mkdir "${MK_CONFDIR}/mk_oracle.d"
}

#   ---do_checks------------------------------------------------------------

test_mk_oracle_do_checks_sections() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_SECTIONS="instance sessions"
ASYNC_SECTIONS="tablespaces rman"
EOF

    load_config
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_sessions" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "mocked-sql_tablespaces
mocked-sql_rman" "$MK_ASYNC_SECTIONS_QUERY"
}

test_mk_oracle_do_checks_exclude_sections() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_SECTIONS="instance sessions logswitches"
ASYNC_SECTIONS="tablespaces rman jobs"
EXCLUDE_MYSID="logswitches jobs"
EOF

    load_config

    # shellcheck disable=SC2034
    ORACLE_SID="MYSID"
    # shellcheck disable=SC2034
    MK_SID="MYSID"
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_sessions" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "mocked-sql_tablespaces
mocked-sql_rman" "$MK_ASYNC_SECTIONS_QUERY"
}

test_mk_oracle_do_checks_sid_sections() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_SECTIONS="instance sessions logswitches undostat recovery_area processes recovery_status longactivesessions dataguard_stats performance locks"
ASYNC_SECTIONS="tablespaces rman jobs resumable"
SYNC_SECTIONS_MYSID="instance sessions"
ASYNC_SECTIONS_MYSID="tablespaces rman"
EOF

    load_config

    # shellcheck disable=SC2034
    ORACLE_SID="MYSID"
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_sessions" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "mocked-sql_tablespaces
mocked-sql_rman" "$MK_ASYNC_SECTIONS_QUERY"
}

test_mk_oracle_case_insensitive_sync_section() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_SECTIONS_MYSID="instance sessions"
ASYNC_SECTIONS_MYSID="tablespaces rman"
EOF

    load_config

    # shellcheck disable=SC2034
    ORACLE_SID="mysid"
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_sessions" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "mocked-sql_tablespaces
mocked-sql_rman" "$MK_ASYNC_SECTIONS_QUERY"
}

test_mk_oracle_do_checks_remote_sid_excluded() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
DBUSER="checkmk:password"
DBUSER_myinst1="checkmk_inst:password_inst::db1xyz_srv12.domain.tld:1521"

ASYNC_SECTIONS="tablespaces rman jobs resumable ts_quotas"

EXCLUDE_myinst1="rman jobs"

REMOTE_INSTANCE_mysinst1="checkmk_inst:password_inst::db1syz-srv12.domain.tld:1521:db1xyz-srv12:myinst1:12.1"
EOF

    load_config
    ORACLE_SID="myinst1"
    do_checks

    assertEquals "mocked-sql_tablespaces
mocked-sql_resumable
mocked-sql_ts_quotas" "$MK_ASYNC_SECTIONS_QUERY"

}

test_mk_oracle_do_checks_sid_sections_excluded() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_SECTIONS="instance sessions logswitches undostat recovery_area processes recovery_status longactivesessions dataguard_stats performance locks"
ASYNC_SECTIONS="tablespaces rman jobs resumable"
SYNC_SECTIONS_MYSID="instance sessions undostat"
ASYNC_SECTIONS_MYSID="tablespaces rman jobs"
EXCLUDE_MYSID="sessions rman"
EOF

    load_config

    # shellcheck disable=SC2034
    ORACLE_SID="MYSID"
    # shellcheck disable=SC2034
    MK_SID="MYSID"
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_undostat" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "mocked-sql_tablespaces
mocked-sql_jobs" "$MK_ASYNC_SECTIONS_QUERY"
}

test_mk_oracle_do_checks_sections_opt() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_SECTIONS="instance sessions logswitches"
ASYNC_SECTIONS="tablespaces rman jobs"
EOF

    # shellcheck disable=SC2034
    MK_ORA_SECTIONS="instance logswitches tablespaces"
    load_config
    # shellcheck disable=SC2034
    ORACLE_SID="MYSID"
    # shellcheck disable=SC2034
    MK_SID="MYSID"
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_logswitches
mocked-sql_tablespaces" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "" "$MK_ASYNC_SECTIONS_QUERY"
}

test_mk_oracle_do_checks_sid_sections_opt() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_SECTIONS_MYSID="instance sessions logswitches undostat"
ASYNC_SECTIONS_MYSID="tablespaces rman jobs"
SQLS_SECTIONS="section1,section2,section3"
EOF

    # shellcheck disable=SC2034
    MK_ORA_SECTIONS="instance tablespaces section1 section2"
    load_config

    # shellcheck disable=SC2034
    ORACLE_SID="MYSID"
    # shellcheck disable=SC2034
    MK_SID="MYSID"
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_tablespaces" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "" "$MK_ASYNC_SECTIONS_QUERY"
    assertEquals " section1 section2" "$custom_sqls_sections"
}

#   ---ASM------------------------------------------------------------------

test_mk_oracle_do_checks_asm() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_ASM_SECTIONS="instance processes"
ASYNC_ASM_SECTIONS="asm_diskgroup"
EOF

    load_config

    # shellcheck disable=SC2034
    ORACLE_SID="+MyASM"
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_processes" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "mocked-sql_asm_diskgroup" "$MK_ASYNC_SECTIONS_QUERY"
}

test_mk_oracle_do_checks_asm_sections_opt() {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_ASM_SECTIONS="instance processes"
ASYNC_ASM_SECTIONS="asm_diskgroup"
EOF

    # shellcheck disable=SC2034
    MK_ORA_SECTIONS="instance asm_diskgroup"
    load_config
    # shellcheck disable=SC2034
    ORACLE_SID="+MyASM"
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_asm_diskgroup" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "" "$MK_ASYNC_SECTIONS_QUERY"
}

#   ---remote instances-----------------------------------------------------

# TODO
# - Remote ASM instances?

#   ---custom SQLs----------------------------------------------------------

# TODO

#   ------------------------------------------------------------------------

test_mk_oracle_mk_ora_db_connect_default() {
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "${CONNECTION}" "/@localhost:1521/"
}

# "username:password:role:hostname:port:piggybackhost(optional):sid(mandatory):version(mandatory):tns_alias(optional)"
# username/password@host:port/service

test_mk_oracle_mk_ora_db_connect_remote_instance_1() {
    # shellcheck disable=SC2034 # variable appears unused
    REMOTE_INSTANCE_UNITTEST="ut_username:ut_password:ut_role:ut_hostname:ut_port::ut_sid:ut_version:"
    CONNECTION=$(mk_ora_db_connect REMOTE_INSTANCE_UNITTEST)
    assertEquals "ut_username/ut_password@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=ut_hostname)(PORT=ut_port))(CONNECT_DATA=(SID=ut_sid)(SERVER=DEDICATED)(UR=A))) as ut_role" "${CONNECTION}"
}

test_mk_oracle_mk_ora_db_connect_remote_instance_2() {
    # shellcheck disable=SC2034 # variable appears unused
    REMOTE_INSTANCE_UNITTEST="ut_username:ut_password:ut_role:ut_hostname_ignored:ut_port_ignored::ut_sid:ut_version:ut_tnsalias"
    CONNECTION=$(mk_ora_db_connect REMOTE_INSTANCE_UNITTEST)
    assertEquals "ut_username/ut_password@ut_tnsalias as ut_role" "${CONNECTION}"
}

test_mk_oracle_mk_ora_db_connect_remote_instance_4() {
    # shellcheck disable=SC2034 # variable appears unused
    REMOTE_INSTANCE_UNITTEST="ut_username_ignored:ut_password_ignored:ut_role_ignored:ut_hostname_ignored:ut_port_ignored::ut_sid_ignored:ut_version:ut_tnsalias"
    # this is a special user to execute user provided sql statements
    # (the main mk_oracle calls mk_ora_db_connect multiple times for the different connections)
    SQLS_DBUSER="ut_sqlss_dbuser"
    # shellcheck disable=SC2034 # variable appears unused
    SQLS_DBPASSWORD="ut_sqls_password"
    SQLS_DBSYSCONNECT="ut_dbsysconnect"
    SQLS_TNSALIAS="ut_sqls_tnsalias"
    CONNECTION=$(mk_ora_db_connect REMOTE_INSTANCE_UNITTEST)
    assertEquals "ut_sqlss_dbuser/ut_sqls_password@ut_sqls_tnsalias as ut_dbsysconnect" "${CONNECTION}"
}

test_mk_oracle_mk_ora_db_connect_remote_instance_3() {
    # same as above, but missing tnsalias in REMOTE_INSTANCE_UNITTEST
    # shellcheck disable=SC2034 # variable appears unused
    REMOTE_INSTANCE_UNITTEST="ut_username_ignored:ut_password_ignored:ut_role_ignored:ut_hostname:ut_port::ut_sid:ut_version"
    SQLS_DBUSER="ut_sqlss_dbuser"
    # shellcheck disable=SC2034 # variable appears unused
    SQLS_DBPASSWORD="ut_sqls_password"
    SQLS_DBSYSCONNECT="ut_dbsysconnect"
    # shellcheck disable=SC2034 # variable appears unused
    SQLS_TNSALIAS="ut_sqls_tnsalias"
    # TODO: this is a BUG! ut_sqls_tnsalias should be visible in the result
    CONNECTION=$(mk_ora_db_connect REMOTE_INSTANCE_UNITTEST)
    assertEquals "ut_sqlss_dbuser/ut_sqls_password@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=ut_hostname)(PORT=ut_port))(CONNECT_DATA=(SID=ut_sid)(SERVER=DEDICATED)(UR=A))) as ut_dbsysconnect" "${CONNECTION}"
}

test_mk_oracle_mk_ora_db_connect_remote_instance_5() {
    # shellcheck disable=SC2034 # variable appears unused
    REMOTE_INSTANCE_UNITTEST="ut_username_ignored:ut_password_ignored:ut_role_ignored:ut_hostname:ut_port::ut_sid:ut_version"
    # this is a special user to execute user provided sql statements
    # (the main mk_oracle calls mk_ora_db_connect multiple times for the different connections)
    SQLS_DBUSER="ut_sqlss_dbuser"
    # shellcheck disable=SC2034 # variable appears unused
    SQLS_DBPASSWORD="ut_sqls_password"
    CONNECTION=$(mk_ora_db_connect REMOTE_INSTANCE_UNITTEST)
    assertEquals "ut_sqlss_dbuser/ut_sqls_password@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=ut_hostname)(PORT=ut_port))(CONNECT_DATA=(SID=ut_sid)(SERVER=DEDICATED)(UR=A)))" "${CONNECTION}"
}

test_mk_oracle_mk_ora_db_connect_1() {
    # shellcheck disable=SC2034 # variable appears unused
    SQLS_DBUSER="ut_sqlss_dbuser"
    # shellcheck disable=SC2034 # variable appears unused
    SQLS_DBPASSWORD="ut_sqls_password"
    # shellcheck disable=SC2034 # variable appears unused
    SQLS_DBSYSCONNECT="ut_dbsysconnect"
    # TODO: this is a BUG! ut_dbsysconnect should be visible in the result.
    ORACLE_SID="ut_oracle_sid"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_sqlss_dbuser/ut_sqls_password@localhost:1521/ut_oracle_sid" "${CONNECTION}"
}

test_mk_oracle_mk_ora_db_connect_2() {
    DBUSER="ut_username:ut_password:ut_role:::ut_tnsalias"
    ORACLE_SID="ut_oracle_sid"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_username/ut_password@ut_tnsalias as ut_role" "${CONNECTION}"
}

test_mk_oracle_mk_ora_db_connect_2_lower_variable() {
    DBUSER="ut_username_ignored:ut_password_ignored:ut_role_ignored:::ut_tnsalias_ignored"
    # shellcheck disable=SC2034 # variable appears unused
    DBUSER_ut_oracle_sid="ut_lower_username:ut_lower_password:ut_lower_role:::ut_lower_tnsalias"
    ORACLE_SID="ut_OrAcLe_sid"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_lower_username/ut_lower_password@ut_lower_tnsalias as ut_lower_role" "${CONNECTION}"
}

test_mk_oracle_mk_ora_db_connect_2_upper_variable() {
    DBUSER="ut_username_ignored:ut_password_ignored:ut_role_ignored:::ut_tnsalias_ignored"
    # shellcheck disable=SC2034 # variable appears unused
    DBUSER_UT_ORACLE_SID="ut_upper_username:ut_upper_password:ut_upper_role:::ut_upper_tnsalias"
    ORACLE_SID="ut_oRaClE_sid"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_upper_username/ut_upper_password@ut_upper_tnsalias as ut_upper_role" "${CONNECTION}"
}

test_mk_oracle_mk_ora_db_connect_2_hostname_port() {
    DBUSER="ut_username:ut_password:ut_role:ut_hostname:ut_port"
    ORACLE_SID="ut_oracle_sid"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_username/ut_password@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=ut_hostname)(PORT=ut_port))(CONNECT_DATA=(SID=ut_oracle_sid)(SERVER=DEDICATED)(UR=A))) as ut_role" "${CONNECTION}"
}

test_mk_oracle_mk_ora_db_connect_asm_1() {
    # shellcheck disable=SC2034 # variable appears unused
    ORACLE_SID="+asm"
    # shellcheck disable=SC2034 # variable appears unused
    ASMUSER="ut_asmuser_username:ut_asmuser_password:ut_role:ut_asmuser_hostname:ut_asmuser_port"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_asmuser_username/ut_asmuser_password@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=ut_asmuser_hostname)(PORT=ut_asmuser_port))(CONNECT_DATA=(SID=+asm)(SERVER=DEDICATED)(UR=A))) as ut_role" "${CONNECTION}"
}

test_mk_oracle_mk_ora_db_connect_asm_1_tnsalias() {
    # shellcheck disable=SC2034 # variable appears unused
    ORACLE_SID="+asm"
    # shellcheck disable=SC2034 # variable appears unused
    ASMUSER="ut_asmuser_username:ut_asmuser_password:ut_role:ut_asmuser_hostname:ut_asmuser_port:ut_tnsalias"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_asmuser_username/ut_asmuser_password@ut_tnsalias as ut_role" "${CONNECTION}"
}

test_mk_oracle_mk_ora_db_connect_asm_2() {
    # shellcheck disable=SC2034 # variable appears unused
    ORACLE_SID="+asm"
    # shellcheck disable=SC2034 # variable appears unused
    ASMUSER="ut_asmuser_username:ut_asmuser_password:ut_role"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_asmuser_username/ut_asmuser_password@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=localhost)(PORT=1521))(CONNECT_DATA=(SID=+asm)(SERVER=DEDICATED)(UR=A))) as ut_role" "${CONNECTION}"
}

test_mk_oracle_mk_ora_db_connect_gi_restart_1() {
    # shellcheck disable=SC2317 # Command appears to be unreachable.
    hostname() {
        echo "ut_hostname_hostname"
    }
    OLRLOC=$(mktemp)
    crs_home=$(mktemp -d)

    DBUSER="ut_dbuser:ut_password"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_dbuser/ut_password@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=ut_hostname_hostname)(PORT=1521))(CONNECT_DATA=(SID=)(SERVER=DEDICATED)(UR=A)))" "${CONNECTION}"

    rm -d "$crs_home"
    rm "$OLRLOC"
    unset -f hostname
}

test_mk_oracle_mk_ora_db_connect_gi_restart_2() {
    OLRLOC=$(mktemp)

    DBUSER="ut_dbuser:ut_password"
    crs_home="defined_variable_but_no_folder"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_dbuser/ut_password@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=localhost)(PORT=1521))(CONNECT_DATA=(SID=)(SERVER=DEDICATED)(UR=A)))" "${CONNECTION}"

    rm "$OLRLOC"
}

setup_tnsping() {
    # set up the tnsping binary: three modes are implemented:
    # * binary not available: `setup_tnsping`
    # * host can be reached: `setup_tnsping true`
    # * host can not be reached: `setup_tnsping false`
    ORACLE_HOME=$(mktemp -d)
    mkdir "$ORACLE_HOME/bin"
    TNS_ADMIN=$(mktemp -d)
    touch "${TNS_ADMIN}/tnsnames.ora"
    if [ "$1" = "true" ] || [ "$1" = "false" ]; then
        echo -e "#!/bin/bash\n$1" >"$ORACLE_HOME/bin/tnsping"
        chmod +x "$ORACLE_HOME/bin/tnsping"
    fi
}

teardown_tnsping() {
    rm -r "$ORACLE_HOME"
    rm -r "${TNS_ADMIN}"
}

test_mk_oracle_mk_ora_db_connect_sqls_tnsalias_tnsping_fail_no_password() {
    setup_tnsping false

    DBUSER="/@ut_user:ut_password::::ut_tnsalias"
    # TODO: this is a strange configuration: if user starts with "/@" user and
    # password are omitted and should not be set in the configuration. current
    # code tests if user starts with "/@" so we keep this in order to document
    # the current behavior.
    # shellcheck disable=SC2034 # variable appears unused
    ORACLE_SID="ut_sid"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "/@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=localhost)(PORT=1521))(CONNECT_DATA=(SID=ut_sid)(SERVER=DEDICATED)(UR=A)))" "${CONNECTION}"

    teardown_tnsping
}

test_mk_oracle_mk_ora_db_connect_sqls_tnsalias_tnsping_fail() {
    setup_tnsping false

    DBUSER="ut_username:ut_password:ut_role:ut_hostname:ut_port:ut_tnsalias"
    ORACLE_SID="ut_sid_two"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_username/ut_password@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=ut_hostname)(PORT=ut_port))(CONNECT_DATA=(SID=ut_sid_two)(SERVER=DEDICATED)(UR=A))) as ut_role" "${CONNECTION}"

    teardown_tnsping
}

test_mk_oracle_mk_ora_db_connect_sqls_tnsalias_tnsping_fail_1() {
    setup_tnsping false

    # shellcheck disable=SC2034 # variable appears unused
    REMOTE_INSTANCE_UTINST="/ut_username:ut_password:ut_role:ut_hostname:ut_port:ut_piggyback_host:ut_sid:ut_version:"
    CONNECTION=$(mk_ora_db_connect REMOTE_INSTANCE_UTINST)
    assertEquals "/@ut_hostname:ut_port/ut_sid as ut_role" "${CONNECTION}"
    # TODO: this is a BUG! username/password should be set!

    teardown_tnsping
}

test_mk_oracle_mk_ora_db_connect_sqls_tnsalias_tnsping_fail_1_tnsalias() {
    setup_tnsping false

    # shellcheck disable=SC2034 # variable appears unused
    REMOTE_INSTANCE_UTINST="/ut_username:ut_password:ut_role:ut_hostname:ut_port:ut_piggyback_host:ut_sid:ut_version:ut_tnsalias"
    CONNECTION=$(mk_ora_db_connect REMOTE_INSTANCE_UTINST)
    assertEquals "/@(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=ut_hostname)(PORT=ut_port))(CONNECT_DATA=(SID=ut_sid)(SERVER=DEDICATED)(UR=A))) as ut_role" "${CONNECTION}"
    # TODO: this is a BUG! username/password should be set!

    teardown_tnsping
}

test_mk_oracle_mk_ora_db_connect_sqls_tnsalias_tnsping_missing() {
    setup_tnsping

    DBUSER="ut_username:ut_password:ut_role:ut_hostname:ut_port:ut_tnsalias"
    ORACLE_SID="ut_sid_two"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_username/ut_password@ut_tnsalias as ut_role" "${CONNECTION}"

    teardown_tnsping
}

test_mk_oracle_mk_ora_db_connect_sqls_tnsalias_tnsping_missing_1() {
    setup_tnsping

    # shellcheck disable=SC2034 # variable appears unused
    REMOTE_INSTANCE_UTINST="/ut_username:ut_password:ut_role:ut_hostname:ut_port:ut_piggyback_host:ut_sid:ut_version:"
    CONNECTION=$(mk_ora_db_connect REMOTE_INSTANCE_UTINST)
    assertEquals "/@ut_sid as ut_role" "${CONNECTION}"
    # TODO: this is a BUG! username/password should be set!

    teardown_tnsping
}

test_mk_oracle_mk_ora_db_connect_sqls_tnsalias_tnsping_missing_1_tnsalias() {
    setup_tnsping

    # shellcheck disable=SC2034 # variable appears unused
    REMOTE_INSTANCE_UTINST="/ut_username:ut_password:ut_role:ut_hostname:ut_port:ut_piggyback_host:ut_sid:ut_version:ut_tnsalias"
    CONNECTION=$(mk_ora_db_connect REMOTE_INSTANCE_UTINST)
    assertEquals "/@ut_tnsalias as ut_role" "${CONNECTION}"
    # TODO: this is a BUG! username/password should be set!

    teardown_tnsping
}

test_mk_oracle_mk_ora_db_connect_sqls_tnsalias_tnsping_ok() {
    setup_tnsping true

    DBUSER="ut_username:ut_password:ut_role:ut_hostname:ut_port:ut_tnsalias"
    ORACLE_SID="ut_sid_two"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_username/ut_password@ut_tnsalias as ut_role" "${CONNECTION}"

    teardown_tnsping
}

test_mk_oracle_mk_ora_db_connect_sqls_tnsalias_tnsping_ok_1() {
    setup_tnsping true

    # shellcheck disable=SC2034 # variable appears unused
    REMOTE_INSTANCE_UTINST="/ut_username:ut_password:ut_role:ut_hostname:ut_port:ut_piggyback_host:ut_sid:ut_version:"
    CONNECTION=$(mk_ora_db_connect REMOTE_INSTANCE_UTINST)

    assertEquals "/@ut_sid as ut_role" "${CONNECTION}"
    # TODO: this is a BUG! why ut_sid as hostname? username/password is also missing!

    teardown_tnsping
}

test_mk_oracle_mk_ora_db_connect_sqls_tnsalias_tnsping_ok_prefix() {
    setup_tnsping true

    DBUSER="ut_username:ut_password:ut_role:ut_hostname:ut_port:ut_tnsalias"
    # shellcheck disable=SC2034 # variable appears unused
    PREFIX="ut_prefix__"
    # shellcheck disable=SC2034 # variable appears unused
    POSTFIX="__ut_postfix"
    CONNECTION=$(mk_ora_db_connect ut_another_sid)
    assertEquals "ut_username/ut_password@ut_prefix__ut_tnsalias__ut_postfix as ut_role" "${CONNECTION}"

    teardown_tnsping
}

test_mk_oracle_mk_ora_db_connect_sqls_tnsalias_tnsping_ok_sid_specific_prefix() {
    setup_tnsping true

    DBUSER="ut_username:ut_password:ut_role:ut_hostname:ut_port:ut_tnsalias"
    # shellcheck disable=SC2034 # variable appears unused
    PREFIX_ut_another_sid="ut_spec_prefix__"
    # shellcheck disable=SC2034 # variable appears unused
    POSTFIX_ut_another_sid="__ut_spec_postfix"
    CONNECTION=$(mk_ora_db_connect ut_another_sid)
    assertEquals "ut_username/ut_password@ut_spec_prefix__ut_tnsalias__ut_spec_postfix as ut_role" "${CONNECTION}"

    teardown_tnsping
}

test_mk_oracle_mk_ora_db_connect_sqls_tnsalias_tnsping_ok_sid_specific_prefix_broken() {
    # this test is nearly identical to the previous one. the only difference in
    # configuration is, that the previous one specifies ut_another_sid via $1
    # of mk_ora_db_connect, and this one specifies it via ORACLE_SID
    # environment variable.
    setup_tnsping true

    # shellcheck disable=SC2034 # variable appears unused
    ORACLE_SID="ut_another_sid"
    DBUSER="ut_username:ut_password:ut_role:ut_hostname:ut_port:ut_tnsalias"
    # shellcheck disable=SC2034 # variable appears unused
    PREFIX_ut_another_sid="ut_spec_prefix__"
    # shellcheck disable=SC2034 # variable appears unused
    POSTFIX_ut_another_sid="__ut_spec_postfix"
    CONNECTION=$(mk_ora_db_connect)
    assertEquals "ut_username/ut_password@ut_tnsalias__ut_postfix as ut_role" "${CONNECTION}"
    # TODO: this has to be a BUG, right? why is only the postfix applied?

    teardown_tnsping
}

test_mk_oracle_sid_matches_defined_sids() {
    assertFalse 'sid_matches_defined_sids "prefixed_value" "prefix"'
    assertTrue 'sid_matches_defined_sids "some,value,here" "value"'
    assertFalse 'sid_matches_defined_sids "some,hello,here" "value"'
    # documentation says, that customer may us "$SIDS" when the section should
    # be executed for all elements, but this variable contains a newline
    # separated list of sids:
    assertTrue "sid_matches_defined_sids $'some\nvalue\nhere' value"
    assertFalse "sid_matches_defined_sids $'some\nprefixed_value\nhere' value"
}

# shellcheck disable=SC1090 # Can't follow
. "$UNIT_SH_SHUNIT2"
