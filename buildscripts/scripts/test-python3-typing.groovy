#!groovy

/// file: test-python3-typing.groovy

def main() {
    dir("${checkout_dir}") {
        stage("Execute Test") {
            sh("""
                MYPY_ADDOPTS='--no-color-output --junit-xml mypy.xml' make -C tests test-mypy-docker
            """);
        }

        stage("Analyse Issues") {
            publishIssues(
                issues:[scanForIssues(
                    tool: myPy(
                        pattern: "mypy.xml",
                    )
                )],
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
