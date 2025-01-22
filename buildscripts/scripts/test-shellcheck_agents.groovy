#!groovy

/// file: test-shellcheck_agents.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            docker_image_from_alias("IMAGE_TESTING").inside("--ulimit nofile=1024:1024 --init") {
                catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
                    dir("tests") {
                        sh("""make SHELLCHECK_OUTPUT_ARGS="-f gcc" test-shellcheck""");
                    }
                }
            }
        }
        stage("Analyse Issues") {
            publishIssues(
                issues:[scanForIssues(tool: gcc())],
                trendChartType: 'TOOLS_ONLY',
                qualityGates: [
                    [
                        threshold: 165,
                        type: 'TOTAL',
                        unstable: false,
                    ]
                ]
            )
        }
    }
}

return this;
