#!groovy

/// file: winagt-test-mk-oracle.groovy

void main() {
    dir("${checkout_dir}/packages/mk-oracle") {
        withCredentials([
            string(
                credentialsId: "CI_ORA_WIN_TEST_PASSWORD",
                variable: "CI_ORA_WIN_TEST_PASSWORD"),
            sshUserPrivateKey(
                    credentialsId: "jenkins-oracle-win-ssh-key",
                    keyFileVariable: "CI_ORA_WIN_SSH_KEYFILE",
                    usernameVariable: "CI_ORA_WIN_REMOTE_USER"),
        ]) {
            stage("Run mk-oracle component tests (local, on Oracle host)") {
                // Ship the test binary to the Oracle host and run it there
                // against its local DB, covering host-local paths. The
                // remote dir is unique per build so overlapping runs on
                // the shared host cannot clobber each other's staging.
                bat("set \"CI_ORA_WIN_REMOTE_DIR=C:\\ci\\%BUILD_TAG%\" && call run.cmd --remote-host");
            }
        }
    }
}

return this;
