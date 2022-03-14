def NODE = "linux"

properties([
  buildDiscarder(logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '7', numToKeepStr: '14')),
  pipelineTriggers([pollSCM('H/3 * * * *')]),
])

timeout(time: 12, unit: 'HOURS') {
    node (NODE) {
        stage('checkout sources') {
            checkout(scm)
            notify = load 'buildscripts/scripts/lib/notify.groovy'
        }
        try {
            stage("Execute Test") {
                sh("make -C $WORKSPACE/tests test-format-shell")
            }
            stage("Analyse Issues") {
                def CLANG = scanForIssues tool: clang()
                publishIssues issues:[CLANG], trendChartType: 'TOOLS_ONLY', qualityGates: [[threshold: 1, type: 'TOTAL', unstable: false]]
            }
        } catch(Exception e) {
            notify.notify_error(e)
        }
    }
}
