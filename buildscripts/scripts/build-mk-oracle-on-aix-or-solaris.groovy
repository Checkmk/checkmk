#!groovy

// file: build-mk-oracle-on-aix-or-solaris.groovy

def main() {
    check_job_parameters([
        "VERSION",
        "SPECIAL_DISTRO"
    ])

    def distro = SPECIAL_DISTRO;
    assert distro in ["aix", "solaris"] : ("Unsupported DISTRO: ${distro}");

    stage("Build mk-oracle for ${distro}") {
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

    stage("Archive artifacts") {
        dir("${checkout_dir}/packages/mk-oracle") {
            archiveArtifacts(allowEmptyArchive: true, artifacts: "mk-oracle.${distro}");
        }
    }
}

return this;
