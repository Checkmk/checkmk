def NODE = "linux"

properties([
  buildDiscarder(logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '7', numToKeepStr: '14')),
  pipelineTriggers([upstream('pylint3')]),
])

timeout(time: 12, unit: 'HOURS') {
    node (NODE) {
        stage('checkout sources') {
            checkout(scm)
            notify = load 'buildscripts/scripts/lib/notify.groovy'
        }
        try {
            stage("Execute Test") {
                sh("""MYPY_ADDOPTS='--cobertura-xml-report=$WORKSPACE/mypy_reports --html-report=$WORKSPACE/mypy_reports/html' \
                      make -C $WORKSPACE/tests test-mypy-docker
                   """)
            }
            stage("Archive reports") {
                archiveArtifacts(artifacts: "mypy_reports/**")
            }
            stage("Analyse Issues") {
                publishIssues(
                    issues:[scanForIssues(tool: clang())],
                    trendChartType: 'TOOLS_ONLY',
                    qualityGates: [
                        [
                            threshold: 1,
                            type: 'TOTAL',
                            unstable: false
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
                    reportTitles: ''
                ])
            }
        } catch(Exception e) {
            notify.notify_error(e)
        }
    }
}
