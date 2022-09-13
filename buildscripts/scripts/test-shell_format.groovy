#!groovy

/// test-shell_format.groovy

def main() {
    stage('Check shell format') {
        dir("${checkout_dir}") {
            docker_image_from_alias("IMAGE_TESTING").inside("--ulimit nofile=1024:1024 --init") {
                sh("make -C tests test-format-shell")
            }
        }
    }
    stage("Analyse Issues") {
        publishIssues(
            issues:[scanForIssues(tool: clang())],
            trendChartType: 'TOOLS_ONLY',
            qualityGates: [[threshold: 1, type: 'TOTAL', unstable: false]],
        );
    }
}
return this;


