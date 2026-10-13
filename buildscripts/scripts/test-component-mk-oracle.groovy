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

    // Test output is captured per lane so the CV result table can link it
    // (RESULT_CHECK_FILE_PATTERN in stages.yml).
    def result_dir = "mk-oracle-component-tests";

    try {
        stage("Run mk-oracle component tests (Linux)") {
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
                        set -o pipefail
                        mkdir -p ${checkout_dir}/${result_dir}
                        ORACLE_HOME=/opt/oracle23/u01/app/oracle/dbhome1 \
                        ${checkout_dir}/packages/mk-oracle/run --remote-host 2>&1 \
                        | tee ${checkout_dir}/${result_dir}/linux.txt
                    """)
                }
            }
        }

        stage("Run mk-oracle component tests (Solaris + AIX)") {
            inside_container() {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'jenkins-aix-build-ssh-key',
                        keyFileVariable: 'SSH_KEYFILE',
                    ),
                ]) {
                    // Runs only the no_db tests.
                    parallel(["solaris", "aix"].collectEntries { distro ->
                        [(distro): {
                            def distro_uc = distro.toUpperCase();
                            sh("""
                                set -o pipefail
                                mkdir -p ${checkout_dir}/${result_dir}
                                . ${checkout_dir}/packages/mk-oracle/ssh-run.conf
                                HOST_ADDRESS="jenkins@\${REMOTE_HOST_${distro_uc}}" \
                                TEST_BINARIES=test_ora_no_db_test.${distro} \
                                ${checkout_dir}/packages/mk-oracle/run --remote-host 2>&1 \
                                | tee ${checkout_dir}/${result_dir}/${distro}.txt
                            """)
                        }]
                    })
                }
            }
        }
    } finally {
        dir("${checkout_dir}") {
            archiveArtifacts(
                allowEmptyArchive: true,
                artifacts: "${result_dir}/*.txt",
                fingerprint: true,  // mandatory to work with ci-artifacts
            );
        }
    }
}

return this;
