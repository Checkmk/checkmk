#!groovy

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
        stage("Analyse Issues") {
            xunit([GoogleTest(
                deleteOutputFiles: true,
                failIfNotNew: true,
                pattern: 'livestatus/src/test_detail.xml, enterprise/core/src/test_detail.xml',
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
        }
    }
}
return this;
