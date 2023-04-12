#!groovy

/// file: test-python3-pylint.groovy

def main() {
    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        docker_image_from_alias("IMAGE_TESTING").inside('--ulimit nofile=1024:1024 --init') {
            dir("${checkout_dir}") {
                stage('Run test-pylint') {
                    sh("make -C tests test-pylint");
                }

                stage("Analyse Issues") {
                    publishIssues(
                        issues: [scanForIssues( tool: pyLint())],
                        trendChartType: 'TOOLS_ONLY',
                        qualityGates: [[
                            threshold: 1,
                            type: 'TOTAL',
                            unstable: false,
                        ]],
                    );
                }
            }
        }
    }
}

return this;
