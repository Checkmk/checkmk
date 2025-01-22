#!groovy

/// file: test-unit-test-cores.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute NEB Test") {
            dir("livestatus/src/test") {
                sh("./.f12");
            }
        }
        stage("Execute CMC Test") {
            dir("enterprise/core/src/test") {
                sh("./.f12");
            }
        }
        def results_livestatus="livestatus/src/test_detail_livestatus.xml"
        def results_core="enterprise/core/src/test_detail_core.xml"

        stage("Analyse Issues") {
            xunit([GoogleTest(
                deleteOutputFiles: true,
                failIfNotNew: true,
                pattern: "${results_livestatus}, ${results_core}",
                skipNoTestFiles: false,
                stopProcessingIfError: true
            )]);
            publishIssues(
                issues: [scanForIssues(tool: gcc())],
                trendChartType: 'TOOLS_ONLY',
                qualityGates: [[
                    threshold: 1,
                    type: 'TOTAL',
                    unstable: false,
                ]]
            );
            archiveArtifacts(artifacts: results_livestatus, followSymlinks: false);
            archiveArtifacts(artifacts: results_core, followSymlinks: false);
        }
    }
}

return this;
