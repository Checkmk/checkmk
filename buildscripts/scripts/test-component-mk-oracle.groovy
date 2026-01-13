#!groovy

/// file: test-component-mk-oracle.groovy

void main() {
    check_job_parameters([
        ["EDITION", true],
        ["VERSION", true],
        "DISABLE_CACHE",
    ]);

    def edition = params.EDITION;
    def version = params.VERSION;
    def disable_cache = params.DISABLE_CACHE;

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, version);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        parallel(
            package_helper.provide_agent_binaries(
            version: version,
            cmk_version: cmk_version,
            edition: edition,
            disable_cache: disable_cache,
            bisect_comment: params.CIPARAM_BISECT_COMMENT,
            artifacts_base_dir: "tmp_artifacts",
            test_binaries_only: true,
            )
        )
    }

    stage("Run mk-oracle component tests") {
        inside_container() {
            withCredentials([
                sshUserPrivateKey(
                    credentialsId: 'jenkins-oracle-ssh-key',
                    keyFileVariable: 'SSH_KEYFILE',
                    usernameVariable: "USER",
                ),
                string(
                    credentialsId: "CI_ORA2_DB_TEST_PASSWORD",
                    variable: "CI_ORA2_DB_TEST_PASSWORD",
                ),
                string(
                    credentialsId: "CI_ORA2_DB_TEST_SERVER",
                    variable: "SERVER",
                ),
            ]) {
                sh("""
                    CI_ORA2_DB_TEST="127.0.0.1:system:$CI_ORA2_DB_TEST_PASSWORD:1521:FREE::FREE.cmkoratest:_:_:" \
                    ORACLE_HOME=/opt/oracle/product/23ai/dbhomeFree \
                    HOST_ADDRESS="$USER@$SERVER" \
                    TEST_BINARY_LOCAL_PATH=test_ora_sql_test \
                    TEST_BINARY_REMOTE_PATH=/home/rocky/test_ora_jenkins \
                    ${checkout_dir}/packages/mk-oracle/run --remote-host
                """)
            }
        }
    }
}

return this;
