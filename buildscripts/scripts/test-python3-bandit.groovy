#!groovy

/// file: test-python3-bandit.groovy

def main() {
    try {
        stage('run Bandit') {
            dir("${checkout_dir}") {
                sh("BANDIT_OUTPUT_ARGS=\"-f xml -o '$WORKSPACE/bandit_results.xml'\" make -C tests test-bandit");
            }
        }
    } finally {
        stage("Archive / process test reports") {
            show_duration("archiveArtifacts") {
                archiveArtifacts("bandit_results.xml");
            }
            xunit([Custom(
                customXSL: "$JENKINS_HOME/userContent/xunit/JUnit/0.1/bandit-xunit.xsl",
                deleteOutputFiles: true,
                failIfNotNew: true,
                pattern: "bandit_results.xml",
                skipNoTestFiles: false,
                stopProcessingIfError: true
            )]);
        }
    }
    stage('check nosec markers') {
        try {
            dir("${checkout_dir}") {
                sh("make -C tests test-bandit-nosec-markers");
            }
        } catch(Exception) {    // groovylint-disable EmptyCatchBlock
            // Don't fail the job if un-annotated markers are found.
            // Security will have to take care of those later.
            // TODO: once we have a green baseline, mark unstable if new un-annotated markers have been added:
            // unstable("failed to validate nosec marker annotations");
        }
    }
}

return this;
