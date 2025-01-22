#!groovy

/// file: test-iwyu.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("make -C tests test-iwyu-docker");
        }

        stage("Analyse Issues") {
            publishIssues(
                issues: [scanForIssues(tool: clang())],
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
