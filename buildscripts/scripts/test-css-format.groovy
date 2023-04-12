#!groovy

/// file: test-css-format.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("make -C tests test-format-css-docker");
        }

        stage("Analyse Issues") {
            publishIssues(
                issues: [scanForIssues( tool: esLint())],
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
