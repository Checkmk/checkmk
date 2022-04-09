#!/bin/bash
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

MK_SAP_HANA_PLUGIN_PATH="${UNIT_SH_PLUGINS_DIR}/mk_sap_hana"

#   .--helper--------------------------------------------------------------.
#   |                    _          _                                      |
#   |                   | |__   ___| |_ __   ___ _ __                      |
#   |                   | '_ \ / _ \ | '_ \ / _ \ '__|                     |
#   |                   | | | |  __/ | |_) |  __/ |                        |
#   |                   |_| |_|\___|_| .__/ \___|_|                        |
#   |                                |_|                                   |
#   '----------------------------------------------------------------------'

oneTimeSetUp() {

    export MK_CONFDIR=${SHUNIT_TMPDIR}
    export USERSTOREKEY="storekey"
    export PASSWORD_CONNECT="123"
    export USER_CONNECT="hana"
    export MK_VARDIR="/vardir"

    # shellcheck disable=SC1090
    . "$MK_SAP_HANA_PLUGIN_PATH" >/dev/null 2>&1

    # Mock sys calls
    nslookup() {
        if [ "$1" = "myServer" ]; then
            cat <<"output"
Server:		127.0.0.53
Address:	127.0.0.53#53

Non-authoritative answer:
Address: 192.168.1.1
output
        fi
    }
    ip() {
        cat <<"output"
2: wlo1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc noqueue state UP group default qlen 1000
    link/ether 00:00:00:00:00:00 brd ff:ff:ff:ff:ff:ff
    inet 192.168.1.1/24 brd 192.111.111.111 scope global dynamic noprefixroute wlo1
       valid_lft 836967sec preferred_lft 836967sec
    inet6 0000::0000:0000:000:000/64 scope global temporary dynamic
       valid_lft 6931sec preferred_lft 3331sec
    inet6 0000::0000:0000:0000:0000/64 scope global dynamic mngtmpaddr noprefixroute
       valid_lft 6931sec preferred_lft 3331sec
    inet6 0000:000:0000:0000:0000:0000:0000:c3b/64 scope global temporary dynamic
       valid_lft 6063sec preferred_lft 2463sec
    inet6 0000:000:0000:0000:0000:0000:0000:c3b/64 scope global temporary dynamic
       valid_lft 6063sec preferred_lft 2463sec
    inet6 0000:000:0000:0000:0000:0000:0000:c3b/64 scope global temporary dynamic
       valid_lft forever preferred_lft forever
output
    }
    #
}

sim_landscape_1_0_worker() {
    cat <<output
| Host     | Host   | Host   | Failover | Remove | Storage   | Storage   | Failover     | Failover     | NameServer  | NameServer  | IndexServer | IndexServer | Host         | Host         |
|          | Active | Status | Status   | Status | Config    | Actual    | Config Group | Actual Group | Config Role | Actual Role | Config Role | Actual Role | Config Roles | Actual Roles |
|          |        |        |          |        | Partition | Partition |              |              |             |             |             |             |              |              |
| -------- | ------ | ------ | -------- | ------ | --------- | --------- | ------------ | ------------ | ----------- | ----------- | ----------- | ----------- | ------------ | ------------ |
| do_not_care_1 | yes    | ok     |          |        |         3 |         3 | default      | default      | slave       | slave       | foobar      | slave       | foobar       | foobar |
| do_not_care_2 | yes    | info   |          |        |         0 |         8 | default      | default      | master 2    | slave       | standby     | slave       | standby      | foobar |
| myServer | yes    | ok     |          |        |         4 |         4 | default      | default      | slave       | slave       | foobar      | slave       | foobar       | worker |
output
}

sim_landscape_1_0_not_worker() {
    cat <<output
| Host     | Host   | Host   | Failover | Remove | Storage   | Storage   | Failover     | Failover     | NameServer  | NameServer  | IndexServer | IndexServer | Host         | Host         |
|          | Active | Status | Status   | Status | Config    | Actual    | Config Group | Actual Group | Config Role | Actual Role | Config Role | Actual Role | Config Roles | Actual Roles |
|          |        |        |          |        | Partition | Partition |              |              |             |             |             |             |              |              |
| -------- | ------ | ------ | -------- | ------ | --------- | --------- | ------------ | ------------ | ----------- | ----------- | ----------- | ----------- | ------------ | ------------ |
| do_not_care_1 | yes    | ok     |          |        |         3 |         3 | default      | default      | slave       | slave       | foobar      | slave       | foobar       | foobar |
| do_not_care_2 | yes    | info   |          |        |         0 |         8 | default      | default      | master 2    | slave       | standby     | slave       | standby      | foobar |
| myServer | yes    | ok     |          |        |         4 |         4 | default      | default      | slave       | slave       | foobar      | slave       | foobar       | not-worker |
output
}

sim_landscape_2_0_worker() {
    cat <<output
| Host          | Host   | Host   | Failover | Remove | Storage   | Storage   | Failover | Failover | NameServer | NameServer | IndexServer | IndexServer | Host    | Host    | Worker  | Worker  |
|               | Active | Status | Status   | Status | Config    | Actual    | Config   | Actual   | Config     | Actual     | Config      | Actual      | Config  | Actual  | Config  | Actual  |
|               |        |        |          |        | Partition | Partition | Group    | Group    | Role       | Role       | Role        | Role        | Roles   | Roles   | Groups  | Groups  |
| ------------- | ------ | ------ | -------- | ------ | --------- | --------- | -------- | -------- | ---------- | ---------- | ----------- | ----------- | ------- | ------- | ------- | ------- |
| myServer | yes    | ok     |          |        |         1 |         1 | default  | default  | master 1   | master     | foobar      | master      | foobar | worker | default | default |
| do_not_care_1 | yes    | ok     |          |        |         2 |         2 | default  | default  | master 2   | slave      | foobar      | slave       | foobar | foobar | default | default |
| do_not_care_2 | no     | ignore |          |        |         0 |         0 | default  | default  | master 3   | slave      | standby     | standby     | standby | standby | default | -       |
output
}

sim_landscape_2_0_not_worker() {
    cat <<output
| Host          | Host   | Host   | Failover | Remove | Storage   | Storage   | Failover | Failover | NameServer | NameServer | IndexServer | IndexServer | Host    | Host    | Worker  | Worker  |
|               | Active | Status | Status   | Status | Config    | Actual    | Config   | Actual   | Config     | Actual     | Config      | Actual      | Config  | Actual  | Config  | Actual  |
|               |        |        |          |        | Partition | Partition | Group    | Group    | Role       | Role       | Role        | Role        | Roles   | Roles   | Groups  | Groups  |
| ------------- | ------ | ------ | -------- | ------ | --------- | --------- | -------- | -------- | ---------- | ---------- | ----------- | ----------- | ------- | ------- | ------- | ------- |
| myServer | yes    | ok     |          |        |         1 |         1 | default  | default  | master 1   | master     | foobar      | master      | foobar | not-worker | default | default |
| do_not_care_1 | yes    | ok     |          |        |         2 |         2 | default  | default  | master 2   | slave      | foobar      | slave       | foobar | foobar | default | default |
| do_not_care_2 | no     | ignore |          |        |         0 |         0 | default  | default  | master 3   | slave      | standby     | standby     | standby | standby | default | -       |
output

}

sim_odbcreg_1_0_OK() {
    cat <<out

ODBC Driver test.

Connect string: 'SERVERNODE=Hana-host:3inst15;SERVERDB=BAS;UID=MyName;PWD=MyPass;'.
retcode:         0
outString(68):  SERVERNODE={Hana-host:3inst15};SERVERDB=BAS;UID=MyName;PWD=MyPass;
Driver version SAP HDB 1.00 (2013-10-15).
Select now(): 2013-11-12 15:44:55.272000000 (29)
out
}

sim_odbcreg_2_0_OK() {
    cat <<out

ODBC Driver test.

Connect string: 'SERVERNODE=Hana-host:3inst13;SERVERDB=BAS;UID=MyName;PWD=MyPass;'.
retcode:         0
outString(68):  SERVERNODE={Hana-host:3inst13};SERVERDB=BAS;UID=MyName;PWD=MyPass;
Driver version SAP HDB 1.00 (2013-10-15).
Select now(): 2013-11-12 15:44:55.272000000 (29)
out
}

#   .--tests---------------------------------------------------------------.
#   |                        _            _                                |
#   |                       | |_ ___  ___| |_ ___                          |
#   |                       | __/ _ \/ __| __/ __|                         |
#   |                       | ||  __/\__ \ |_\__ \                         |
#   |                        \__\___||___/\__|___/                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'
#.

test_mk_sap_hana_single_hostname() {

    # Mock landscape
    landscape=$(
        cat <<output
| Host |
|      |
|      |
| ------------- |
| myServer |
output
    )

    actual=$(sap_hana_host_from_landscape "$landscape")
    expected="myServer"
    assertEquals "$expected" "$actual"

}

test_mk_sap_hana_multiple_hostnames() {

    # Mock landscape
    landscape=$(
        cat <<output
| Host |
|      |
|      |
| ------------- |
| do_not_care_1 |
| myServer |
output
    )
    actual=$(sap_hana_host_from_landscape "$landscape")
    expected="myServer"
    assertEquals "$expected" "$actual"

}

test_mk_sap_hana_multiple_hostnames_non_active() {

    # Mock landscape
    landscape=$(
        cat <<output
| Host |
|      |
|      |
| ------------- |
| non-active-host1 |
| non-active-host2 |
output
    )

    actual=$(sap_hana_host_from_landscape "$landscape")
    expected=""
    assertEquals "$expected" "$actual"

}

test_mk_sap_hana_1-0_get_role() {

    # Mock landscape
    landscape=$(sim_landscape_1_0_worker)

    actual=$(sap_hana_role_from_landscape "$landscape" "myServer")
    expected="worker"
    assertEquals "$expected" "$actual"

}

test_mk_sap_hana_2-0_get_role() {

    # Mock landscape
    landscape=$(sim_landscape_2_0_worker)
    actual=$(sap_hana_role_from_landscape "$landscape" "myServer")
    expected="worker"
    assertEquals "$expected" "$actual"

}

test_mk_sap_hana_1_connect_OK() {

    # Mocks
    landscape=$(sim_landscape_1_0_worker)
    status=$'Version;;1.00.122.22.1543461992 (fa/hana1sp12)\nAll Started;WARNING;No'
    su() {
        called_bin=$(echo "$4" | awk '{print $1}')
        if [[ "$called_bin" != *"odbcreg"* ]]; then
            # Ensure that we're called for odbcred
            return
        fi

        port=$(echo "$4" | awk '{print $2}' | awk -F":" '{print $2}')
        if [ "$port" = "3inst15" ]; then
            # Ensure that we're called with the correct port
            sim_odbcreg_1_0_OK
        fi
    }

    actual=$(SAP_HANA_VERSION="1" sap_hana_connect "sid" "inst" "inst_user" "myServer" "$landscape" "$status")
    expected=$(sim_odbcreg_1_0_OK | tr ';' ',' | tr '\n' ';' | sed -e "s/^;//g" -e "s/;$/\n/g")
    assertEquals "$expected" "$actual"
}

test_mk_sap_hana_1_connect_standby_not_worker() {

    # Mocks
    landscape=$(sim_landscape_1_0_not_worker)
    status=$'Version;;1.00.122.22.1543461992 (fa/hana1sp12)\nAll Started;WARNING;No'

    actual=$(SAP_HANA_VERSION="1" sap_hana_connect "sid" "inst" "inst_user" "myServer" "$landscape" "$status")
    expected="retcode: 1"
    assertEquals "$expected" "$actual"
}

test_mk_sap_hana_2_connect_OK() {

    # Mocks
    landscape=$(sim_landscape_2_0_worker)
    status=$'Version;;2.00.122.22.1543461992 (fa/hana1sp12)\nAll Started;WARNING;No'
    su() {
        called_bin=$(echo "$4" | awk '{print $1}')
        if [[ "$called_bin" != *"odbcreg"* ]]; then
            # Ensure that we're called for odbcred
            return
        fi

        # Ensure that we're called with the correct port
        port=$(echo "$4" | awk '{print $2}' | awk -F":" '{print $2}')
        if [ "$port" = "3inst13" ]; then
            sim_odbcreg_2_0_OK
        fi
    }

    actual=$(SAP_HANA_VERSION="2" sap_hana_connect "sid" "inst" "inst_user" "myServer" "$landscape" "$status")
    expected=$(sim_odbcreg_2_0_OK | tr ';' ',' | tr '\n' ';' | sed -e "s/^;//g" -e "s/;$/\n/g")
    assertEquals "$expected" "$actual"
}

test_mk_sap_hana_2_connect_standby_not_worker() {

    # Mocks
    landscape=$(sim_landscape_2_0_not_worker)
    status=$'Version;;2.00.122.22.1543461992 (fa/hana1sp12)\nAll Started;WARNING;No'

    actual=$(SAP_HANA_VERSION="2" sap_hana_connect "sid" "inst" "inst_user" "myServer" "$landscape" "$status")
    expected="retcode: 1"

    assertEquals "$expected" "$actual"
}

test_mk_sap_hana_unknown_version() {

    # Mocks
    status=$'Version;;9.22.122.22.123445 (fa/hanaUNKNOWN)\nAll Started;WARNING;No'

    set_sap_hana_version "$status"
    actual=$(sap_hana_connect "sid" "inst" "inst_user" "do not care" "do not care" "$status")
    expected="Cannot determine port due to unknown HANA version."

    assertEquals "$expected" "$actual"

}

test_mk_sap_hana_skip_sql_queries() {

    # Mocks
    mk_hdbsql() {
        # Return code 43 in case SQL DB is not open (see SUP-1436 for details)
        return 43
    }

    actual=$(query_instance "sid" "inst" "inst_user" "" "" "" 2>/dev/null)
    # SQL DB not available so we only want non-sql sections to be executed
    expected_sections=("sap_hana_replication_status" "sap_hana_connect:sep(59)")

    for exp_section in "${expected_sections[@]}"; do
        :
        assertContains "$actual" "$exp_section"
    done
}

test_mk_sap_hana_get_ssl_option_with_ssl() {

    # Mocks read_global_ini
    read_global_ini() {
        echo "sslenforce = true"
    }

    actual=$(get_ssl_option "sid" "hostname")
    assertEquals "-e -sslhostnameincert $(hostname -f)" "$actual"
}

test_mk_sap_hana_get_ssl_option_without_ssl() {

    # Mocks read_global_ini
    read_global_ini() {
        echo "sslenforce = false"
    }

    actual=$(get_ssl_option "sid" "hostname")
    assertEquals "" "$actual"
}

test_mk_sap_hana_get_alerts_last_check_file_no_remote_host() {

    actual=$(get_alerts_last_check_file "sid" "instance" "_DB")
    assertEquals "/vardir/sap_hana_alerts_sid_instance_DB.last_checked" "$actual"
}

test_mk_sap_hana_get_alerts_last_check_file_with_remote_host() {
    actual=$(REMOTE="hostname" get_alerts_last_check_file "sid" "instance" "")
    assertEquals "/vardir/sap_hana_alerts_sid_instance.hostname.last_checked" "$actual"
}

test_mk_sap_hana_get_last_used_check_file_new_file_exists() {

    # Mocks file_exists
    file_exists() {
        local path="$1"

        if [ "$path" == "/vardir/sap_hana_alerts_sid_instance_DB.last_checked" ]; then
            return 0
        else
            return 1
        fi
    }

    actual=$(get_last_used_check_file "/vardir/sap_hana_alerts_sid_instance_DB.last_checked" "_DB")
    assertEquals "/vardir/sap_hana_alerts_sid_instance_DB.last_checked" "$actual"
}

test_mk_sap_hana_get_last_used_check_file_old_file_exists() {

    # Mocks file_exists
    file_exists() {
        local path="$1"

        if [ "$path" == "/vardir/sap_hana_alerts_sid_instance.last_checked" ]; then
            return 0
        else
            return 1
        fi
    }

    actual=$(get_last_used_check_file "/vardir/sap_hana_alerts_sid_instance_DB.last_checked" "_DB")
    assertEquals "/vardir/sap_hana_alerts_sid_instance.last_checked" "$actual"
}

test_mk_sap_hana_get_last_used_check_file_no_file() {

    # Mocks file_exists
    file_exists() {
        return 1
    }

    actual=$(get_last_used_check_file "/vardir/sap_hana_alerts_sid_instance_DB.last_checked" "_DB")
    assertEquals "" "$actual"
}

# shellcheck disable=SC1090 # Can't follow
. "$UNIT_SH_SHUNIT2"
