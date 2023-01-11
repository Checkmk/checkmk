#!groovy

/// file: test-python3-typing.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("""
                MYPY_ADDOPTS='--cobertura-xml-report=$checkout_dir/mypy_reports' \
                make -C tests test-mypy-docker
               """);
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
    }
}
return this;
