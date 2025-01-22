#!groovy

/// file: test-compile_cores.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("make compile-neb-cmc-docker");
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
