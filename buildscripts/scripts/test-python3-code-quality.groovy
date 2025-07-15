#!groovy

/// file: test-python3-code-quality.groovy

def main() {
    def docker_args = "${mount_reference_repo_dir} --ulimit nofile=1024:1024 --init";
    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        docker_image_from_alias("IMAGE_TESTING").inside(docker_args) {
            stage('test python3 code quality') {
                dir("${checkout_dir}") {
                    withCredentials([
                        sshUserPrivateKey(
                            credentialsId: "jenkins-gerrit-fips-compliant-ssh-key",
                            keyFileVariable: 'KEYFILE')]
                    ) {
                        withEnv(["GIT_SSH_COMMAND=ssh -o 'StrictHostKeyChecking no' -i ${KEYFILE} -l jenkins"]) {
                            // Since checkmk_ci:df2be57e we don't have the tags available anymore in the checkout
                            // however the werk tests heavily rely on them, so fetch them here
                            sh("git fetch origin 'refs/tags/*:refs/tags/*'")
                        }
                    }
                    sh("make -C tests test-code-quality");
                }
            }
        }
    }
}

return this;
