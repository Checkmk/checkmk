#!groovy

/// test-python3-typing.groovy

def main() {
    stage("Execute Test") {
        sh("""
            MYPY_ADDOPTS='--cobertura-xml-report=$WORKSPACE/mypy_reports --html-report=$WORKSPACE/mypy_reports/html' \
            make -C $checkout_dir/tests test-mypy-docker
           """);
    }

    stage("Archive reports") {
        archiveArtifacts(artifacts: "mypy_reports/**");
    }

    stage("Analyse Issues") {
        publishIssues(
            issues:[scanForIssues(tool: clang())],
            trendChartType: 'TOOLS_ONLY',
            qualityGates: [
                [
                    threshold: 1,
                    type: 'TOTAL',
                    unstable: false,
                ]
            ]
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
return this;

