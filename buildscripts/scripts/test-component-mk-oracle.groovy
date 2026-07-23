#!groovy

/// file: test-component-mk-oracle.groovy

void main() {
    check_job_parameters([
        "DISABLE_CACHE",
        ["EDITION", true],
        ["VERSION", true],
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, version);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def edition = params.EDITION;
    def version = params.VERSION;
    def disable_cache = params.DISABLE_CACHE;

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
                    usernameVariable: "SSH_USER",
                ),
                string(
                    credentialsId: "CI_ORA_TEST_PASSWORD",
                    variable: "CI_ORA_TEST_PASSWORD",
                ),
            ]) {
                // SSH_USER comes from the jenkins-oracle-ssh-key credential;
                // run pairs it with the host and DB endpoint from
                // packages/mk-oracle/test-db-endpoints.conf and stages the
                // test binary in a unique remote directory it creates itself.
                sh("""
                    ORACLE_HOME=/opt/oracle23/u01/app/oracle/dbhome1 \
                    ${checkout_dir}/packages/mk-oracle/run --remote-host
                """)
            }
        }
    }
}

return this;
