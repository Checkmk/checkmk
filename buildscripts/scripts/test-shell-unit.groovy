#!groovy

/// file: test-shell-unit.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside("--ulimit nofile=1024:1024 --init") {
            stage('Run shell unit tests') {
                sh("make -C tests test-unit-shell");
            }

            stage("Analyse Issues") {
                publishIssues(
                    issues: [scanForIssues( tool: gcc())],
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

return this;
