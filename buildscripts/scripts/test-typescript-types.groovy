#!groovy

/// file: test-typescript-types.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("make -C tests test-typescript-types-docker");
        }

        stage("Analyse Issues") {
            publishIssues(
                issues: [scanForIssues( tool: tsLint())],
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
