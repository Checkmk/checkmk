#!groovy

/// file: test-python3-typing.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            // catch any error, set stage + build result to failure,
            // but continue in order to execute the publishIssues function
            catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                sh("""
                    MYPY_ADDOPTS='--cobertura-xml-report=$checkout_dir/mypy_reports --html-report=$checkout_dir/mypy_reports/html' \
                    make -C tests test-mypy-docker
                   """);
            }
        }

        stage("Archive reports") {
            archiveArtifacts(artifacts: "mypy_reports/**");
        }

        stage("Analyse Issues") {
            publishIssues(
                issues:[scanForIssues(tool: clang())],
                trendChartType: 'TOOLS_ONLY',
                qualityGates: [[
                    threshold: 1,
                    type: 'TOTAL',
                    unstable: false,
                ]]
            )
        }

        stage("Publish coverage") {
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: false,
                keepAll: true,
                reportDir: 'mypy_reports/html',
                reportFiles: 'index.html',
                reportName: 'Typing coverage',
                reportTitles: '',
            ])
        }
    }
}

return this;
