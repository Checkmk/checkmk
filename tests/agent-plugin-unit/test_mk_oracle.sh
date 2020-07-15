#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
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

oneTimeSetUp () {
    export MK_CONFDIR=${SHUNIT_TMPDIR}
    export MK_VARDIR=${SHUNIT_TMPDIR}

    touch "$MK_VARDIR/mk_oracle.found"

    # shellcheck disable=SC1090
    . "$MK_ORACLE_PLUGIN_PATH" >/dev/null 2>&1

    # Overwrite functions from mk_oracle which cannot/won't be unit tested for now
    mk_ora_sqlplus () { true; }
    run_cached () { true; }

    do_sync_checks () { true; }
    do_async_checks () { true; }
    do_testmode () { true; }

    do_async_custom_sqls () { true; }
    do_testmode_custom_sql () { true; }

    sql_performance () { echo "mocked-sql_performance"; }
    sql_tablespaces () { echo "mocked-sql_tablespaces"; }
    sql_dataguard_stats () { echo "mocked-sql_dataguard_stats"; }
    sql_recovery_status () { echo "mocked-sql_recovery_status"; }
    sql_rman () { echo "mocked-sql_rman"; }
    sql_recovery_area () { echo "mocked-sql_recovery_area"; }
    sql_undostat () { echo "mocked-sql_undostat"; }
    sql_resumable () { echo "mocked-sql_resumable"; }
    sql_jobs () { echo "mocked-sql_jobs"; }
    sql_ts_quotas () { echo "mocked-sql_ts_quotas"; }
    sql_version () { echo "mocked-sql_version"; }
    sql_instance () { echo "mocked-sql_instance"; }
    sql_sessions () { echo "mocked-sql_sessions"; }
    sql_processes () { echo "mocked-sql_processes"; }
    sql_logswitches () { echo "mocked-sql_logswitches"; }
    sql_locks () { echo "mocked-sql_locks"; }
    sql_locks_old () { echo "mocked-sql_locks_old"; }
    sql_longactivesessions () { echo "mocked-sql_longactivesessions"; }
    sql_asm_diskgroup () { echo "mocked-sql_asm_diskgroup"; }
}


tearDown () {
    if [ -f "${MK_CONFDIR}/mk_oracle.cfg" ]; then
        # shellcheck disable=SC1090
        rm "${MK_CONFDIR}/mk_oracle.cfg"
    fi
    unset SYNC_SECTIONS ASYNC_SECTIONS SYNC_ASM_SECTIONS ASYNC_ASM_SECTIONS CACHE_MAXAGE OLRLOC
    unset ONLY_SIDS SKIP_SIDS EXCLUDE_MySID EXCLUDE_OtherSID SYNC_SECTIONS_MySID ASYNC_SECTIONS_MySID
    unset MK_SYNC_SECTIONS_QUERY MK_ASYNC_SECTIONS_QUERY
    unset ORACLE_SID MK_SID MK_ORA_SECTIONS
    unset custom_sqls_sections
}

#.

#   ---load_config----------------------------------------------------------

test_mk_oracle_default_config () {
    load_config

    assertEquals "instance sessions logswitches undostat recovery_area processes recovery_status longactivesessions dataguard_stats performance locks systemparameter" "$SYNC_SECTIONS"
    assertEquals "tablespaces rman jobs resumable" "$ASYNC_SECTIONS"
    assertEquals "instance processes" "$SYNC_ASM_SECTIONS"
    assertEquals "asm_diskgroup" "$ASYNC_ASM_SECTIONS"
    assertEquals "600" "$CACHE_MAXAGE"
    assertEquals "/etc/oracle/olr.loc" "$OLRLOC"
}


test_mk_oracle_load_config () {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
# Some comments
SYNC_SECTIONS="instance undostat"
ASYNC_SECTIONS="tablespaces jobs"
SYNC_ASM_SECTIONS=instance
ASYNC_ASM_SECTIONS=asm_diskgroup
CACHE_MAXAGE=300
OLRLOC=/other/path
EOF

    load_config

    assertEquals "instance undostat" "$SYNC_SECTIONS"
    assertEquals "tablespaces jobs" "$ASYNC_SECTIONS"
    assertEquals "instance" "$SYNC_ASM_SECTIONS"
    assertEquals "asm_diskgroup" "$ASYNC_ASM_SECTIONS"
    assertEquals "300" "$CACHE_MAXAGE"
    assertEquals "/other/path" "$OLRLOC"
}


test_mk_oracle_load_config_sections_opt () {
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

test_mk_oracle_only_sids0 () {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
ONLY_SIDS="YourSID HisSID HerSID"
EOF

    load_config

    assertEquals "yes" "$(skip_sid "MySID")"
}


test_mk_oracle_only_sids1 () {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
ONLY_SIDS="MySID YourSID HisSID HerSID"
EOF

    load_config

    assertEquals "no" "$(skip_sid "MySID")"
}


test_mk_oracle_skip_sids0 () {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SKIP_SIDS="MySID YourSID"
EOF

    load_config

    assertEquals "yes" "$(skip_sid "MySID")"
}


test_mk_oracle_skip_sids1 () {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SKIP_SIDS="YourSID"
EOF

    load_config

    assertEquals "no" "$(skip_sid "MySID")"
}


test_mk_oracle_exclude_all0 () {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
EXCLUDE_MySID="ALL"
EOF

    load_config

    assertEquals "yes" "$(skip_sid "MySID")"
}


test_mk_oracle_exclude_all1 () {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
EXCLUDE_OtherSID="ALL"
EOF

    load_config

    assertEquals "no" "$(skip_sid "MySID")"
}


test_mk_oracle_only_vs_skip () {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
ONLY_SIDS="MySID"
SKIP_SIDS="MySID"
EXCLUDE_MySID="ALL"
EOF

    load_config

    assertEquals "no" "$(skip_sid "MySID")"
}

#   ---do_checks------------------------------------------------------------

test_mk_oracle_do_checks_sections () {
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


test_mk_oracle_do_checks_exclude_sections () {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_SECTIONS="instance sessions logswitches"
ASYNC_SECTIONS="tablespaces rman jobs"
EXCLUDE_MySID="logswitches jobs"
EOF

    load_config

    # shellcheck disable=SC2034
    ORACLE_SID="MySID"
    # shellcheck disable=SC2034
    MK_SID="MySID"
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_sessions" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "mocked-sql_tablespaces
mocked-sql_rman" "$MK_ASYNC_SECTIONS_QUERY"
}


test_mk_oracle_do_checks_sid_sections () {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_SECTIONS="instance sessions logswitches undostat recovery_area processes recovery_status longactivesessions dataguard_stats performance locks"
ASYNC_SECTIONS="tablespaces rman jobs resumable"
SYNC_SECTIONS_MySID="instance sessions"
ASYNC_SECTIONS_MySID="tablespaces rman"
EOF

    load_config

    # shellcheck disable=SC2034
    ORACLE_SID="MySID"
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_sessions" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "mocked-sql_tablespaces
mocked-sql_rman" "$MK_ASYNC_SECTIONS_QUERY"
}


test_mk_oracle_do_checks_remote_sid_excluded () {
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


test_mk_oracle_do_checks_sid_sections_excluded () {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_SECTIONS="instance sessions logswitches undostat recovery_area processes recovery_status longactivesessions dataguard_stats performance locks"
ASYNC_SECTIONS="tablespaces rman jobs resumable"
SYNC_SECTIONS_MySID="instance sessions undostat"
ASYNC_SECTIONS_MySID="tablespaces rman jobs"
EXCLUDE_MySID="sessions rman"
EOF

    load_config

    # shellcheck disable=SC2034
    ORACLE_SID="MySID"
    # shellcheck disable=SC2034
    MK_SID="MySID"
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_undostat" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "mocked-sql_tablespaces
mocked-sql_jobs" "$MK_ASYNC_SECTIONS_QUERY"
}


test_mk_oracle_do_checks_sections_opt () {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_SECTIONS="instance sessions logswitches"
ASYNC_SECTIONS="tablespaces rman jobs"
EOF

    # shellcheck disable=SC2034
    MK_ORA_SECTIONS="instance logswitches tablespaces"
    load_config
    # shellcheck disable=SC2034
    ORACLE_SID="MySID"
    # shellcheck disable=SC2034
    MK_SID="MySID"
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_logswitches
mocked-sql_tablespaces" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "" "$MK_ASYNC_SECTIONS_QUERY"
}


test_mk_oracle_do_checks_sid_sections_opt () {
    cat <<EOF >"${MK_CONFDIR}/mk_oracle.cfg"
SYNC_SECTIONS_MySID="instance sessions logswitches undostat"
ASYNC_SECTIONS_MySID="tablespaces rman jobs"
SQLS_SECTIONS="section1,section2,section3"
EOF

    # shellcheck disable=SC2034
    MK_ORA_SECTIONS="instance tablespaces section1 section2"
    load_config

    # shellcheck disable=SC2034
    ORACLE_SID="MySID"
    # shellcheck disable=SC2034
    MK_SID="MySID"
    do_checks

    assertEquals "mocked-sql_instance
mocked-sql_tablespaces" "$MK_SYNC_SECTIONS_QUERY"
    assertEquals "" "$MK_ASYNC_SECTIONS_QUERY"
    assertEquals " section1 section2" "$custom_sqls_sections"
}

#   ---ASM------------------------------------------------------------------

test_mk_oracle_do_checks_asm () {
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

test_mk_oracle_do_checks_asm_sections_opt () {
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

# shellcheck disable=SC1090
. "$UNIT_SH_SHUNIT2"
