#!groovy

// file: build-oracle-aix.groovy

def main() {
    check_job_parameters([
        "VERSION",
    ])

    stage("Build AIX") {
        inside_container() {
            dir("${checkout_dir}") {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: "jenkins-aix-build-ssh-key",
                        keyFileVariable: 'KEYFILE'
                    ),
                    file(
                        credentialsId: 'know_hosts_ssh_aix',
                        variable: 'KNOWN_HOSTS_FILE'
                    ),
                    usernamePassword(
                        credentialsId: 'oracle_test_db_user_password',
                        usernameVariable: 'ORACLEDB_USER',
                        passwordVariable: 'ORACLEDB_PASSWORD'
                    ),
                ]) {
                    sh("""
                        checkout_dir=${checkout_dir} REMOTE_USER=jenkins packages/mk-oracle/ssh-run-ci aix -bu
                    """)
                }
            }
        }
    }

    stage("Archive artifacts") {
        dir("${checkout_dir}/packages/mk-oracle") {
            archiveArtifacts(allowEmptyArchive: true, artifacts: "mk-oracle.aix");
        }
    }
}

return this;
