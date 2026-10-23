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
                try {
                    // Capture the output into an artifact so the CV result
                    // table can link it (RESULT_CHECK_FILE_PATTERN in
                    // stages.yml); cmd redirection has no tee, so type the
                    // file afterwards to keep it in the build log too.
                    bat("set \"CI_ORA_WIN_REMOTE_DIR=C:\\ci\\%BUILD_TAG%\" && call run.cmd --remote-host > mk-oracle-win.txt 2>&1");
                } finally {
                    bat("if exist mk-oracle-win.txt type mk-oracle-win.txt");
                    archiveArtifacts(
                        allowEmptyArchive: true,
                        artifacts: "mk-oracle-win.txt",
                        fingerprint: true,  // mandatory to work with ci-artifacts
                    );
                }
            }
        }
    }
}

return this;
