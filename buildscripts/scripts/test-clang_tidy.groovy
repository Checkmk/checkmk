#!groovy

/// file: test-clang_tidy.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("make -C tests test-tidy-docker");
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
