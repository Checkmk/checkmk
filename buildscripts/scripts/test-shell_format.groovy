#!groovy

/// file: test-shell_format.groovy

def main() {
    stage('Check shell format') {
        dir("${checkout_dir}") {
            sh("make -C tests test-format-shell")
        }
    }
    stage("Analyse Issues") {
        publishIssues(
            issues:[scanForIssues(tool: clang())],
            trendChartType: 'TOOLS_ONLY',
            qualityGates: [[
                threshold: 1,
                type: 'TOTAL',
                unstable: false,
            ]],
        );
    }
}

return this;
