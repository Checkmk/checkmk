#!groovy

/// file: test-unit-test-cores.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute CMC Test") {
            dir("enterprise/core/src/test") {
                sh("./.f12");
            }
        }
        def results_core="enterprise/core/src/test_detail_core.xml"

        stage("Analyse Issues") {
            xunit([GoogleTest(
                deleteOutputFiles: true,
                failIfNotNew: true,
                pattern: "${results_core}",
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
            archiveArtifacts(artifacts: results_core, followSymlinks: false);
        }
    }
}
return this;
