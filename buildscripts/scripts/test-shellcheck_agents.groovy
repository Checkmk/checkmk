def main() {
    /*
    properties([
        pipelineTriggers([pollSCM('H/3 * * * *')]),
    ])

    def TEST_IMAGE = docker.build("test-image:${env.BUILD_ID}", "--pull buildscripts/docker_image_aliases/IMAGE_TESTING")
    TEST_IMAGE.inside("--ulimit nofile=1024:1024 --init") {
        stage("Execute Test") {
            catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
                dir("tests") {
                    sh("""make SHELLCHECK_OUTPUT_ARGS="-f gcc" test-shellcheck""");
                }
            }
        }
        stage("Analyse Issues") {
            def GCC = scanForIssues(tool: gcc())
            publishIssues(
                issues:[GCC],
                trendChartType: 'TOOLS_ONLY',
                qualityGates: [
                    [
                        threshold: 165,
                        type: 'TOTAL',
                        unstable: false
                    ]
                ]
            )
        }
    }
    */
}
return this;

