#!groovy

/// file: test-python3-code-quality.groovy

def main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def safe_branch_name = versioning.safe_branch_name();

    stage('Fetch tags') {
        dir("${checkout_dir}") {
            withCredentials([
                sshUserPrivateKey(
                    credentialsId: "jenkins-gerrit-fips-compliant-ssh-key",
                    keyFileVariable: 'KEYFILE')]
            ) {
                withEnv(["GIT_SSH_COMMAND=ssh -o 'StrictHostKeyChecking no' -i ${KEYFILE} -l jenkins"]) {
                    // Since checkmk_ci:df2be57e we don't have the tags available anymore in the checkout
                    // however the werk tests heavily rely on them, so fetch them here
                    // this requires a lot of CPU power
                    // thereby switch to the larger container with more resources granted
                    container("minimal-ubuntu-checkmk-${safe_branch_name}") {
                        sh("git fetch origin 'refs/tags/*:refs/tags/*'");
                    }
                }
            }
        }
    }

    dir("${checkout_dir}") {
        test_jenkins_helper.execute_test([
            name: "test-code-quality",
            cmd: "make -C tests test-code-quality",
        ]);
    }
}

return this;
