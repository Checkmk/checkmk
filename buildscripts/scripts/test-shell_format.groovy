def main() {
    /*
    properties([
        pipelineTriggers([pollSCM('H/3 * * * *')]),
    ])

    stage("Execute Test") {
        sh("make -C $WORKSPACE/tests test-format-shell")
    }

    stage("Analyse Issues") {
        def CLANG = scanForIssues tool: clang()
        publishIssues(
            issues:[CLANG],
            trendChartType: 'TOOLS_ONLY',
            qualityGates: [[threshold: 1, type: 'TOTAL', unstable: false]],
        );
    }
    */
}
return this;

