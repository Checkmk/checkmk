#!groovy

/// file: test-livestatus.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Compile & Test Livestatus') {
                sh("packages/livestatus/run --clean --all");
            }
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

return this;
