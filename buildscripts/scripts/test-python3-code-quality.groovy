#!groovy

/// file: test-python3-code-quality.groovy

def main() {
    inside_container(
        init: true,
        ulimit_nofile: 1024,
    ) {
        stage('test python3 code quality') {
            dir("${checkout_dir}") {
                // TODO: Re-enable having tags available
                //withCredentials([
                //    sshUserPrivateKey(
                //        credentialsId: "jenkins-gerrit-fips-compliant-ssh-key",
                //        keyFileVariable: 'KEYFILE')]
                //) {
                //    withEnv(["GIT_SSH_COMMAND=ssh -o 'StrictHostKeyChecking no' -i ${KEYFILE} -l jenkins"]) {
                //        // Since checkmk_ci:df2be57e we don't have the tags available anymore in the checkout
                //        // however the werk tests heavily rely on them, so fetch them here
                //        sh("git fetch origin 'refs/tags/*:refs/tags/*'")
                //    }
                //}

                sh("make -C tests test-code-quality");
            }
        }
    }
}

return this;
