#!/usr/bin/bash
# export MK_CONFDIR="${PWD}"
cargo run -- -c tests/files/test-mini-host-always.yml --find-runtime
ORACLE_HOME=${PWD}/runtimes/oracle_home cargo run -- -c tests/files/test-mini-host-auto.yml --find-runtime
ORACLE_HOME=${PWD}/runtimes/oracle_home cargo run -- -c tests/files/test-mini-host-auto.yml
ORACLE_INSTANT_CLIENT=${PWD}/runtimes/plugins/packages/mk-oracle cargo run -- -c tests/files/test-mini-host-auto.yml
