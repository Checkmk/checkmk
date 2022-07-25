#!groovy

def main() {
    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        docker_image_from_alias("IMAGE_TESTING").inside('--ulimit nofile=1024:1024 --init') {
            try {
                stage('run Bandit') {
                    dir("${checkout_dir}") {
                        sh("BANDIT_OUTPUT_ARGS=\"-f xml -o '$WORKSPACE/bandit_results.xml'\" make -C tests test-bandit")
                    }
                }
            } finally {
                stage('process results') {
                    archiveArtifacts("bandit_results.xml")
                    xunit([Custom(
                        customXSL: "$JENKINS_HOME/userContent/xunit/JUnit/0.1/bandit-xunit.xsl",
                        deleteOutputFiles: true,
                        failIfNotNew: true,
                        pattern: "bandit_results.xml",
                        skipNoTestFiles: false,
                        stopProcessingIfError: true
                    )])
                }
            }
        }
    }
}
return this;
