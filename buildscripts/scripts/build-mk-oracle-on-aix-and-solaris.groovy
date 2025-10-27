#!groovy

// file: build-mk-oracle-on-aix-and-solaris.groovy

def main() {
    check_job_parameters([
        "VERSION",
    ])

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def version = params.VERSION;

    def branch_version = versioning.get_branch_version(checkout_dir);
    def safe_branch_name = versioning.safe_branch_name();
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, version);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    stage("Set version") {
        inside_container() {
            dir("${checkout_dir}") {
                // mk-oracle is not edition specific, use "managed" as it is the superset
                versioning.configure_checkout_folder("managed", cmk_version);
            }
        }
    }

    ["aix", "solaris"].collectEntries { distro ->
        [("Building mk-oracle on ${distro}"): {
            smart_stage(
                name: "Building mk-oracle on ${distro}",
                condition: true,
                raiseOnError: true,
            ) {
                inside_container() {
                    dir("${checkout_dir}") {
                        withCredentials([
                            // We use the same SSH key as for the aix and solaris machine
                            sshUserPrivateKey(
                                credentialsId: "jenkins-aix-build-ssh-key",
                                keyFileVariable: 'KEYFILE'
                            ),
                            file(
                                credentialsId: "know_hosts_ssh_${distro}",
                                variable: 'KNOWN_HOSTS_FILE'
                            ),
                            usernamePassword(
                                credentialsId: 'oracle_test_db_user_password',
                                usernameVariable: 'ORACLEDB_USER',
                                passwordVariable: 'ORACLEDB_PASSWORD'
                            ),
                        ]) {
                            sh("""
                                checkout_dir=${checkout_dir} REMOTE_USER=jenkins packages/mk-oracle/ssh-run-ci ${distro} -bu
                            """)
                        }
                    }
                }
            }
        }
        ]
    }

    stage("Archive artifacts") {
        dir("${checkout_dir}/packages/mk-oracle") {
            archiveArtifacts(allowEmptyArchive: true, artifacts: "mk-oracle.*");
        }
    }
}

return this;
