def NODE = "linux"

properties([
  buildDiscarder(logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '7', numToKeepStr: '14')),
  pipelineTriggers([pollSCM('H/2 * * * *')]),
])

timeout(time: 12, unit: 'HOURS') {
    node (NODE) {
        stage('checkout sources') {
            checkout(scm)
            notify = load 'buildscripts/scripts/lib/notify.groovy'
        }
        try {
            stage("Execute Test") {
                sh("make compile-neb-cmc-docker")
            }
            stage("Analyse Issues") {
                def GCC = scanForIssues tool: gcc()
                publishIssues issues:[GCC], trendChartType: 'TOOLS_ONLY', qualityGates: [[threshold: 1, type: 'TOTAL', unstable: false]]
            }
        } catch(Exception e) {
            notify.notify_error(e)
        }
    }
}
