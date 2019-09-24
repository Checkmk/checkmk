#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

oneTimeSetUp(){
    CONF_FILE="${SHUNIT_TMPDIR}/sshd_config"
    cat <<EOF > "${CONF_FILE}"
# Skip comment
Hi test

# Compress tables
One    First    Unique
Two    Second   Repeated

EOF
}

test_sshd_config() {
    . "${DIR}"/../../../../agents/plugins/mk_sshd_config > /dev/null
    result=$(drop_comments_whitespace ${CONF_FILE})
    assertEquals "no stuff" "Hi test
One First Unique
Two Second Repeated" "${result}"

}


. "${DIR}"/../../../shunit2
